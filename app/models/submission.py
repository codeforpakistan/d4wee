from django.db import models


class Submission(models.Model):
    """Student submission for an assignment"""
    class StatusChoices(models.TextChoices):
        NEW = "NEW", "New"
        CREATED = "CREATED", "Created"
        TURNED_IN = "TURNED_IN", "Turned In"
        RETURNED = "RETURNED", "Returned"
        RECLAIMED_BY_STUDENT = "RECLAIMED_BY_STUDENT", "Reclaimed by Student"
    
    # Google Classroom fields
    google_id = models.CharField(max_length=255, unique=True)
    enrollment = models.ForeignKey('Enrollment', on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE, related_name='submissions')
    state = models.CharField(max_length=50, choices=StatusChoices)
    late = models.BooleanField(default=False)
    assigned_grade = models.FloatField(null=True, blank=True)
    draft_grade = models.FloatField(null=True, blank=True)
    alternate_link = models.URLField(max_length=500, blank=True)
    
    # Timestamps from Google Classroom
    google_creation_time = models.DateTimeField(null=True, blank=True)
    google_update_time = models.DateTimeField(null=True, blank=True)
    
    # Local timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.enrollment.student.full_name} - {self.assignment.title}"
    
    @property
    def grade_percentage(self):
        """Get grade as percentage"""
        if self.assigned_grade is not None and self.assignment.max_points:
            return (self.assigned_grade / self.assignment.max_points) * 100
        return None
    
    class Meta:
        ordering = ['-google_update_time', '-created_at']
        unique_together = ['enrollment', 'assignment']
        indexes = [
            models.Index(fields=['state']),
            models.Index(fields=['late']),
        ]
