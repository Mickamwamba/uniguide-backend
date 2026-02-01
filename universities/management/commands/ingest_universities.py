from django.core.management.base import BaseCommand
from universities.scrapers.tcu import TCUScraper
from universities.models import University, Programme

class Command(BaseCommand):
    help = 'Ingest universities and programmes from TCU website'

    def handle(self, *args, **options):
        self.stdout.write("Starting ingestion process...")
        
        self.stdout.write("Deleting existing data...")
        Programme.objects.all().delete() 
        University.objects.all().delete()
        
        scraper = TCUScraper()
        
        # 1. Fetch programs (generator)
        total_count = 0
        for batch in scraper.fetch_programmes():
            self.stdout.write(f"Processing batch of {len(batch)} items...")
            
            for data in batch:
                uni_name = data['university_name']
                prog_name = data['programme_name']
                
                # 2. Get or Create University
                university, _ = University.objects.get_or_create(name=uni_name)
                
                # 3. Create or Update Programme
                Programme.objects.update_or_create(
                    university=university,
                    name=prog_name,
                    defaults={
                        'award_level': data['award_level'],
                        'duration_months': data['duration_months'],
                        'duration_years': data['duration_months'] / 12.0,
                        'qualification_framework': data['qualification_framework'],
                        'study_mode': data['study_mode']
                    }
                )
            
            total_count += len(batch)
            self.stdout.write(f"Total processed so far: {total_count}")
            
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {total_count} programmes.'))
