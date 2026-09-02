from django.db import models


class Course(models.Model):
    """
    Course from Google Classroom
    Maps directly to Google Classroom Course resource
    """
    class StatusChoices(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"
        PROVISIONED = "PROVISIONED", "Provisioned"
        DECLINED = "DECLINED", "Declined"
        SUSPENDED = "SUSPENDED", "Suspended"
        
    # Google Classroom fields
    google_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=500)
    section = models.CharField(max_length=500, blank=True)
    description_heading = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    room = models.CharField(max_length=255, blank=True)
    owner_id = models.CharField(max_length=255, blank=True)
    enrollment_code = models.CharField(max_length=50, blank=True)
    course_state = models.CharField(max_length=20, choices=StatusChoices, default=StatusChoices.ACTIVE)
    alternate_link = models.URLField(max_length=500, blank=True)
    teacher_group_email = models.EmailField(blank=True)
    course_group_email = models.EmailField(blank=True)
    guardians_enabled = models.BooleanField(default=False)
    calendar_id = models.CharField(max_length=255, blank=True)
    
    # Timestamps from Google Classroom
    google_creation_time = models.DateTimeField(null=True, blank=True)
    google_update_time = models.DateTimeField(null=True, blank=True)
    
    # Local fields
    is_available = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    @property
    def display_name(self):
        """Full display name with section"""
        return self.name
    
    @property
    def is_active(self):
        """Check if course is active in Google Classroom"""
        return self.course_state == 'ACTIVE'
    
    @property
    def is_archived(self):
        """Check if course is archived"""
        return self.course_state == 'ARCHIVED'
    
    @property
    def student_count(self):
        """Count of unique students enrolled in this course"""
        return self.enrollments.values('student').distinct().count()
    
    @property
    def assignment_count(self):
        """Count of assignments in this course"""
        return self.assignments.count()
    
    @property
    def average_completion_rate(self):
        """Average completion rate across all enrollments"""
        enrollments = list(self.enrollments.all())
        if not enrollments:
            return 0
        total = sum(e.completion_rate or 0 for e in enrollments)
        return total / len(enrollments)
    
    @property
    def ungraded_assignments_count(self):
        """Count of assignments with ungraded submissions"""
        from .submission import Submission
        count = 0
        for assignment in self.assignments.all():
            if Submission.objects.filter(
                assignment=assignment,
                state='TURNED_IN',
                assigned_grade__isnull=True
            ).exists():
                count += 1
        return count
    
    class Meta:
        ordering = ['name', 'section']
        indexes = [
            models.Index(fields=['google_id']),
            models.Index(fields=['course_state']),
        ]


