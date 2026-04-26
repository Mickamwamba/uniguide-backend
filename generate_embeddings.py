import os
import sys
import django
import json
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from universities.models import Programme
from google import genai
from dotenv import load_dotenv

load_dotenv()

def generate():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("MISSING GEMINI API KEY")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    missing = Programme.objects.filter(embedding__isnull=True).exclude(university=None)
    total = missing.count()
    print(f"Found {total} programmes missing AI descriptions and embeddings.")
    
    for i, p in enumerate(missing):
        print(f"[{i+1}/{total}] Processing {p.name} at {p.university.name}")
        
        prompt = f"""
        You are a Tanzanian university academic advisor.
        Write a 4-sentence beautiful but highly factual description summarizing the academic and practical focus of the programme: {p.name} offered at {p.university.name} in Tanzania.
        Then, list 3 highly specific realistic entry-level or junior career titles that graduates of this program in Tanzania can pursue.
        Respond in pure JSON using exactly this format:
        {{"description": "The description string here...", "career_outlooks": [ {{"title": "Career 1"}}, {{"title": "Career 2"}} ] }}
        """
        
        try:
            resp = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            raw_text = resp.text.strip()
            if raw_text.startswith("```json"): raw_text = raw_text[7:-3]
            elif raw_text.startswith("```"): raw_text = raw_text[3:-3]
            
            data = json.loads(raw_text.strip())
            p.description = data.get('description', '')
            p.career_outlooks = data.get('career_outlooks', [])
            
            # Now embed it using gemini-embedding-001 combining name, desc, and careers
            careers_str = ", ".join([c.get('title', '') for c in p.career_outlooks])
            embed_string = f"{p.name} at {p.university.name}. {p.description} Careers: {careers_str}"
            
            embed_result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=embed_string
            )
            
            p.embedding = embed_result.embeddings[0].values
            p.save()
            
            print(f"   -> Success! Saved description and {len(p.career_outlooks)} careers.")
        except Exception as e:
            print(f"   -> Error processing {p.name}: {e}")
        
        time.sleep(1) # Prevent rapid rate limiting

if __name__ == '__main__':
    generate()
