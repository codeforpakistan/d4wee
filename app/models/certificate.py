from django.db import models


class Certificate(models.Model):
    """Issued certificates - one per enrollment (student + course + cohort)"""

    enrollment = models.OneToOneField("Enrollment", on_delete=models.CASCADE, related_name="certificate")
    issued_date = models.DateField()
    completion_percentage = models.FloatField()
    average_grade = models.FloatField(null=True, blank=True)
    certificate_url = models.URLField(blank=True)
    certificate_file = models.FileField(upload_to="certificates/", null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.enrollment.student.full_name} - {self.enrollment.course.name} ({self.enrollment.cohort.name})"
