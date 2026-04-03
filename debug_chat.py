
import os
from dotenv import load_dotenv
import django

load_dotenv()

# Setup Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import google.generativeai as genai
from pgvector.django import CosineDistance
from universities.models import Programme

def debug_chat():
    print("Debugging Chat Logic...")
    
    message = "Tell me about computer science"
    history = [
        {"role": "model", "parts": [{"text": "Hi! I am your UniGuide AI Advisor."}]}
    ]
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found.")
        return

    print(f"API Key found.")
    genai.configure(api_key=api_key)

    try:
        print("1. Generating Embedding...")
        embed_result = genai.embed_content(
            model="models/text-embedding-004",
            content=message,
            task_type="retrieval_query"
        )
        query_vector = embed_result['embedding']
        print(f"   Embedding generated. Length: {len(query_vector)}")

        print("2. Vector Search...")
        matches = Programme.objects.order_by(CosineDistance('embedding', query_vector))[:5]
        print(f"   Found {len(matches)} matches.")
        
        context_pieces = []
        for p in matches:
            info = f"- Programme: {p.name} at {p.university.name if p.university else 'Unknown University'}\n"
            info += f"  Award: {p.award_level}, Mode: {p.study_mode}\n"
            info += f"  Description: {p.description[:300]}..." 
            context_pieces.append(info)
        context_str = "\n".join(context_pieces)
        print("   Context prepared.")

        print("3. Generating Response...")
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        system_instruction = "You are a helpful assistant."
        full_prompt = f"{system_instruction}\n\nCONTEXT:\n{context_str}\n\nQUESTION:\n{message}"
        
        # Test start_chat with history
        print("   Starting chat session with history...")
        chat_session = model.start_chat(history=history)
        
        print("   Sending message...")
        response_obj = chat_session.send_message(full_prompt)
        
        print("\nSUCCESS! Response:")
        print(response_obj.text[:100] + "...")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_chat()
