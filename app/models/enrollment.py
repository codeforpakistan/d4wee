from django.db import models

from .registration import Registration


class Enrollment(models.Model):
    """Student taking Course within Cohort context"""

    class StatusChoices(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        DROPPED = "DROPPED", "Dropped"

    course = models.ForeignKey("Course", on_delete=models.CASCADE, related_name="enrollments")
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.IN_PROGRESS)
    completion_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Properties to access student and cohort via registration
    @property
    def student(self):
        """Get student from registration"""
        return self.registration.student

    @property
    def cohort(self):
        """Get cohort from registration"""
        return self.registration.cohort

    def __str__(self):
        return f"{self.student.full_name} - {self.course.display_name} ({self.cohort.name})"

    # Helper methods (fat model)
    def get_assignments(self, assignment_type=None):
        """Get assignments for this course, optionally filtered by type"""
        qs = self.course.assignments.all()
        if assignment_type:
            qs = qs.filter(assignment_type=assignment_type)
        return qs

    def get_missing_assignments(self):
        """Get assignments that haven't been submitted"""
        submitted_assignment_ids = self.submissions.values_list(
            "assignment_id", flat=True
        )
        return self.course.assignments.exclude(id__in=submitted_assignment_ids).filter(
            assignment_type="ASSIGNMENT"
        )

    def get_late_submissions(self):
        """Get submissions that were late"""
        return self.submissions.filter(late=True)

    # Calculated properties for Pre/Post tests (fat model)
    @property
    def pre_test_attempted(self):
        """Check if pre-test was attempted"""
        return self.submissions.filter(assignment__assignment_type="PRE_TEST").exists()

    @property
    def pre_test_score(self):
        """Get pre-test score as percentage"""
        submission = (
            self.submissions.filter(
                assignment__assignment_type="PRE_TEST",
                assigned_grade__isnull=False,
                assignment__max_points__isnull=False,
            )
            .select_related("assignment")
            .first()
        )

        if (
            submission
            and submission.assigned_grade is not None
            and submission.assignment.max_points
        ):
            return (submission.assigned_grade / submission.assignment.max_points) * 100
        return None

    @property
    def post_test_attempted(self):
        """Check if post-test was attempted"""
        return self.submissions.filter(assignment__assignment_type="POST_TEST").exists()

    @property
    def post_test_score(self):
        """Get post-test score as percentage"""
        submission = (
            self.submissions.filter(
                assignment__assignment_type="POST_TEST",
                assigned_grade__isnull=False,
                assignment__max_points__isnull=False,
            )
            .select_related("assignment")
            .first()
        )

        if (
            submission
            and submission.assigned_grade is not None
            and submission.assignment.max_points
        ):
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
        return self.course.assignments.filter(assignment_type="ASSIGNMENT").count()

    @property
    def completed_assignments(self):
        """Count completed assignments"""
        return self.submissions.filter(
            assignment__assignment_type="ASSIGNMENT",
            state__in=["TURNED_IN", "RETURNED"],
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
            assignment__assignment_type="ASSIGNMENT", late=True
        ).count()

    @property
    def assignment_average_score(self):
        """Average score for assignments only"""
        submissions = self.submissions.filter(
            assignment__assignment_type="ASSIGNMENT",
            assigned_grade__isnull=False,
            assignment__max_points__isnull=False,
            assignment__max_points__gt=0,
        ).select_related("assignment")

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
        return self.course.assignments.filter(assignment_type="QUIZ").count()

    @property
    def completed_quizzes(self):
        """Count completed quizzes"""
        return self.submissions.filter(
            assignment__assignment_type="QUIZ", state__in=["TURNED_IN", "RETURNED"]
        ).count()

    @property
    def quiz_average_score(self):
        """Average score for quizzes"""
        submissions = self.submissions.filter(
            assignment__assignment_type="QUIZ",
            assigned_grade__isnull=False,
            assignment__max_points__isnull=False,
            assignment__max_points__gt=0,
        ).select_related("assignment")

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

        completed = self.submissions.filter(state__in=["TURNED_IN", "RETURNED"]).count()

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
        """Average score across all graded submissions (assignments, quizzes, pre/post tests)"""
        submissions = self.submissions.filter(
            assigned_grade__isnull=False,
            assignment__max_points__isnull=False,
            assignment__max_points__gt=0,
            assignment__assignment_type__in=["ASSIGNMENT", "QUIZ"],
        ).select_related("assignment")

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
            return "FOCUS"

        # PRAISE: High completion and high scores
        if completion >= 85 and (score is None or score >= 85):
            return "PRAISE"

        # PUSH: Everything else
        return "PUSH"

    @property
    def certificate_eligible(self):
        """Check if student is eligible for course certificate"""
        # Must have at least 50% attendance
        attendance = self.registration.session_attendance_rate
        assessment = self.overall_average_score
        completion = self.completion_rate

        attendance = attendance if attendance else 0
        assessment = assessment if assessment else 0
        completion = completion if completion else 0

        return (assessment >= 60) and ((assessment + attendance) > 100)

    @property
    def certificate_eligibility_notes(self):
        """Get reasons for certificate ineligibility"""
        if self.certificate_eligible:
            return "Meets all certificate requirements"

        reasons = []

        if self.registration.session_attendance_rate < 50:
            reasons.append(
                f"Attendance ({self.registration.session_attendance_rate:.1f}%) below 50%"
            )

        if self.completion_rate < 50:
            reasons.append(f"Completion ({self.completion_rate:.1f}%) below 50%")

        avg_score = self.overall_average_score
        if avg_score is None:
            reasons.append("No grades available")
        elif avg_score < 60:
            reasons.append(f"Average score ({avg_score:.1f}%) below 60%")

        has_pre_test = self.course.assignments.filter(
            assignment_type="PRE_TEST"
        ).exists()
        has_post_test = self.course.assignments.filter(
            assignment_type="POST_TEST"
        ).exists()

        if has_pre_test and not self.pre_test_attempted:
            reasons.append("Pre-test not attempted")
        if has_post_test and not self.post_test_attempted:
            reasons.append("Post-test not attempted")

        return "; ".join(reasons)

    @property
    def has_certificate(self):
        """Check if a certificate has been issued for this enrollment"""
        return hasattr(self, "certificate")

    class Meta:
        ordering = ["-enrolled_date"]
        unique_together = ["registration", "course"]
        verbose_name_plural = "Enrollments"
