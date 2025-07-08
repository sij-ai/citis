"""
URL configuration for citis project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Core Apps
    path('accounts/', include('allauth.urls')),
    path('stripe/', include('djstripe.urls', namespace='djstripe')),

    # API Endpoints
    path('api/v1/', include('archive.urls')),

    # API Schema & Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Frontend Web UI - This must be last to catch the root path
    path('', include('web.urls')),
]
