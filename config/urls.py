from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView, 
    SpectacularRedocView, 
    SpectacularSwaggerView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Core API Core App Endpoints
    path('api/v1/', include('accounts.urls')),
    path('api/v1/audit/', include('audit.urls')),
    path('api/v1/learning/', include('learning.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/payments/', include('payments.urls')),
    
    # OpenAPI Schema Auto-Generation Engines & Swagger UIs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
