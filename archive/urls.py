"""
URL patterns for archive-related API endpoints.

These URLs replace the original FastAPI router definitions and provide
structured routing for the Django REST Framework API.
"""

from django.urls import path
from . import views

app_name = 'archive'

urlpatterns = [
    # Archive creation
    path('add', views.AddArchiveView.as_view(), name='add_archive'),
    
    # Shortcode management
    path('shortcodes', views.ListShortcodesView.as_view(), name='list_shortcodes'),
    path('shortcodes/<str:shortcode>', views.ShortcodeDetailView.as_view(), name='shortcode_detail'),
    
    # Analytics
    path('analytics/<str:shortcode>', views.AnalyticsView.as_view(), name='analytics'),
    
    # API key management
    path('api/keys', views.APIKeyCreateView.as_view(), name='create_api_key'),
    path('api/keys/<str:api_key>', views.APIKeyUpdateView.as_view(), name='update_api_key'),
    
    # Admin endpoints
    path('cache/clear', views.clear_cache, name='clear_cache'),
    path('health', views.health_check, name='health_check'),
    path('info', views.get_info, name='info'),
] 