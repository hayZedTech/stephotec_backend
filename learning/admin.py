from django.contrib import admin
from .models import (
    LearningContent,
    Assignment,
    AssignmentSubmission,
    Attendance,
    Certificate,
    Handout,
    HandoutPurchase,
    Notification,
    Message,
    StudentLearningContent,
    StudentAssignment,
    StudentCertificate,
    StudentHandout,
)


@admin.register(LearningContent)
class LearningContentAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "content_type", "is_published", "created_at"]
    list_filter = ["content_type", "is_published", "course"]
    search_fields = ["title", "description"]
    ordering = ["order", "created_at"]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "status", "due_date", "max_score"]
    list_filter = ["status", "course", "due_date"]
    search_fields = ["title", "description"]


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ["assignment", "student", "status", "score", "submitted_at"]
    list_filter = ["status", "assignment", "submitted_at"]
    search_fields = ["student__username", "assignment__title"]
    readonly_fields = ["submitted_at", "graded_at"]


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ["student_course", "date", "status", "recorded_at"]
    list_filter = ["status", "date", "student_course__course"]
    search_fields = ["student_course__student__username"]
    readonly_fields = ["recorded_at"]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ["title", "student_course", "status", "earned_date", "issued_date"]
    list_filter = ["status", "earned_date", "issued_date"]
    search_fields = ["student_course__student__username", "certificate_number"]


@admin.register(Handout)
class HandoutAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "price", "status", "created_at"]
    list_filter = ["status", "course", "created_at"]
    search_fields = ["title", "description"]


@admin.register(HandoutPurchase)
class HandoutPurchaseAdmin(admin.ModelAdmin):
    list_display = ["handout", "student", "amount_paid", "status", "purchased_at"]
    list_filter = ["status", "handout", "purchased_at"]
    search_fields = ["student__username", "handout__title", "transaction_id"]
    readonly_fields = ["purchased_at"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "recipient", "notification_type", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["recipient__username", "title", "message"]
    readonly_fields = ["created_at"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["subject", "sender", "recipient", "is_read", "created_at"]
    list_filter = ["is_read", "created_at"]
    search_fields = ["sender__username", "recipient__username", "subject", "body"]
    readonly_fields = ["created_at"]


@admin.register(StudentLearningContent)
class StudentLearningContentAdmin(admin.ModelAdmin):
    list_display = ["student_course", "learning_content", "assigned_at", "completed_at"]
    list_filter = ["assigned_at", "completed_at", "learning_content__course"]
    search_fields = ["student_course__student__username", "learning_content__title"]
    readonly_fields = ["assigned_at"]
    filter_horizontal = []


@admin.register(StudentAssignment)
class StudentAssignmentAdmin(admin.ModelAdmin):
    list_display = ["student", "assignment", "assigned_at"]
    list_filter = ["assigned_at", "assignment__course"]
    search_fields = ["student__username", "assignment__title"]
    readonly_fields = ["assigned_at"]


@admin.register(StudentCertificate)
class StudentCertificateAdmin(admin.ModelAdmin):
    list_display = ["student", "certificate", "assigned_at"]
    list_filter = ["assigned_at"]
    search_fields = ["student__username", "certificate__title"]
    readonly_fields = ["assigned_at"]


@admin.register(StudentHandout)
class StudentHandoutAdmin(admin.ModelAdmin):
    list_display = ["student", "handout", "assigned_at"]
    list_filter = ["assigned_at", "handout__course"]
    search_fields = ["student__username", "handout__title"]
    readonly_fields = ["assigned_at"]
