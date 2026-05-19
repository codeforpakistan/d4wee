#!/usr/bin/env python
"""Check student attendance data"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from app.models import Student, AttendanceRecord

google_id = '106106480963001484845'

# Find student
student = Student.objects.filter(google_id=google_id).first()
if student:
    print(f"✅ Student Found:")
    print(f"   Name: {student.full_name}")
    print(f"   Email: {student.email}")
    print(f"   Google ID: {student.google_id}")
    print(f"   Course: {student.course.name}")
else:
    print(f"❌ Student with google_id {google_id} not found")
    print("\nSearching all students...")
    all_students = Student.objects.all()[:10]
    for s in all_students:
        print(f"  - {s.full_name} ({s.email}) - {s.google_id}")
    exit()

print(f"\n📊 Attendance Records:")

# Check attendance with google_id
att_with_gid = AttendanceRecord.objects.filter(google_id=google_id)
print(f"\n   With google_id '{google_id}': {att_with_gid.count()} records")
if att_with_gid.exists():
    weeks = att_with_gid.values('week_number').distinct().count()
    print(f"   Unique weeks: {weeks}")
    for record in att_with_gid.order_by('week_number'):
        print(f"     - Week {record.week_number}: {record.date} ({record.student_email})")

# Check attendance with email
att_with_email = AttendanceRecord.objects.filter(student_email__iexact=student.email)
print(f"\n   With email '{student.email}': {att_with_email.count()} records")
if att_with_email.exists():
    weeks = att_with_email.values('week_number').distinct().count()
    print(f"   Unique weeks: {weeks}")
    for record in att_with_email.order_by('week_number'):
        print(f"     - Week {record.week_number}: {record.date} (google_id: '{record.google_id}')")

# Check for similar emails (typos)
email_base = student.email.split('@')[0]
att_similar = AttendanceRecord.objects.filter(student_email__icontains=email_base).exclude(student_email__iexact=student.email)
if att_similar.exists():
    print(f"\n   ⚠️  Similar emails found (possible typos): {att_similar.count()} records")
    for record in att_similar.order_by('week_number'):
        print(f"     - Week {record.week_number}: {record.date} ({record.student_email}) [google_id: '{record.google_id}']")

# Calculate what the rate should be
total_weeks = AttendanceRecord.objects.values('week_number').distinct().count()
print(f"\n📈 Attendance Calculation:")
print(f"   Total weeks in system: {total_weeks}")
print(f"   Weeks attended (by google_id): {att_with_gid.values('week_number').distinct().count() if att_with_gid.exists() else 0}")
print(f"   Weeks attended (by email): {att_with_email.values('week_number').distinct().count() if att_with_email.exists() else 0}")
if att_with_gid.exists() and total_weeks > 0:
    rate = round((att_with_gid.values('week_number').distinct().count() / total_weeks) * 100, 1)
    print(f"   Attendance rate: {rate}%")
