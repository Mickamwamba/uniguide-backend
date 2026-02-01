from rest_framework import serializers
from .models import University, Programme

class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = [
            'id', 'name', 'location', 'website', 'logo_url',
            'head_office', 'university_type', 'status', 
            'address', 'email', 'accreditation_status', 'registration_no',
            'overview'
        ]

class ProgrammeSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(source='university.name', read_only=True)

    class Meta:
        model = Programme
        fields = [
            'id', 
            'name', 
            'university', 
            'university_name',
            'award_level', 
            'duration_months', 
            'qualification_framework', 
            'study_mode',
            'description'
        ]
