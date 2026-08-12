from rest_framework import serializers
import random
from django.contrib.auth import get_user_model
from accounts.models import Course, StudentGroup
User = get_user_model()

from .models import (
    LearningContent,
    Assignment,
    AssignmentSubmission,
    Attendance,
    Certificate,
    Handout,
    HandoutPurchase,
    Brochure,
    Notification,
    Message,
    StudentLearningContent,
    StudentAssignment,
    StudentCertificate,
    StudentHandout,
    Quiz,
    QuizQuestion,
    QuestionOption,
    QuizAttempt,
    ClassMaterial,
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


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source="student_course.student.get_full_name", read_only=True
    )
    student_username = serializers.CharField(
        source="student_course.student.username", read_only=True
    )
    course_name = serializers.CharField(
        source="student_course.course.name", read_only=True
    )
    enrollment_id = serializers.CharField(
        source="student_course.enrollment_id", read_only=True
    )
    approved_by_name = serializers.CharField(
        source="approved_by.get_full_name", read_only=True
    )

    class Meta:
        model = Attendance
        fields = [
            "id",
            "student_course",
            "student_name",
            "student_username",
            "enrollment_id",
            "course_name",
            "date",
            "status",
            "approval_status",
            "remarks",
            "recorded_by",
            "recorded_at",
            "approved_by",
            "approved_by_name",
            "approved_at",
        ]
        read_only_fields = ["id", "recorded_at", "approved_by", "approved_at", "approved_by_name"]


class CertificateSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source="student_course.student.get_full_name", read_only=True
    )
    student_id = serializers.IntegerField(
        source="student_course.student.id", read_only=True
    )
    student_username = serializers.CharField(
        source="student_course.student.username", read_only=True
    )
    course_name = serializers.CharField(
        source="student_course.course.name", read_only=True
    )

    class Meta:
        model = Certificate
        fields = [
            "id",
            "student_course",
            "student_id",
            "student_username",
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


class BrochureSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True)

    class Meta:
        model = Brochure
        fields = [
            "id",
            "course",
            "course_name",
            "title",
            "description",
            "file",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]



class HandoutPurchaseSerializer(serializers.ModelSerializer):
    handout_title = serializers.CharField(source="handout.title", read_only=True)
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    student_username = serializers.CharField(source="student.username", read_only=True)

    class Meta:
        model = HandoutPurchase
        fields = [
            "id",
            "handout",
            "handout_title",
            "student",
            "student_id",
            "student_username",
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


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "question", "option_text", "is_correct"]


class QuestionOptionPublicSerializer(serializers.ModelSerializer):
    """Option serializer for active student test taking (hides is_correct)"""
    class Meta:
        model = QuestionOption
        fields = ["id", "option_text"]


class QuizQuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizQuestion
        fields = ["id", "quiz", "question_text", "explanation", "points", "order", "options"]


class QuizQuestionPublicSerializer(serializers.ModelSerializer):
    """Question serializer for live test taking (hides answer explanation until submission)"""
    options = QuestionOptionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = QuizQuestion
        fields = ["id", "question_text", "points", "order", "options"]


class QuizSerializer(serializers.ModelSerializer):
    course_name = serializers.SerializerMethodField()
    course_code = serializers.CharField(source="course.code_prefix", read_only=True, allow_null=True)
    courses_details = serializers.SerializerMethodField()
    course_ids = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        many=True,
        required=False,
        source="courses"
    )
    questions_count = serializers.IntegerField(source="questions.count", read_only=True)
    total_points = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "course",
            "courses",
            "course_ids",
            "courses_details",
            "course_name",
            "course_code",
            "title",
            "description",
            "level",
            "duration_minutes",
            "passing_score_percentage",
            "display_questions_count",
            "is_published",
            "questions_count",
            "total_points",
            "created_at",
            "updated_at",
        ]

    def get_courses_details(self, obj):
        return [
            {
                "id": c.id,
                "name": c.name,
                "code_prefix": c.code_prefix,
            }
            for c in obj.courses.all()
        ]

    def get_course_name(self, obj):
        names = [c.name for c in obj.courses.all()]
        if not names and obj.course:
            names = [obj.course.name]
        return ", ".join(names) if names else "Unassigned"

    def get_total_points(self, obj):
        return sum(q.points for q in obj.questions.all())

    def create(self, validated_data):
        courses = validated_data.pop("courses", [])
        if "course" in validated_data and validated_data["course"] and validated_data["course"] not in courses:
            courses.append(validated_data["course"])
        
        if courses and not validated_data.get("course"):
            validated_data["course"] = courses[0]

        quiz = super().create(validated_data)
        if courses:
            quiz.courses.set(courses)
        return quiz

    def update(self, instance, validated_data):
        courses = validated_data.pop("courses", None)
        if courses is not None:
            if "course" not in validated_data:
                validated_data["course"] = courses[0] if courses else None
            instance.courses.set(courses)
        elif "course" in validated_data and validated_data["course"]:
            instance.courses.add(validated_data["course"])

        return super().update(instance, validated_data)


class QuizDetailSerializer(QuizSerializer):
    """Detailed quiz serializer with full questions and options for active test taking"""
    questions = serializers.SerializerMethodField()

    class Meta(QuizSerializer.Meta):
        fields = QuizSerializer.Meta.fields + ["questions"]

    def get_questions(self, obj):
        all_questions = list(obj.questions.all().prefetch_related('options'))
        if obj.display_questions_count and obj.display_questions_count > 0 and obj.display_questions_count < len(all_questions):
            selected_questions = random.sample(all_questions, obj.display_questions_count)
        else:
            selected_questions = all_questions
            # Still randomize order even if we show all
            random.shuffle(selected_questions)
            
        return QuizQuestionPublicSerializer(selected_questions, many=True).data


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    course_name = serializers.CharField(source="quiz.course.name", read_only=True)
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "quiz",
            "quiz_title",
            "course_name",
            "student",
            "student_name",
            "score_percentage",
            "passed",
            "total_questions",
            "correct_answers_count",
            "answers_data",
            "completed_at",
        ]
        read_only_fields = ["id", "completed_at"]


class ClassMaterialSerializer(serializers.ModelSerializer):
    assigned_group_ids = serializers.PrimaryKeyRelatedField(
        queryset=StudentGroup.objects.all(),
        many=True,
        required=False,
        source="assigned_groups"
    )
    assigned_student_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="STUDENT"),
        many=True,
        required=False,
        source="assigned_students"
    )
    assigned_groups_details = serializers.SerializerMethodField()
    assigned_students_details = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, allow_null=True)

    class Meta:
        model = ClassMaterial
        fields = [
            "id",
            "title",
            "description",
            "file",
            "file_name",
            "file_size",
            "assigned_groups",
            "assigned_group_ids",
            "assigned_groups_details",
            "assigned_students",
            "assigned_student_ids",
            "assigned_students_details",
            "created_by",
            "created_by_name",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_assigned_groups_details(self, obj):
        return [{"id": g.id, "name": g.name} for g in obj.assigned_groups.all()]

    def get_assigned_students_details(self, obj):
        return [
            {
                "id": s.id,
                "username": s.username,
                "full_name": s.get_full_name() or s.username,
            }
            for s in obj.assigned_students.all()
        ]


