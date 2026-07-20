from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from .models import Notification, NotificationRecipient, AdminAlert
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    StudentNotificationSerializer,
    AdminAlertSerializer,
)
from accounts.models import StudentCourse
from accounts.permissions import IsAdminUserRole

User = get_user_model()


class AdminAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin-only inbox for system-generated alerts."""
    serializer_class = AdminAlertSerializer
    permission_classes = [IsAdminUserRole]

    def get_queryset(self):
        return AdminAlert.objects.all()

    @action(detail=True, methods=["post"], url_path="mark_read")
    def mark_read(self, request, pk=None):
        alert = self.get_object()
        alert.is_read = True
        alert.read_at = timezone.now()
        alert.save()
        return Response(AdminAlertSerializer(alert).data)

    @action(detail=False, methods=["post"], url_path="mark_all_read")
    def mark_all_read(self, request):
        AdminAlert.objects.filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({"detail": "All alerts marked as read"})

    @action(detail=False, methods=["get"], url_path="unread_count")
    def unread_count(self, request):
        return Response({"unread_count": AdminAlert.objects.filter(is_read=False).count()})


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()
    
    def get_permissions(self):
        if self.action in ["student_notifications", "unread_count", "mark_as_read"]:
            return [IsAuthenticated()]
        return [IsAdminUserRole()]
    
    def get_serializer_class(self):
        if self.action == "create":
            return NotificationCreateSerializer
        return NotificationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create notification
        notification = Notification.objects.create(
            created_by=request.user,
            title=serializer.validated_data["title"],
            message=serializer.validated_data["message"],
            type=serializer.validated_data.get("type", Notification.Type.INFO),
            target_type=serializer.validated_data["target_type"],
        )
        
        # Determine recipients
        recipients = []
        target_type = serializer.validated_data["target_type"]
        
        if target_type == Notification.TargetType.ALL:
            recipients = User.objects.filter(role=User.Role.STUDENT)
        
        elif target_type == Notification.TargetType.SPECIFIC:
            student_ids = serializer.validated_data.get("student_ids", [])
            recipients = User.objects.filter(id__in=student_ids, role=User.Role.STUDENT)
        
        elif target_type == Notification.TargetType.COURSE:
            course_ids = serializer.validated_data.get("course_ids", [])
            recipients = User.objects.filter(
                courses__course_id__in=course_ids,
                role=User.Role.STUDENT
            ).distinct()
        
        # Create notification recipients
        notification_recipients = [
            NotificationRecipient(notification=notification, recipient=recipient)
            for recipient in recipients
        ]
        NotificationRecipient.objects.bulk_create(notification_recipients)
        
        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=["get"])
    def student_notifications(self, request):
        """Get notifications for the current student"""
        if request.user.role != User.Role.STUDENT:
            return Response(
                {"detail": "This endpoint is only for students."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        notifications = Notification.objects.filter(
            recipients__recipient=request.user
        ).distinct()
        
        serializer = StudentNotificationSerializer(
            notifications,
            many=True,
            context={"request": request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        recipient = NotificationRecipient.objects.filter(
            notification=notification,
            recipient=request.user
        ).first()
        
        if not recipient:
            return Response(
                {"detail": "Notification not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        recipient.is_read = True
        recipient.read_at = timezone.now()
        recipient.save()
        
        return Response(
            {"message": "Notification marked as read."},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Get count of unread notifications for current user"""
        if request.user.role != User.Role.STUDENT:
            return Response(
                {"detail": "This endpoint is only for students."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        unread_count = NotificationRecipient.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return Response({"unread_count": unread_count})
