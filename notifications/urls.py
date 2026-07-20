from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, AdminAlertViewSet

router = DefaultRouter()
router.register(r"admin-alerts", AdminAlertViewSet, basename="admin-alert")
router.register(r"", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
]
