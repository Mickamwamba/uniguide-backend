import os
import time
import json
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from universities.models import University, Programme, Course, AdmissionRequirement

from google import genai
from google.genai import types

from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

PDF_MAPPING = {
    'prospectuses/udsm.pdf': 'University of Dar es Salaam',
    'prospectuses/mzumbe.pdf': 'Mzumbe University',
}

class Command(BaseCommand):
    help = 'Ingests university prospectus PDFs, extracts course details concurrently using the modern google.genai SDK.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Limit number of programmes to process per university (0 for all)')
        parser.add_argument('--programme', type=str, help='Process a specific programme by name (partial match)')
        parser.add_argument('--file', type=str, help='Specific PDF file to process (must be in backend/)')
        parser.add_argument('--university', type=str, help='Specific University name (if using --file)')
        parser.add_argument('--workers', type=int, default=3, help='Number of concurrent threads (default: 3)')

    def handle(self, *args, **options):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY not found."))
            return

        client = genai.Client(api_key=api_key)
        
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
            self.process_university(filename, uni_name, options, client)

    def scrape_website(self, url):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'
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

    def process_university(self, pdf_path, uni_name_query, options, client):
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
        
        self.stdout.write("Uploading PDF to Gemini using new SDK...")
        try:
            sample_file = client.files.upload(file=pdf_path)
            
            while "PROCESSING" in str(sample_file.state):
                print(".", end="", flush=True)
                time.sleep(2)
                sample_file = client.files.get(name=sample_file.name)
            
            if "FAILED" in str(sample_file.state):
                self.stdout.write(self.style.ERROR("File processing failed."))
                return
                
            self.stdout.write(self.style.SUCCESS("PDF Ready."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Upload failed: {e}"))
            return

        # Generate University Overview & Global Description
        self.generate_university_overview(client, sample_file, uni, website_text)

        programmes = Programme.objects.filter(university=uni, name__icontains='Bachelor')
        if options['programme']:
            programmes = programmes.filter(name__icontains=options['programme'])
        
        if options['limit'] > 0:
            programmes = programmes[:options['limit']]

        max_workers = options.get('workers', 3)
        self.stdout.write(self.style.MIGRATE_HEADING(f"Processing {programmes.count()} programmes concurrently using {max_workers} threads..."))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.process_programme_with_retry, client, sample_file, prog): prog for prog in programmes}
            for future in as_completed(futures):
                prog = futures[future]
                try:
                    future.result()
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"Unhandled thread exception for {prog.name}: {exc}"))

    def process_programme_with_retry(self, client, pdf_file, programme, max_retries=5):
        base_delay = 10
        for attempt in range(max_retries):
            try:
                self.process_programme(client, pdf_file, programme)
                return True
            except Exception as e:
                error_msg = str(e).lower()
                if '429' in error_msg or 'quota' in error_msg or 'exhausted' in error_msg or 'internal' in error_msg or '503' in error_msg:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 2)
                    self.stdout.write(self.style.WARNING(f"  [Rate Limit for {programme.name}] Retrying in {delay:.1f}s (Attempt {attempt+1}/{max_retries})..."))
                    time.sleep(delay)
                else:
                    self.stdout.write(self.style.ERROR(f"  [Fatal Error {programme.name}]: {e}"))
                    return False
                    
        self.stdout.write(self.style.ERROR(f"  [Failed] Max retries reached for {programme.name}."))
        return False

    def generate_university_overview(self, client, pdf_file, uni, website_text):
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
            "overview": "A high-value ~150 word summary of the university.",
            "description": "A more detailed history/background of the institution.",
            "location": "List of cities or regions where campuses are located, if found."
        }}
        
        Constraints: Only return valid JSON. Do not use markdown blocks. Use an empty string "" if completely unknown.
        """

        try:
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=[prompt, pdf_file]
            )
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

    def process_programme(self, client, pdf_file, programme):
        self.stdout.write(f"Extracting for: {programme.name}...")
        
        prompt = f"""
        You are an expert data extraction agent.
        Identify the specific section for the programme: "{programme.name}" in the attached prospectus.
        
        Output JSON Format:
        {{
            "description": "A comprehensive summary of what the programme entails. If the prospectus does not explicitly provide a summary paragraph, synthesize a highly relevant 2-sentence description based on the programme name, career outlooks, and courses.",
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
        - For Admission Requirements: If explicitly NOT mentioned in text, set values to null. Do NOT hallucinate.
        - For Course `description`, `objectives`, and `career_outlooks`: If the prospectus lacks explicit text, you ARE authorized to intelligently synthesize highly relevant content based entirely on the programme or course title. However, if you do synthesize them, you MUST prefix the associated strings with "[AI Auto-Generated] ".
        - `min_points` should be a float if found, otherwise null.
        - If the exact programme name isn't found, look for variations. If not found at all, return {{ "error": "Programme not found" }}.
        """

        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=[prompt, pdf_file]
        )
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

        adm = data.get("admission_requirements", {})
        if adm:
            desc = adm.get("description")
            if desc: 
                min_pts = adm.get("min_points")
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

        careers = data.get("career_outlooks")
        if careers and isinstance(careers, list):
            programme.career_outlooks = careers
            programme.save()

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
        
        self.stdout.write(self.style.SUCCESS(f"  Ingested {count} courses for {programme.name}."))
