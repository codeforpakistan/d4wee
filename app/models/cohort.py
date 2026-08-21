from django.db import models
from django.utils import timezone


class Cohort(models.Model):
    """Time-bound training batches (3 months)"""

    class StatusChoices(models.TextChoices):
        UPCOMING = "Upcoming"
        ACTIVE = "Active"
        CLOSED = "Closed"

    name = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=StatusChoices, default=StatusChoices.UPCOMING)
    is_open_for_registration = models.BooleanField(default=False)
    max_students = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        """Check if cohort is currently active"""
        if self.status != self.StatusChoices.ACTIVE:
            return False
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date

    @property
    def total_weeks(self):
        """Calculate total weeks in cohort"""
        days = (self.end_date - self.start_date).days
        return max(1, round(days / 7))

    @property
    def current_registrations_count(self):
        """Count current registrations (approved only)"""
        return self.registrations.filter(status="APPROVED").count()

    @property
    def total_enrolled_students(self):
        """Count total unique students enrolled in cohort courses"""
        from .student import Student

        return Student.objects.filter(registrations__cohort=self).distinct().count()

    @property
    def can_accept_registrations(self):
        """Check if cohort can accept new registrations"""
        if not self.is_open_for_registration:
            return False
        return not (self.max_students and self.total_enrolled_students >= self.max_students)

    @property
    def average_completion_rate(self):
        """Average completion rate across approved registrations"""
        approved_registrations = self.registrations.filter(status="APPROVED")
        if not approved_registrations.exists():
            return 0

        total = sum(r.overall_completion_rate or 0 for r in approved_registrations)
        return total / approved_registrations.count()

    @property
    def unique_courses_count(self):
        """Count of unique courses students are enrolled in for this cohort"""
        from .enrollment import Enrollment
        return (
            Enrollment.objects.filter(registration__cohort=self)
            .values("course")
            .distinct()
            .count()
        )

    @property
    def total_enrollments(self):
        """Count of students with approved status"""
        return self.registrations.filter(status="APPROVED").count()

    @property
    def certificates_count(self):
        """Count of certificates issued for this cohort"""
        from .certificate import Certificate

        return Certificate.objects.filter(enrollment__registration__cohort=self).count()

    @property
    def approved_registrations_count(self):
        """Count of registrations with APPROVED status"""
        return self.registrations.filter(status="APPROVED").count()

    @property
    def pending_registrations_count(self):
        """Count of registrations with PENDING status"""
        return self.registrations.filter(status="PENDING").count()

    class Meta:
        ordering = ["-start_date"]
