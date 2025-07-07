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
    path('_add', views.AddArchiveView.as_view(), name='add_archive'),
    
    # Shortcode management
    path('_shortcodes', views.ListShortcodesView.as_view(), name='list_shortcodes'),
    path('_shortcodes/<str:shortcode>', views.ShortcodeDetailView.as_view(), name='shortcode_detail'),
    
    # Analytics
    path('_analytics/<str:shortcode>', views.AnalyticsView.as_view(), name='analytics'),
    
    # API key management
    path('_api/keys', views.APIKeyCreateView.as_view(), name='create_api_key'),
    path('_api/keys/<str:api_key>', views.APIKeyUpdateView.as_view(), name='update_api_key'),
    
    # Admin endpoints
    path('_cache/clear', views.clear_cache, name='clear_cache'),
    path('_health', views.health_check, name='health_check'),
    path('_info', views.get_info, name='info'),
] 