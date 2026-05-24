import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Submission, Assignment, Student, Enrollment
from collections import Counter

print('=' * 80)
print('SUBMISSION VERIFICATION')
print('=' * 80)
print()

# Overall stats
total = Submission.objects.count()
print(f'Total submissions: {total}')
print()

# By state
print('Submissions by state:')
states = Submission.objects.values_list('state', flat=True)
for state, count in Counter(states).most_common():
    print(f'  {state}: {count}')

print()

# Graded vs ungraded
graded = Submission.objects.filter(assigned_grade__isnull=False).count()
ungraded = Submission.objects.filter(assigned_grade__isnull=True).count()
print(f'Graded submissions: {graded}')
print(f'Ungraded submissions: {ungraded}')

print()

# Late submissions
late_count = Submission.objects.filter(late=True).count()
on_time_count = Submission.objects.filter(late=False).count()
print(f'Late submissions: {late_count}')
print(f'On-time submissions: {on_time_count}')

print()

# By assignment
print('Top 10 assignments by submission count:')
from django.db.models import Count
top_assignments = Assignment.objects.annotate(
    submission_count=Count('submissions')
).order_by('-submission_count')[:10]

for assignment in top_assignments:
    print(f'  {assignment.title[:60]}: {assignment.submission_count}')

print()

# Student participation
students_with_submissions = Submission.objects.values('enrollment__student').distinct().count()
total_students = Student.objects.filter(is_pilot_student=True).count()
print(f'Students with at least one submission: {students_with_submissions} / {total_students}')

print()

# Sample submission details
print('Sample submissions:')
for submission in Submission.objects.filter(assigned_grade__isnull=False)[:5]:
    print(f'\nStudent: {submission.enrollment.student.full_name}')
    print(f'  Assignment: {submission.assignment.title[:60]}')
    print(f'  State: {submission.state}')
    print(f'  Grade: {submission.assigned_grade} / {submission.assignment.max_points}')
    if submission.grade_percentage:
        print(f'  Percentage: {submission.grade_percentage:.1f}%')
    print(f'  Late: {submission.late}')
    print(f'  Updated: {submission.google_update_time}')

print()
print('=' * 80)
