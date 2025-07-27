"""
URL patterns for internal webhook endpoints.

These endpoints are used for receiving notifications from external services
like ChangeDetection.io for content integrity monitoring.
"""

from django.urls import path
from . import webhook_views

urlpatterns = [
    # ChangeDetection.io webhook endpoint
    path('webhook/changedetection', webhook_views.changedetection_webhook, name='changedetection_webhook'),
] 