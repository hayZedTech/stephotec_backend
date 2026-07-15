from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LearningContentViewSet,
    AssignmentViewSet,
    AssignmentSubmissionViewSet,
    AttendanceViewSet,
    CertificateViewSet,
    HandoutViewSet,
    HandoutPurchaseViewSet,
    NotificationViewSet,
    MessageViewSet,
    StudentLearningContentViewSet,
    StudentAssignmentViewSet,
    StudentCertificateViewSet,
    StudentHandoutViewSet,
)

router = DefaultRouter()
router.register(r"learning-content", LearningContentViewSet, basename="learning-content")
router.register(r"assignments", AssignmentViewSet, basename="assignment")
router.register(r"submissions", AssignmentSubmissionViewSet, basename="submission")
router.register(r"attendance", AttendanceViewSet, basename="attendance")
router.register(r"certificates", CertificateViewSet, basename="certificate")
router.register(r"handouts", HandoutViewSet, basename="handout")
router.register(r"handout-purchases", HandoutPurchaseViewSet, basename="handout-purchase")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"messages", MessageViewSet, basename="message")
router.register(r"student-learning-content", StudentLearningContentViewSet, basename="student-learning-content")
router.register(r"student-assignments", StudentAssignmentViewSet, basename="student-assignment")
router.register(r"student-certificates", StudentCertificateViewSet, basename="student-certificate")
router.register(r"student-handouts", StudentHandoutViewSet, basename="student-handout")

urlpatterns = [
    path("", include(router.urls)),
]
