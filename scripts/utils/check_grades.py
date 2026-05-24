import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Submission
from collections import Counter

print('=' * 80)
print('GRADE DISTRIBUTION ANALYSIS')
print('=' * 80)
print()

# Total graded vs ungraded
total = Submission.objects.count()
graded = Submission.objects.filter(assigned_grade__isnull=False).count()
ungraded = Submission.objects.filter(assigned_grade__isnull=True).count()

print(f'Total submissions: {total}')
print(f'Graded: {graded} ({graded/total*100:.1f}%)')
print(f'Ungraded: {ungraded} ({ungraded/total*100:.1f}%)')
print()

# Grade value distribution
print('Grade values (assigned_grade):')
graded_subs = Submission.objects.filter(assigned_grade__isnull=False)
grade_values = [s.assigned_grade for s in graded_subs]

zero_grades = len([g for g in grade_values if g == 0.0])
non_zero_grades = len([g for g in grade_values if g > 0.0])

print(f'  Zero (0.0): {zero_grades}')
print(f'  Non-zero (>0.0): {non_zero_grades}')
print()

if non_zero_grades > 0:
    print('Non-zero grade distribution:')
    non_zero = [g for g in grade_values if g > 0.0]
    print(f'  Min: {min(non_zero)}')
    print(f'  Max: {max(non_zero)}')
    print(f'  Average: {sum(non_zero)/len(non_zero):.2f}')
    print()
    
    # Sample non-zero grades
    print('Sample submissions with non-zero grades:')
    for submission in Submission.objects.filter(assigned_grade__gt=0)[:10]:
        print(f'\n  Student: {submission.enrollment.student.full_name}')
        print(f'  Assignment: {submission.assignment.title[:60]}')
        print(f'  Grade: {submission.assigned_grade} / {submission.assignment.max_points}')
        if submission.grade_percentage:
            print(f'  Percentage: {submission.grade_percentage:.1f}%')
        print(f'  State: {submission.state}')
else:
    print('⚠ No non-zero grades found!')
    print()
    print('Sample graded submissions (all zeros):')
    for submission in Submission.objects.filter(assigned_grade=0.0)[:10]:
        print(f'\n  Student: {submission.enrollment.student.full_name}')
        print(f'  Assignment: {submission.assignment.title[:60]}')
        print(f'  Grade: {submission.assigned_grade} / {submission.assignment.max_points}')
        print(f'  State: {submission.state}')

print()
print('=' * 80)
