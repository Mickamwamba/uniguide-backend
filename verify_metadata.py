
import os
import django
import sys

# Setup Django
sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from universities.models import University

def verify():
    unis = University.objects.all()
    print(f"Total Universities: {unis.count()}")
    
    with_email = unis.exclude(email='').count()
    with_address = unis.exclude(address='').count()
    with_status = unis.exclude(status='').count()
    
    print(f"With Email: {with_email}")
    print(f"With Address: {with_address}")
    print(f"With Status: {with_status}")
    
    # Sample
    u = unis.filter(name__icontains='Dar es Salaam').first()
    if u:
        print("\nSample (UDSM):")
        print(f"Name: {u.name}")
        print(f"Email: {u.email}")
        print(f"Address: {u.address}")
        print(f"Status: {u.status}")
        print(f"Reg No: {u.registration_no}")

if __name__ == "__main__":
    verify()
