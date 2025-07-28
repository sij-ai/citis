"""
URL patterns for archive-related API endpoints.

These URLs replace the original FastAPI router definitions and provide
structured routing for the Django REST Framework API.
"""

from django.urls import path
from . import views

app_name = 'archive'

urlpatterns = [
    # API endpoints
    path('add', views.AddArchiveView.as_view(), name='add_archive'),
    path('shortcodes', views.ListShortcodesView.as_view(), name='shortcode_list'),
    path('shortcodes/<str:shortcode>', views.ShortcodeDetailView.as_view(), name='shortcode_detail'),
    path('analytics/<str:shortcode>', views.AnalyticsView.as_view(), name='shortcode_analytics'),
    
    # Verification endpoint (implements Basic Proof feature)
    path('verify/<str:shortcode>', views.VerificationView.as_view(), name='verify_shortcode'),
    
    # Archive access endpoint - commented out until ArchivePageView is implemented
    # path('archive/<str:shortcode>', views.ArchivePageView.as_view(), name='archive_page'),
    
    # Health monitoring endpoints - commented out until HealthCheckView is implemented  
    # path('health/<str:shortcode>', views.HealthCheckView.as_view(), name='health_check'),
] 