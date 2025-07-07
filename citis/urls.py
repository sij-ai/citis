"""
URL configuration for citis project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication URLs
    path('accounts/', include('allauth.urls')),
    
    # API endpoints
    path('api/v1/', include('archive.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # Add future app URLs here:
    # path('api/v1/analytics/', include('analytics.urls')),
    # path('api/v1/accounts/', include('accounts.urls')),
    # path('', include('web.urls')),  # Web interface URLs
]

# Add URL prefix if configured
if settings.SERVER_URL_PREFIX:
    # Wrap all patterns with the prefix
    prefixed_patterns = [
        path(f'{settings.SERVER_URL_PREFIX}/', include(urlpatterns)),
    ]
    urlpatterns = prefixed_patterns
