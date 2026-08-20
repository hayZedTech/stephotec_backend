from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from django.utils import timezone
from rest_framework import status, mixins, viewsets, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from notifications.email_service import EmailService
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import User, Course, StudentCourse, StudentGroup
from audit.models import AuditLog
from .permissions import IsAdminUserRole
from .serializers import (
    CourseSerializer,
    AdminStudentCreationSerializer,
    AdminStaffSerializer,
    CustomTokenObtainPairSerializer,
    StudentProfileActivationSerializer,
    StudentProfileUpdateSerializer,
    StudentProfileDetailSerializer,
    StudentProfilePageSerializer,
    StudentCourseSerializer,
    AdminProfileUpdateSerializer,
    StudentGroupSerializer,
)
from .services import FileUploadService
from notifications.services import send_student_notification, notify_admins, is_email_enabled

User = get_user_model()

def log_action(user, target, action, changes=None):
    AuditLog.objects.create(
        actor=user,
        target_user=target,
        action=action,
        changes=changes or {},
    )


@extend_schema_view(
    list=extend_schema(summary="List all courses inside Stephotec"),
    create=extend_schema(summary="Create a new course profile (Admin only)"),
    retrieve=extend_schema(summary="Retrieve specific course details"),
    update=extend_schema(summary="Update entire course properties"),
    partial_update=extend_schema(summary="Patch specific course fields"),
    destroy=extend_schema(summary="Delete a course profile"),
)
class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [IsAdminUserRole]
    pagination_class = None
    queryset = Course.objects.all().order_by("-created_at")
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active"]
    search_fields = ["name", "code_prefix"]
    ordering_fields = ["name", "code_prefix", "created_at"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        course = serializer.save()
        log_action(
            self.request.user,
            None,
            "CREATE",
            {"course": course.name, "code_prefix": course.code_prefix},
        )

    def perform_update(self, serializer):
        course = serializer.save()
        log_action(
            self.request.user,
            None,
            "UPDATE",
            {"course": course.name},
        )

    def destroy(self, request, *args, **kwargs):
        course = self.get_object()
        if StudentCourse.objects.filter(course=course).exists():
            return Response(
                {"detail": "This course cannot be deleted because students are still enrolled in it."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        log_action(
            request.user,
            None,
            "DELETE",
            {"course": course.name},
        )
        course.delete()
        return Response(
            {"message": "Course deleted successfully."},
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    create=extend_schema(summary="Onboard / Provision a new Student"),
    list=extend_schema(summary="List all registered students"),
    retrieve=extend_schema(summary="Retrieve a student"),
    update=extend_schema(summary="Update a student"),
    partial_update=extend_schema(summary="Partially update a student"),
    destroy=extend_schema(summary="Delete a student"),
)
class AdminStudentManagementViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AdminStudentCreationSerializer
    permission_classes = [IsAdminUserRole]
    pagination_class = None
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "status",
        "is_industrial_training",
    ]
    search_fields = [
        "username",
        "first_name",
        "last_name",
        "email",
        "courses__course__name",
    ]
    ordering_fields = [
        "username",
        "first_name",
        "last_name",
        "email",
        "status",
        "date_joined",
    ]
    ordering = ["-date_joined"]

    def get_queryset(self):
        queryset = (
            User.objects.filter(role=User.Role.STUDENT)
            .prefetch_related("courses__course")
            .order_by("-date_joined")
        )
        
        # Handle course filtering
        course_id = self.request.query_params.get('courses__course_id')
        if course_id:
            queryset = queryset.filter(courses__course_id=course_id)
        
        return queryset

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        temporary_password = student.temporary_password
        log_action(
            request.user,
            student,
            "CREATE",
            {"email": student.email, "username": student.username},
        )
        send_student_notification(
            student=student,
            title="Welcome to Stephotec Portal!",
            message=f"Hello {student.first_name or student.username}, your student account has been created successfully. Welcome aboard!",
            notification_type="SUCCESS",
            created_by=request.user,
        )
        if student.email and temporary_password and is_email_enabled("email_welcome"):
            try:
                frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
                activation_url = f"{frontend_url}/activate-profile"
                EmailService.send_welcome_account_email(student, temporary_password, activation_url)
            except Exception:
                pass

        resp_data = self.get_serializer(student).data
        resp_data["message"] = "Student account provisioned successfully."
        resp_data["temporary_password"] = temporary_password
        resp_data["student_details"] = self.get_serializer(student).data
        return Response(resp_data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        student = serializer.save()
        log_action(
            self.request.user,
            student,
            "UPDATE",
        )

    def destroy(self, request, *args, **kwargs):
        student = self.get_object()
        if student.status == User.Status.ACTIVE:
            return Response(
                {"detail": "Active students cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        student.is_deleted = True
        student.deleted_at = timezone.now()
        student.deleted_by = request.user
        student.save()
        log_action(
            request.user,
            student,
            "DELETE",
        )
        return Response(
            {"message": "Student soft deleted successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        ids = request.data.get("ids", [])
        students = User.objects.filter(
            id__in=ids,
            role=User.Role.STUDENT,
        )
        active = students.filter(status=User.Status.ACTIVE)
        if active.exists():
            return Response(
                {
                    "detail": "Cannot delete ACTIVE students.",
                    "blocked_ids": list(active.values_list("id", flat=True)),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        for student in students:
            student.is_deleted = True
            student.deleted_at = timezone.now()
            student.deleted_by = request.user
            student.save()
            log_action(
                request.user,
                student,
                "DELETE",
            )
        return Response(
            {"message": f"{students.count()} students deleted."},
            status=status.HTTP_200_OK,
        )

@extend_schema_view(
    list=extend_schema(summary="List student's courses"),
    create=extend_schema(summary="Add course to student"),
    retrieve=extend_schema(summary="Get student's course details"),
    update=extend_schema(summary="Update student's course status"),
    partial_update=extend_schema(summary="Partially update student's course"),
    destroy=extend_schema(summary="Remove course from student"),
)
class StudentCourseViewSet(viewsets.ModelViewSet):
    serializer_class = StudentCourseSerializer
    permission_classes = [IsAdminUserRole]
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "is_primary", "admission_year"]
    ordering_fields = ["started_at", "admission_year", "status"]
    ordering = ["-started_at"]
    
    def get_queryset(self):
        student_id = self.kwargs.get("student_id")
        return StudentCourse.objects.filter(
            student_id=student_id
        ).select_related("course")
    
    def create(self, request, *args, **kwargs):
        student_id = self.kwargs.get("student_id")
        student = User.objects.get(id=student_id)
        
        # Get admission year from student's existing courses
        existing_course = student.courses.first()
        admission_year = existing_course.admission_year if existing_course else 2026
        
        # Add admission_year to request data
        data = request.data.copy()
        data['admission_year'] = admission_year
        
        serializer = self.get_serializer(data=data, context={**self.get_serializer_context(), "student": student})
        serializer.is_valid(raise_exception=True)
        course_enrollment = serializer.save(student=student)
        
        # Auto-create Payment with course default_fee
        from payments.models import Payment
        payment, _ = Payment.objects.get_or_create(student_course=course_enrollment)
        if payment.course_fee == 0 and course_enrollment.course.default_fee:
            payment.course_fee = course_enrollment.course.default_fee
            payment.save()
        
        log_action(
            request.user,
            student,
            "ADD_COURSE",
            {"course": course_enrollment.course.name},
        )
        send_student_notification(
            student=student,
            title="New Course Enrollment",
            message=f"You have been enrolled in '{course_enrollment.course.name}'. Check your dashboard to access course materials.",
            notification_type="INFO",
            created_by=request.user,
            event_key="email_course_enrollment",
        )
        
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )
    
    def perform_update(self, serializer):
        # If setting is_primary to True, unset other primary courses
        if serializer.validated_data.get('is_primary', False):
            StudentCourse.objects.filter(
                student=serializer.instance.student
            ).exclude(id=serializer.instance.id).update(is_primary=False)
        
        course_enrollment = serializer.save()
        log_action(
            self.request.user,
            course_enrollment.student,
            "UPDATE_COURSE",
            {"course": course_enrollment.course.name, "status": course_enrollment.status},
        )
        send_student_notification(
            student=course_enrollment.student,
            title="Course Status Updated",
            message=f"Your course status for '{course_enrollment.course.name}' has been updated to {course_enrollment.status}.",
            notification_type="INFO",
            created_by=self.request.user,
            event_key="email_course_enrollment",
        )
    
    def destroy(self, request, *args, **kwargs):
        course_enrollment = self.get_object()
        student = course_enrollment.student
        course_name = course_enrollment.course.name
        log_action(
            request.user,
            student,
            "REMOVE_COURSE",
            {"course": course_name},
        )
        course_enrollment.delete()
        return Response(
            {"message": "Course removed from student successfully."},
            status=status.HTTP_200_OK,
        )

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class StudentProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if user.role != User.Role.STUDENT:
            return Response(
                {"detail": "This endpoint is only for students."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        serializer = StudentProfileDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        user = request.user
        if user.role != User.Role.STUDENT:
            return Response(
                {"detail": "This endpoint is only for students."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        serializer = StudentProfileUpdateSerializer(
            instance=user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            StudentProfileDetailSerializer(user).data,
            status=status.HTTP_200_OK,
        )

class StudentProfilePageView(APIView):
    """Dedicated endpoint for profile page with complete user data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if user.role != User.Role.STUDENT:
            return Response(
                {"detail": "This endpoint is only for students."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        serializer = StudentProfilePageSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class StudentProfileActivationView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentProfileActivationSerializer
    def put(self, request, *args, **kwargs):
        user = request.user
        if user.role != User.Role.STUDENT:
            return Response(
                {"detail": "This endpoint is only for students."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.serializer_class(
            instance=user,
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Dispatch notification alert to all admins
        try:
            student_name = user.get_full_name() or user.username
            notify_admins(
                title="Student Profile Activated",
                message=f"Student '{student_name}' ({user.username}) has successfully activated their profile.",
                alert_type="STUDENT_ACTION",
                triggered_by=user,
                related_object_id=user.id,
            )
        except Exception:
            pass

        log_action(
            user,
            user,
            "ACTIVATE_PROFILE",
        )

        return Response(
            {
                "message": "Profile activated successfully.",
                "user": AdminStudentCreationSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        if not old_password or not new_password or not confirm_password:
            return Response(
                {"detail": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if not user.check_password(old_password):
            return Response(
                {"detail": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if new_password != confirm_password:
            return Response(
                {"detail": "New passwords do not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if len(new_password) < 8:
            return Response(
                {"detail": "Password must be at least 8 characters long."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        user.set_password(new_password)
        user.save()
        
        log_action(
            user,
            user,
            "CHANGE_PASSWORD",
        )
        
        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )

class FileUploadView(APIView):
    """Handle file uploads to Cloudinary"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Upload profile picture",
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}},
    )
    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {"detail": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            url = FileUploadService.upload_profile_picture(file, request.user.id)
            user = request.user
            user.profile_picture_url = url
            user.save(update_fields=['profile_picture_url'])
            return Response(
                {"url": url},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PublicStudentVerifyView(APIView):
    """Public endpoint to verify a student ID / enrollment ID / username without authentication"""
    permission_classes = []

    @extend_schema(summary="Public student verification endpoint")
    def get(self, request):
        query = request.query_params.get("query") or request.query_params.get("student") or request.query_params.get("id")
        if not query:
            return Response({"detail": "Verification query parameter required."}, status=status.HTTP_400_BAD_REQUEST)

        query = query.strip().rstrip('/')
        
        # Search by username, email, or StudentCourse enrollment_id!
        student = User.objects.filter(
            models.Q(username__iexact=query) |
            models.Q(email__iexact=query) |
            models.Q(courses__enrollment_id__iexact=query)
        ).distinct().first()

        if not student:
            return Response(
                {
                    "is_verified": False,
                    "detail": f"No official student record found matching '{query}'.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        primary_course = student.courses.filter(is_primary=True).first() or student.courses.first()
        course_name = primary_course.course.name if primary_course else "Computer Studies"
        student_id_display = primary_course.enrollment_id if primary_course else student.username

        return Response(
            {
                "is_verified": True,
                "full_name": student.get_full_name() or student.username,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "username": student_id_display,
                "status": student.status,
                "primary_course": course_name,
                "admission_year": primary_course.admission_year if primary_course else student.admission_year,
                "profile_picture_url": student.profile_picture_url,
                "verification_date": timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "institution": "Stephotec Computer Technologies Ltd",
            },
            status=status.HTTP_200_OK,
        )


class RequestPasswordResetView(APIView):
    """Public endpoint to request a password reset email."""
    permission_classes = []

    @extend_schema(summary="Request Password Reset Email")
    def post(self, request):
        query = request.data.get("email_or_username") or request.data.get("email") or request.data.get("username")
        if not query:
            return Response(
                {"detail": "Email or Username is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        query = query.strip()
        user = User.objects.filter(
            models.Q(email__iexact=query) | models.Q(username__iexact=query)
        ).first()

        if user and user.email:
            if is_email_enabled("email_password_reset"):
                print(f"[PASSWORD RESET] Request received for existing user '{user.username}' ({user.email}). Dispatching email...", flush=True)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
                reset_url = f"{frontend_url}/reset-password?uid={uidb64}&token={token}"
                EmailService.send_password_reset_email(user, reset_url)
            else:
                print(f"[PASSWORD RESET] Password reset email is disabled in settings for user '{user.username}'.", flush=True)
        else:
            print(f"[PASSWORD RESET] Request received for query '{query}', but NO MATCHING USER or NO EMAIL found in database! (user={user})", flush=True)

        return Response(
            {
                "message": "If an account with that email or username exists, password reset instructions have been sent to your email."
            },
            status=status.HTTP_200_OK,
        )


class ConfirmPasswordResetView(APIView):
    """Public endpoint to confirm password reset with token."""
    permission_classes = []

    @extend_schema(summary="Confirm Password Reset")
    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not uidb64 or not token or not new_password:
            return Response(
                {"detail": "uid, token, and new_password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 6:
            return Response(
                {"detail": "Password must be at least 6 characters long."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid reset link or user does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired reset token. Please request a new password reset."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.must_change_password = False
        user.save()

        return Response(
            {"message": "Your password has been reset successfully. You may now log in with your new password."},
            status=status.HTTP_200_OK,
        )


class AdminStaffManagementViewSet(viewsets.ModelViewSet):
    """ViewSet to list, create, update, and delete Admin / Staff users."""
    serializer_class = AdminStaffSerializer
    permission_classes = [IsAdminUserRole]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["username", "first_name", "last_name", "email", "phone"]
    ordering_fields = ["username", "first_name", "last_name", "date_joined"]
    ordering = ["-date_joined"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.filter(role=User.Role.ADMIN).order_by("-date_joined")
        return User.objects.filter(pk=user.pk)

    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Only superusers can create new staff accounts."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff = serializer.save()
        log_action(
            request.user,
            staff,
            "CREATE_STAFF",
            {"email": staff.email, "username": staff.username},
        )
        return Response(
            {
                "message": "Staff / Administrator account created successfully.",
                "temporary_password": staff.temporary_password,
                "staff_details": self.get_serializer(staff).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_superuser and instance.pk != request.user.pk:
            return Response(
                {"detail": "You do not have permission to update other staff profiles."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_superuser and instance.pk != request.user.pk:
            return Response(
                {"detail": "You do not have permission to update other staff profiles."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Only superusers can delete staff accounts."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="titles")
    def titles(self, request):
        titles = [choice[0] for choice in User.STAFF_TITLE_CHOICES]
        return Response({"titles": titles}, status=status.HTTP_200_OK)


class PublicStaffVerifyView(APIView):
    """Public endpoint to verify a Staff / Administrator ID or username without authentication"""
    permission_classes = []

    @extend_schema(summary="Public staff verification endpoint")
    def get(self, request):
        query = (
            request.query_params.get("staff")
            or request.query_params.get("username")
            or request.query_params.get("query")
            or request.query_params.get("id")
        )
        if not query:
            return Response({"detail": "Verification query parameter required."}, status=status.HTTP_400_BAD_REQUEST)

        query = query.strip().rstrip('/')
        staff = User.objects.filter(role=User.Role.ADMIN).filter(
            models.Q(username__iexact=query) |
            models.Q(email__iexact=query) |
            models.Q(id=int(query) if query.isdigit() else -1)
        ).first()

        if not staff:
            return Response(
                {
                    "is_verified": False,
                    "detail": f"No official Staff / Administrator record found matching '{query}'.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "is_verified": True,
                "full_name": staff.get_full_name() or staff.username,
                "first_name": staff.first_name,
                "last_name": staff.last_name,
                "username": staff.username,
                "role": staff.job_title or "System Administrator",
                "status": staff.status,
                "email": staff.email,
                "phone": staff.phone,
                "profile_picture_url": staff.profile_picture_url,
                "verification_date": timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "institution": "Stephotec Computer Technologies Ltd",
            },
            status=status.HTTP_200_OK,
        )


class AdminProfileView(APIView):
    """Allows the logged-in admin/staff user to view and update their own profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in [User.Role.ADMIN]:
            return Response({"detail": "Only admin users can access this endpoint."}, status=status.HTTP_403_FORBIDDEN)
        serializer = AdminProfileUpdateSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        if request.user.role not in [User.Role.ADMIN]:
            return Response({"detail": "Only admin users can access this endpoint."}, status=status.HTTP_403_FORBIDDEN)
        serializer = AdminProfileUpdateSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.to_representation(request.user), status=status.HTTP_200_OK)


import json
import os

class AdminSettingsView(APIView):
    """
    Endpoint to load and update global system settings.
    Saves state in a json file system_settings.json.
    """
    permission_classes = []

    @property
    def settings_file_path(self):
        return os.path.join(settings.BASE_DIR, 'system_settings.json')

    def get_default_settings(self):
        return {
            "emailNotifications": True,
            "email_welcome": True,
            "email_password_reset": True,
            "email_status_change": True,
            "email_course_enrollment": True,
            "email_class_materials": True,
            "email_new_assignment": True,
            "email_assignment_grading": True,
            "email_attendance": False,
            "email_quiz_results": True,
            "email_certificate": True,
            "email_payment_receipt": True,
            "autoApproveStudents": False,
            "maintenanceMode": False,
            "allowNewRegistrations": True,
            "allowIdCardDownload": True,
        }

    def load_settings(self):
        file_path = self.settings_file_path
        if not os.path.exists(file_path):
            return self.get_default_settings()
        try:
            with open(file_path, 'r') as f:
                return {**self.get_default_settings(), **json.load(f)}
        except Exception:
            return self.get_default_settings()

    def save_settings(self, settings_data):
        try:
            with open(self.settings_file_path, 'w') as f:
                json.dump(settings_data, f, indent=4)
            return True
        except Exception:
            return False

    def get(self, request):
        return Response(self.load_settings(), status=status.HTTP_200_OK)

    def put(self, request):
        current = self.load_settings()
        new_data = request.data
        for key in self.get_default_settings().keys():
            if key in new_data:
                # convert to boolean
                val = new_data[key]
                if isinstance(val, str):
                    current[key] = val.lower() == 'true'
                else:
                    current[key] = bool(val)
        if self.save_settings(current):
            return Response(current, status=status.HTTP_200_OK)
        return Response({"detail": "Failed to save settings file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        return self.put(request)


class StudentGroupViewSet(viewsets.ModelViewSet):
    """Admin CRUD for student groups, plus student-facing list of own groups."""
    serializer_class = StudentGroupSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["course"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "ADMIN":
            return StudentGroup.objects.select_related("course").prefetch_related("members").all()
        # Students see only their own groups
        return StudentGroup.objects.filter(members=user).select_related("course").prefetch_related("members")

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "bulk_delete"]:
            return [IsAdminUserRole()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        group = serializer.save()
        log_action(self.request.user, None, "CREATE", {"group": group.name, "course": group.course.name})

    def perform_destroy(self, instance):
        log_action(self.request.user, None, "DELETE", {"group": instance.name})
        instance.delete()

    @action(detail=False, methods=["post"], permission_classes=[IsAdminUserRole], url_path="bulk-delete")
    def bulk_delete(self, request):
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"detail": "ids list is required."}, status=status.HTTP_400_BAD_REQUEST)
        deleted_count, _ = StudentGroup.objects.filter(id__in=ids).delete()
        return Response({"detail": f"{deleted_count} group(s) deleted."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUserRole], url_path="add-members")
    def add_members(self, request, pk=None):
        group = self.get_object()
        member_ids = request.data.get("member_ids", [])
        if not member_ids:
            return Response({"detail": "member_ids is required."}, status=status.HTTP_400_BAD_REQUEST)
        students = User.objects.filter(id__in=member_ids, role="STUDENT")
        group.members.add(*students)
        return Response(StudentGroupSerializer(group, context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUserRole], url_path="remove-members")
    def remove_members(self, request, pk=None):
        group = self.get_object()
        member_ids = request.data.get("member_ids", [])
        if not member_ids:
            return Response({"detail": "member_ids is required."}, status=status.HTTP_400_BAD_REQUEST)
        students = User.objects.filter(id__in=member_ids)
        group.members.remove(*students)
        return Response(StudentGroupSerializer(group, context={"request": request}).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="my-groups")
    def my_groups(self, request):
        """Returns all groups the current student belongs to."""
        if request.user.role != "STUDENT":
            return Response({"detail": "Only students can access this endpoint."}, status=status.HTTP_403_FORBIDDEN)
        groups = StudentGroup.objects.filter(members=request.user).select_related("course").prefetch_related("members")
        serializer = StudentGroupSerializer(groups, many=True, context={"request": request})
        return Response(serializer.data)
