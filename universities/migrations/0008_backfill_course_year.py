from django.db import migrations
import re

def extract_year(apps, schema_editor):
    Course = apps.get_model('universities', 'Course')
    courses_to_update = []
    for course in Course.objects.all():
        if course.description:
            # Look for "Year 1", "Year 2", etc.
            match = re.search(r'Year\s+(\d+)', course.description, re.IGNORECASE)
            if match:
                course.year = int(match.group(1))
                courses_to_update.append(course)
    
    if courses_to_update:
        Course.objects.bulk_update(courses_to_update, ['year'])

class Migration(migrations.Migration):

    dependencies = [
        ('universities', '0007_course_year'),
    ]

    operations = [
        migrations.RunPython(extract_year),
    ]
