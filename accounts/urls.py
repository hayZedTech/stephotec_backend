from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CourseViewSet,
    AdminStudentManagementViewSet,
    StudentCourseViewSet,
    CustomTokenObtainPairView,
    StudentProfileView,
    StudentProfilePageView,
    StudentProfileActivationView,
    ChangePasswordView,
    FileUploadView,
    PublicStudentVerifyView,
    RequestPasswordResetView,
    ConfirmPasswordResetView,
    AdminStaffManagementViewSet,
    PublicStaffVerifyView,
    AdminProfileView,
    AdminSettingsView,
    StudentGroupViewSet,
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'admin/students', AdminStudentManagementViewSet, basename='admin-student')
router.register(r'admin/staff', AdminStaffManagementViewSet, basename='admin-staff')
router.register(r'admin/groups', StudentGroupViewSet, basename='admin-group')

# Nested router for student courses
student_router = DefaultRouter()
student_router.register(
    r'courses',
    StudentCourseViewSet,
    basename='student-course'
)

urlpatterns = [
    # Router ViewSets (Courses and Admin Student Management)
    path('', include(router.urls)),
    # Nested student courses
    path('admin/students/<int:student_id>/', include(student_router.urls)),
    # Core Authentication & Profile Activation Routes
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/password-reset/request/', RequestPasswordResetView.as_view(), name='password_reset_request'),
    path('auth/password-reset/confirm/', ConfirmPasswordResetView.as_view(), name='password_reset_confirm'),
    path('student/profile/', StudentProfileView.as_view(), name='student_profile'),
    path('student/profile-page/', StudentProfilePageView.as_view(), name='student_profile_page'),
    path('student/activate-profile/', StudentProfileActivationView.as_view(), name='student_activate_profile'),
    path('student/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('student/verify/', PublicStudentVerifyView.as_view(), name='student_verify'),
    path('staff/verify/', PublicStaffVerifyView.as_view(), name='staff_verify'),
    # File Upload
    path('upload/profile-picture/', FileUploadView.as_view(), name='upload_profile_picture'),
    path('admin/profile/', AdminProfileView.as_view(), name='admin_profile'),
    path('admin/settings/', AdminSettingsView.as_view(), name='admin_settings'),
]
