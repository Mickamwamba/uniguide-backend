import os
import django
import sys
from dotenv import load_dotenv

sys.path.append('/Users/michaelkimollo/DSProjects/uniguide/uniguide-web/backend')
load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from universities.models import University, Programme
from django.db.models import Count

print("=== Audit of Failed Course Extractions per University ===") 

universities = University.objects.all()

for uni in universities:
    # Annotate programmes with their course count. Filter for Bachelor degrees only to avoid Master's/PhD noise.
    programmes = Programme.objects.filter(university=uni, name__icontains='Bachelor').annotate(course_count=Count('courses'))
    
    total_progs = programmes.count()
    if total_progs == 0:
        continue
        
    succeeded_progs = programmes.filter(course_count__gt=0).count()
    failed_progs = programmes.filter(course_count=0)
    failed_count = failed_progs.count()
    
    # We only care about universities that had AT LEAST ONE successful extraction 
    # (meaning we definitely processed their PDF) or if the user explicitly requested ZU/SUZA.
    # To be safe, we'll list any university that has BOTH successes and failures, 
    # OR if it's one of the ones specifically failing that we processed.
    
    # If succeeded_progs > 0, it means we definitely ingested their PDF but some failed.
    if succeeded_progs > 0 and failed_count > 0:
        print(f"\n[+] {uni.name}")
        print(f"    Total Programmes: {total_progs} | Successfully Extracted: {succeeded_progs} | Failed (0 courses): {failed_count}")
        print("    Failed Programmes List:")
        for fp in failed_progs:
            print(f"      - {fp.name}")

print("\n=== Audit Complete ===")
