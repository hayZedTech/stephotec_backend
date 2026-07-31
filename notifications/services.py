from django.contrib.auth import get_user_model
from .models import Notification, NotificationRecipient

User = get_user_model()


def send_student_notification(student, title, message, notification_type=Notification.Type.INFO, created_by=None):
    """
    Sends a system notification to a specific student user,
    which will be delivered to their student notifications feed.
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
