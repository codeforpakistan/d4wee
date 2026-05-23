from django.db import models
from django.contrib.auth.models import User


class Student(models.Model):
    """
    Student from Google Classroom
    
    TWO SCENARIOS:
    1. PILOT Cohort (Legacy): Students auto-created from Google Classroom sync
    2. Future Students: Register first, then link to Google Classroom on first OAuth login
    
    Django User account is optional - only created when student logs in via OAuth
    """
    # Google Classroom fields
    google_id = models.CharField(
        max_length=255, 
        unique=True, 
        help_text="Google user ID (userId from Google Classroom)"
    )
    email = models.EmailField(
        unique=True,
        help_text="Email address from Google profile"
    )
    full_name = models.CharField(max_length=500, help_text="Full name from Google profile")
    given_name = models.CharField(max_length=255, blank=True, help_text="Given/first name")
    family_name = models.CharField(max_length=255, blank=True, help_text="Family/last name")
    photo_url = models.URLField(
        max_length=500, 
        blank=True, 
        help_text="Profile photo URL from Google"
    )
    
    # Django User account (optional - only if student has logged in)
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        help_text="Django user account if student has logged in"
    )
    
    # Local fields
    city = models.CharField(max_length=100, blank=True, help_text="City (local data)")
    unique_id = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="D4WEE unique ID (local data)"
    )
    is_pilot_student = models.BooleanField(
        default=False,
        help_text="Student from PILOT cohort (legacy data)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.full_name
    
    @property
    def has_logged_in(self):
        """Check if student has a Django user account"""
        return self.user is not None
    
    class Meta:
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['google_id']),
        ]
