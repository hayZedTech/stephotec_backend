from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.services import FileUploadService
from notifications.models import AdminAlert
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
from .serializers import (
    LearningContentSerializer,
    AssignmentSerializer,
    AssignmentSubmissionSerializer,
    AttendanceSerializer,
    CertificateSerializer,
    HandoutSerializer,
    HandoutPurchaseSerializer,
    NotificationSerializer,
    MessageSerializer,
    StudentLearningContentSerializer,
    StudentAssignmentSerializer,
    StudentCertificateSerializer,
    StudentHandoutSerializer,
)
from accounts.permissions import IsAdminUserRole
from accounts.models import StudentCourse

User = get_user_model()


class LearningContentViewSet(viewsets.ModelViewSet):
    serializer_class = LearningContentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["course", "content_type", "is_published"]
    search_fields = ["title", "description"]
    ordering_fields = ["order", "created_at"]
    ordering = ["order", "created_at"]

    def get_queryset(self):
        if self.request.user.role == "ADMIN":
            return LearningContent.objects.all()
        return LearningContent.objects.filter(is_published=True)

    def _handle_file_upload(self, request, instance=None):
        """Upload file to Cloudinary and return URL, or None if no file."""
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return None
        course_id = request.data.get("course") or (instance.course_id if instance else None)
        return FileUploadService.upload_learning_material(uploaded_file, course_id)

    def create(self, request, *args, **kwargs):
        file_url = self._handle_file_upload(request)
        data = request.data.copy()
        if file_url:
            data["file"] = file_url
            data["video_url"] = ""
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        file_url = self._handle_file_upload(request, instance)
        data = request.data.copy()
        if file_url:
            data["file"] = file_url
            data["video_url"] = None
        elif data.get("video_url"):
            data["file"] = None
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["course", "status"]
    search_fields = ["title", "description"]
    ordering_fields = ["due_date", "created_at"]
    ordering = ["-due_date"]

    def get_queryset(self):
        if self.request.user.role == "ADMIN":
            return Assignment.objects.all()
        return Assignment.objects.filter(status="PUBLISHED")

    def create(self, request, *args, **kwargs):
        if request.user.role != "ADMIN":
            return Response({"detail": "Only admins can create assignments"}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            data["file"] = FileUploadService.upload_assignment(uploaded_file, data.get("course"))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            data["file"] = FileUploadService.upload_assignment(uploaded_file, instance.course_id)
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["assignment", "student", "status"]
    ordering_fields = ["submitted_at", "score"]
    ordering = ["-submitted_at"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return AssignmentSubmission.objects.all()
        return AssignmentSubmission.objects.filter(student=user)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            data["file"] = FileUploadService.upload_submission(uploaded_file, request.user.id)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(student=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUserRole])
    def grade(self, request, pk=None):
        submission = self.get_object()
        score = request.data.get("score")
        feedback = request.data.get("feedback", "")

        if score is None:
            return Response(
                {"detail": "Score is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        submission.score = score
        submission.feedback = feedback
        submission.status = "GRADED"
        submission.graded_at = timezone.now()
        submission.graded_by = request.user
        submission.save()

        return Response(
            AssignmentSubmissionSerializer(submission).data,
            status=status.HTTP_200_OK,
        )


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["student_course", "date", "status", "approval_status"]
    ordering_fields = ["date"]
    ordering = ["-date"]

    def get_permissions(self):
        if self.action in ["mark_attendance", "my_attendance", "cancel_attendance"]:
            return [IsAuthenticated()]
        return [IsAdminUserRole()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return Attendance.objects.select_related(
                "student_course__student", "student_course__course", "approved_by"
            ).all()
        return Attendance.objects.filter(student_course__student=user)

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="mark")
    def mark_attendance(self, request):
        """Student marks their own attendance for a specific date (defaults to today)."""
        student_course_id = request.data.get("student_course")
        date = request.data.get("date") or timezone.now().date()
        remarks = request.data.get("remarks", "")

        if not student_course_id:
            return Response({"detail": "student_course is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student_course = StudentCourse.objects.get(id=student_course_id, student=request.user)
        except StudentCourse.DoesNotExist:
            return Response({"detail": "Student course not found"}, status=status.HTTP_404_NOT_FOUND)

        existing = Attendance.objects.filter(student_course=student_course, date=date).first()
        if existing:
            return Response(
                {"detail": "Attendance already marked for this date", "attendance": AttendanceSerializer(existing).data},
                status=status.HTTP_400_BAD_REQUEST
            )

        attendance = Attendance.objects.create(
            student_course=student_course,
            date=date,
            status="PRESENT",
            approval_status="PENDING",
            remarks=remarks,
            recorded_by=request.user,
        )

        # Notify admins
        student_name = request.user.get_full_name() or request.user.username
        AdminAlert.objects.create(
            alert_type=AdminAlert.AlertType.ATTENDANCE_REQUEST,
            title=f"Attendance Request — {student_name}",
            message=(
                f"{student_name} ({student_course.enrollment_id}) marked attendance "
                f"for {date} in {student_course.course.name}."
                + (f" Note: {remarks}" if remarks else "")
            ),
            triggered_by=request.user,
            related_object_id=attendance.id,
        )

        return Response(AttendanceSerializer(attendance).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="my_attendance")
    def my_attendance(self, request):
        """Student fetches their own attendance records."""
        student_course_id = request.query_params.get("student_course")
        month = request.query_params.get("month")  # format: YYYY-MM

        qs = Attendance.objects.filter(student_course__student=request.user)

        if student_course_id:
            qs = qs.filter(student_course_id=student_course_id)
        if month:
            try:
                year, m = month.split("-")
                qs = qs.filter(date__year=year, date__month=m)
            except ValueError:
                pass

        serializer = AttendanceSerializer(qs.order_by("-date"), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["delete"], url_path="cancel")
    def cancel_attendance(self, request, pk=None):
        """Student cancels a pending attendance mark."""
        attendance = self.get_object()
        if attendance.student_course.student != request.user:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        if attendance.approval_status != "PENDING":
            return Response({"detail": "Cannot cancel an already reviewed attendance"}, status=status.HTTP_400_BAD_REQUEST)
        attendance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """Admin approves a pending attendance."""
        attendance = self.get_object()
        attendance.approval_status = "APPROVED"
        attendance.approved_by = request.user
        attendance.approved_at = timezone.now()
        attendance.save()
        return Response(AttendanceSerializer(attendance).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        """Admin rejects a pending attendance."""
        attendance = self.get_object()
        attendance.approval_status = "REJECTED"
        attendance.approved_by = request.user
        attendance.approved_at = timezone.now()
        attendance.remarks = request.data.get("remarks", attendance.remarks)
        attendance.save()
        return Response(AttendanceSerializer(attendance).data)

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        """Admin fetches all pending attendance records."""
        qs = Attendance.objects.filter(approval_status="PENDING").select_related(
            "student_course__student", "student_course__course"
        ).order_by("-date")
        return Response(AttendanceSerializer(qs, many=True).data)


class CertificateViewSet(viewsets.ModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["student_course", "status"]
    ordering_fields = ["earned_date"]
    ordering = ["-earned_date"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return Certificate.objects.all()
        return Certificate.objects.filter(student_course__student=user)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            data["file"] = FileUploadService.upload_certificate(uploaded_file, "new")
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            data["file"] = FileUploadService.upload_certificate(uploaded_file, instance.id)
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUserRole])
    def issue(self, request, pk=None):
        certificate = self.get_object()
        certificate.status = "ISSUED"
        certificate.issued_date = timezone.now().date()
        certificate.issued_by = request.user
        certificate.save()

        return Response(
            CertificateSerializer(certificate).data, status=status.HTTP_200_OK
        )


class HandoutViewSet(viewsets.ModelViewSet):
    serializer_class = HandoutSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["course", "status"]
    search_fields = ["title", "description"]
    ordering_fields = ["price", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if self.request.user.role == "ADMIN":
            return Handout.objects.all()
        return Handout.objects.filter(status="PUBLISHED")

    def create(self, request, *args, **kwargs):
        if request.user.role != "ADMIN":
            return Response({"detail": "Only admins can create handouts"}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            data["file"] = FileUploadService.upload_handout(uploaded_file, data.get("course"))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            data["file"] = FileUploadService.upload_handout(uploaded_file, instance.course_id)
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class HandoutPurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = HandoutPurchaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["handout", "student", "status"]
    ordering_fields = ["purchased_at"]
    ordering = ["-purchased_at"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return HandoutPurchase.objects.all()
        return HandoutPurchase.objects.filter(student=user)

    @action(detail=False, methods=["post"])
    def purchase(self, request):
        handout_id = request.data.get("handout_id")
        if not handout_id:
            return Response(
                {"detail": "handout_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            handout = Handout.objects.get(id=handout_id)
        except Handout.DoesNotExist:
            return Response(
                {"detail": "Handout not found"}, status=status.HTTP_404_NOT_FOUND
            )

        existing = HandoutPurchase.objects.filter(
            handout=handout, student=request.user
        ).first()
        if existing and existing.status == "COMPLETED":
            return Response(
                {"detail": "You have already purchased this handout"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        purchase = HandoutPurchase.objects.create(
            handout=handout,
            student=request.user,
            amount_paid=handout.price,
            status="COMPLETED",
            transaction_id=f"TXN_{handout.id}_{request.user.id}_{timezone.now().timestamp()}",
        )

        return Response(
            HandoutPurchaseSerializer(purchase).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        purchase = self.get_object()
        if purchase.student != request.user and request.user.role != "ADMIN":
            return Response(
                {"detail": "You don't have access to this handout"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if purchase.status != "COMPLETED":
            return Response(
                {"detail": "Purchase not completed"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "download_url": purchase.handout.file,
                "filename": purchase.handout.file.split("/")[-1],
            }
        )


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["notification_type", "is_read"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

        return Response(
            NotificationSerializer(notification).data, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"])
    def mark_all_as_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )

        return Response(
            {"detail": "All notifications marked as read"}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response({"unread_count": count}, status=status.HTTP_200_OK)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["subject", "body"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(
            recipient=user
        )

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        message = self.get_object()
        if message.recipient != request.user:
            return Response(
                {"detail": "You can only mark your own messages as read"},
                status=status.HTTP_403_FORBIDDEN,
            )

        message.is_read = True
        message.read_at = timezone.now()
        message.save()

        return Response(MessageSerializer(message).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def inbox(self, request):
        messages = Message.objects.filter(recipient=request.user).order_by(
            "-created_at"
        )
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def sent(self, request):
        messages = Message.objects.filter(sender=request.user).order_by("-created_at")
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)


class StudentLearningContentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentLearningContentSerializer
    permission_classes = [IsAdminUserRole]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["student_course", "learning_content"]
    ordering_fields = ["assigned_at"]
    ordering = ["-assigned_at"]

    def get_queryset(self):
        return StudentLearningContent.objects.all()

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUserRole])
    def assign_to_students(self, request):
        content_id = request.data.get("content_id")
        student_ids = request.data.get("student_ids", [])

        if not content_id or not student_ids:
            return Response(
                {"detail": "content_id and student_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            content = LearningContent.objects.get(id=content_id)
        except LearningContent.DoesNotExist:
            return Response(
                {"detail": "Learning content not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        created_count = 0
        for student_id in student_ids:
            student_courses = StudentCourse.objects.filter(
                student_id=student_id,
                course_id=content.course_id
            )
            for student_course in student_courses:
                StudentLearningContent.objects.get_or_create(
                    student_course=student_course, learning_content=content
                )
                created_count += 1

        return Response(
            {"detail": f"Content assigned to {created_count} student(s)"},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUserRole])
    def unassign_from_students(self, request):
        content_id = request.data.get("content_id")
        student_ids = request.data.get("student_ids", [])

        if not content_id or not student_ids:
            return Response(
                {"detail": "content_id and student_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            content = LearningContent.objects.get(id=content_id)
        except LearningContent.DoesNotExist:
            return Response(
                {"detail": "Learning content not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        deleted_count = 0
        for student_id in student_ids:
            student_courses = StudentCourse.objects.filter(
                student_id=student_id,
                course_id=content.course_id
            )
            for student_course in student_courses:
                StudentLearningContent.objects.filter(
                    student_course=student_course, learning_content=content
                ).delete()
                deleted_count += 1

        return Response(
            {"detail": f"Content removed from {deleted_count} student(s)"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def student_content(self, request):
        student_id = request.query_params.get("student_id")
        course_id = request.query_params.get("course_id")

        if not student_id or not course_id:
            return Response(
                {"detail": "student_id and course_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignments = StudentLearningContent.objects.filter(
            student_course__student_id=student_id,
            student_course__course_id=course_id
        ).select_related("learning_content", "learning_content__course", "student_course")

        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)


class StudentAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentAssignmentSerializer
    permission_classes = [IsAdminUserRole]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["student", "assignment"]
    ordering_fields = ["assigned_at"]
    ordering = ["-assigned_at"]

    def get_queryset(self):
        return StudentAssignment.objects.all()

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUserRole])
    def assign_to_students(self, request):
        assignment_id = request.data.get("assignment_id")
        student_ids = request.data.get("student_ids", [])

        if not assignment_id or not student_ids:
            return Response(
                {"detail": "assignment_id and student_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response(
                {"detail": "Assignment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        created_count = 0
        for student_id in student_ids:
            try:
                student = User.objects.get(id=student_id)
                StudentAssignment.objects.get_or_create(
                    student=student, assignment=assignment
                )
                created_count += 1
            except User.DoesNotExist:
                continue

        return Response(
            {"detail": f"Assignment assigned to {created_count} student(s)"},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUserRole])
    def unassign_from_students(self, request):
        assignment_id = request.data.get("assignment_id")
        student_ids = request.data.get("student_ids", [])

        if not assignment_id or not student_ids:
            return Response(
                {"detail": "assignment_id and student_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response(
                {"detail": "Assignment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        deleted_count = 0
        for student_id in student_ids:
            deleted, _ = StudentAssignment.objects.filter(
                student_id=student_id, assignment=assignment
            ).delete()
            deleted_count += deleted

        return Response(
            {"detail": f"Assignment removed from {deleted_count} student(s)"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def student_assignments(self, request):
        student_id = request.query_params.get("student_id")

        if not student_id:
            return Response(
                {"detail": "student_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignments = StudentAssignment.objects.filter(
            student_id=student_id
        ).select_related("assignment", "assignment__course")

        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)


class StudentCertificateViewSet(viewsets.ModelViewSet):
    serializer_class = StudentCertificateSerializer
    permission_classes = [IsAdminUserRole]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["student", "certificate"]
    ordering_fields = ["assigned_at"]
    ordering = ["-assigned_at"]

    def get_queryset(self):
        return StudentCertificate.objects.all()

    @action(detail=False, methods=["post"])
    def assign_to_students(self, request):
        certificate_id = request.data.get("certificate_id")
        student_ids = request.data.get("student_ids", [])

        if not certificate_id or not student_ids:
            return Response(
                {"detail": "certificate_id and student_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            certificate = Certificate.objects.get(id=certificate_id)
        except Certificate.DoesNotExist:
            return Response(
                {"detail": "Certificate not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        created_count = 0
        for student_id in student_ids:
            try:
                student = User.objects.get(id=student_id)
                StudentCertificate.objects.get_or_create(
                    student=student, certificate=certificate
                )
                created_count += 1
            except User.DoesNotExist:
                continue

        return Response(
            {"detail": f"Certificate assigned to {created_count} student(s)"},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def student_certificates(self, request):
        student_id = request.query_params.get("student_id")

        if not student_id:
            return Response(
                {"detail": "student_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        certificates = StudentCertificate.objects.filter(
            student_id=student_id
        ).select_related("certificate")

        serializer = self.get_serializer(certificates, many=True)
        return Response(serializer.data)


class StudentHandoutViewSet(viewsets.ModelViewSet):
    serializer_class = StudentHandoutSerializer
    permission_classes = [IsAdminUserRole]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["student", "handout"]
    ordering_fields = ["assigned_at"]
    ordering = ["-assigned_at"]

    def get_queryset(self):
        return StudentHandout.objects.all()

    @action(detail=False, methods=["post"])
    def assign_to_students(self, request):
        handout_id = request.data.get("handout_id")
        student_ids = request.data.get("student_ids", [])

        if not handout_id or not student_ids:
            return Response(
                {"detail": "handout_id and student_ids are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            handout = Handout.objects.get(id=handout_id)
        except Handout.DoesNotExist:
            return Response(
                {"detail": "Handout not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        created_count = 0
        for student_id in student_ids:
            try:
                student = User.objects.get(id=student_id)
                StudentHandout.objects.get_or_create(
                    student=student, handout=handout
                )
                created_count += 1
            except User.DoesNotExist:
                continue

        return Response(
            {"detail": f"Handout assigned to {created_count} student(s)"},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def student_handouts(self, request):
        student_id = request.query_params.get("student_id")

        if not student_id:
            return Response(
                {"detail": "student_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        handouts = StudentHandout.objects.filter(
            student_id=student_id
        ).select_related("handout", "handout__course")

        serializer = self.get_serializer(handouts, many=True)
        return Response(serializer.data)
