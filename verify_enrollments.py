import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Student, Registration, Enrollment, Cohort, Course

print('=' * 60)
print('ENROLLMENT VERIFICATION')
print('=' * 60)
print()

# Get counts
total_students = Student.objects.filter(is_pilot_student=True).count()
total_registrations = Registration.objects.filter(cohort__name='Pilot').count()
total_enrollments = Enrollment.objects.filter(cohort__name='Pilot').count()

print(f'PILOT Students: {total_students}')
print(f'Registrations in Pilot cohort: {total_registrations}')
print(f'Total Enrollments in Pilot cohort: {total_enrollments}')
print()

# Check enrollment distribution by course
print('Enrollments by PILOT course:')
pilot_courses = Course.objects.filter(name__in=[
    'Orientation Class - Pilot Phase',
    'Basic Computer Literacy',
    'AI Essentials and Prompt Engineering',
    'Digital Safety & Online Security',
    'Modern Digital Workspace'
])

for course in pilot_courses:
    count = Enrollment.objects.filter(course=course, cohort__name='Pilot').count()
    print(f'  {course.display_name}: {count} enrollments')

print()

# Sample student verification
sample_student = Student.objects.filter(is_pilot_student=True).first()
if sample_student:
    print(f'Sample Student: {sample_student.full_name}')
    print(f'  Email: {sample_student.email}')
    
    registration = Registration.objects.filter(student=sample_student, cohort__name='Pilot').first()
    if registration:
        print(f'  Registration: {registration.cohort.name} - Status: {registration.status}')
        
        enrollments = Enrollment.objects.filter(registration=registration)
        print(f'  Enrollments ({enrollments.count()}):')
        for enrollment in enrollments:
            print(f'    - {enrollment.course.name} ({enrollment.status})')
    else:
        print('  No registration found!')

print()
print('=' * 60)
