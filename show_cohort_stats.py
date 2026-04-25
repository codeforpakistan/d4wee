#!/usr/bin/env python
"""Show cohort completion statistics"""

from core.models import Cohort, CohortEnrollment, Certificate

print('\nCohort Completion Statistics')
print('=' * 80)

cohorts = Cohort.objects.all()

for cohort in cohorts:
    print(f'\n{cohort.name}')
    print(f'  Period: {cohort.start_date} to {cohort.end_date}')
    print(f'  Status: {"Active" if cohort.is_active else "Inactive"}, {"Closed" if cohort.is_closed else "Open"}')
    
    enrollments = CohortEnrollment.objects.filter(cohort=cohort)
    total = enrollments.count()
    completed = enrollments.filter(status='COMPLETED').count()
    in_progress = enrollments.filter(status='IN_PROGRESS').count()
    dropped = enrollments.filter(status='DROPPED').count()
    enrolled = enrollments.filter(status='ENROLLED').count()
    
    print(f'\n  Enrollments:')
    print(f'    Total: {total}')
    print(f'    Completed: {completed}')
    print(f'    In Progress: {in_progress}')
    print(f'    Enrolled: {enrolled}')
    print(f'    Dropped: {dropped}')
    
    if total > 0:
        completion_rate = (completed / total) * 100
        print(f'    Completion Rate: {completion_rate:.1f}%')
    
    certificates = Certificate.objects.filter(cohort=cohort)
    print(f'\n  Certificates Issued: {certificates.count()}')
    
    # Show courses in this cohort
    courses = cohort.courses.all()
    if courses.exists():
        print(f'\n  Courses ({courses.count()}):')
        for course in courses:
            print(f'    - {course.name}')

print('\n' + '=' * 80)
