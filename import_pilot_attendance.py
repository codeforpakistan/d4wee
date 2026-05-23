"""
Import attendance data from Google Sheets JSON into database
"""
import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Attendance, Student, Cohort
from django.utils import timezone

# Load the JSON data
with open('data/pilot_attendance.json', 'r', encoding='utf-8') as f:
    attendance_data = json.load(f)

print('=' * 80)
print('IMPORTING ATTENDANCE DATA')
print('=' * 80)
print(f'Total records in JSON: {len(attendance_data)}')
print()

# Get PILOT cohort
pilot_cohort = Cohort.objects.get(name='Pilot')
print(f'Target cohort: {pilot_cohort.name}')
print()

created_count = 0
updated_count = 0
skipped_count = 0
error_count = 0

for idx, record in enumerate(attendance_data, 1):
    try:
        # Extract fields
        timestamp_str = record.get('Timestamp', '').strip()
        email = record.get('Email Address', '').strip()
        hours_daily_str = record.get('How many hours do you spend daily on your course(s).   ', '').strip()
        
        # Skip if no email or timestamp
        if not email or not timestamp_str:
            skipped_count += 1
            continue
        
        # Parse timestamp to get date
        try:
            timestamp = datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
            attendance_date = timestamp.date()
        except ValueError:
            print(f'  [{idx}] Invalid timestamp: {timestamp_str}')
            error_count += 1
            continue
        
        # Find student by email
        student = Student.objects.filter(email__iexact=email).first()
        if not student:
            # Try to find by email in the student records
            error_count += 1
            continue
        
        # Parse hours (if provided)
        hours_spent = None
        if hours_daily_str:
            try:
                hours_spent = float(hours_daily_str)
            except (ValueError, TypeError):
                pass
        
        # Create or update attendance record
        attendance, created = Attendance.objects.update_or_create(
            student=student,
            cohort=pilot_cohort,
            date=attendance_date,
            defaults={
                'hours_spent': hours_spent,
            }
        )
        
        if created:
            created_count += 1
        else:
            updated_count += 1
            
    except Exception as e:
        print(f'  [{idx}] Error: {e}')
        error_count += 1
        continue

print()
print('=' * 80)
print('IMPORT SUMMARY')
print('=' * 80)
print(f'Created: {created_count}')
print(f'Updated: {updated_count}')
print(f'Skipped: {skipped_count}')
print(f'Errors: {error_count}')
print()
print(f'Total attendance records in database: {Attendance.objects.filter(cohort=pilot_cohort).count()}')
print('=' * 80)
