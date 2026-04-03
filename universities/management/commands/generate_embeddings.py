import os
import time
import google.generativeai as genai
from django.core.management.base import BaseCommand
from django.db import models
from universities.models import University, Programme, Course, AdmissionRequirement, CareerOutlook
from dotenv import load_dotenv

load_dotenv()

class Command(BaseCommand):
    help = 'Generates vector embeddings for Universities, Programmes, Courses, Admissions, and Careers using Gemini text-embedding-004.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Embed all models')
        parser.add_argument('--universities', action='store_true', help='Embed universities')
        parser.add_argument('--programmes', action='store_true', help='Embed programmes (enriched with courses, careers, admissions)')
        parser.add_argument('--courses', action='store_true', help='Embed courses independently')
        parser.add_argument('--admissions', action='store_true', help='Embed admission requirements independently')
        parser.add_argument('--careers', action='store_true', help='Embed career outlooks independently')

    def handle(self, *args, **options):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("GEMINI_API_KEY not found."))
            return

        genai.configure(api_key=api_key)

        embed_univs = options['universities'] or options['all']
        embed_progs = options['programmes'] or options['all']
        embed_courses = options['courses'] or options['all']
        embed_adm = options['admissions'] or options['all']
        embed_careers = options['careers'] or options['all']

        if not any([embed_univs, embed_progs, embed_courses, embed_adm, embed_careers]):
            # Default to programmes if nothing is specified
            embed_progs = True

        if embed_univs: self.embed_universities()
        if embed_progs: self.embed_programmes()
        if embed_courses: self.embed_courses()
        if embed_adm: self.embed_admissions()
        if embed_careers: self.embed_careers()

    def generate_vector(self, text, title):
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
                title=title
            )
            return result['embedding']
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Embedding failed: {e}"))
            return None

    def embed_universities(self):
        universities = University.objects.all()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Embedding {universities.count()} Universities..."))
        count = 0
        for uni in universities:
            text_blob = f"""
            University: {uni.name}
            Location: {uni.location}
            Type: {uni.university_type}
            Accreditation: {uni.accreditation_status}
            Overview: {uni.overview}
            Description: {uni.description}
            """
            vector = self.generate_vector(text_blob, uni.name)
            if vector:
                uni.embedding = vector
                uni.save()
                count += 1
            time.sleep(0.5)
        self.stdout.write(self.style.SUCCESS(f"Finished embedding {count} universities."))

    def embed_programmes(self):
        programmes = Programme.objects.prefetch_related('career_outlooks', 'courses').select_related('admission_requirement', 'university').all()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Embedding {programmes.count()} Programmes with enriched super-blob..."))
        count = 0
        for prog in programmes:
            careers = ", ".join([c.title for c in prog.career_outlooks.all()])
            courses = ", ".join([c.name for c in prog.courses.all()])
            
            adm = ""
            if hasattr(prog, 'admission_requirement') and prog.admission_requirement:
                adm = f"Reqs: {prog.admission_requirement.description}. Subjects: {prog.admission_requirement.required_subjects}. Min Points: {prog.admission_requirement.min_points}"

            text_blob = f"""
            Programme: {prog.name}
            University: {prog.university.name if prog.university else 'Unknown'}
            Award Level: {prog.award_level}
            Study Mode: {prog.study_mode}
            Description: {prog.description}
            Careers: {careers}
            Admission Details: {adm}
            Courses Offered: {courses}
            """
            vector = self.generate_vector(text_blob, f"{prog.name} at {prog.university.name if prog.university else ''}")
            if vector:
                prog.embedding = vector
                prog.save()
                count += 1
            time.sleep(1)
        self.stdout.write(self.style.SUCCESS(f"Finished embedding {count} programmes."))

    def embed_courses(self):
        courses = Course.objects.select_related('programme__university').all()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Embedding {courses.count()} Courses..."))
        count = 0
        for course in courses:
            prog_name = course.programme.name if course.programme else "Unknown"
            uni_name = course.programme.university.name if course.programme and course.programme.university else "Unknown"
            text_blob = f"""
            Course: {course.name} ({course.code})
            Programme: {prog_name}
            University: {uni_name}
            Credits: {course.credits}
            Description: {course.description}
            Objectives: {course.objectives}
            """
            vector = self.generate_vector(text_blob, f"{course.name} ({prog_name})")
            if vector:
                course.embedding = vector
                course.save()
                count += 1
            time.sleep(0.5)
        self.stdout.write(self.style.SUCCESS(f"Finished embedding {count} courses."))

    def embed_admissions(self):
        adms = AdmissionRequirement.objects.select_related('programme__university').all()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Embedding {adms.count()} Admission Requirements..."))
        count = 0
        for adm in adms:
            prog_name = adm.programme.name if adm.programme else "Unknown"
            uni_name = adm.programme.university.name if adm.programme and adm.programme.university else "Unknown"
            text_blob = f"Admission for {prog_name} at {uni_name}. Require {adm.min_points} points in {adm.required_subjects}. {adm.description}"
            vector = self.generate_vector(text_blob, f"Admission: {prog_name}")
            if vector:
                adm.embedding = vector
                adm.save()
                count += 1
            time.sleep(0.5)
        self.stdout.write(self.style.SUCCESS(f"Finished embedding {count} admission requirements."))

    def embed_careers(self):
        careers = CareerOutlook.objects.select_related('programme__university').all()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Embedding {careers.count()} Career Outlooks..."))
        count = 0
        for career in careers:
            prog_name = career.programme.name if career.programme else "Unknown"
            text_blob = f"Career: {career.title}. {career.description}. Studied {prog_name}."
            vector = self.generate_vector(text_blob, career.title)
            if vector:
                career.embedding = vector
                career.save()
                count += 1
            time.sleep(0.5)
        self.stdout.write(self.style.SUCCESS(f"Finished embedding {count} career outlooks."))
