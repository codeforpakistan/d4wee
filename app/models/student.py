from django.contrib.auth.models import User
from django.db import models

from .enrollment import Enrollment


class Student(models.Model):
    """
    Student from Google Classroom
    
    TWO SCENARIOS:
    1. PILOT Cohort (Legacy): Students auto-created from Google Classroom sync
    2. Future Students: Register first, then link to Google Classroom on first OAuth login
    
    Django User account is optional - only created when student logs in via OAuth
    """
    # Django User account (optional - only if student has logged in)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_profile')
    # Google Classroom fields
    google_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=500)
    given_name = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    photo_url = models.URLField(max_length=500, blank=True)
    # Local fields
    city = models.CharField(max_length=100, blank=True)
    unique_id = models.CharField(max_length=100, blank=True)
    is_pilot_student = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.full_name
    
    @property
    def has_logged_in(self):
        """Check if student has a Django user account"""
        return self.user is not None
    
    @property
    def has_active_registration(self):
        """Check if student has an approved registration"""
        from .registration import Registration
        return Registration.objects.filter(
            student=self,
            status='APPROVED'
        ).exists()
    
    @property
    def enrollment_count(self):
        """Count of course enrollments (visible courses)"""
        return Enrollment.objects.filter(registration__student=self, course__is_visible=True).count()
    
    @property
    def average_completion_rate(self):
        """Average completion rate across all enrollments (visible courses)"""
        enrollments = list(Enrollment.objects.filter(registration__student=self, course__is_visible=True))
        if not enrollments:
            return 0
        total = sum(e.completion_rate or 0 for e in enrollments)
        return total / len(enrollments)
    
    @property
    def average_score(self):
        """Average score across all enrollments (visible courses)"""
        enrollments = list(Enrollment.objects.filter(registration__student=self, course__is_visible=True))
        scores = [e.overall_average_score for e in enrollments if e.overall_average_score is not None]
        return sum(scores) / len(scores) if scores else 0
    
    @property
    def average_improvement(self):
        """Average improvement rate across enrollments with pre/post tests (visible courses)"""
        enrollments = list(Enrollment.objects.filter(registration__student=self, course__is_visible=True))
        improvements = [e.improvement_rate for e in enrollments if e.improvement_rate is not None]
        return sum(improvements) / len(improvements) if improvements else 0
    
    @property
    def has_improvement_data(self):
        """Check if student has any improvement data (pre/post tests) (visible courses)"""
        enrollments = list(Enrollment.objects.filter(registration__student=self, course__is_visible=True))
        return any(e.improvement_rate is not None for e in enrollments)
    
    @property
    def average_on_time_rate(self):
        """Average on-time submission rate across all enrollments (visible courses)"""
        enrollments = list(Enrollment.objects.filter(registration__student=self, course__is_visible=True))
        if not enrollments:
            return 0
        rates = [e.on_time_rate or 0 for e in enrollments]
        return sum(rates) / len(rates)
    
    @property
    def attendance_rate(self):
        """Attendance rate averaged across all approved registrations"""
        from .registration import Registration
        approved_regs = Registration.objects.filter(
            student=self,
            status='APPROVED'
        )
        if not approved_regs.exists():
            return 0
        
        # Calculate average attendance rate across all approved registrations
        rates = [reg.session_attendance_rate for reg in approved_regs]
        return sum(rates) / len(rates) if rates else 0
    
    @property
    def total_attendance_hours(self):
        """Total hours spent in attendance sessions"""
        from .attendance import Attendance
        return sum(a.hours_spent or 0 for a in Attendance.objects.filter(student=self))
    
    @property
    def total_attendance_weeks(self):
        """Count of attendance records (weeks)"""
        from .attendance import Attendance
        return Attendance.objects.filter(student=self).count()
    
    class Meta:
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['google_id']),
        ]
