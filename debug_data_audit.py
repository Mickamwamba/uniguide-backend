
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from universities.models import University, Programme

def audit_data():
    print("=== DATA AUDIT ===")
    
    # 1. Universities with NO Programmes
    unis_without_programmes = University.objects.filter(programmes__isnull=True).distinct()
    print(f"\n1. Universities with NO Programmes ({unis_without_programmes.count()}):")
    for uni in unis_without_programmes:
        print(f"   - {uni.name}")

    # 2. Bachelor Programmes with NO Courses (Modules)
    progs_without_courses = Programme.objects.filter(courses__isnull=True, award_level__icontains='Bachelor').distinct()
    
    print(f"\n2. Bachelor Programmes with NO Courses/Modules listed ({progs_without_courses.count()}):")
    
    # Printing all might be too much if there are thousands, let's print first 50
    count = 0
    for prog in progs_without_courses[:50]:
        print(f"   - {prog.name} ({prog.university.name if prog.university else 'No Uni'})")
        count += 1
    
    if progs_without_courses.count() > 50:
        print(f"   ... and {progs_without_courses.count() - 50} more.")

if __name__ == "__main__":
    audit_data()
