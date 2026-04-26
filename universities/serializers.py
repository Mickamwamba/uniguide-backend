from rest_framework import serializers
from .models import University, Programme, Course

class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = [
            'id', 'name', 'short_name', 'tcu_code', 'location', 'website', 'logo_url',
            'head_office', 'university_type', 'status', 
            'address', 'email', 'accreditation_status', 'registration_no',
            'overview'
        ]

class ProgrammeSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(source='university.name', read_only=True)
    university_short_name = serializers.CharField(source='university.short_name', read_only=True)

    class Meta:
        model = Programme
        fields = [
            'id', 
            'name', 
            'university', 
            'university_name',
            'university_short_name',
            'award_level', 
            'duration_months', 
            'qualification_framework', 
            'study_mode',
            'description',
            'career_outlooks'
        ]


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course # Assuming Course is imported from models, but it wasn't. Need to update imports too.
        fields = ['id', 'name', 'code', 'semester', 'year', 'credits', 'description']

class ProgrammeDetailSerializer(ProgrammeSerializer):
    courses = CourseSerializer(many=True, read_only=True)
    
    class Meta(ProgrammeSerializer.Meta):
        fields = ProgrammeSerializer.Meta.fields + ['courses']
