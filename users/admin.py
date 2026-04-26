from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(ModelAdmin):
    list_display = ('email', 'is_staff', 'is_superuser')
    search_fields = ('email',)
