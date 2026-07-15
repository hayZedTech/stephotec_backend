from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Route matching ws://your-domain/ws/dashboard/notifications/
    re_path(r'^ws/dashboard/notifications/$', consumers.DashboardNotificationConsumer),
]