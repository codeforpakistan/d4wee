from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Registration(models.Model):
    """Student enrolled in Cohort"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('DECLINED', 'Declined'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('DROPPED', 'Dropped'),
    ]
    
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='registrations')
    cohort = models.ForeignKey('Cohort', on_delete=models.CASCADE, related_name='registrations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    requested_date = models.DateTimeField(auto_now_add=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_registrations')
    completion_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Admin notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.full_name} - {self.cohort.name} ({self.status})"
    
    # State transition methods (fat model)
    def approve(self, admin_user):
        """Approve registration"""
        self.status = 'APPROVED'
        self.approved_by = admin_user
        self.approved_date = timezone.now()
        self.save()
    
    def decline(self, admin_user, reason=""):
        """Decline registration"""
        self.status = 'DECLINED'
        self.approved_by = admin_user
        self.notes = f"Declined: {reason}\n{self.notes}" if reason else self.notes
        self.save()
    
    def activate(self):
        """Move from approved to active"""
        if self.status == 'APPROVED':
            self.status = 'ACTIVE'
            self.save()
    
    def complete(self):
        """Mark as completed"""
        if self.certificate_eligible:
            self.status = 'COMPLETED'
            self.completion_date = timezone.now()
            self.save()
            return True
        return False
    
    # Calculated properties (fat model)
    @property
    def session_attendance_rate(self):
        """Calculate attendance rate for this registration"""
        from .tracking import AttendanceRecord
        
        total_weeks = self.cohort.total_weeks
        if total_weeks == 0:
            return 0.0
        
        attended_weeks = AttendanceRecord.objects.filter(
            student=self.student,
            cohort=self.cohort
        ).values('week_number').distinct().count()
        
        return (attended_weeks / total_weeks) * 100
    
    @property
    def overall_completion_rate(self):
        """Average completion rate across all enrollments"""
        enrollments = self.enrollments.all()
        if not enrollments:
            return 0.0
        
        rates = [e.completion_rate for e in enrollments]
        return sum(rates) / len(rates) if rates else 0.0
    
    @property
    def overall_average_score(self):
        """Average score across all enrollments"""
        enrollments = self.enrollments.all()
        if not enrollments:
            return None
        
        scores = [e.overall_average_score for e in enrollments if e.overall_average_score is not None]
        return sum(scores) / len(scores) if scores else None
    
    @property
    def courses_enrolled_count(self):
        """Count of courses enrolled"""
        return self.enrollments.count()
    
    @property
    def courses_completed_count(self):
        """Count of completed courses"""
        return self.enrollments.filter(status='COMPLETED').count()
    
    @property
    def certificate_eligible(self):
        """Check if student is eligible for certificate"""
        # Must have at least 75% attendance
        if self.session_attendance_rate < 75:
            return False
        
        # Must have average score of at least 50%
        avg_score = self.overall_average_score
        if avg_score is None or avg_score < 50:
            return False
        
        # Must have attempted all pre and post tests
        for enrollment in self.enrollments.all():
            if not enrollment.pre_test_attempted or not enrollment.post_test_attempted:
                return False
        
        return True
    
    @property
    def eligibility_notes(self):
        """Get reasons for certificate ineligibility"""
        if self.certificate_eligible:
            return "Meets all certificate requirements"
        
        reasons = []
        
        if self.session_attendance_rate < 75:
            reasons.append(f"Attendance ({self.session_attendance_rate:.1f}%) below 75%")
        
        avg_score = self.overall_average_score
        if avg_score is None:
            reasons.append("No grades available")
        elif avg_score < 50:
            reasons.append(f"Average score ({avg_score:.1f}%) below 50%")
        
        for enrollment in self.enrollments.all():
            if not enrollment.pre_test_attempted:
                reasons.append(f"Pre-test not attempted for {enrollment.course.code}")
            if not enrollment.post_test_attempted:
                reasons.append(f"Post-test not attempted for {enrollment.course.code}")
        
        return "; ".join(reasons)
    
    class Meta:
        ordering = ['-requested_date']
        unique_together = ['student', 'cohort']
        verbose_name_plural = 'Registrations'


class Enrollment(models.Model):
    """Student taking Course within Cohort context"""
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('DROPPED', 'Dropped'),
    ]
    
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='enrollments')
    cohort = models.ForeignKey('Cohort', on_delete=models.CASCADE, related_name='enrollments')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    completion_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.full_name} - {self.course.code} ({self.cohort.name})"
    
    # Helper methods (fat model)
    def get_assignments(self, assignment_type=None):
        """Get assignments for this course, optionally filtered by type"""
        qs = self.course.assignments.all()
        if assignment_type:
            qs = qs.filter(assignment_type=assignment_type)
        return qs
    
    def get_missing_assignments(self):
        """Get assignments that haven't been submitted"""
        submitted_assignment_ids = self.submissions.values_list('assignment_id', flat=True)
        return self.course.assignments.exclude(
            id__in=submitted_assignment_ids
        ).filter(assignment_type='ASSIGNMENT')
    
    def get_late_submissions(self):
        """Get submissions that were late"""
        return self.submissions.filter(late=True)
    
    # Calculated properties for Pre/Post tests (fat model)
    @property
    def pre_test_attempted(self):
        """Check if pre-test was attempted"""
        return self.submissions.filter(
            assignment__assignment_type='PRE_TEST'
        ).exists()
    
    @property
    def pre_test_score(self):
        """Get pre-test score as percentage"""
        submission = self.submissions.filter(
            assignment__assignment_type='PRE_TEST',
            assigned_grade__isnull=False,
            assignment__max_points__isnull=False
        ).select_related('assignment').first()
        
        if submission and submission.assigned_grade is not None and submission.assignment.max_points:
            return (submission.assigned_grade / submission.assignment.max_points) * 100
        return None
    
    @property
    def post_test_attempted(self):
        """Check if post-test was attempted"""
        return self.submissions.filter(
            assignment__assignment_type='POST_TEST'
        ).exists()
    
    @property
    def post_test_score(self):
        """Get post-test score as percentage"""
        submission = self.submissions.filter(
            assignment__assignment_type='POST_TEST',
            assigned_grade__isnull=False,
            assignment__max_points__isnull=False
        ).select_related('assignment').first()
        
        if submission and submission.assigned_grade is not None and submission.assignment.max_points:
            return (submission.assigned_grade / submission.assignment.max_points) * 100
        return None
    
    @property
    def improvement_rate(self):
        """Calculate improvement from pre to post test"""
        pre = self.pre_test_score
        post = self.post_test_score
        if pre is not None and post is not None:
            return post - pre
        return None
    
    # Calculated properties for Assignments (fat model)
    @property
    def total_assignments(self):
        """Count total assignments (excludes pre/post/quizzes)"""
        return self.course.assignments.filter(assignment_type='ASSIGNMENT').count()
    
    @property
    def completed_assignments(self):
        """Count completed assignments"""
        return self.submissions.filter(
            assignment__assignment_type='ASSIGNMENT',
            state__in=['TURNED_IN', 'RETURNED']
        ).count()
    
    @property
    def assignment_completion_rate(self):
        """Calculate assignment completion rate"""
        total = self.total_assignments
        if total == 0:
            return 0.0
        return (self.completed_assignments / total) * 100
    
    @property
    def missing_assignments_count(self):
        """Count missing assignments"""
        return self.total_assignments - self.completed_assignments
    
    @property
    def late_assignments_count(self):
        """Count late assignments"""
        return self.submissions.filter(
            assignment__assignment_type='ASSIGNMENT',
            late=True
        ).count()
    
    @property
    def assignment_average_score(self):
        """Average score for assignments only"""
        submissions = self.submissions.filter(
            assignment__assignment_type='ASSIGNMENT',
            assigned_grade__isnull=False,
            assignment__max_points__isnull=False,
            assignment__max_points__gt=0
        ).select_related('assignment')
        
        if not submissions:
            return None
        
        scores = []
        for sub in submissions:
            if sub.assigned_grade is not None and sub.assignment.max_points:
                percentage = (sub.assigned_grade / sub.assignment.max_points) * 100
                scores.append(percentage)
        
        return sum(scores) / len(scores) if scores else None
    
    # Calculated properties for Quizzes (fat model)
    @property
    def total_quizzes(self):
        """Count total quizzes"""
        return self.course.assignments.filter(assignment_type='QUIZ').count()
    
    @property
    def completed_quizzes(self):
        """Count completed quizzes"""
        return self.submissions.filter(
            assignment__assignment_type='QUIZ',
            state__in=['TURNED_IN', 'RETURNED']
        ).count()
    
    @property
    def quiz_average_score(self):
        """Average score for quizzes"""
        submissions = self.submissions.filter(
            assignment__assignment_type='QUIZ',
            assigned_grade__isnull=False,
            assignment__max_points__isnull=False,
            assignment__max_points__gt=0
        ).select_related('assignment')
        
        if not submissions:
            return None
        
        scores = []
        for sub in submissions:
            if sub.assigned_grade is not None and sub.assignment.max_points:
                percentage = (sub.assigned_grade / sub.assignment.max_points) * 100
                scores.append(percentage)
        
        return sum(scores) / len(scores) if scores else None
    
    # Overall metrics (fat model)
    @property
    def completion_rate(self):
        """Overall completion rate (all work types)"""
        total = self.course.assignments.count()
        if total == 0:
            return 0.0
        
        completed = self.submissions.filter(
            state__in=['TURNED_IN', 'RETURNED']
        ).count()
        
        return (completed / total) * 100
    
    @property
    def on_time_rate(self):
        """Percentage of work submitted on time"""
        total = self.submissions.count()
        if total == 0:
            return 0.0
        
        on_time = self.submissions.filter(late=False).count()
        return (on_time / total) * 100
    
    @property
    def overall_average_score(self):
        """Average score across assignments and quizzes (excludes pre/post tests)"""
        submissions = self.submissions.filter(
            assignment__assignment_type__in=['ASSIGNMENT', 'QUIZ'],
            assigned_grade__isnull=False,
            assignment__max_points__isnull=False,
            assignment__max_points__gt=0
        ).select_related('assignment')
        
        if not submissions:
            return None
        
        scores = []
        for sub in submissions:
            if sub.assigned_grade is not None and sub.assignment.max_points:
                percentage = (sub.assigned_grade / sub.assignment.max_points) * 100
                scores.append(percentage)
        
        return sum(scores) / len(scores) if scores else None
    
    @property
    def category(self):
        """Categorize student: FOCUS, PUSH, or PRAISE"""
        completion = self.assignment_completion_rate
        score = self.assignment_average_score or self.overall_average_score
        
        # FOCUS: Low completion or low scores
        if completion < 60 or (score is not None and score < 60):
            return 'FOCUS'
        
        # PRAISE: High completion and high scores
        if completion >= 85 and (score is None or score >= 85):
            return 'PRAISE'
        
        # PUSH: Everything else
        return 'PUSH'
    
    class Meta:
        ordering = ['-enrolled_date']
        unique_together = ['student', 'course', 'cohort']
        verbose_name_plural = 'Enrollments'
