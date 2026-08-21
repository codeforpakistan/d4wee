from django.db import models


class Attendance(models.Model):
    """Weekly attendance tracking - one record per student per week"""

    student = models.ForeignKey("Student", on_delete=models.CASCADE, related_name="attendance")
    cohort = models.ForeignKey("Cohort", on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField()
    hours_spent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def week_number(self):
        """Calculate ISO week number from date"""
        return self.date.isocalendar()[1]

    def __str__(self):
        return (
            f"{self.student.full_name} - {self.cohort.name} - Week {self.week_number}"
        )

    class Meta:
        ordering = ["-date", "student__full_name"]
        unique_together = ["student", "cohort", "date"]
        indexes = [
            models.Index(fields=["student", "cohort", "date"]),
        ]
        verbose_name_plural = "Attendance"
