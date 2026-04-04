from django.core.management.base import BaseCommand
from universities.models import University, Programme, Course
from django.db.models import Count

class Command(BaseCommand):
    help = 'Audits the database for courses missing from programmes'

    def handle(self, *args, **options):
        unis = University.objects.annotate(prog_count=Count('programmes')).filter(prog_count__gt=0)
        self.stdout.write("--- Audit Report: Universities with Empty Course Lists ---")
        
        for uni in unis:
            progs = Programme.objects.filter(university=uni).annotate(course_count=Count('courses'))
            empty_progs = progs.filter(course_count=0)
            
            if empty_progs.exists():
                self.stdout.write(f"\n{uni.name}:")
                self.stdout.write(f"  Total Programmes: {progs.count()}")
                self.stdout.write(f"  Programmes with ZERO courses: {empty_progs.count()}")
                
                # Show up to 3 examples
                for p in empty_progs[:3]:
                    self.stdout.write(f"    - {p.name}")
        
        self.stdout.write("\nDone.")
