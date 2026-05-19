import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'd4wee.settings')
django.setup()

from core.models import Cohort, Course

# Get Pilot cohort
pilot = Cohort.objects.get(name='Pilot')
print(f'Assigning courses to: {pilot.name} ({pilot.start_date} to {pilot.end_date})')

# Course IDs to assign (those with students enrolled)
course_ids = [70, 73, 74, 71, 72]  # Orientation, AI Essentials, Basic Computer, Modern Digital, Digital Safety

courses_to_assign = Course.objects.filter(id__in=course_ids)

print(f'\nAssigning {courses_to_assign.count()} courses to Pilot cohort:')
for course in courses_to_assign:
    student_count = course.students.count()
    course.cohort = pilot
    course.save()
    print(f'  ✓ {course.name} - {student_count} students')

print(f'\n✅ Successfully assigned {courses_to_assign.count()} courses to Pilot cohort')

# Verify
pilot_courses = Course.objects.filter(cohort=pilot)
print(f'\nVerification - Pilot cohort now has {pilot_courses.count()} courses:')
for course in pilot_courses:
    print(f'  - {course.name}: {course.students.count()} students')

# Show unique student count
from core.models import Student
unique_students = Student.objects.filter(
    course__cohort=pilot
).values('google_id').distinct().count()
print(f'\nTotal unique students in Pilot cohort: {unique_students}')
