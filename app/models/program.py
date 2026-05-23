from django.db import models
from django.utils import timezone


class Course(models.Model):
    """
    Course from Google Classroom
    Maps directly to Google Classroom Course resource
    """
    COURSE_STATE_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
        ('PROVISIONED', 'Provisioned'),
        ('DECLINED', 'Declined'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    # Google Classroom fields
    google_id = models.CharField(
        max_length=255, 
        unique=True, 
        help_text="Google Classroom course ID"
    )
    name = models.CharField(max_length=500, help_text="Course name")
    section = models.CharField(max_length=500, blank=True, help_text="Course section")
    description_heading = models.CharField(
        max_length=500, 
        blank=True, 
        help_text="Short description heading"
    )
    description = models.TextField(blank=True, help_text="Full course description")
    room = models.CharField(max_length=255, blank=True, help_text="Classroom room location")
    owner_id = models.CharField(max_length=255, blank=True, help_text="Google user ID of owner")
    enrollment_code = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Enrollment code for students"
    )
    course_state = models.CharField(
        max_length=20, 
        choices=COURSE_STATE_CHOICES, 
        default='ACTIVE',
        help_text="Course state in Google Classroom"
    )
    alternate_link = models.URLField(
        max_length=500, 
        blank=True, 
        help_text="Link to course in Google Classroom"
    )
    teacher_group_email = models.EmailField(blank=True, help_text="Teacher group email")
    course_group_email = models.EmailField(blank=True, help_text="Course group email")
    guardians_enabled = models.BooleanField(default=False, help_text="Are guardians enabled")
    calendar_id = models.CharField(max_length=255, blank=True, help_text="Calendar ID")
    
    # Timestamps from Google Classroom
    google_creation_time = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="When course was created in Google Classroom"
    )
    google_update_time = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="When course was last updated in Google Classroom"
    )
    
    # Local fields
    is_visible = models.BooleanField(
        default=True, 
        help_text="Show in student catalog"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.section:
            return f"{self.name} - {self.section}"
        return self.name
    
    @property
    def display_name(self):
        """Full display name with section"""
        if self.section:
            return f"{self.name} ({self.section})"
        return self.name
    
    @property
    def is_active(self):
        """Check if course is active in Google Classroom"""
        return self.course_state == 'ACTIVE'
    
    @property
    def is_archived(self):
        """Check if course is archived"""
        return self.course_state == 'ARCHIVED'
    
    class Meta:
        ordering = ['name', 'section']
        indexes = [
            models.Index(fields=['google_id']),
            models.Index(fields=['course_state']),
        ]


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
