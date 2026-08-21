from django.db import models


class Assignment(models.Model):
    """Coursework from Google Classroom"""
    class WorkTypes(models.TextChoices):
        ASSIGNMENT = "Assignment"
        SHORT_ANSWER_QUESTION = "Short Answer Question"
        MULTIPLE_CHOICE_QUESTION = "Multiple Choice Question"

    class AssignmentType(models.TextChoices):
        PRE_TEST = "Pre-Test"
        POST_TEST = "Post-Test"
        ASSIGNMENT = "Assignment"
        QUIZ = "Quiz"

    class StatusChoices(models.TextChoices):
        PUBLISHED = "Published"
        DRAFT = "Draft"
        DELETED = "Deleted"
    
    # Google Classroom fields
    google_id = models.CharField(max_length=255, unique=True)
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=1000)
    description = models.TextField(blank=True)
    work_type = models.CharField(max_length=50, choices=WorkTypes)
    state = models.CharField(max_length=50, choices=StatusChoices, default=StatusChoices.PUBLISHED)
    max_points = models.FloatField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    topic_id = models.CharField(max_length=255, blank=True)
    alternate_link = models.URLField(max_length=500, blank=True)
    
    # Timestamps from Google Classroom
    google_creation_time = models.DateTimeField(null=True, blank=True)
    google_update_time = models.DateTimeField(null=True, blank=True)
    
    # Local fields
    assignment_type = models.CharField(max_length=20, choices=AssignmentType, default=AssignmentType.ASSIGNMENT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title[:100]} ({self.course.name})"
    
    class Meta:
        ordering = ['due_date', 'title']
        indexes = [
            models.Index(fields=['assignment_type']),
            models.Index(fields=['due_date']),
        ]

