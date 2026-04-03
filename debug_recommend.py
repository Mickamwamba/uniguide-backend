
import os
from dotenv import load_dotenv
import django

load_dotenv()

# Setup Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Now import models
import google.generativeai as genai
from pgvector.django import CosineDistance
from universities.models import Programme

def debug_recommend():
    print("Debugging Recommendation Logic...")
    
    interests = "I want to study computer science"
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found.")
        return

    print(f"API Key found (length: {len(api_key)})")
    genai.configure(api_key=api_key)

    try:
        print("1. Generating Embedding...")
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=interests,
            task_type="retrieval_query"
        )
        user_embedding = result['embedding']
        print(f"   Embedding generated. Length: {len(user_embedding)}")
        
        print("2. Performing Vector Search...")
        # This is likely where it fails if pgvector isn't set up
        matches = Programme.objects.order_by(CosineDistance('embedding', user_embedding))[:5]
        
        print(f"   Query executed. Found {len(matches)} matches.")
        for m in matches:
            print(f"   - {m.name}")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_recommend()
