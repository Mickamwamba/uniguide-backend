
import os
import time
import google.generativeai as genai
from django.core.management.base import BaseCommand
from universities.models import Programme
from dotenv import load_dotenv

load_dotenv()

class Command(BaseCommand):
    help = 'Generates vector embeddings for Programmes using Gemini text-embedding-004.'

    def handle(self, *args, **options):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY not found."))
            return

        genai.configure(api_key=api_key)
        
        # Select programmes without embeddings or force update
        # For now, let's just get all and we can optimize later
        programmes = Programme.objects.all()
        
        self.stdout.write(f"Found {programmes.count()} programmes.")
        
        count = 0
        batch_size = 10
        
        for prog in programmes:
            # Construct text blob
            # Combine relevant fields to create a semantic representation
            text_blob = f"""
            Programme: {prog.name}
            University: {prog.university.name if prog.university else 'Unknown'}
            Award Level: {prog.award_level}
            Study Mode: {prog.study_mode}
            Description: {prog.description}
            Framework: {prog.qualification_framework}
            """
            
            try:
                # Generate embedding
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text_blob,
                    task_type="retrieval_document",
                    title=f"{prog.name} at {prog.university.name if prog.university else ''}"
                )
                
                embedding = result['embedding']
                
                # Verify dimension
                if len(embedding) != 768:
                    self.stdout.write(self.style.WARNING(f"Warning: Embedding dim is {len(embedding)}, expected 768"))
                
                prog.embedding = embedding
                prog.save()
                
                count += 1
                if count % 10 == 0:
                    self.stdout.write(f"Processed {count} programmes...")
                    time.sleep(1) # Rate limit kindness
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to embed {prog.name}: {e}"))
                time.sleep(2)

        self.stdout.write(self.style.SUCCESS(f"Successfully generated embeddings for {count} programmes."))
