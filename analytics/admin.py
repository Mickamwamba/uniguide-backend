from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import SearchLog, GuidanceSessionLog, PageViewLog, EligibilityCheckLog, UserInquiry, ContentReport, StudentLead, ComparisonLog

class OptimizationFilter(SimpleListFilter):
    title = 'Optimization Status'
    parameter_name = 'optimization'

    def lookups(self, request, model_admin):
        return (
            ('needs_opt', 'Needs Optimization (0 Results)'),
            ('healthy', 'Healthy (>0 Results)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'needs_opt':
            return queryset.filter(results_count=0)
        if self.value() == 'healthy':
            return queryset.exclude(results_count=0)
        return queryset

@admin.register(UserInquiry)
class UserInquiryAdmin(ModelAdmin):
    list_display = ('full_name', 'email', 'is_resolved', 'created_at')
    list_filter = ('is_resolved',)
    search_fields = ('full_name', 'email', 'message')

@admin.register(ContentReport)
class ContentReportAdmin(ModelAdmin):
    list_display = ('report_type', 'status', 'url', 'created_at')
    list_filter = ('report_type', 'status')
    search_fields = ('description', 'url', 'contact_email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(StudentLead)
class StudentLeadAdmin(ModelAdmin):
    list_display = ('email', 'combination', 'synthesis_snippet', 'created_at')
    list_filter = ('combination', 'created_at')
    search_fields = ('email', 'combination', 'interests', 'ai_synthesis')
    readonly_fields = ('created_at', 'personality_display', 'ai_synthesis', 'matches_summary')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {
            'fields': ('email', 'combination', 'interests', 'matches_summary', 'created_at')
        }),
        ('Detailed Profile', {
            'fields': ('ai_synthesis', 'personality_display'),
        }),
    )

@admin.register(SearchLog)
class SearchLogAdmin(ModelAdmin):
    list_display = ('query_string', 'optimization_status', 'results_count', 'created_at')
    search_fields = ('query_string', 'session_id')
    list_filter = (OptimizationFilter, 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('session_id', 'query_string', 'optimization_status', 'results_count', 'filters_applied', 'ip_address', 'user_agent', 'created_at')
    
    fieldsets = (
        ('Search Details', {
            'fields': ('query_string', 'optimization_status', 'results_count', 'created_at')
        }),
        ('Technical Data', {
            'fields': ('filters_applied', 'session_id', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        })
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        """Hide any historical blank searches from the view"""
        qs = super().get_queryset(request)
        return qs.exclude(query_string__exact='').exclude(query_string__isnull=True)

    @admin.display(description='Status')
    def optimization_status(self, obj):
        """Visual badge to immediately identify searches needing attention"""
        from django.utils.safestring import mark_safe
        if obj.results_count == 0:
            return mark_safe('<span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #ef4444;" title="Needs Optimization"></span>')
        return mark_safe('<span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #22c55e;" title="Healthy"></span>')

@admin.register(GuidanceSessionLog)
class GuidanceSessionLogAdmin(ModelAdmin):
    list_display = ('session_id', 'pathway', 'rating', 'converted_to_lead', 'created_at')
    list_filter = ('pathway', 'rating', 'converted_to_lead', 'created_at')
    search_fields = ('session_id', 'raw_interests', 'feedback_comment')
    readonly_fields = ('session_id', 'pathway', 'rating', 'feedback_comment', 'raw_interests', 'academic_inputs', 'psychometric_inputs', 'ai_synthesis', 'ai_recommendations', 'converted_to_lead', 'ip_address', 'user_agent', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.utils import timezone
        from django.db.models import Avg
        
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            # We extract the filtered queryset from the ChangeList instance
            cl = response.context_data['cl']
            qs = cl.queryset
        except (AttributeError, KeyError):
            return response

        today = timezone.now().date()
        
        total_sessions = qs.count()
        total_today = qs.filter(created_at__date=today).count()
        
        acsee_count = qs.filter(pathway='ACSEE').count()
        diploma_count = qs.filter(pathway='DIPLOMA').count()
        
        ratings = qs.exclude(rating__isnull=True).exclude(rating=0)
        avg_rating = ratings.aggregate(Avg('rating'))['rating__avg'] or 0
        
        converted = qs.filter(converted_to_lead=True).count()
        conversion_rate = int((converted / total_sessions * 100)) if total_sessions > 0 else 0
        
        # Rating distribution for chart
        from django.db.models import Count
        rating_dist = qs.exclude(rating__isnull=True).exclude(rating=0).values('rating').annotate(count=Count('id')).order_by('rating')
        rating_counts = [0] * 5 # [1*, 2*, 3*, 4*, 5*]
        for r in rating_dist:
            if 1 <= r['rating'] <= 5:
                rating_counts[r['rating']-1] = r['count']

        response.context_data['dashboard_stats'] = {
            'total_sessions': total_sessions,
            'total_today': total_today,
            'acsee_count': acsee_count,
            'diploma_count': diploma_count,
            'avg_rating': round(avg_rating, 1),
            'conversion_rate': conversion_rate,
            'rating_counts': rating_counts, # For bar chart
        }
        
        return response

@admin.register(PageViewLog)
class PageViewLogAdmin(ModelAdmin):
    list_display = ('entity_name', 'entity_type', 'referrer', 'created_at')
    list_filter = ('entity_type', 'referrer', 'created_at')
    ordering = ('-created_at',)

    @admin.display(description='Entity')
    def entity_name(self, obj):
        from universities.models import University, Programme
        if obj.entity_type == 'UNIVERSITY':
            try:
                return University.objects.get(id=obj.entity_id).name
            except University.DoesNotExist:
                return f"Univ: {obj.entity_id}"
        elif obj.entity_type == 'PROGRAMME':
            try:
                p = Programme.objects.select_related('university').get(id=obj.entity_id)
                return f"{p.name} ({p.university.name})"
            except Programme.DoesNotExist:
                return f"Prog: {obj.entity_id}"
        return str(obj.entity_id)

@admin.register(EligibilityCheckLog)
class EligibilityCheckLogAdmin(ModelAdmin):
    list_display = ('session_id', 'programme_id', 'ai_decision', 'created_at')
    list_filter = ('ai_decision', 'created_at')
    ordering = ('-created_at',)

@admin.register(ComparisonLog)
class ComparisonLogAdmin(ModelAdmin):
    list_display = ('programmes_compared', 'universities_compared', 'same_university', 'rating_stars', 'created_at')
    list_filter = ('same_university', 'rating', 'created_at')
    search_fields = ('programme_a_name', 'programme_b_name', 'university_a_name', 'university_b_name', 'session_id')
    ordering = ('-created_at',)
    readonly_fields = (
        'session_id', 'created_at', 'ip_address', 'user_agent',
        'programme_a_name', 'programme_b_name', 'university_a_name', 'university_b_name',
        'programme_a_id', 'programme_b_id', 'same_university',
        'rating', 'comment',
        'synthesis_display', 'recommendation_display',
        'contents_display', 'structure_display', 'careers_display',
    )

    fieldsets = (
        ('Programmes Compared', {
            'fields': (
                ('programme_a_name', 'university_a_name'),
                ('programme_b_name', 'university_b_name'),
                'same_university',
            )
        }),
        ('AI Synthesis', {
            'fields': ('synthesis_display',),
        }),
        ('AI Recommendation', {
            'fields': ('recommendation_display',),
        }),
        ('Course Contents', {
            'fields': ('contents_display',),
        }),
        ('Programme Structure', {
            'fields': ('structure_display',),
        }),
        ('Career Pathways', {
            'fields': ('careers_display',),
        }),
        ('Student Feedback', {
            'fields': ('rating', 'comment'),
        }),
        ('Session Info', {
            'fields': ('session_id', 'ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    # --- List display columns ---

    @admin.display(description='Programmes')
    def programmes_compared(self, obj):
        a = obj.programme_a_name or str(obj.programme_a_id)
        b = obj.programme_b_name or str(obj.programme_b_id)
        return format_html('<span style="font-weight:600">{}</span> <span style="color:#94a3b8">vs</span> <span style="font-weight:600">{}</span>', a, b)

    @admin.display(description='Universities')
    def universities_compared(self, obj):
        if obj.university_a_name and obj.university_b_name:
            if obj.same_university:
                return obj.university_a_name
            return format_html('{} / {}', obj.university_a_name, obj.university_b_name)
        return '—'

    @admin.display(description='Rating')
    def rating_stars(self, obj):
        from django.utils.safestring import mark_safe
        if obj.rating is None:
            return mark_safe('<span style="color:#cbd5e1">Not rated</span>')
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return mark_safe(f'<span style="color:#f59e0b;letter-spacing:2px">{stars}</span>')

    # --- Detail view computed fields ---

    def _dimension_html(self, obj, key):
        from django.utils.safestring import mark_safe
        if not obj.ai_result:
            return mark_safe('<em style="color:#94a3b8">No data captured</em>')
        dim = (obj.ai_result.get('dimensions') or {}).get(key, {})
        similarities = dim.get('similarities') or []
        differences = dim.get('differences') or []

        def bullet_list(items, color):
            if not items:
                return '<p style="color:#94a3b8;font-style:italic;margin:0">None identified</p>'
            lis = ''.join(f'<li style="margin-bottom:4px">{item}</li>' for item in items)
            return f'<ul style="margin:0;padding-left:18px;color:{color}">{lis}</ul>'

        html = (
            f'<div style="margin-bottom:12px">'
            f'<strong style="color:#059669;font-size:11px;text-transform:uppercase;letter-spacing:.05em">Similarities</strong>'
            f'<div style="margin-top:6px">{bullet_list(similarities, "#374151")}</div>'
            f'</div>'
            f'<div>'
            f'<strong style="color:#d97706;font-size:11px;text-transform:uppercase;letter-spacing:.05em">Differences</strong>'
            f'<div style="margin-top:6px">{bullet_list(differences, "#374151")}</div>'
            f'</div>'
        )
        return mark_safe(html)

    @admin.display(description='Synthesis (AI Summary)')
    def synthesis_display(self, obj):
        from django.utils.safestring import mark_safe
        if not obj.ai_result:
            return mark_safe('<em style="color:#94a3b8">No data captured</em>')
        text = obj.ai_result.get('synthesis') or ''
        if not text:
            return mark_safe('<em style="color:#94a3b8">Not available</em>')
        return mark_safe(f'<p style="line-height:1.7;color:#374151;max-width:700px">{text}</p>')

    @admin.display(description='Recommendation (AI)')
    def recommendation_display(self, obj):
        from django.utils.safestring import mark_safe
        if not obj.ai_result:
            return mark_safe('<em style="color:#94a3b8">No data captured</em>')
        rec = obj.ai_result.get('recommendation') or {}
        for_a = rec.get('for_a') or ''
        for_b = rec.get('for_b') or ''
        if not for_a and not for_b:
            return mark_safe('<em style="color:#94a3b8">Not available</em>')
        rows = ''
        if for_a:
            rows += f'<p style="margin:0 0 8px;color:#374151">→ {for_a}</p>'
        if for_b:
            rows += f'<p style="margin:0;color:#374151">→ {for_b}</p>'
        return mark_safe(f'<div style="max-width:700px">{rows}</div>')

    @admin.display(description='Contents — Similarities & Differences')
    def contents_display(self, obj):
        return self._dimension_html(obj, 'contents')

    @admin.display(description='Structure — Similarities & Differences')
    def structure_display(self, obj):
        return self._dimension_html(obj, 'structure')

    @admin.display(description='Careers — Similarities & Differences')
    def careers_display(self, obj):
        return self._dimension_html(obj, 'careers')

    def changelist_view(self, request, extra_context=None):
        from django.db.models import Avg, Count
        from django.utils import timezone
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            cl = response.context_data['cl']
            qs = cl.queryset
        except (AttributeError, KeyError):
            return response
        rated = qs.exclude(rating__isnull=True)
        avg_rating = rated.aggregate(Avg('rating'))['rating__avg'] or 0
        today = timezone.now().date()
        rating_dist = rated.values('rating').annotate(count=Count('id')).order_by('rating')
        rating_counts = [0] * 5
        for r in rating_dist:
            if 1 <= r['rating'] <= 5:
                rating_counts[r['rating'] - 1] = r['count']
        response.context_data['comparison_stats'] = {
            'total_comparisons': qs.count(),
            'total_today': qs.filter(created_at__date=today).count(),
            'avg_rating': round(avg_rating, 1),
            'rated_count': rated.count(),
            'cross_university': qs.filter(same_university=False).count(),
            'same_university': qs.filter(same_university=True).count(),
            'rating_counts': rating_counts,
        }
        return response
