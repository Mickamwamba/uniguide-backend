from django.core.management.base import BaseCommand
from universities.models import Programme
from django.db.models import Count

class Command(BaseCommand):
    help = 'Count empty bachelor programmes'

    def handle(self, *args, **options):
        # 1. strictly filter for Bachelor
        bachelors = Programme.objects.filter(name__icontains='Bachelor')
        bachelors_with_counts = bachelors.annotate(course_count=Count('courses'))
        
        # 2. total bachelors
        total_bachelors = bachelors_with_counts.count()
        if total_bachelors == 0:
            self.stdout.write("No bachelor programmes found.")
            return
            
        # 3. empty bachelors
        failed_bachelors = bachelors_with_counts.filter(course_count=0)
        total_failed = failed_bachelors.count()
        
        self.stdout.write(f"Total Bachelor Programmes in TCU DB: {total_bachelors}")
        self.stdout.write(f"Bachelor Programmes that FAILED to extract courses: {total_failed}")
        self.stdout.write(f"Success Rate: {((total_bachelors - total_failed) / total_bachelors * 100):.1f}%")
        
        # Breakdown by university
        self.stdout.write("\nTop 10 Universities with highest failure counts for Bachelors:")
        unis = failed_bachelors.values('university__name').annotate(failed=Count('id')).order_by('-failed')[:10]
        for u in unis:
            self.stdout.write(f" - {u['university__name']}: {u['failed']} failed bachelor programmes")
