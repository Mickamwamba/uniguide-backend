from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import University, Programme, AdmissionRequirement

@admin.register(University)
class UniversityAdmin(ModelAdmin):
    list_display = ('name', 'short_name', 'rank', 'created_at')
    search_fields = ('name', 'short_name')
    ordering = ('rank', 'name')

@admin.register(Programme)
class ProgrammeAdmin(ModelAdmin):
    list_display = ('name', 'get_university_name', 'award_level', 'duration_years', 'is_stem')
    search_fields = ('name', 'generic_name', 'university__name')
    list_filter = ('award_level', 'is_stem', 'is_active')

    def get_university_name(self, obj):
        return obj.university.name if obj.university else "-"
    get_university_name.short_description = "University"

@admin.register(AdmissionRequirement)
class AdmissionRequirementAdmin(ModelAdmin):
    list_display = ('programme', 'pathway')
    list_filter = ('pathway',)
