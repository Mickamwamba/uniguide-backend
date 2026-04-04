import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Supported EmbedContent models:")
for m in client.models.list():
    if getattr(m, 'supported_generation_methods', None):
         if "embedContent" in getattr(m, 'supported_generation_methods', []):
              print(m.name)
    elif getattr(m, 'supported_actions', None):
         if "embedContent" in getattr(m, 'supported_actions', []):
              print(m.name)
