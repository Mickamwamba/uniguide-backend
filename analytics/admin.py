from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SearchLog, GuidanceSessionLog, PageViewLog, EligibilityCheckLog, UserInquiry, ContentReport, StudentLead

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
    list_display = ('session_id', 'query_string', 'results_count', 'created_at')
    search_fields = ('query_string', 'session_id')
    list_filter = ('created_at',)
    ordering = ('-created_at',)

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

@admin.register(PageViewLog)
class PageViewLogAdmin(ModelAdmin):
    list_display = ('session_id', 'entity_type', 'referrer', 'created_at')
    list_filter = ('entity_type', 'referrer', 'created_at')
    ordering = ('-created_at',)

@admin.register(EligibilityCheckLog)
class EligibilityCheckLogAdmin(ModelAdmin):
    list_display = ('session_id', 'programme_id', 'ai_decision', 'created_at')
    list_filter = ('ai_decision', 'created_at')
    ordering = ('-created_at',)
