
import os
import django
import sys
import json

sys.path.append('/Users/michaelkimollo/DSProjects/uniguide/uniguide-web/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from universities.models import Programme
from universities.serializers import ProgrammeDetailSerializer

def check():
    # Get a programme with courses
    prog = Programme.objects.filter(courses__isnull=False).first()
    if not prog:
        print("No programme with courses found.")
        return

    print(f"Checking Programme: {prog.name}")
    serializer = ProgrammeDetailSerializer(prog)
    data = serializer.data
    
    print(f"Has 'courses' key? {'courses' in data}")
    if 'courses' in data:
        print(f"Courses count: {len(data['courses'])}")
        if len(data['courses']) > 0:
            print("First course sample:", data['courses'][0])
            
    # Check structure match for frontend
    # Frontend expects: id, name, code, semester, credits
    required_fields = ['id', 'name', 'code', 'semester', 'credits']
    if len(data['courses']) > 0:
        c = data['courses'][0]
        missing = [f for f in required_fields if f not in c]
        if missing:
            print(f"MISSING FIELDS in Course: {missing}")
        else:
            print("All required course fields present.")

if __name__ == "__main__":
    check()
