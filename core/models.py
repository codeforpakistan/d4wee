from django.db import models
from django.contrib.auth.models import User


class Course(models.Model):
    """Google Classroom Course/Cohort"""
    google_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    section = models.CharField(max_length=255, blank=True)
    description_heading = models.TextField(blank=True)
    enrollment_code = models.CharField(max_length=50, blank=True)
    course_state = models.CharField(max_length=50, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']


class Student(models.Model):
    """Student in a course"""
    google_id = models.CharField(max_length=255)  # Removed unique=True since students can be in multiple courses
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students')
    email = models.EmailField()
    full_name = models.CharField(max_length=255)
    profile_photo = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.full_name} ({self.course.name})"
    
    class Meta:
        ordering = ['full_name']
        unique_together = ['google_id', 'course']


class Assignment(models.Model):
    """Course work (assignment, quiz, test)"""
    WORK_TYPE_CHOICES = [
        ('ASSIGNMENT', 'Assignment'),
        ('SHORT_ANSWER_QUESTION', 'Short Answer Question'),
        ('MULTIPLE_CHOICE_QUESTION', 'Multiple Choice Question'),
    ]
    
    google_id = models.CharField(max_length=255, unique=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    work_type = models.CharField(max_length=50, choices=WORK_TYPE_CHOICES)
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
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='submissions')
    state = models.CharField(max_length=50, choices=STATE_CHOICES)
    late = models.BooleanField(default=False)
    assigned_grade = models.FloatField(null=True, blank=True)
    draft_grade = models.FloatField(null=True, blank=True)
    creation_time = models.DateTimeField(null=True, blank=True)
    update_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.full_name} - {self.assignment.title}"
    
    class Meta:
        ordering = ['-update_time']
        unique_together = ['assignment', 'student']


class StudentMetrics(models.Model):
    """Calculated metrics for student performance"""
    CATEGORY_CHOICES = [
        ('FOCUS', 'Needs Focus'),
        ('PUSH', 'Needs Push'),
        ('PRAISE', 'Deserves Praise'),
    ]
    
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='metrics')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='student_metrics')
    
    # Metrics
    completion_rate = models.FloatField(default=0.0)  # Percentage of assignments completed
    average_score = models.FloatField(null=True, blank=True)  # Average grade across all assignments
    on_time_rate = models.FloatField(default=0.0)  # Percentage submitted on time
    late_submissions = models.IntegerField(default=0)
    missing_submissions = models.IntegerField(default=0)
    
    # Categorization
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, null=True, blank=True)
    
    # Metadata
    last_calculated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.full_name} Metrics"
    
    class Meta:
        verbose_name_plural = 'Student Metrics'


class SyncLog(models.Model):
    """Track data synchronization from Google Classroom"""
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, default='IN_PROGRESS')
    courses_synced = models.IntegerField(default=0)
    students_synced = models.IntegerField(default=0)
    assignments_synced = models.IntegerField(default=0)
    submissions_synced = models.IntegerField(default=0)
    errors = models.TextField(blank=True)
    
    def __str__(self):
        return f"Sync {self.id} - {self.status} ({self.started_at})"
    
    class Meta:
        ordering = ['-started_at']
