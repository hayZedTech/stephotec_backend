from rest_framework import serializers
from .models import Payment, PaymentEntry


class PaymentEntrySerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentEntry
        fields = ["id", "amount", "mode", "note", "recorded_by_name", "date"]
        read_only_fields = ["id", "recorded_by_name", "date"]

    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return f"{obj.recorded_by.first_name} {obj.recorded_by.last_name}".strip() or obj.recorded_by.username
        return None


class PaymentSerializer(serializers.ModelSerializer):
    enrollment_id = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()
    course_id = serializers.SerializerMethodField()
    is_primary = serializers.SerializerMethodField()
    outstanding = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    student_course_id = serializers.IntegerField(source="student_course.id", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "student_course_id",
            "course_id",
            "enrollment_id",
            "course_name",
            "is_primary",
            "course_fee",
            "amount_paid",
            "outstanding",
            "status",
            "notes",
            "last_updated",
            "created_at",
        ]
        read_only_fields = ["id", "status", "outstanding", "last_updated", "created_at"]

    def get_enrollment_id(self, obj):
        return obj.student_course.enrollment_id

    def get_course_name(self, obj):
        return obj.student_course.course.name

    def get_course_id(self, obj):
        return obj.student_course.course.id

    def get_is_primary(self, obj):
        return obj.student_course.is_primary


class StudentPaymentSummarySerializer(serializers.Serializer):
    """One row per student — primary course fee shown in table, all courses in detail."""
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    student_username = serializers.CharField()
    primary_course_name = serializers.CharField()
    primary_course_fee = serializers.DecimalField(max_digits=12, decimal_places=2)
    primary_amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    primary_outstanding = serializers.DecimalField(max_digits=12, decimal_places=2)
    primary_status = serializers.CharField()
    courses = PaymentSerializer(many=True)
