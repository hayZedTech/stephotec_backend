from rest_framework import serializers
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
from config.validators import (
    validate_document_file,
    validate_video_file,
    validate_assignment_submission_file,
)


class LearningContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningContent
        fields = [
            "id",
            "course",
            "title",
            "description",
            "content_type",
            "file",
            "video_url",
            "order",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_file(self, value):
        if value:
            # Allow both document and video files
            try:
                validate_document_file(value)
            except:
                validate_video_file(value)
        return value


class AssignmentSerializer(serializers.ModelSerializer):
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            "id",
            "course",
            "title",
            "description",
            "instructions",
            "file",
            "status",
            "due_date",
            "max_score",
            "submission_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "submission_count"]

    def get_submission_count(self, obj):
        return obj.submissions.count()

    def validate_file(self, value):
        if value:
            validate_document_file(value)
        return value


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = [
            "id",
            "assignment",
            "assignment_title",
            "student",
            "student_name",
            "file",
            "submitted_at",
            "score",
            "feedback",
            "status",
            "graded_at",
            "graded_by",
        ]
        read_only_fields = ["id", "student", "submitted_at", "graded_at"]

    def validate_file(self, value):
        if value:
            validate_assignment_submission_file(value)
        return value


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source="student_course.student.get_full_name", read_only=True
    )
    course_name = serializers.CharField(
        source="student_course.course.name", read_only=True
    )

    class Meta:
        model = Attendance
        fields = [
            "id",
            "student_course",
            "student_name",
            "course_name",
            "date",
            "status",
            "remarks",
            "recorded_by",
            "recorded_at",
        ]
        read_only_fields = ["id", "recorded_at"]


class CertificateSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source="student_course.student.get_full_name", read_only=True
    )
    course_name = serializers.CharField(
        source="student_course.course.name", read_only=True
    )

    class Meta:
        model = Certificate
        fields = [
            "id",
            "student_course",
            "student_name",
            "course_name",
            "title",
            "certificate_number",
            "status",
            "earned_date",
            "issued_date",
            "file",
            "issued_by",
        ]
        read_only_fields = ["id"]


class HandoutSerializer(serializers.ModelSerializer):
    purchase_count = serializers.SerializerMethodField()

    class Meta:
        model = Handout
        fields = [
            "id",
            "course",
            "title",
            "description",
            "file",
            "price",
            "status",
            "purchase_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "purchase_count"]

    def get_purchase_count(self, obj):
        return obj.purchases.filter(status="COMPLETED").count()


class HandoutPurchaseSerializer(serializers.ModelSerializer):
    handout_title = serializers.CharField(source="handout.title", read_only=True)
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)

    class Meta:
        model = HandoutPurchase
        fields = [
            "id",
            "handout",
            "handout_title",
            "student",
            "student_name",
            "amount_paid",
            "status",
            "transaction_id",
            "purchased_at",
            "expires_at",
        ]
        read_only_fields = ["id", "purchased_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient",
            "title",
            "message",
            "notification_type",
            "related_object_id",
            "is_read",
            "created_at",
            "read_at",
        ]
        read_only_fields = ["id", "created_at"]


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    recipient_name = serializers.CharField(
        source="recipient.get_full_name", read_only=True
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "sender",
            "sender_name",
            "recipient",
            "recipient_name",
            "subject",
            "body",
            "is_read",
            "created_at",
            "read_at",
        ]
        read_only_fields = ["id", "created_at"]


class StudentLearningContentSerializer(serializers.ModelSerializer):
    learning_content_title = serializers.CharField(
        source="learning_content.title", read_only=True
    )
    description = serializers.CharField(
        source="learning_content.description", read_only=True
    )
    content_type = serializers.CharField(
        source="learning_content.content_type", read_only=True
    )
    file = serializers.URLField(
        source="learning_content.file", read_only=True, allow_null=True
    )
    video_url = serializers.URLField(
        source="learning_content.video_url", read_only=True, allow_null=True
    )
    course_name = serializers.CharField(
        source="learning_content.course.name", read_only=True
    )
    course_id = serializers.IntegerField(
        source="learning_content.course.id", read_only=True
    )
    student_name = serializers.CharField(
        source="student_course.student.get_full_name", read_only=True
    )
    student_id = serializers.IntegerField(
        source="student_course.student.id", read_only=True
    )

    class Meta:
        model = StudentLearningContent
        fields = [
            "id",
            "student_course",
            "student_id",
            "student_name",
            "learning_content",
            "learning_content_title",
            "description",
            "content_type",
            "file",
            "video_url",
            "course_id",
            "course_name",
            "assigned_at",
            "completed_at",
        ]
        read_only_fields = ["id", "assigned_at"]


class StudentAssignmentSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(
        source="assignment.title", read_only=True
    )
    description = serializers.CharField(
        source="assignment.description", read_only=True
    )
    instructions = serializers.CharField(
        source="assignment.instructions", read_only=True
    )
    file = serializers.URLField(
        source="assignment.file", read_only=True, allow_null=True
    )
    due_date = serializers.DateTimeField(
        source="assignment.due_date", read_only=True
    )
    max_score = serializers.IntegerField(
        source="assignment.max_score", read_only=True
    )
    status = serializers.CharField(
        source="assignment.status", read_only=True
    )
    course_id = serializers.IntegerField(
        source="assignment.course.id", read_only=True
    )
    course_name = serializers.CharField(
        source="assignment.course.name", read_only=True
    )

    class Meta:
        model = StudentAssignment
        fields = [
            "id",
            "student",
            "assignment",
            "assignment_title",
            "description",
            "instructions",
            "file",
            "due_date",
            "max_score",
            "status",
            "course_id",
            "course_name",
            "assigned_at",
        ]
        read_only_fields = ["id", "assigned_at"]


class StudentCertificateSerializer(serializers.ModelSerializer):
    certificate_title = serializers.CharField(
        source="certificate.title", read_only=True
    )

    class Meta:
        model = StudentCertificate
        fields = [
            "id",
            "student",
            "certificate",
            "certificate_title",
            "assigned_at",
        ]
        read_only_fields = ["id", "assigned_at"]


class StudentHandoutSerializer(serializers.ModelSerializer):
    handout_title = serializers.CharField(
        source="handout.title", read_only=True
    )
    course_name = serializers.CharField(
        source="handout.course.name", read_only=True
    )

    class Meta:
        model = StudentHandout
        fields = [
            "id",
            "student",
            "handout",
            "handout_title",
            "course_name",
            "assigned_at",
        ]
        read_only_fields = ["id", "assigned_at"]
