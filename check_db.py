import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from universities.models import University, Programme

print(f"Universities: {University.objects.count()}")
print(f"Programmes: {Programme.objects.count()}")
