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
    FileUploadView,
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'admin/students', AdminStudentManagementViewSet, basename='admin-student')

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
    path('student/profile/', StudentProfileView.as_view(), name='student_profile'),
    path('student/profile-page/', StudentProfilePageView.as_view(), name='student_profile_page'),
    path('student/activate-profile/', StudentProfileActivationView.as_view(), name='student_activate_profile'),
    # File Upload
    path('upload/profile-picture/', FileUploadView.as_view(), name='upload_profile_picture'),
]
