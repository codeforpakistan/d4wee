from django.db import models


class SyncLog(models.Model):
    """Track data synchronization from Google Classroom"""

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, default="IN_PROGRESS")
    cohort = models.ForeignKey("Cohort", on_delete=models.SET_NULL, null=True, blank=True)
    courses_synced = models.IntegerField(default=0)
    students_synced = models.IntegerField(default=0)
    assignments_synced = models.IntegerField(default=0)
    submissions_synced = models.IntegerField(default=0)
    errors = models.TextField(blank=True)

    def __str__(self):
        cohort_name = f" ({self.cohort.name})" if self.cohort else ""
        return f"Sync {self.id} - {self.status} - {self.started_at.strftime('%Y-%m-%d %H:%M')}{cohort_name}"

    class Meta:
        ordering = ["-started_at"]

