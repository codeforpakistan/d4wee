import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Cohort, Course

# Get all cohorts
cohorts = Cohort.objects.all().order_by('start_date')
print("Available Cohorts:")
for c in cohorts:
    print(f"  {c.id}: {c.name} ({c.start_date} to {c.end_date})")

# Get all courses without a cohort
unassigned_courses = Course.objects.filter(cohort__isnull=True).order_by('name')
print(f"\n{unassigned_courses.count()} Courses without cohort assignment:")
for course in unassigned_courses:
    student_count = course.students.count()
    print(f"  {course.id}: {course.name} - {student_count} students")

# Check if there are already assigned courses
assigned_courses = Course.objects.filter(cohort__isnull=False).order_by('cohort__name', 'name')
if assigned_courses.exists():
    print(f"\nCourses already assigned to cohorts:")
    for course in assigned_courses:
        print(f"  {course.name} -> {course.cohort.name}")
