"""
Root URL configuration for Campus Complaint Management Portal.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Root → redirect to login
    path('', RedirectView.as_view(url='/auth/login/', permanent=False)),

    path('admin/', admin.site.urls),

    # Module 4 - Authentication
    path('auth/', include('automation_auth.urls')),

    # Module 5 - Complaint submission
    path('complaints/', include('submission_monitoring.urls')),

    # Module 6 - Status tracking
    path('track/', include('status_caching.urls')),

    # Module 3 - Analytics & dashboard
    path('dashboard/', include('analytics_scheduling.urls')),

    # Module 1 - Concurrency & transactions (admin-facing)
    path('assign/', include('concurrency_transactions.urls')),

    # Module 2 - File engine (attachments)
    path('files/', include('file_engine.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
