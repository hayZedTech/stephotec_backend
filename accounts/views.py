from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, mixins, viewsets, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import User, Course, StudentCourse
from audit.models import AuditLog
from .permissions import IsAdminUserRole
from .serializers import (
    CourseSerializer,
    AdminStudentCreationSerializer,
    CustomTokenObtainPairSerializer,
    StudentProfileActivationSerializer,
    StudentProfileUpdateSerializer,
    StudentProfileDetailSerializer,
    StudentProfilePageSerializer,
    StudentCourseSerializer,
)
from .services import FileUploadService

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
        return Response(
            {
                "message": "Student account provisioned successfully.",
                "temporary_password": temporary_password,
                "student_details": self.get_serializer(student).data,
            },
            status=status.HTTP_201_CREATED,
        )

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
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        course_enrollment = serializer.save(student=student)
        
        log_action(
            request.user,
            student,
            "ADD_COURSE",
            {"course": course_enrollment.course.name},
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
            return Response(
                {"url": url},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
