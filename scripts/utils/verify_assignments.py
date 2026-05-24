import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Assignment, Course
from collections import Counter

print('=' * 80)
print('ASSIGNMENT VERIFICATION')
print('=' * 80)
print()

# Overall stats
total = Assignment.objects.count()
print(f'Total assignments: {total}')
print()

# By course
print('Assignments by course:')
pilot_courses = Course.objects.filter(name__in=[
    'Orientation Class - Pilot Phase',
    'Basic Computer Literacy',
    'AI Essentials and Prompt Engineering',
    'Digital Safety & Online Security',
    'Modern Digital Workspace'
])

for course in pilot_courses:
    count = Assignment.objects.filter(course=course).count()
    print(f'  {course.name}: {count}')

print()

# By work type
print('Assignments by work type:')
work_types = Assignment.objects.values_list('work_type', flat=True)
for work_type, count in Counter(work_types).most_common():
    print(f'  {work_type}: {count}')

print()

# By state
print('Assignments by state:')
states = Assignment.objects.values_list('state', flat=True)
for state, count in Counter(states).most_common():
    print(f'  {state}: {count}')

print()

# Assignments with/without due dates
with_due_date = Assignment.objects.filter(due_date__isnull=False).count()
without_due_date = Assignment.objects.filter(due_date__isnull=True).count()
print(f'Assignments with due dates: {with_due_date}')
print(f'Assignments without due dates: {without_due_date}')

print()

# Assignments with/without points
with_points = Assignment.objects.filter(max_points__isnull=False).count()
without_points = Assignment.objects.filter(max_points__isnull=True).count()
print(f'Assignments with max points: {with_points}')
print(f'Assignments without max points: {without_points}')

print()

# Sample assignments
print('Sample assignments:')
for assignment in Assignment.objects.all()[:3]:
    print(f'\nTitle: {assignment.title[:80]}...' if len(assignment.title) > 80 else f'\nTitle: {assignment.title}')
    print(f'  Course: {assignment.course.name}')
    print(f'  Work Type: {assignment.work_type}')
    print(f'  State: {assignment.state}')
    print(f'  Max Points: {assignment.max_points}')
    print(f'  Due Date: {assignment.due_date}')
    print(f'  Created: {assignment.google_creation_time}')

print()
print('=' * 80)
