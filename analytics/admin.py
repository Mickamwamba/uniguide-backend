from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SearchLog, GuidanceSessionLog, PageViewLog, EligibilityCheckLog

@admin.register(SearchLog)
class SearchLogAdmin(ModelAdmin):
    list_display = ('session_id', 'query_string', 'results_count', 'created_at')
    search_fields = ('query_string', 'session_id')
    list_filter = ('created_at',)
    ordering = ('-created_at',)

@admin.register(GuidanceSessionLog)
class GuidanceSessionLogAdmin(ModelAdmin):
    list_display = ('session_id', 'pathway', 'converted_to_lead', 'created_at')
    list_filter = ('pathway', 'converted_to_lead', 'created_at')
    ordering = ('-created_at',)

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
