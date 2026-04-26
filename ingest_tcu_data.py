import os
import sys
import django
import json
import re

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from universities.models import (
    University, Programme, AdmissionRequirement, 
    ProgrammeCategory, GlobalAdmissionRequirement
)

def clean_name(name):
    clean = re.sub(r'\(.*?\).*', '', name)
    clean = clean.split(',')[0].replace('–', '-').strip().lower()
    return clean

MANUAL_DB_TO_JSON = {
    "kizumbi institute of cooperative business education": "Kizumbi Institute of Co-operative and Business Education",
    "moshi cooperative university": "Moshi Co-operative University",
    "sokoine university of agriculture - mizengo pinda campus college": "Sokoine University of Agriculture Mizengo Pinda Campus",
    "mbeya university of science and technology - rukwa campus college": "Mbeya University of Science and Technology Rukwa Campus",
    "mzumbe university - dar es salaam campus college": "Mzumbe University Dar es Salaam Campus College",
    "mzumbe university - mbeya campus college": "Mzumbe University Mbeya Campus College"
}

def ingest():
    with open('unipathfinder_data.json', 'r') as f:
        data = json.load(f)
        
    print("1. Ingesting Global Settings")
    GlobalAdmissionRequirement.objects.all().delete()
    GlobalAdmissionRequirement.objects.create(
        academic_year=data.get('_meta', {}).get('academic_year', '2025/2026'),
        general_requirements=data.get('general_minimum_entry_requirements', {}),
        admission_cycles=data.get('admission_cycles', [])
    )
    
    print("2. Ingesting Categories")
    cat_map = {}
    for c in data.get('programme_categories', []):
        cat, created = ProgrammeCategory.objects.get_or_create(
            slug=c['slug'], defaults={'name': c['name']}
        )
        cat_map[c['slug']] = cat

    print("3. Ingesting Institutions")
    json_inst_map = {}
    db_unis = list(University.objects.all())
    
    for j_u in data.get('institutions', []):
        j_name = j_u['name']
        match_db = None
        for db_u in db_unis:
            cleaned = clean_name(db_u.name)
            if cleaned == j_name.lower().strip() or MANUAL_DB_TO_JSON.get(cleaned) == j_name.strip():
                match_db = db_u
                break
        
        if match_db:
            match_db.short_name = j_u.get('short_name')
            match_db.tcu_code = j_u.get('tcu_code')
            match_db.slug = j_u.get('slug')
            match_db.ownership = j_u.get('ownership')
            match_db.location_city = j_u.get('location_city')
            match_db.region = j_u.get('region')
            match_db.is_campus_college = j_u.get('is_campus_college', False)
            match_db.phone = j_u.get('phone')
            match_db.po_box = j_u.get('po_box')
            match_db.longitude = j_u.get('longitude')
            match_db.latitude = j_u.get('latitude')
            match_db.save()
            json_inst_map[j_u['id']] = match_db
        else:
            new_u = University.objects.create(
                name=j_name,
                short_name=j_u.get('short_name'),
                tcu_code=j_u.get('tcu_code'),
                slug=j_u.get('slug'),
                ownership=j_u.get('ownership'),
                location_city=j_u.get('location_city'),
                region=j_u.get('region'),
                is_campus_college=j_u.get('is_campus_college', False),
                phone=j_u.get('phone'),
                po_box=j_u.get('po_box'),
                latitude=j_u.get('latitude'),
                longitude=j_u.get('longitude')
            )
            json_inst_map[j_u['id']] = new_u
            
    print("4. Ingesting Programmes & Requirements")
    inserted_progs = 0
    updated_progs = 0
    
    for j_p in data.get('programmes', []):
        db_uni = json_inst_map.get(j_p['institution_id'])
        if not db_uni:
            continue
            
        prog_cat = cat_map.get(j_p['category_slug'])
        existing = Programme.objects.filter(university=db_uni, name__iexact=j_p['name']).first()
        
        if not existing:
            # Fallback soft word matching
            for ep in Programme.objects.filter(university=db_uni):
                e_clean = set(ep.name.lower().split())
                j_clean = set(j_p['name'].lower().split())
                if len(e_clean.intersection(j_clean)) >= 3:
                    existing = ep
                    break

        if existing:
            existing.code = j_p.get('code')
            existing.slug = j_p.get('slug')
            existing.category = prog_cat
            existing.degree_type = j_p.get('degree_type')
            existing.academic_year = j_p.get('academic_year')
            existing.is_active = j_p.get('is_active', True)
            try:
                existing.duration_years = float(j_p.get('duration_years', 3))
            except:
                existing.duration_years = 3.0
            existing.save()
            updated_progs += 1
            AdmissionRequirement.objects.filter(programme=existing).delete()
        else:
            existing = Programme.objects.create(
                university=db_uni,
                name=j_p['name'],
                code=j_p.get('code'),
                slug=j_p.get('slug'),
                category=prog_cat,
                degree_type=j_p.get('degree_type'),
                academic_year=j_p.get('academic_year'),
                is_active=j_p.get('is_active', True),
                duration_years=float(j_p.get('duration_years', 3) if str(j_p.get('duration_years', 3)).replace('.','').isdigit() else 3.0),
                award_level="Bachelor"
            )
            inserted_progs += 1
            
        my_reqs = [r for r in data.get('admission_requirements', []) if r['programme_id'] == j_p['id']]
        for r in my_reqs:
            AdmissionRequirement.objects.create(
                programme=existing,
                pathway=r.get('pathway', 'ACSEE').upper()[:50],
                admission_capacity=r.get('admission_capacity'),
                description=r.get('requirements_raw', ''),
                
                min_grade=r.get('min_grade'),
                alevel_requirements=r.get('alevel_requirements') or {},
                olevel_requirements=r.get('olevel_requirements') or {},
                
                min_gpa=r.get('min_gpa'),
                diploma_fields_accepted=r.get('diploma_fields_accepted') or [],
                accepts_out_foundation=r.get('accepts_out_foundation', False),
                out_foundation_min_gpa=r.get('out_foundation_min_gpa')
            )
            
    print(f"DONE! Inserted {inserted_progs} completely new Programmes. Updated {updated_progs} existing Programmes.")

if __name__ == '__main__':
    ingest()
