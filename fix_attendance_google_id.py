#!/usr/bin/env python
"""Fix missing google_id in attendance records by matching email to Student records"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'd4wee.settings')
django.setup()

from core.models import Student, AttendanceRecord

print("🔧 Fixing missing google_id in attendance records...\n")

# Find all attendance records with empty google_id
missing_gid = AttendanceRecord.objects.filter(google_id='')
print(f"Found {missing_gid.count()} records with missing google_id\n")

fixed_count = 0
not_found_count = 0

for record in missing_gid:
    # Try to match student by email
    student = Student.objects.filter(email__iexact=record.student_email).first()
    
    if student:
        record.google_id = student.google_id
        record.save()
        print(f"✅ Fixed: {record.student_name} ({record.student_email}) - Week {record.week_number}")
        print(f"   Added google_id: {student.google_id}")
        fixed_count += 1
    else:
        print(f"⚠️  No match: {record.student_name} ({record.student_email}) - Week {record.week_number}")
        not_found_count += 1

print(f"\n📊 Summary:")
print(f"   Fixed: {fixed_count} records")
print(f"   Not found: {not_found_count} records")
