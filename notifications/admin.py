from django.contrib import admin
from .models import Notification, NotificationRecipient


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "type", "target_type", "created_by", "recipient_count", "created_at"]
    list_filter = ["type", "target_type", "created_at"]
    search_fields = ["title", "message"]
    readonly_fields = ["created_at", "updated_at"]
    
    def recipient_count(self, obj):
        return obj.recipients.count()
    recipient_count.short_description = "Recipients"


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ["notification", "recipient", "is_read", "read_at", "created_at"]
    list_filter = ["is_read", "created_at"]
    search_fields = ["notification__title", "recipient__username"]
    readonly_fields = ["created_at"]
