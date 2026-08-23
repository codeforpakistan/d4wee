from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Registration(models.Model):
    """Student enrolled in Cohort"""

    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    student = models.ForeignKey("Student", on_delete=models.CASCADE, related_name="registrations")
    cohort = models.ForeignKey("Cohort", on_delete=models.CASCADE, related_name="registrations")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    requested_date = models.DateTimeField(auto_now_add=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_registrations")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.cohort.name} ({self.status})"

    # State transition methods (fat model)
    def approve(self, admin_user):
        """Approve registration"""
        self.status = self.StatusChoices.APPROVED
        self.approved_by = admin_user
        self.approved_date = timezone.now()
        self.save()

    def reject(self, admin_user, reason=""):
        """Reject registration"""
        self.status = self.StatusChoices.REJECTED
        self.approved_by = admin_user
        self.notes = f"Rejected: {reason}\n{self.notes}" if reason else self.notes
        self.save()

    # Calculated properties (fat model)
    @property
    def session_attendance_rate(self):
        """Calculate attendance rate for this registration"""
        from .attendance import Attendance

        total_weeks = self.cohort.total_weeks
        if total_weeks == 0:
            return 0.0

        # Get all attendance records and count distinct weeks in Python
        # (week_number is a property, not a database field)
        attendance_records = Attendance.objects.filter(
            student=self.student, cohort=self.cohort
        )
        unique_weeks = set(record.week_number for record in attendance_records)
        attended_weeks = len(unique_weeks)

        return (attended_weeks / total_weeks) * 100

    @property
    def overall_completion_rate(self):
        """Average completion rate across all enrollments (visible courses)"""
        enrollments = self.enrollments.filter(course__is_visible=True)
        if not enrollments:
            return 0.0

        rates = [e.completion_rate for e in enrollments]
        return sum(rates) / len(rates) if rates else 0.0

    @property
    def overall_average_score(self):
        """Average score across all enrollments (visible courses)"""
        enrollments = self.enrollments.filter(course__is_visible=True)
        if not enrollments:
            return None

        scores = [
            e.overall_average_score
            for e in enrollments
            if e.overall_average_score is not None
        ]
        return sum(scores) / len(scores) if scores else None

    @property
    def courses_enrolled_count(self):
        """Count of courses enrolled (visible courses)"""
        return self.enrollments.filter(course__is_visible=True).count()

    @property
    def courses_completed_count(self):
        """Count of completed courses (visible courses)"""
        return self.enrollments.filter(
            status="COMPLETED", course__is_visible=True
        ).count()

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

        # Must have attempted all pre and post tests (visible courses)
        for enrollment in self.enrollments.filter(course__is_visible=True):
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
            reasons.append(
                f"Attendance ({self.session_attendance_rate:.1f}%) below 75%"
            )

        avg_score = self.overall_average_score
        if avg_score is None:
            reasons.append("No grades available")
        elif avg_score < 50:
            reasons.append(f"Average score ({avg_score:.1f}%) below 50%")

        for enrollment in self.enrollments.filter(course__is_visible=True):
            if not enrollment.pre_test_attempted:
                reasons.append(f"Pre-test not attempted for {enrollment.course.name}")
            if not enrollment.post_test_attempted:
                reasons.append(f"Post-test not attempted for {enrollment.course.name}")

        return "; ".join(reasons)

    class Meta:
        ordering = ["-requested_date"]
        unique_together = ["student", "cohort"]
        verbose_name_plural = "Registrations"
