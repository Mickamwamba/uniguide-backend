
import os
import django
import sys

# Add backend dir to sys.path
sys.path.append('/Users/michaelkimollo/DSProjects/uniguide/uniguide-web/backend')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from universities.models import University, Programme, Course

def check():
    output = []
    try:
        udsm = University.objects.get(name__icontains="University of Dar es Salaam")
        output.append(f"University: {udsm.name}")
        
        progs = Programme.objects.filter(university=udsm, name__icontains="Computer Science")
        output.append(f"Found {progs.count()} Computer Science programmes.")
        
        for p in progs:
            output.append(f"Programme: {p.name}")
            output.append(f"Description: {p.description[:100]}..." if p.description else "Description: None")
            
            courses = Course.objects.filter(programme=p)
            output.append(f"Course Count: {courses.count()}")
            for c in courses[:5]:
                output.append(f" - {c.code}: {c.name} (Sem {c.semester})")
                
    except Exception as e:
        output.append(f"Error: {e}")

    with open("/Users/michaelkimollo/DSProjects/uniguide/uniguide-web/backend/ingestion_status.txt", "w") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    check()
