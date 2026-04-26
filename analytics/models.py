from django.db import models
from django.utils import timezone
import uuid

class SessionLog(models.Model):
    """
    Base model to track sessions and metadata logically across multiple events.
    Because users are mostly anonymous, we use session_id to stitch the funnel together.
    """
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

class SearchLog(SessionLog):
    """Captures every executed search across the platform."""
    query_string = models.CharField(max_length=500, blank=True)
    filters_applied = models.JSONField(default=dict, blank=True)
    results_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Search: '{self.query_string}' -> {self.results_count} results"

class GuidanceSessionLog(SessionLog):
    """Telemetry capturing what students input into the Pathfinder AI."""
    pathway = models.CharField(max_length=50, blank=True)  # ACSEE, DIPLOMA
    academic_inputs = models.JSONField(default=dict, blank=True)
    psychometric_inputs = models.JSONField(default=dict, blank=True)
    
    # Store recommended slugs or IDs to know exactly what the AI spat out
    ai_recommendations = models.JSONField(default=list, blank=True)
    ai_synthesis = models.TextField(blank=True)
    converted_to_lead = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Guidance [{self.pathway}] - Converted: {self.converted_to_lead}"

class PageViewLog(SessionLog):
    """Event triggered whenever a Programme or University is explicitly viewed."""
    entity_type = models.CharField(max_length=50, choices=[('PROGRAMME', 'Programme'), ('UNIVERSITY', 'University')])
    entity_id = models.UUIDField() 
    referrer = models.CharField(max_length=255, blank=True) # e.g. ORGANIC_SEARCH, AI_GUIDANCE
    
    def __str__(self):
        return f"View {self.entity_type} - {self.entity_id}"

class EligibilityCheckLog(SessionLog):
    """Telemetry strictly recording attempts to 'Verify Eligibility' against specific courses."""
    programme_id = models.UUIDField()
    academic_inputs = models.JSONField(default=dict, blank=True)
    ai_decision = models.BooleanField(default=False) # True = Qualified
    failure_reason = models.TextField(blank=True)
    
    def __str__(self):
        status = "PASSED" if self.ai_decision else "FAILED"
        return f"Eligibility Check [{status}] -> Prog:{self.programme_id}"

class UserInquiry(models.Model):
    """Captures messages from the 'Contact Us' form."""
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name_plural = "User Inquiries"

    def __str__(self):
        return f"Inquiry from {self.full_name} ({self.created_at.strftime('%Y-%m-%d')})"
class ContentReport(models.Model):
    """Captures user reports about inaccurate or broken content."""
    REPORT_TYPES = [
        ('INACCURATE', 'Inaccurate Information'),
        ('BROKEN_LINK', 'Broken Link'),
        ('OTHER', 'Other Issue')
    ]

    report_type = models.CharField(max_length=50, choices=REPORT_TYPES, default='INACCURATE')
    description = models.TextField()
    url = models.URLField(max_length=500, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    
    status = models.CharField(
        max_length=20, 
        choices=[('NEW', 'New'), ('REVIEWING', 'Reviewing'), ('RESOLVED', 'Resolved'), ('IGNORED', 'Ignored')],
        default='NEW'
    )
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Content Reports"

    def __str__(self):
        return f"Report: {self.report_type} on {self.created_at.strftime('%Y-%m-%d')}"

class StudentLead(models.Model):
    """
    Captured when a user 'saves' their guidance results.
    Links an email to their academic background and matches.
    """
    email = models.EmailField()
    combination = models.CharField(max_length=255, blank=True)
    interests = models.TextField(blank=True)
    personality = models.JSONField(default=dict, blank=True)
    ai_synthesis = models.TextField(blank=True)
    matches_summary = models.TextField(blank=True) # Comma separated names
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Student Leads"
        ordering = ['-created_at']

    def __str__(self):
        return f"Lead: {self.email} ({self.created_at.strftime('%Y-%m-%d')})"

    @property
    def synthesis_snippet(self):
        if not self.ai_synthesis:
            return "-"
        return (self.ai_synthesis[:75] + "...") if len(self.ai_synthesis) > 75 else self.ai_synthesis

    @property
    def personality_display(self):
        from django.utils.html import format_html
        from django.utils.safestring import mark_safe
        if not self.personality or not isinstance(self.personality, dict):
            return "No data"
        
        items = []
        for q, a in self.personality.items():
            items.append(format_html("<b>{}:</b> {}", q, a))
        return mark_safe("<br>".join(items))
