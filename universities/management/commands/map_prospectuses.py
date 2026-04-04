from django.core.management.base import BaseCommand
from universities.models import University, Programme
from django.db.models import Count
import os

class Command(BaseCommand):
    help = 'Map prospectuses to universities and audit missing courses'

    def handle(self, *args, **options):
        # Precise Mapping
        mapping = {
            "SJUIT.pdf": "St. Joseph University in Tanzania (SJUIT)",
            "ardhi.pdf": "Ardhi University (ARU)",
            "cuhas.pdf": "Catholic University of Health and Allied Sciences (CUHAS)",
            "jordan.pdf": "Jordan University College (JUCo)",
            "kcmc.pdf": "KCMC University",
            "mihayo.pdf": "Archbishop Mihayo University College of Tabora (AMUCTA)",
            "mnuat.pdf": "Mwalimu Nyerere University of Agriculture and Technology (MNUAT)",
            "muhimbili.pdf": "Muhimbili University of Health and Allied Sciences (MUHAS)",
            "muslim.pdf": "Muslim University of Morogoro (MUM)",
            "must.pdf": "Mbeya University of Science and Technology (MUST)",
            "mzu.pdf": "Mwanza University (MzU)",
            "mzumbe.pdf": "Mzumbe University (MU)",
            "out.pdf": "Open University of Tanzania (OUT)",
            "rucu.pdf": "Ruaha Catholic University (RUCU)",
            "saut.pdf": "St. Augustine University of Tanzania (SAUT)",
            "sjut.pdf": "St. John's University of Tanzania (SJUT)",
            "smmco.pdf": "Stefano Moshi Memorial University College (SMMUCo)",
            "stella.pdf": "Stella Maris Mtwara University College (STeMMUCo)",
            "sua.pdf": "Sokoine University of Agriculture (SUA)",
            "teku.pdf": "Teofilo Kisanji University (TEKU)",
            "tuma.pdf": "Tumaini University Makumira (TUMA)",
            "uaut.pdf": "United African University of Tanzania (UAUT)",
            "udom.pdf": "University of Dodoma (UDOM)",
            "udsm.pdf": "University of Dar es Salaam (UDSM)",
            "uoi.pdf": "University of Iringa (UoI)"
        }

        self.stdout.write(f"{'Filename':<15} | {'University Name':<50} | {'Bachelors':<10} | {'Empty Courses':<10}")
        self.stdout.write("-" * 95)

        for filename, uni_full in mapping.items():
            uni = University.objects.filter(name=uni_full).first()
            if not uni:
                # Fallback to icontains if exact fails
                uni = University.objects.filter(name__icontains=uni_full).first()
            
            if not uni:
                self.stdout.write(f"{filename:<15} | {uni_full[:50]:<50} | {'NOT FOUND':<10}")
                continue
            
            bachelors = Programme.objects.filter(university=uni, name__icontains='Bachelor')
            empty_bachelors = bachelors.annotate(c_count=Count('courses')).filter(c_count=0)
            
            success_count = bachelors.count() - empty_bachelors.count()
            self.stdout.write(f"{filename:<15} | {uni.name[:50]:<50} | {bachelors.count():<10} | {empty_bachelors.count():<10}")
            
            if empty_bachelors.count() > 0:
                self.stdout.write(f"   -> Failed Bachelors: {', '.join([p.name for p in empty_bachelors[:5]])}")
                if empty_bachelors.count() > 5:
                    self.stdout.write(f"      ... and {empty_bachelors.count() - 5} more.")

        self.stdout.write("\nDone.")
