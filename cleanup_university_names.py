import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from universities.models import University

def cleanup():
    unis = University.objects.all()
    updated = 0
    
    print("Scanning Universities...")
    for u in unis:
        if u.short_name:
            suffix = f"({u.short_name})"
            # Check if name ends with the exact suffix, e.g. " (UDSM)"
            if u.name.endswith(suffix):
                # Slice off the suffix and strip any trailing space
                new_name = u.name[:-len(suffix)].strip()
                print(f" ✏️ Updated: '{u.name}' -> '{new_name}'")
                u.name = new_name
                
                # Use update_fields to safely touch only the name field, avoiding overriding background tasks
                u.save(update_fields=['name'])
                updated += 1
                
    print(f"\nDone! Safely stripped short codes from {updated} university names.")

if __name__ == '__main__':
    cleanup()
