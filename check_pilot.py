import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'd4wee.settings')
django.setup()

from core.models import Cohort, Course, Student, StudentMetrics

# Find Pilot cohort
pilot = Cohort.objects.filter(name__icontains='pilot').first()
print(f'Pilot cohort: {pilot}')

if pilot:
    # Check courses
    courses = Course.objects.filter(cohort=pilot)
    print(f'\nCourses in Pilot: {courses.count()}')
    for c in courses:
        student_count = c.students.count()
        print(f'  - {c.name} ({c.google_id}): {student_count} students')
    
    # Check unique students across all courses
    unique_students = Student.objects.filter(
        course__cohort=pilot
    ).values('google_id').distinct().count()
    print(f'\nUnique students across all Pilot courses: {unique_students}')
    
    # Check StudentMetrics
    metrics_count = StudentMetrics.objects.filter(course__cohort=pilot).count()
    print(f'StudentMetrics records for Pilot: {metrics_count}')
    
    # Check if courses exist but have NULL cohort
    null_cohort_courses = Course.objects.filter(cohort__isnull=True)
    print(f'\nCourses with NULL cohort: {null_cohort_courses.count()}')
    for c in null_cohort_courses[:5]:
        print(f'  - {c.name} ({c.google_id}): {c.students.count()} students')
