import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Cohort, CohortEnrollment, Student

# Check CohortEnrollment records
pilot = Cohort.objects.get(name='Pilot')
enrollments = CohortEnrollment.objects.filter(cohort=pilot)

print(f'CohortEnrollment records for Pilot: {enrollments.count()}')

if enrollments.exists():
    print('\nEnrollment breakdown:')
    for status in ['ENROLLED', 'IN_PROGRESS', 'COMPLETED', 'DROPPED']:
        count = enrollments.filter(status=status).count()
        if count > 0:
            print(f'  {status}: {count}')
else:
    print('\n⚠️  No CohortEnrollment records found for Pilot cohort!')
    print('\nThis is why the stats show 0.')
    
    # Show unique students from all courses
    all_students = Student.objects.values('google_id', 'full_name', 'email').distinct()
    print(f'\nTotal unique students in system: {all_students.count()}')
    print('\nThese students need to be enrolled in cohorts using CohortEnrollment records.')

# Check total CohortEnrollment records
total_enrollments = CohortEnrollment.objects.all().count()
print(f'\nTotal CohortEnrollment records in system: {total_enrollments}')
