import os
import time
import json
import re
from django.core.management.base import BaseCommand
from universities.models import University, Programme, Course
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class Command(BaseCommand):
    help = 'Ingests UDSM prospectus PDF and extracts course details using Gemini 1.5 Flash.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Limit number of programmes to process (0 for all)')
        parser.add_argument('--programme', type=str, help='Process a specific programme by name (partial match)')

    def handle(self, *args, **options):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY not found."))
            return

        genai.configure(api_key=api_key)
        
        # 1. Find UDSM
        try:
            udsm = University.objects.get(name__icontains="University of Dar es Salaam")
        except University.DoesNotExist:
            self.stdout.write(self.style.ERROR("University of Dar es Salaam not found in DB."))
            return
        except University.MultipleObjectsReturned:
            udsm = University.objects.filter(name__icontains="University of Dar es Salaam").first()
            self.stdout.write(self.style.WARNING(f"Multiple UDSM found, using: {udsm.name}"))

        self.stdout.write(f"Target University: {udsm.name}")

        # 2. Upload PDF
        pdf_path = 'udsm.pdf'
        if not os.path.exists(pdf_path):
            self.stdout.write(self.style.ERROR(f"PDF not found at {pdf_path}"))
            return

        self.stdout.write("Uploading PDF to Gemini...")
        try:
            sample_file = genai.upload_file(path=pdf_path, display_name="UDSM Prospectus")
            self.stdout.write(f"Uploaded file: {sample_file.name}")
            
            # Wait for processing
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

        # 3. Get Programmes
        # Filter for Bachelor programmes only as per user request
        programmes = Programme.objects.filter(university=udsm, award_level__icontains="Bachelor")
        if options['programme']:
            programmes = programmes.filter(name__icontains=options['programme'])
        
        # Filter out ones already seemingly enriched? (Optional, but user said 'for each course' so maybe we re-run)
        # For now, let's just create courses.
        
        if options['limit'] > 0:
            programmes = programmes[:options['limit']]
        
        model = genai.GenerativeModel(model_name="gemini-flash-latest")

        self.stdout.write(f"Processing {programmes.count()} programmes...")

        for prog in programmes:
            self.process_programme(model, sample_file, prog)
            time.sleep(4) # Rate limit buffer

    def process_programme(self, model, pdf_file, programme):
        self.stdout.write(f"Extracting for: {programme.name}...")
        
        prompt = f"""
        You are an expert data extraction agent.
        I will provide a university prospectus PDF.
        Identify the specific section for the programme: "{programme.name}".
        
        Task:
        1. Extract the **Programme Description** (a brief summary of what the course is about).
        2. Extract the **List of Courses** offered in this programme, organized by **Year** and **Semester**.
        
        Output JSON Format:
        {{
            "description": "The programme description text...",
            "structure": [
                {{
                    "year": 1,
                    "semester": 1,
                    "courses": [
                        {{ "code": "CS 101", "name": "Introduction to Computer Science", "credits": 3 }}
                    ]
                }}
            ]
        }}
        
        Constraints:
        - Only return valid JSON. Do not use markdown blocks.
        - If the exact programme name isn't found, look for variations (e.g., "BSc in CS" vs "Bachelor of Science in Computer Science").
        - If not found at all, return {{ "error": "Programme not found" }}.
        """

        try:
            response = model.generate_content([prompt, pdf_file])
            text = response.text.strip()
            
            # Clean markdown if present
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            data = json.loads(text)
            
            if "error" in data:
                self.stdout.write(self.style.WARNING(f"  Result: {data['error']}"))
                return

            # Update Programme
            if data.get("description"):
                programme.description = data["description"]
                programme.save()
                self.stdout.write(f"  Updated description.")

            # Create Courses
            count = 0
            for year_data in data.get("structure", []):
                year = year_data.get("year", 1)
                semester = year_data.get("semester", 1)
                
                for course_data in year_data.get("courses", []):
                    code = course_data.get("code", "N/A")
                    name = course_data.get("name", "Unknown Course")
                    credits_val = course_data.get("credits", 0)
                    
                    # Convert credits to int if possible
                    try:
                        credits_val = int(float(str(credits_val).split()[0])) # Handle "3 credits" or "3.0"
                    except:
                        credits_val = 0

                    Course.objects.update_or_create(
                        programme=programme,
                        code=code,
                        defaults={
                            'name': name,
                            'semester': semester, # We might need to map Year/Sem to a single integer or store Year separately? 
                                                  # Model says 'semester' (int). Let's use 1, 2, 3, 4 etc relative to programme or just 1/2?
                                                  # Usually users want "Year 1 Sem 1". 
                                                  # If model only has semester, I'll store (Year-1)*2 + Sem.
                            'credits': credits_val,
                            'description': f"Year {year}, Semester {semester}" # Store context in description for now
                        }
                    )
                    count += 1
            
            self.stdout.write(self.style.SUCCESS(f"  Ingested {count} courses."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error: {e}"))
