from django.db import models
from django.contrib.auth.models import User


class Student(models.Model):
    """Student profile - created when first Registration is approved"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    google_id = models.CharField(max_length=255, unique=True, help_text="Google ID from OAuth")
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    profile_photo = models.URLField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    unique_id = models.CharField(max_length=100, blank=True, help_text="D4WEE unique ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    class Meta:
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['google_id']),
        ]
