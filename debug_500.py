import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
u, _ = User.objects.get_or_create(username='testadmin', is_superuser=True, is_staff=True)

c = Client()
c.force_login(u)

try:
    response = c.get('/admin/analytics/guidancesessionlog/')
    print("Status code:", response.status_code)
    if response.status_code == 500:
        print(response.content.decode())
except Exception as e:
    import traceback
    traceback.print_exc()
