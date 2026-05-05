from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import University, Programme, AdmissionRequirement

@admin.register(University)
class UniversityAdmin(ModelAdmin):
    list_display = ('name', 'short_name', 'rank', 'total_views', 'created_at')
    search_fields = ('name', 'short_name')
    ordering = ('rank', 'name')

    @admin.display(description='Popularity')
    def total_views(self, obj):
        from analytics.models import PageViewLog
        count = PageViewLog.objects.filter(entity_type='UNIVERSITY', entity_id=obj.id).count()
        if count > 0:
            from django.utils.html import format_html
            return format_html('<span style="font-weight: bold; color: #10b981;">{} views</span>', count)
        return "0"

    def changelist_view(self, request, extra_context=None):
        from analytics.models import PageViewLog
        from django.db.models import Count
        
        univ_views = PageViewLog.objects.filter(entity_type='UNIVERSITY').values('entity_id').annotate(count=Count('id')).order_by('-count')
        
        top_univs = []
        for v in univ_views[:5]:
            try:
                u = University.objects.get(id=v['entity_id'])
                top_univs.append({'name': u.name, 'count': v['count']})
            except University.DoesNotExist: continue
            
        logged_ids = [v['entity_id'] for v in univ_views]
        bottom_univs = University.objects.exclude(id__in=logged_ids)[:5]
        
        extra_context = extra_context or {}
        extra_context['univ_stats'] = {
            'top': top_univs,
            'bottom': bottom_univs,
        }
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(Programme)
class ProgrammeAdmin(ModelAdmin):
    list_display = ('name', 'get_university_name', 'award_level', 'total_views', 'is_stem')
    search_fields = ('name', 'generic_name', 'university__name')
    list_filter = ('award_level', 'is_stem', 'is_active')

    def get_university_name(self, obj):
        return obj.university.name if obj.university else "-"
    get_university_name.short_description = "University"

    @admin.display(description='Popularity')
    def total_views(self, obj):
        from analytics.models import PageViewLog
        count = PageViewLog.objects.filter(entity_type='PROGRAMME', entity_id=obj.id).count()
        if count > 0:
            from django.utils.html import format_html
            return format_html('<span style="font-weight: bold; color: #3b82f6;">{} views</span>', count)
        return "0"

    def changelist_view(self, request, extra_context=None):
        from analytics.models import PageViewLog
        from django.db.models import Count
        
        prog_views = PageViewLog.objects.filter(entity_type='PROGRAMME').values('entity_id').annotate(count=Count('id')).order_by('-count')
        
        top_progs = []
        for v in prog_views[:5]:
            try:
                p = Programme.objects.select_related('university').get(id=v['entity_id'])
                top_progs.append({'name': f"{p.name} ({p.university.name})", 'count': v['count']})
            except Programme.DoesNotExist: continue
            
        logged_ids = [v['entity_id'] for v in prog_views]
        bottom_progs = Programme.objects.select_related('university').exclude(id__in=logged_ids)[:5]
        
        extra_context = extra_context or {}
        extra_context['prog_stats'] = {
            'top': top_progs,
            'bottom': bottom_progs,
        }
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(AdmissionRequirement)
class AdmissionRequirementAdmin(ModelAdmin):
    list_display = ('programme', 'pathway')
    list_filter = ('pathway',)
