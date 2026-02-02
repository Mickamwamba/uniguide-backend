
import os
import django
import sys

sys.path.append('/Users/michaelkimollo/DSProjects/uniguide/uniguide-web/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from universities.models import Course

def check():
    # Check if we have years > 1
    total = Course.objects.count()
    year_2 = Course.objects.filter(year=2).count()
    year_3 = Course.objects.filter(year__gte=3).count()
    
    print(f"Total Courses: {total}")
    print(f"Courses in Year 2: {year_2}")
    print(f"Courses in Year 3+: {year_3}")
    
    if year_2 > 0:
        print("SUCCESS: Year extracted successfully.")
        sample = Course.objects.filter(year=2).first()
        print(f"Sample Year 2 Course: {sample.name} (Year: {sample.year}, Desc: {sample.description})")
    else:
        print("WARNING: No year 2 courses found. Regex might have failed or data is missing.")

if __name__ == "__main__":
    check()
