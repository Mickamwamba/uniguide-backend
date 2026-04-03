from django.core.management.base import BaseCommand
from universities.scrapers.tcu import TCUScraper
from universities.models import University, Programme

class Command(BaseCommand):
    help = 'Unified ingestion: Fetch universities, metadata, and programmes from TCU website'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-all', 
            action='store_true', 
            help='Delete all existing data before ingesting'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Starting unified ingestion process..."))
        
        if options['delete_all']:
            self.stdout.write(self.style.WARNING("Deleting existing data for a fresh ingest..."))
            Programme.objects.all().delete() 
            University.objects.all().delete()
        else:
            self.stdout.write("Updating existing entries and adding new ones (no deletion)...")
        
        scraper = TCUScraper()
        
        # 1. Fetch Universities and their Metadata
        self.stdout.write(self.style.MIGRATE_HEADING("Phase 1: Ingesting Universities and Metadata"))
        uni_count = 0
        for uni_data in scraper.fetch_universities_metadata():
            University.objects.update_or_create(
                name=uni_data['name'],
                defaults={
                    'head_office': uni_data.get('head_office', ''),
                    'university_type': uni_data.get('university_type', ''),
                    'status': uni_data.get('status', ''),
                    'address': uni_data.get('address', ''),
                    'email': uni_data.get('email', ''),
                    'website': uni_data.get('website', ''),
                    'accreditation_status': uni_data.get('accreditation_status', ''),
                    'registration_no': uni_data.get('registration_no', '')
                }
            )
            uni_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully ingested {uni_count} universities.'))

        # 2. Fetch Programmes
        self.stdout.write(self.style.MIGRATE_HEADING("Phase 2: Ingesting Programmes"))
        total_count = 0
        for batch in scraper.fetch_programmes():
            self.stdout.write(f"Processing batch of {len(batch)} programmes...")
            
            for data in batch:
                uni_name = data['university_name']
                prog_name = data['programme_name']
                
                # We use get_or_create to gracefully handle universities that were only found on the programmes site
                university, created = University.objects.get_or_create(name=uni_name)
                
                if created:
                    self.stdout.write(self.style.WARNING(f"Sub-note: Created fallback University '{uni_name}' because it was absent from metadata site."))

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
            self.stdout.write(f"Total programmes processed so far: {total_count}")
            
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {total_count} programmes. Ingestion complete.'))
