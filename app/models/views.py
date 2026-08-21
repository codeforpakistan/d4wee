from django.db import models


class AttendanceWeekly(models.Model):
    """Summary of attendance for a cohort and week"""

    year_week = models.CharField(max_length=7)
    cohort_name = models.CharField(max_length=255)
    record_count = models.IntegerField(default=0)
    total_enrollments = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = "attendance_weekly"


class StudentGrades(models.Model):
    """Describe the student grades view"""

    email = models.CharField(max_length=100)
    student = models.CharField(max_length=100)
    cohort = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    grade = models.IntegerField()

    class Meta:
        managed = False
        db_table = "student_grades"
