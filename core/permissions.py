"""
Custom Django REST Framework permission classes for the citis application.

These permission classes replace the manual API key validation functions from the
original FastAPI implementation and provide Django-integrated authorization.
"""

from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from archive.models import ApiKey


class IsAuthenticatedWithApiKey(permissions.BasePermission):
    """
    Permission class that requires a valid API key for access.
    
    Checks the Authorization header for a Bearer token and validates it
    against active API keys with usage limits.
    """
    
    def has_permission(self, request, view):
        """Check if request has valid API key authentication"""
        api_key = self._extract_api_key(request)
        if not api_key:
            return False
            
        # Store the validated API key in the request for later use
        request.api_key = api_key
        return True
    
    def _extract_api_key(self, request):
        """Extract and validate API key from Authorization header"""
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        key = auth_header[7:]  # Remove 'Bearer ' prefix
        return self._validate_api_key(key)
    
    def _validate_api_key(self, key):
        """Validate API key and check usage limits"""
        try:
            api_key = ApiKey.objects.get(key=key, is_active=True)
        except ApiKey.DoesNotExist:
            return None
        
        # Check total usage limit
        if api_key.max_uses_total is not None:
            total_uses = api_key.get_total_usage()
            if total_uses >= api_key.max_uses_total:
                return None
        
        # Check daily usage limit
        if api_key.max_uses_per_day is not None:
            daily_uses = api_key.get_daily_usage()
            if daily_uses >= api_key.max_uses_per_day:
                return None
        
        # Update last used timestamp
        api_key.last_used = timezone.now()
        api_key.save(update_fields=['last_used'])
        
        return api_key


class IsMasterApiKey(permissions.BasePermission):
    """
    Permission class that only allows access with the master API key.
    
    This provides system-level access for administrative operations.
    """
    
    def has_permission(self, request, view):
        """Check if request has master API key"""
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return False
        
        provided_key = auth_header[7:]  # Remove 'Bearer ' prefix
        return settings.MASTER_API_KEY and provided_key == settings.MASTER_API_KEY


class IsMasterOrCreatorApiKey(permissions.BasePermission):
    """
    Permission class that allows access with either master API key or valid creator API key.
    
    Used for endpoints that need to track creators but also allow system access.
    """
    
    def has_permission(self, request, view):
        """Check if request has master key or valid API key"""
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return False
        
        provided_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check master key first
        if settings.MASTER_API_KEY and provided_key == settings.MASTER_API_KEY:
            request.is_master_key = True
            request.api_key = None
            return True
        
        # Check regular API key
        api_key_permission = IsAuthenticatedWithApiKey()
        api_key = api_key_permission._validate_api_key(provided_key)
        if api_key:
            request.is_master_key = False
            request.api_key = api_key
            return True
        
        return False


class IsOwnerOrMasterKey(permissions.BasePermission):
    """
    Permission class that allows access to resource owners or master key holders.
    
    Used for object-level permissions where users can only access their own resources.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user owns the object or has master key"""
        # Check master key first
        if hasattr(request, 'is_master_key') and request.is_master_key:
            return True
        
        # Check ownership
        if hasattr(obj, 'creator_user') and hasattr(request, 'api_key'):
            return obj.creator_user == request.api_key.user
        
        return False


class IsPublicOrAuthenticated(permissions.BasePermission):
    """
    Permission class for endpoints that may be public or require authentication.
    
    Allows public access when API keys are not required, otherwise requires
    valid authentication.
    """
    
    def has_permission(self, request, view):
        """Check permission based on server configuration"""
        # If API keys are not required and no master key is set, allow public access
        if not settings.SERVER_REQUIRE_API_KEY and not settings.MASTER_API_KEY:
            return True
        
        # Otherwise, require authentication
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return not settings.SERVER_REQUIRE_API_KEY
        
        if not auth_header.startswith('Bearer '):
            return False
        
        provided_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check if it's the master key
        if settings.MASTER_API_KEY and provided_key == settings.MASTER_API_KEY:
            request.is_master_key = True
            request.api_key = None
            return True
        
        # Check if it's a valid API key
        api_key_permission = IsAuthenticatedWithApiKey()
        api_key = api_key_permission._validate_api_key(provided_key)
        if api_key:
            request.is_master_key = False
            request.api_key = api_key
            return True
        
        return False


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Permission class that allows read-only access to anyone, but requires authentication for write operations.
    
    Used for verification endpoints where anyone should be able to verify archives,
    but only authenticated users can create them.
    """
    
    def has_permission(self, request, view):
        """Allow read-only access to all, require auth for writes"""
        # Allow read operations (GET, HEAD, OPTIONS) for anyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # For write operations, require authentication
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return False
        
        provided_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check master key
        if settings.MASTER_API_KEY and provided_key == settings.MASTER_API_KEY:
            request.is_master_key = True
            request.api_key = None
            return True
        
        # Check API key
        api_key_permission = IsAuthenticatedWithApiKey()
        api_key = api_key_permission._validate_api_key(provided_key)
        if api_key:
            request.is_master_key = False
            request.api_key = api_key
            return True
        
        return False 