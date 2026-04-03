import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Supported GenerateContent models:")
for m in client.models.list():
    if "generateContent" in getattr(m, 'supported_generation_methods', []) or "generateContent" in getattr(m, 'supported_actions', []):
        print(m.name)
