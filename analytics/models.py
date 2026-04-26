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
