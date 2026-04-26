import uuid
from django.db import models
from pgvector.django import VectorField

class ProgrammeCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Programme Categories"

    def __str__(self):
        return self.name

class GlobalAdmissionRequirement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    academic_year = models.CharField(max_length=50, default="2025/2026")
    general_requirements = models.JSONField(default=dict, blank=True)
    admission_cycles = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Global Requirements ({self.academic_year})"


class University(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, blank=True, null=True)
    tcu_code = models.CharField(max_length=50, blank=True, null=True)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    
    ownership = models.CharField(max_length=100, blank=True, null=True)
    location_city = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    
    website = models.URLField(blank=True, null=True)
    logo_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    
    head_office = models.CharField(max_length=255, blank=True)
    university_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=100, blank=True)
    
    is_campus_college = models.BooleanField(default=False)
    parent_institution_id = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='campus_colleges')
    
    phone = models.CharField(max_length=255, blank=True, null=True)
    po_box = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    
    address = models.TextField(blank=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    accreditation_status = models.CharField(max_length=255, blank=True)
    registration_no = models.CharField(max_length=100, blank=True)
    overview = models.TextField(blank=True, help_text="AI-generated high-level overview.")
    
    embedding = VectorField(dimensions=3072, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Universities"

    def __str__(self):
        return self.name

class Programme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='programmes', null=True)
    category = models.ForeignKey(ProgrammeCategory, on_delete=models.SET_NULL, related_name='programmes', null=True, blank=True)
    
    code = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, null=True)
    
    degree_type = models.CharField(max_length=100, blank=True, null=True)
    award_level = models.CharField(max_length=100, default="Bachelor", help_text="e.g. Bachelor Degree, Diploma")
    
    duration_months = models.IntegerField(default=0)
    duration_years = models.FloatField(default=3)
    
    academic_year = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    qualification_framework = models.CharField(max_length=50, blank=True, help_text="e.g. UQF 10")
    study_mode = models.CharField(max_length=50, blank=True, help_text="e.g. Full Time")

    description = models.TextField(blank=True)
    career_outlooks = models.JSONField(default=list, blank=True, help_text="List of extracted career objects")
    
    embedding = VectorField(dimensions=3072, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.university.name}"

class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)
    semester = models.IntegerField(help_text="Semester number (1-8)")
    year = models.IntegerField(default=1, help_text="Year of study (e.g. 1, 2, 3)")
    credits = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    objectives = models.TextField(blank=True)
    
    embedding = VectorField(dimensions=3072, blank=True, null=True)

    def __str__(self):
        return self.name

class AdmissionRequirement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='admission_requirements')
    pathway = models.CharField(max_length=50, choices=(('ACSEE', 'ACSEE'), ('DIPLOMA', 'DIPLOMA'), ('OTHER', 'OTHER')), default='ACSEE')
    admission_capacity = models.IntegerField(blank=True, null=True)
    
    description = models.TextField(blank=True, help_text="General description of requirements or raw requirements text")
    
    # ACSEE Specific
    min_points = models.FloatField(default=0.0, blank=True, null=True, help_text="Minimum points required")
    required_subjects = models.TextField(blank=True, help_text="Legacy string")
    alevel_requirements = models.JSONField(default=list, blank=True)
    olevel_requirements = models.JSONField(default=list, blank=True)
    
    # Diploma Specific
    min_gpa = models.FloatField(blank=True, null=True)
    min_grade = models.CharField(max_length=50, blank=True, null=True)
    diploma_fields_accepted = models.JSONField(default=list, blank=True)
    
    accepts_out_foundation = models.BooleanField(default=False)
    out_foundation_min_gpa = models.FloatField(blank=True, null=True)
    
    embedding = VectorField(dimensions=3072, blank=True, null=True)

    def __str__(self):
        return f"Requirements ({self.pathway}) for {self.programme.name}"

class StudentLead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    combination = models.CharField(max_length=100, blank=True)
    interests = models.TextField(blank=True)
    personality_data = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

