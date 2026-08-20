import os
import json
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Notification, NotificationRecipient, AdminAlert
from .email_service import EmailService

User = get_user_model()


def is_email_enabled(event_key=None):
    """
    Checks whether email notifications are enabled globally and for a specific event.
    Reads from system_settings.json.
    """
    settings_file = os.path.join(settings.BASE_DIR, "system_settings.json")
    if not os.path.exists(settings_file):
        return True

    try:
        with open(settings_file, "r") as f:
            data = json.load(f)
            # Master toggle
            if not data.get("emailNotifications", True):
                return False
            # Specific event toggle if provided
            if event_key and not data.get(event_key, True):
                return False
            return True
    except Exception:
        return True


def send_student_notification(student, title, message, notification_type=Notification.Type.INFO, created_by=None, event_key=None):
    """
    Sends a system notification to a specific student user,
    delivers to their portal feed, and dispatches an email notification if enabled.
    """
    if not student:
        return None

    if not created_by:
        created_by = User.objects.filter(role=User.Role.ADMIN).first()

    if not created_by:
        return None

    notification = Notification.objects.create(
        created_by=created_by,
        title=title,
        message=message,
        type=notification_type,
        target_type=Notification.TargetType.SPECIFIC,
    )
    NotificationRecipient.objects.create(
        notification=notification,
        recipient=student,
    )

    # Only dispatch HTML email notification if enabled in system settings
    if is_email_enabled(event_key):
        try:
            EmailService.send_notification_email(student, title, message)
        except Exception:
            pass

    return notification


def send_bulk_student_notifications(students, title, message, notification_type=Notification.Type.INFO, created_by=None):
    """
    Sends a system notification to a list/queryset of student users.
    """
    if not students:
        return None

    if not created_by:
        created_by = User.objects.filter(role=User.Role.ADMIN).first()

    if not created_by:
        return None

    notification = Notification.objects.create(
        created_by=created_by,
        title=title,
        message=message,
        type=notification_type,
        target_type=Notification.TargetType.SPECIFIC,
    )

    recipients = [
        NotificationRecipient(notification=notification, recipient=student)
        for student in students if student
    ]
    NotificationRecipient.objects.bulk_create(recipients)
    return notification


def notify_admins(title, message, alert_type="STUDENT_ACTION", triggered_by=None, related_object_id=None):
    """
    Sends notifications to all admin users via both:
    1. System Notification (recipients feed for each admin)
    2. AdminAlert (inbox alert for admins)
    """
    admin_users = list(User.objects.filter(role=User.Role.ADMIN))
    if not admin_users:
        return

    # 1. Send system notification to all admins
    send_bulk_student_notifications(
        students=admin_users,
        title=title,
        message=message,
        notification_type=Notification.Type.INFO,
    )

    # 2. Create AdminAlert record if triggered_by user exists
    if triggered_by:
        valid_types = [c[0] for c in AdminAlert.AlertType.choices]
        final_alert_type = alert_type if alert_type in valid_types else AdminAlert.AlertType.STUDENT_ACTION
        AdminAlert.objects.create(
            alert_type=final_alert_type,
            title=title,
            message=message,
            triggered_by=triggered_by,
            related_object_id=related_object_id,
        )

