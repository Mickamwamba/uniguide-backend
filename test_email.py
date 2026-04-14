import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail

try:
    result = send_mail(
        'Test Subject', 
        'Test Message', 
        'awscloudup@gmail.com', 
        ['vitabu.co.tz@gmail.com'], 
        fail_silently=False
    )
    print(f"SEND STATUS: {result}")
except Exception as e:
    print(f"CRASH TRACE: {str(e)}")
