from django.db import models


class Assignment(models.Model):
    """Coursework from Google Classroom"""
    WORK_TYPE_CHOICES = [
        ('ASSIGNMENT', 'Assignment'),
        ('SHORT_ANSWER_QUESTION', 'Short Answer Question'),
        ('MULTIPLE_CHOICE_QUESTION', 'Multiple Choice Question'),
    ]
    
    ASSIGNMENT_TYPE_CHOICES = [
        ('PRE_TEST', 'Pre-Test'),
        ('POST_TEST', 'Post-Test'),
        ('ASSIGNMENT', 'Assignment'),
        ('QUIZ', 'Quiz'),
    ]
    
    google_id = models.CharField(max_length=255, unique=True)
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    work_type = models.CharField(max_length=50, choices=WORK_TYPE_CHOICES, 
                                  help_text="Type from Google Classroom API")
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPE_CHOICES, 
                                       default='ASSIGNMENT',
                                       help_text="Explicit categorization for tracking")
    max_points = models.FloatField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=50, default='PUBLISHED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} ({self.course.name})"
    
    class Meta:
        ordering = ['due_date', 'title']
        indexes = [
            models.Index(fields=['assignment_type']),
            models.Index(fields=['due_date']),
        ]


class Submission(models.Model):
    """Student submission for an assignment"""
    STATE_CHOICES = [
        ('NEW', 'New'),
        ('CREATED', 'Created'),
        ('TURNED_IN', 'Turned In'),
        ('RETURNED', 'Returned'),
        ('RECLAIMED_BY_STUDENT', 'Reclaimed by Student'),
    ]
    
    google_id = models.CharField(max_length=255, unique=True)
    enrollment = models.ForeignKey('Enrollment', on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    state = models.CharField(max_length=50, choices=STATE_CHOICES)
    late = models.BooleanField(default=False)
    assigned_grade = models.FloatField(null=True, blank=True)
    draft_grade = models.FloatField(null=True, blank=True)
    creation_time = models.DateTimeField(null=True, blank=True)
    update_time = models.DateTimeField(null=True, blank=True)
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
        ordering = ['-update_time']
        unique_together = ['enrollment', 'assignment']
        indexes = [
            models.Index(fields=['state']),
            models.Index(fields=['late']),
        ]
