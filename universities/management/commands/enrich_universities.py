from django.core.management.base import BaseCommand
from universities.scrapers.university_metadata import UniversityMetadataScraper

class Command(BaseCommand):
    help = 'Enrich university data with metadata (Address, Status, etc) from TCU registry'

    def handle(self, *args, **options):
        self.stdout.write("Starting University Metadata Enrichment...")
        try:
            scraper = UniversityMetadataScraper()
            scraper.scrape_metadata()
            self.stdout.write(self.style.SUCCESS("University Metadata Enrichment Complete."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error during enrichment: {e}"))
