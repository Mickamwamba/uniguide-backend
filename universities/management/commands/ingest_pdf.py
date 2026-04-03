import os
import time
import json
import re
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from universities.models import University, Programme, Course, AdmissionRequirement, CareerOutlook
import google.generativeai as genai
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

PDF_MAPPING = {
    'udsm.pdf': 'University of Dar es Salaam',
    'mzumbe.pdf': 'Mzumbe University',
}

class Command(BaseCommand):
    help = 'Ingests university prospectus PDFs, extracts course details, and generates enriched overviews using Gemini 1.5 Flash.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Limit number of programmes to process per university (0 for all)')
        parser.add_argument('--programme', type=str, help='Process a specific programme by name (partial match)')
        parser.add_argument('--file', type=str, help='Specific PDF file to process (must be in backend/)')
        parser.add_argument('--university', type=str, help='Specific University name (if using --file)')

    def handle(self, *args, **options):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY not found."))
            return

        genai.configure(api_key=api_key)
        
        targets = []
        if options['file'] and options['university']:
            targets.append((options['file'], options['university']))
        elif options['file'] or options['university']:
            self.stdout.write(self.style.ERROR("If specifying --file or --university, you must provide BOTH."))
            return
        else:
            for filename, uni_name in PDF_MAPPING.items():
                if os.path.exists(filename):
                    targets.append((filename, uni_name))
                else:
                    self.stdout.write(self.style.WARNING(f"Skipping {filename} (not found)"))

        if not targets:
            self.stdout.write(self.style.WARNING("No valid targets found."))
            return

        for filename, uni_name in targets:
            self.process_university(filename, uni_name, options)

    def scrape_website(self, url):
        """Scrapes text content from the homepage."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for script in soup(["script", "style", "nav", "footer", "iframe"]):
                script.decompose()

            text = soup.get_text(separator=' ')
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text[:20000]
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Scraping error for {url}: {e}"))
            return ""

    def process_university(self, pdf_path, uni_name_query, options):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\nProcessing {uni_name_query} from {pdf_path}..."))
        
        try:
            uni = University.objects.get(name__icontains=uni_name_query)
        except University.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"University '{uni_name_query}' not found in DB."))
            return
        except University.MultipleObjectsReturned:
            uni = University.objects.filter(name__icontains=uni_name_query).first()
            self.stdout.write(self.style.WARNING(f"Multiple universities found, using: {uni.name}"))

        self.stdout.write(f"Target: {uni.name}")

        website_text = ""
        if uni.website:
            self.stdout.write(f"Scraping website: {uni.website}")
            website_text = self.scrape_website(uni.website)
        
        self.stdout.write("Uploading PDF to Gemini...")
        try:
            sample_file = genai.upload_file(path=pdf_path, display_name=f"{uni.name} Prospectus")
            
            while sample_file.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(2)
                sample_file = genai.get_file(sample_file.name)
            
            if sample_file.state.name == "FAILED":
                self.stdout.write(self.style.ERROR("File processing failed."))
                return
                
            self.stdout.write(self.style.SUCCESS("PDF Ready."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Upload failed: {e}"))
            return

        model = genai.GenerativeModel(model_name="gemini-3.0-pro") # Using Gemini 3.0 Pro for maximum accuracy

        # Generate University Overview & Global Description
        self.generate_university_overview(model, sample_file, uni, website_text)

        programmes = Programme.objects.filter(university=uni, award_level__icontains="Bachelor")
        if options['programme']:
            programmes = programmes.filter(name__icontains=options['programme'])
        
        if options['limit'] > 0:
            programmes = programmes[:options['limit']]

        self.stdout.write(f"Processing {programmes.count()} programmes...")

        for prog in programmes:
            self.process_programme(model, sample_file, prog)
            time.sleep(4)

    def generate_university_overview(self, model, pdf_file, uni, website_text):
        self.stdout.write("Generating University Overview and Context...")
        
        prompt = f"""
        You are an expert educational consultant.
        I am providing you with the university prospectus PDF and the scraped text from the university's website below.
        
        Website Scraped Text:
        ---
        {website_text}
        ---

        Task: Extract general university details combining both the PDF Prospectus and the Website text.
        
        Output JSON Format:
        {{
            "overview": "A high-value ~150 word summary of the university (Location, Type, Key Offerings, Campus Life).",
            "description": "A more detailed history/background of the institution.",
            "location": "List of cities or regions where campuses are located, if found."
        }}
        
        Constraints:
        - Only return valid JSON. Do not use markdown blocks.
        - If a specific field is entirely unknown, use an empty string "".
        """

        try:
            response = model.generate_content([prompt, pdf_file])
            text = response.text.strip()
            
            if text.startswith("```json"): text = text[7:]
            if text.endswith("```"): text = text[:-3]
            
            data = json.loads(text)
            
            if data.get("overview"): uni.overview = data["overview"]
            if data.get("description"): uni.description = data["description"]
            if data.get("location"): uni.location = data["location"]
            
            uni.save()
            self.stdout.write(self.style.SUCCESS(f"  Saved enriched overview and details for {uni.name}."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Failed to generate university overview: {e}"))

    def process_programme(self, model, pdf_file, programme):
        self.stdout.write(f"Extracting for: {programme.name}...")
        
        prompt = f"""
        You are an expert data extraction agent.
        Identify the specific section for the programme: "{programme.name}" in the attached prospectus.
        
        Output JSON Format:
        {{
            "description": "A brief summary of what the course is about...",
            "admission_requirements": {{
                "description": "Text describing general O-level/A-level requirements",
                "min_points": 4.0,
                "required_subjects": "Mathematics, Physics"
            }},
            "career_outlooks": [
                {{ "title": "Software Engineer", "description": "Develops software applications." }}
            ],
            "structure": [
                {{
                    "year": 1,
                    "semester": 1,
                    "courses": [
                        {{ 
                            "code": "CS 101", 
                            "name": "Introduction to Computer Science", 
                            "credits": 3,
                            "description": "Basic intro to CS",
                            "objectives": "Understand basic programming paradigms"
                        }}
                    ]
                }}
            ]
        }}
        
        Critical Constraints & Safety rules:
        - Only return valid JSON without markdown wrapping.
        - If details like admission requirements, required subjects, or career outlooks are NOT explicitly mentioned, set their values to null. Do NOT hallucinate data.
        - `min_points` should be a float if found, otherwise null.
        - If the exact programme name isn't found, look for variations. If not found at all, return {{ "error": "Programme not found" }}.
        """

        try:
            response = model.generate_content([prompt, pdf_file])
            text = response.text.strip()
            
            if text.startswith("```json"): text = text[7:]
            if text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR("  Failed to parse JSON response. Skipping."))
                return
            
            if "error" in data:
                self.stdout.write(self.style.WARNING(f"  Result: {data['error']}"))
                return

            if data.get("description"):
                programme.description = data["description"]
                programme.save()

            # Admission Requirements
            adm = data.get("admission_requirements", {})
            if adm:
                desc = adm.get("description")
                if desc: # Only create if there's actual data
                    min_pts = adm.get("min_points")
                    # handle possible strings in min_points safely
                    try:
                         if min_pts is not None: min_pts = float(min_pts)
                         else: min_pts = 0.0
                    except (ValueError, TypeError):
                         min_pts = 0.0

                    AdmissionRequirement.objects.update_or_create(
                        programme=programme,
                        defaults={
                            'description': desc,
                            'min_points': min_pts,
                            'required_subjects': adm.get("required_subjects") or ""
                        }
                    )

            # Career Outlooks
            careers = data.get("career_outlooks")
            if careers and isinstance(careers, list):
                CareerOutlook.objects.filter(programme=programme).delete() # clear old
                for career in careers:
                    if career and career.get("title"):
                        CareerOutlook.objects.create(
                            programme=programme,
                            title=career.get("title"),
                            description=career.get("description") or ""
                        )

            # Create Courses
            count = 0
            for year_data in data.get("structure", []):
                year = year_data.get("year", 1)
                semester = year_data.get("semester", 1)
                
                for course_data in year_data.get("courses", []):
                    code = course_data.get("code", "N/A")
                    name = course_data.get("name", "Unknown Course")
                    credits_val = course_data.get("credits", 0)
                    
                    try:
                        credits_str = str(credits_val).split()[0]
                        if credits_str.replace('.', '', 1).isdigit():
                             credits_val = int(float(credits_str))
                        else:
                             credits_val = 0
                    except:
                        credits_val = 0

                    c_desc = course_data.get("description") or ""
                    c_obj = course_data.get("objectives") or ""

                    Course.objects.update_or_create(
                        programme=programme,
                        code=code,
                        defaults={
                            'name': name,
                            'semester': semester,
                            'year': year,
                            'credits': credits_val,
                            'description': c_desc,
                            'objectives': c_obj
                        }
                    )
                    count += 1
            
            self.stdout.write(self.style.SUCCESS(f"  Ingested {count} courses, updated admission & career profiles."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error: {e}"))
