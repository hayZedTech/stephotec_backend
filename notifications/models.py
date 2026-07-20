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


class Notification(models.Model):
    class Type(models.TextChoices):
        INFO = "INFO", "Information"
        WARNING = "WARNING", "Warning"
        SUCCESS = "SUCCESS", "Success"
        ERROR = "ERROR", "Error"
    
    class TargetType(models.TextChoices):
        ALL = "ALL", "All Students"
        SPECIFIC = "SPECIFIC", "Specific Students"
        COURSE = "COURSE", "By Course"
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications_created",
        limit_choices_to={"role": "ADMIN"}
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.INFO
    )
    target_type = models.CharField(
        max_length=20,
        choices=TargetType.choices,
        default=TargetType.ALL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.title} ({self.target_type})"


class NotificationRecipient(models.Model):
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="recipients"
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_notifications"
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ("notification", "recipient")
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.notification.title} -> {self.recipient.username}"
