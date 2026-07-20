from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminAlert(models.Model):
    """System-generated alerts for admins (e.g. attendance requests)."""

    class AlertType(models.TextChoices):
        ATTENDANCE_REQUEST = "ATTENDANCE_REQUEST", "Attendance Request"

    alert_type = models.CharField(max_length=50, choices=AlertType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    triggered_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="triggered_alerts",
    )
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.alert_type}] {self.title}"
