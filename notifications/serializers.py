from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification, NotificationRecipient, AdminAlert

User = get_user_model()


class AdminAlertSerializer(serializers.ModelSerializer):
    triggered_by_name = serializers.CharField(source="triggered_by.get_full_name", read_only=True)
    triggered_by_username = serializers.CharField(source="triggered_by.username", read_only=True)

    class Meta:
        model = AdminAlert
        fields = [
            "id", "alert_type", "title", "message",
            "triggered_by", "triggered_by_name", "triggered_by_username",
            "related_object_id", "is_read", "read_at", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class NotificationRecipientSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source="recipient.get_full_name", read_only=True)
    recipient_email = serializers.CharField(source="recipient.email", read_only=True)
    
    class Meta:
        model = NotificationRecipient
        fields = ["id", "recipient_name", "recipient_email", "is_read", "read_at", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    recipient_count = serializers.SerializerMethodField()
    recipients = NotificationRecipientSerializer(many=True, read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "type",
            "target_type",
            "created_by",
            "created_by_username",
            "recipient_count",
            "recipients",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]
    
    def get_recipient_count(self, obj):
        return obj.recipients.count()


class NotificationCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    type = serializers.ChoiceField(choices=Notification.Type.choices, default=Notification.Type.INFO)
    target_type = serializers.ChoiceField(choices=Notification.TargetType.choices)
    student_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    course_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    
    def validate(self, data):
        target_type = data.get("target_type")
        
        if target_type == Notification.TargetType.SPECIFIC:
            if not data.get("student_ids"):
                raise serializers.ValidationError(
                    "student_ids is required when target_type is SPECIFIC"
                )
        elif target_type == Notification.TargetType.COURSE:
            if not data.get("course_ids"):
                raise serializers.ValidationError(
                    "course_ids is required when target_type is COURSE"
                )
        
        return data


class StudentNotificationSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    is_read = serializers.SerializerMethodField()
    read_at = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "type",
            "created_by_username",
            "is_read",
            "read_at",
            "created_at",
        ]
    
    def get_is_read(self, obj):
        request = self.context.get("request")
        if request and request.user:
            recipient = obj.recipients.filter(recipient=request.user).first()
            return recipient.is_read if recipient else False
        return False
    
    def get_read_at(self, obj):
        request = self.context.get("request")
        if request and request.user:
            recipient = obj.recipients.filter(recipient=request.user).first()
            return recipient.read_at if recipient else None
        return None
