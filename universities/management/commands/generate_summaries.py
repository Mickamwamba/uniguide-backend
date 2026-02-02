import os
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import models
from universities.models import University
import google.generativeai as genai
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Command(BaseCommand):
    help = 'Generates AI summaries for universities using their website content.'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='Process a specific university by ID')
        parser.add_argument('--limit', type=int, default=0, help='Limit the number of universities to process')
        parser.add_argument('--force', action='store_true', help='Overwrite existing overviews')

    def handle(self, *args, **options):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.WARNING("GEMINI_API_KEY not found in environment variables. Using dummy generation mode?"))
            # For now, let's warn and return, or we could ask user. 
            # But per plan, I should implement the real thing.
            # I'll implement it such that it fails gracefully or I can patch it if I need to simulate.
            self.stdout.write(self.style.ERROR("Please set GEMINI_API_KEY in your .env file."))
            
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-flash-latest')

        universities = University.objects.all()
        
        if options['id']:
            universities = universities.filter(id=options['id'])
        
        if not options['force']:
            # Skip ones that already have a valid overview
            universities = universities.filter(models.Q(overview="") | models.Q(overview__startswith="AI Summary unavailable"))

        if options['limit']:
            universities = universities[:options['limit']]

        count = universities.count()
        self.stdout.write(f"Processing {count} universities...")

        for uni in universities:
            self.stdout.write(f"Processing {uni.name} ({uni.website})...")
            
            if not uni.website:
                self.stdout.write(self.style.WARNING(f"Skipping {uni.name}: No website URL"))
                continue

            try:
                # 1. Scrape Website
                text_content = self.scrape_website(uni.website)
                if not text_content:
                    self.stdout.write(self.style.WARNING(f"Could not extract text from {uni.website}"))
                    continue

                # 2. Generate Summary
                if api_key:
                    summary = self.generate_summary(model, uni.name, text_content)
                    if summary:
                        uni.overview = summary
                        uni.save()
                        self.stdout.write(self.style.SUCCESS(f"Saved overview for {uni.name}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"Failed to generate summary for {uni.name} - Using fallback"))
                        uni.overview = f"AI Summary unavailable: Could not generate summary for {uni.name} due to API limits. (Try again later)"
                        uni.save()
                    
                    # Rate limiting
                    time.sleep(2) 
                else:
                    self.stdout.write(self.style.WARNING(f"dry-run: scraped {len(text_content)} chars from {uni.website}, but no API key to generate."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {uni.name}: {str(e)}"))

    def scrape_website(self, url):
        """Scrapes text content from the homepage and potential 'About' pages."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15, verify=False) # verify=False for some TZ uni certs
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove scripts, styles, etc.
            for script in soup(["script", "style", "nav", "footer", "iframe"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator=' ')
            
            # Simple cleaning
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Truncate to reasonable context window (e.g., 20k chars)
            return text[:20000]
        except Exception as e:
            print(f"Scraping error for {url}: {e}")
            return None

    def generate_summary(self, model, uni_name, context, retries=3):
        prompt = f"""
You are an expert educational consultant helping students choose a university in Tanzania.
I will provide you with text scraped from the website of "{uni_name}".
Analyze the content and strictly ignore any navigation menus, footers, or irrelevant text like copyright notices.

Summarize key details into a single, high-value paragraph (approx. 150 words) for a first-time prospective student.
Focus strictly on:
1.  **Location & Setting**: Where is it? What is the region/city like (briefly)?
2.  **Type & Scale**: Is it a large public university or a specialized private college?
3.  **Key Offerings**: What are its flagship faculties or unique programmes?
4.  **Student Experience**: Mention campus life, accommodation, or specific status (e.g., "chartered", "accredited") if available.

Tone: Professional, welcoming, and informative.
Constraint: Do NOT invent information. If specific details (like weather or campus life) are missing from the text, focus on the academic profile and location.

Website Content:
{context}
        """
        for attempt in range(retries):
            try:
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                if "429" in str(e):
                    wait_time = (2 ** attempt) * 20 # 20s, 40s, 80s
                    print(f"Rate limit hit. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Gemini generation error: {e}")
                    return None
        return None
