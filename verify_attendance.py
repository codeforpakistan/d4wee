import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Attendance, Cohort

pilot_cohort = Cohort.objects.get(name='Pilot')

print('=' * 80)
print('ATTENDANCE VERIFICATION')
print('=' * 80)
print()

total = Attendance.objects.filter(cohort=pilot_cohort).count()
print(f'Total PILOT attendance records: {total}')
print()

# By date
from django.db.models import Count
by_date = Attendance.objects.filter(cohort=pilot_cohort).values('date').annotate(count=Count('id')).order_by('date')

print('Attendance by date:')
for entry in by_date[:10]:
    print(f'  {entry["date"]}: {entry["count"]} submissions')

print()

# Students with attendance
students_with_attendance = Attendance.objects.filter(cohort=pilot_cohort).values('student').distinct().count()
print(f'Students with attendance records: {students_with_attendance}')

print()

# Sample records
print('Sample attendance records:')
for attendance in Attendance.objects.filter(cohort=pilot_cohort).order_by('date')[:5]:
    print(f'\n  Date: {attendance.date}')
    print(f'  Student: {attendance.student.full_name}')
    print(f'  Email: {attendance.student.email}')
    print(f'  Hours: {attendance.hours_spent}')

print()
print('=' * 80)
