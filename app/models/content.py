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
    
    STATE_CHOICES = [
        ('PUBLISHED', 'Published'),
        ('DRAFT', 'Draft'),
        ('DELETED', 'Deleted'),
    ]
    
    # Google Classroom fields
    google_id = models.CharField(max_length=255, unique=True, help_text="Google Classroom coursework ID")
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=1000)
    description = models.TextField(blank=True)
    work_type = models.CharField(max_length=50, choices=WORK_TYPE_CHOICES, 
                                  help_text="Type from Google Classroom API")
    state = models.CharField(max_length=50, choices=STATE_CHOICES, default='PUBLISHED')
    max_points = models.FloatField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True, help_text="Combined dueDate + dueTime")
    topic_id = models.CharField(max_length=255, blank=True, help_text="Google Classroom topic ID")
    alternate_link = models.URLField(max_length=500, blank=True, help_text="Link to assignment in Google Classroom")
    
    # Timestamps from Google Classroom
    google_creation_time = models.DateTimeField(null=True, blank=True)
    google_update_time = models.DateTimeField(null=True, blank=True)
    
    # Local fields
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPE_CHOICES, 
                                       default='ASSIGNMENT',
                                       help_text="Explicit categorization for tracking (PRE_TEST, POST_TEST, etc.)")
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


class Submission(models.Model):
    """Student submission for an assignment"""
    STATE_CHOICES = [
        ('NEW', 'New'),
        ('CREATED', 'Created'),
        ('TURNED_IN', 'Turned In'),
        ('RETURNED', 'Returned'),
        ('RECLAIMED_BY_STUDENT', 'Reclaimed by Student'),
    ]
    
    # Google Classroom fields
    google_id = models.CharField(max_length=255, unique=True, help_text="Google Classroom submission ID")
    enrollment = models.ForeignKey('Enrollment', on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    state = models.CharField(max_length=50, choices=STATE_CHOICES)
    late = models.BooleanField(default=False, help_text="Whether submission was late")
    assigned_grade = models.FloatField(null=True, blank=True, help_text="Final assigned grade")
    draft_grade = models.FloatField(null=True, blank=True, help_text="Draft grade before returning")
    alternate_link = models.URLField(max_length=500, blank=True, help_text="Link to submission in Google Classroom")
    
    # Timestamps from Google Classroom
    google_creation_time = models.DateTimeField(null=True, blank=True, help_text="When submission was created")
    google_update_time = models.DateTimeField(null=True, blank=True, help_text="When submission was last updated")
    
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
