from django.db import models
from django.utils import timezone


class Course(models.Model):
    """Course catalog - independent of cohorts"""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
    ]
    
    code = models.CharField(max_length=50, unique=True, help_text="Course code (e.g., PY101)")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True, 
                                  help_text="Google Classroom course ID (if exists)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    is_visible = models.BooleanField(default=True, help_text="Show in student catalog")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def has_classroom_integration(self):
        """Check if course is linked to Google Classroom"""
        return bool(self.google_id)
    
    class Meta:
        ordering = ['code']


class Cohort(models.Model):
    """Time-bound training batches (3 months)"""
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')
    is_open_for_registration = models.BooleanField(default=False, 
                                                    help_text="Students can request to join")
    max_students = models.IntegerField(null=True, blank=True, 
                                       help_text="Maximum number of students (optional)")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    @property
    def is_active(self):
        """Check if cohort is currently active"""
        if self.status != 'ACTIVE':
            return False
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    @property
    def total_weeks(self):
        """Calculate total weeks in cohort"""
        days = (self.end_date - self.start_date).days
        return max(1, round(days / 7))
    
    @property
    def current_registrations_count(self):
        """Count current registrations"""
        return self.registrations.filter(status__in=['APPROVED', 'ACTIVE']).count()
    
    @property
    def can_accept_registrations(self):
        """Check if cohort can accept new registrations"""
        if not self.is_open_for_registration:
            return False
        if self.max_students and self.current_registrations_count >= self.max_students:
            return False
        return True
    
    class Meta:
        ordering = ['-start_date']
