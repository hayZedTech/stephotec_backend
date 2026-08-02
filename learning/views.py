from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.services import FileUploadService
from notifications.models import AdminAlert
from notifications.services import (
    send_student_notification,
    send_bulk_student_notifications,
    notify_admins,
)
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
)
from .serializers import (
    LearningContentSerializer,
    AssignmentSerializer,
    AssignmentSubmissionSerializer,
    AttendanceSerializer,
    CertificateSerializer,
    HandoutSerializer,
    HandoutPurchaseSerializer,
    BrochureSerializer,
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
    pagination_class = None
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
    pagination_class = None
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
    pagination_class = None
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
        submission = serializer.save(student=request.user)

        # Notify admins about assignment submission
        student_name = request.user.get_full_name() or request.user.username
        assignment_title = submission.assignment.title if hasattr(submission, "assignment") else "Assignment"
        notify_admins(
            title="New Assignment Submission",
            message=f"{student_name} ({request.user.username}) submitted assignment '{assignment_title}'.",
            alert_type="ASSIGNMENT_SUBMISSION",
            triggered_by=request.user,
            related_object_id=submission.id,
        )

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

        # Send notification to student
        send_student_notification(
            student=submission.student,
            title="Assignment Graded",
            message=f"Your submission for '{submission.assignment.title}' has been graded. Score: {score}/{submission.assignment.max_score}." + (f" Feedback: {feedback}" if feedback else ""),
            notification_type="SUCCESS",
            created_by=request.user,
        )

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
        notify_admins(
            title=f"Attendance Request — {student_name}",
            message=(
                f"{student_name} ({student_course.enrollment_id}) marked attendance "
                f"for {date} in {student_course.course.name}."
                + (f" Note: {remarks}" if remarks else "")
            ),
            alert_type="ATTENDANCE_REQUEST",
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

        send_student_notification(
            student=attendance.student_course.student,
            title="Attendance Approved",
            message=f"Your attendance for {attendance.date} in '{attendance.student_course.course.name}' has been approved.",
            notification_type="SUCCESS",
            created_by=request.user,
        )

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

        send_student_notification(
            student=attendance.student_course.student,
            title="Attendance Rejected",
            message=f"Your attendance for {attendance.date} in '{attendance.student_course.course.name}' was rejected." + (f" Reason: {attendance.remarks}" if attendance.remarks else ""),
            notification_type="WARNING",
            created_by=request.user,
        )

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
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["student_course", "status"]
    ordering_fields = ["earned_date"]
    ordering = ["-earned_date"]

    def get_queryset(self):
        user = self.request.user
        qs = Certificate.objects.all() if user.role == "ADMIN" else Certificate.objects.filter(student_course__student=user)
        student_id = (
            self.request.query_params.get("student_id")
            or self.request.query_params.get("student_course__student")
            or self.request.query_params.get("student")
        )
        if student_id:
            qs = qs.filter(student_course__student_id=student_id)
        return qs

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            data["file"] = FileUploadService.upload_certificate(uploaded_file, "new")
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Send notification to student
        student = instance.student_course.student
        send_student_notification(
            student=student,
            title="New Certificate Earned!",
            message=f"You have earned a new certificate: '{instance.title}' ({instance.certificate_number}) for {instance.student_course.course.name}.",
            notification_type="SUCCESS",
            created_by=request.user,
        )

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

        student = certificate.student_course.student
        send_student_notification(
            student=student,
            title="Certificate Issued!",
            message=f"Congratulations! Your certificate '{certificate.title}' ({certificate.certificate_number}) for {certificate.student_course.course.name} has been officially issued. You can now download it from your Learning Portal.",
            notification_type="SUCCESS",
            created_by=request.user,
        )

        return Response(
            CertificateSerializer(certificate).data, status=status.HTTP_200_OK
        )


class HandoutViewSet(viewsets.ModelViewSet):
    serializer_class = HandoutSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
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


class BrochureViewSet(viewsets.ModelViewSet):
    serializer_class = BrochureSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["course"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return Brochure.objects.all()
        # For students: return brochures for courses the student is registered/enrolled in
        student_course_ids = user.courses.values_list("course_id", flat=True)
        return Brochure.objects.filter(course_id__in=student_course_ids)

    def create(self, request, *args, **kwargs):
        if request.user.role != "ADMIN":
            return Response({"detail": "Only admins can upload brochures"}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            data["file"] = FileUploadService.upload_brochure(uploaded_file, data.get("course"))
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role != "ADMIN":
            return Response({"detail": "Only admins can update brochures"}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        data = request.data.copy()
        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            data["file"] = FileUploadService.upload_brochure(uploaded_file, instance.course_id)
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != "ADMIN":
            return Response({"detail": "Only admins can delete brochures"}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class HandoutPurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = HandoutPurchaseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["handout", "student", "status"]
    ordering_fields = ["purchased_at"]
    ordering = ["-purchased_at"]

    def get_queryset(self):
        user = self.request.user
        qs = HandoutPurchase.objects.all() if user.role == "ADMIN" else HandoutPurchase.objects.filter(student=user)
        student_id = self.request.query_params.get("student_id") or self.request.query_params.get("student")
        if student_id:
            qs = qs.filter(student_id=student_id)
        return qs

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
        if existing:
            if existing.status == "COMPLETED":
                return Response(
                    {"detail": "You have already acquired this handout."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if existing.status == "PENDING":
                return Response(
                    HandoutPurchaseSerializer(existing).data,
                    status=status.HTTP_200_OK,
                )

        txn_id = f"REQ_{handout.id}_{request.user.id}_{int(timezone.now().timestamp())}"
        purchase = HandoutPurchase.objects.create(
            handout=handout,
            student=request.user,
            amount_paid=handout.price,
            status="PENDING",
            transaction_id=txn_id,
        )

        # Notify student: their request is pending
        send_student_notification(
            student=request.user,
            title="Handout Request Received",
            message=f"Your request for '{handout.title}' (₦{handout.price:,.2f}) has been received and is pending payment confirmation. Please make payment to the provided bank account.",
        )

        # Notify all admins about the new request
        student_name = request.user.get_full_name() or request.user.username
        notify_admins(
            title="New Handout Payment Request",
            message=f"{student_name} ({request.user.username}) requested handout '{handout.title}' (₦{handout.price:,.2f}). Please confirm payment and approve.",
            alert_type="HANDOUT_REQUEST",
            triggered_by=request.user,
            related_object_id=purchase.id,
        )

        return Response(
            HandoutPurchaseSerializer(purchase).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUserRole])
    def approve(self, request, pk=None):
        purchase = self.get_object()
        purchase.status = "COMPLETED"
        purchase.save()

        # Create StudentHandout link
        StudentHandout.objects.get_or_create(
            student=purchase.student, handout=purchase.handout
        )

        # Notify student of approval
        send_student_notification(
            student=purchase.student,
            title="Handout Payment Approved! ✅",
            message=f"Your payment for '{purchase.handout.title}' has been confirmed and approved. You can now access and download it from your Learning Portal.",
            created_by=request.user,
        )

        return Response(HandoutPurchaseSerializer(purchase).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUserRole])
    def reject(self, request, pk=None):
        purchase = self.get_object()
        purchase.status = "FAILED"
        purchase.save()

        send_student_notification(
            student=purchase.student,
            title="Handout Request Not Approved",
            message=f"Your payment request for '{purchase.handout.title}' was not confirmed. Please contact support if you believe this is an error.",
            created_by=request.user,
        )

        return Response(HandoutPurchaseSerializer(purchase).data, status=status.HTTP_200_OK)

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
                item, created = StudentLearningContent.objects.get_or_create(
                    student_course=student_course, learning_content=content
                )
                if created:
                    send_student_notification(
                        student=student_course.student,
                        title="New Learning Material Assigned",
                        message=f"New material '{content.title}' ({content.content_type}) has been assigned to you in {content.course.name}.",
                        notification_type="INFO",
                        created_by=request.user,
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

        if not student_id:
            return Response(
                {"detail": "student_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignments = StudentLearningContent.objects.filter(
            student_course__student_id=student_id
        )
        if course_id:
            assignments = assignments.filter(student_course__course_id=course_id)

        assignments = assignments.select_related("learning_content", "learning_content__course", "student_course")

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
                item, created = StudentAssignment.objects.get_or_create(
                    student=student, assignment=assignment
                )
                if created:
                    send_student_notification(
                        student=student,
                        title="New Assignment Assigned",
                        message=f"You have been assigned '{assignment.title}' in {assignment.course.name}. Due date: {assignment.due_date or 'N/A'}.",
                        notification_type="INFO",
                        created_by=request.user,
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
                item, created = StudentCertificate.objects.get_or_create(
                    student=student, certificate=certificate
                )
                if created:
                    send_student_notification(
                        student=student,
                        title="Certificate Assigned",
                        message=f"Certificate '{certificate.title}' ({certificate.certificate_number}) has been assigned to you.",
                        notification_type="SUCCESS",
                        created_by=request.user,
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
                item, created = StudentHandout.objects.get_or_create(
                    student=student, handout=handout
                )
                if created:
                    send_student_notification(
                        student=student,
                        title="New Study Handout Available",
                        message=f"Study handout '{handout.title}' for {handout.course.name} is now available.",
                        notification_type="INFO",
                        created_by=request.user,
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
