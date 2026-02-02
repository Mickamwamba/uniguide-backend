from django.db import models
from pgvector.django import VectorField

class University(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    head_office = models.CharField(max_length=255, blank=True)
    university_type = models.CharField(max_length=100, blank=True) # e.g. Private/Public
    status = models.CharField(max_length=100, blank=True) # e.g. Active
    
    # Contact & Details
    address = models.TextField(blank=True)
    email = models.CharField(max_length=255, blank=True) # CharField to handle multiple emails if needed
    accreditation_status = models.CharField(max_length=255, blank=True)
    registration_no = models.CharField(max_length=100, blank=True)
    overview = models.TextField(blank=True, help_text="AI-generated high-level overview.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Universities"

    def __str__(self):
        return self.name

class Programme(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='programmes', null=True)
    name = models.CharField(max_length=255, null=True)
    
    # New fields from TCU Table
    award_level = models.CharField(max_length=100, default="Bachelor", help_text="e.g. Bachelor Degree, Diploma")
    duration_months = models.IntegerField(default=0)
    qualification_framework = models.CharField(max_length=50, blank=True, help_text="e.g. UQF 10")
    study_mode = models.CharField(max_length=50, blank=True, help_text="e.g. Full Time")

    # Keep these for backward/future compatibility or derived values
    duration_years = models.FloatField(default=3) # Derived from months if needed
    description = models.TextField(blank=True)
    
    # Text embedding for RAG
    # Using 1536 dimensions (OpenAI text-embedding-3-small standard)
    embedding = VectorField(dimensions=1536, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.university.name}"

class Course(models.Model):
    """
    Represents a specific unit/module within a programme (e.g. 'Introduction to CS').
    """
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    semester = models.IntegerField(help_text="Semester number (1-8)")
    year = models.IntegerField(default=1, help_text="Year of study (e.g. 1, 2, 3)")
    credits = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    
    # Often courses have specific objectives
    objectives = models.TextField(blank=True)

    def __str__(self):
        return self.name

class AdmissionRequirement(models.Model):
    programme = models.OneToOneField(Programme, on_delete=models.CASCADE, related_name='admission_requirement')
    description = models.TextField(help_text="General description of requirements")
    min_points = models.FloatField(default=0.0, help_text="Minimum points required")
    required_subjects = models.TextField(blank=True, help_text="Comma-separated list of required subjects (e.g. Physics, Math)")

    def __str__(self):
        return f"Requirements for {self.programme.name}"

class CareerOutlook(models.Model):
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='career_outlooks')
    title = models.CharField(max_length=255, help_text="Job title or Career path")
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title
