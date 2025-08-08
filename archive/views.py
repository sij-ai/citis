"""
Django REST Framework views for archive-related API endpoints.

These views replace the original FastAPI routes and provide the main archiving
functionality including shortcode creation, content serving, and analytics.
"""

import asyncio
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import (
    IsAuthenticatedWithApiKey, IsMasterApiKey, IsMasterOrCreatorApiKey,
    IsOwnerOrMasterKey, IsPublicOrAuthenticated, IsAuthenticatedOrReadOnly
)
from core.services import get_archive_managers
from core.utils import generate_shortcode, get_client_ip, clean_text_fragment, parse_ts_str, generate_api_key, validate_shortcode, generate_unique_shortcode
from .models import Shortcode, Visit, ApiKey
from .serializers import (
    AddRequestSerializer, AddResponseSerializer, ShortcodeSerializer,
    ShortcodeInfoSerializer, ListShortcodesResponseSerializer,
    UpdateShortcodeRequestSerializer, UpdateShortcodeResponseSerializer,
    AnalyticsResponseSerializer, VisitSerializer,
    CreateAPIKeyRequestSerializer, CreateAPIKeyResponseSerializer,
    UpdateAPIKeyRequestSerializer
)


class AddArchiveView(APIView):
    """Create a new archive and shortcode"""
    permission_classes = [IsMasterOrCreatorApiKey]

    def post(self, request):
        """Archive a URL and create a shortcode"""
        serializer = AddRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data['url']
        custom_shortcode = serializer.validated_data.get('shortcode')
        text_fragment = serializer.validated_data.get('text_fragment', '')

        # Get user from API key for quota checking
        api_key = getattr(request, 'api_key', None)
        is_master_key = getattr(request, 'is_master_key', False)
        
        if is_master_key:
            # For master API key, get the first superuser
            from django.contrib.auth import get_user_model
            User = get_user_model()
            creator_user = User.objects.filter(is_superuser=True).first()
            if not creator_user:
                return Response(
                    {"error": "No superuser found for master API key access. Please create a superuser."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            creator_user = api_key.user if api_key else None
            
        # Prevent anonymous shortcode creation
        if not creator_user:
            return Response(
                {"error": "Authentication required. Please provide a valid API key."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Skip quota checks for master key
        if not is_master_key and creator_user:
            # Check if user can create another shortcode
            if not creator_user.can_create_shortcode():
                return Response(
                    {"error": f"Monthly archive limit reached ({creator_user.get_effective_monthly_limit()}). Upgrade for higher limits."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # Check redirect quota 
            if not creator_user.can_create_redirect():
                return Response(
                    {"error": f"Monthly redirect limit reached ({creator_user.monthly_redirect_limit}). Upgrade for higher limits."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # Check custom shortcode permissions
            if custom_shortcode and creator_user.current_plan not in ['professional', 'sovereign']:
                return Response(
                    {"error": "Custom shortcodes are only available for Professional and Sovereign plans."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get user's allowed shortcode length
        if creator_user:
            shortcode_length = creator_user.shortcode_length
        else:
            shortcode_length = settings.SHORTCODE_LENGTH  # fallback for anonymous users

        # Generate shortcode if not provided
        if custom_shortcode:
            # Validate custom shortcode with user's length requirement
            is_admin = creator_user and (creator_user.is_staff or creator_user.is_superuser)
            is_valid, error_message = validate_shortcode(custom_shortcode, shortcode_length, is_admin)
            if not is_valid:
                return Response(
                    {"error": error_message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            shortcode = custom_shortcode
        else:
            # Generate unique shortcode using user's length
            shortcode = generate_unique_shortcode(shortcode_length)
            if not shortcode:
                return Response(
                    {"error": "Could not generate a unique shortcode. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Get client IP from request for proxy selection
        client_ip = get_client_ip(request)

        # Determine archive method based on settings and API key preferences
        archive_method = settings.ARCHIVE_MODE
        if hasattr(creator_user, 'default_archive_method'):
            archive_method = creator_user.default_archive_method

        # Create shortcode record
        shortcode_obj = Shortcode.objects.create(
            shortcode=shortcode,
            url=url,
            text_fragment=clean_text_fragment(text_fragment),
            archive_method=archive_method,
            creator_user=creator_user,
            creator_api_key=api_key,
            creator_ip=client_ip
        )

        # Execute archiving synchronously and wait for completion
        try:
            from .tasks import archive_url_task
            
            # Always run synchronously for immediate feedback
            result = archive_url_task.apply(args=[shortcode_obj.shortcode], kwargs={'requester_ip': client_ip})
            
            if result.successful() and result.result.get('success', False):
                message = "Archive created successfully."
                # Add quota info for regular users
                if creator_user and not is_master_key:
                    monthly_usage = creator_user.get_monthly_shortcode_count()
                    effective_limit = creator_user.get_effective_monthly_limit()
                    message += f" ({monthly_usage}/{effective_limit} used this month)"
            else:
                error_details = result.result.get('error', 'Unknown error') if result.result else 'Task failed'
                message = f"Archive creation failed: {error_details}"
                
        except Exception as e:
            # Archive task failed to start, but shortcode is created
            message = f"Shortcode created, but archive task failed to start: {str(e)}"

        # Format response
        base_url = settings.SERVER_BASE_URL
        if settings.SERVER_URL_PREFIX:
            shortcode_url = f"{base_url}/{settings.SERVER_URL_PREFIX}/{shortcode}"
        else:
            shortcode_url = f"{base_url}/{shortcode}"

        response_data = {
            "url": shortcode_url,
            "shortcode": shortcode,
            "archive_url": url,
            "message": message
        }

        response_serializer = AddResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class VerificationView(APIView):
    """
    Get verification information for a shortcode.
    
    This implements the "Basic Proof" feature from the Free tier,
    allowing users to verify archive integrity.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, shortcode):
        """Get verification details for a shortcode"""
        try:
            shortcode_obj = Shortcode.objects.get(shortcode=shortcode)
        except Shortcode.DoesNotExist:
            return Response(
                {"error": "Shortcode not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if user has permission to view verification info
        if not shortcode_obj.is_archived():
            return Response(
                {"error": "Archive not available for verification"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Build verification response based on user's plan
        verification_data = {
            "shortcode": shortcode_obj.shortcode,
            "url": shortcode_obj.url,
            "created_at": shortcode_obj.created_at.isoformat(),
            "archive_method": shortcode_obj.archive_method,
        }

        # Basic proof (available to all)
        if shortcode_obj.archive_checksum:
            verification_data["integrity"] = {
                "checksum": shortcode_obj.archive_checksum,
                "algorithm": "SHA256",
                "size_bytes": shortcode_obj.archive_size_bytes,
                "verification_url": f"{settings.SERVER_BASE_URL}/verify/{shortcode}"
            }

        # Trust information based on plan
        if shortcode_obj.trust_timestamp:
            trust_info = {
                "timestamp": shortcode_obj.trust_timestamp.isoformat(),
                "metadata": shortcode_obj.trust_metadata
            }
            
            # Add plan-specific trust features
            if shortcode_obj.creator_user:
                plan = shortcode_obj.creator_user.current_plan
                trust_info["plan"] = plan
                
                if plan == 'professional':
                    trust_info["features"] = [
                        "SHA256 integrity verification",
                        "Trusted timestamp (enhanced)",
                        "Archive preservation guarantee"
                    ]
                elif plan == 'sovereign':
                    trust_info["features"] = [
                        "SHA256 integrity verification", 
                        "Commercial-grade timestamp",
                        "Multi-source verification",
                        "Legal-grade chain of custody",
                        "Portable archive format"
                    ]
                else:  # free
                    trust_info["features"] = [
                        "SHA256 integrity verification",
                        "Basic timestamp proof"
                    ]
            
            verification_data["trust"] = trust_info

        # Proxy information (if available)
        if shortcode_obj.proxy_ip:
            verification_data["proxy"] = {
                "country": shortcode_obj.proxy_country,
                "provider": shortcode_obj.proxy_provider,
                "ip_masked": shortcode_obj.proxy_ip[:8] + "..."  # Mask IP for privacy
            }

        return Response(verification_data, status=status.HTTP_200_OK)


class ShortcodeDetailView(APIView):
    """Retrieve, update, or delete a specific shortcode"""
    permission_classes = [IsOwnerOrMasterKey]

    def get_object(self, shortcode):
        """Get shortcode object or raise 404"""
        return get_object_or_404(Shortcode, shortcode=shortcode)

    def get(self, request, shortcode):
        """Get shortcode details"""
        shortcode_obj = self.get_object(shortcode)
        self.check_object_permissions(request, shortcode_obj)
        
        serializer = ShortcodeSerializer(shortcode_obj)
        return Response(serializer.data)

    def put(self, request, shortcode):
        """Update shortcode details"""
        shortcode_obj = self.get_object(shortcode)
        self.check_object_permissions(request, shortcode_obj)
        
        serializer = UpdateShortcodeRequestSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Track updated fields
        updated_fields = []
        for field, value in serializer.validated_data.items():
            if field == 'creator_key':
                try:
                    api_key = ApiKey.objects.get(key=value)
                    shortcode_obj.creator_api_key = api_key
                    shortcode_obj.creator_user = api_key.user
                    updated_fields.extend(['creator_api_key', 'creator_user'])
                except ApiKey.DoesNotExist:
                    return Response({"error": "Invalid creator API key"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                setattr(shortcode_obj, field, value)
                updated_fields.append(field)

        shortcode_obj.save(update_fields=updated_fields)

        response_data = {
            "message": "Shortcode updated successfully",
            "shortcode": shortcode_obj.shortcode,
            "updated_fields": updated_fields
        }
        
        response_serializer = UpdateShortcodeResponseSerializer(response_data)
        return Response(response_serializer.data)

    def delete(self, request, shortcode):
        """Delete shortcode"""
        shortcode_obj = self.get_object(shortcode)
        self.check_object_permissions(request, shortcode_obj)
        
        shortcode_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListShortcodesView(APIView):
    """List shortcodes based on API key access level"""
    permission_classes = [IsPublicOrAuthenticated]

    def get(self, request):
        """List shortcodes with appropriate filtering"""
        limit = min(int(request.query_params.get('limit', 100)), 1000)
        offset = int(request.query_params.get('offset', 0))

        is_master = getattr(request, 'is_master_key', False)
        api_key = getattr(request, 'api_key', None)

        if is_master:
            queryset = Shortcode.objects.all()
            access_level = "master"
        elif api_key:
            queryset = Shortcode.objects.filter(creator_api_key=api_key)
            access_level = "creator"
        else:
            queryset = Shortcode.objects.all()
            access_level = "public"

        total_count = queryset.count()
        shortcodes = queryset.order_by('-created_at')[offset:offset + limit]

        response_data = {
            "shortcodes": shortcodes,
            "total_count": total_count,
            "access_level": access_level
        }

        serializer = ListShortcodesResponseSerializer(response_data)
        return Response(serializer.data)


class AnalyticsView(APIView):
    """Get analytics for a specific shortcode"""
    permission_classes = [IsOwnerOrMasterKey]

    def get_object(self, shortcode):
        """Get shortcode object or raise 404"""
        return get_object_or_404(Shortcode, shortcode=shortcode)

    def get(self, request, shortcode):
        """Get analytics data for a shortcode"""
        shortcode_obj = self.get_object(shortcode)
        self.check_object_permissions(request, shortcode_obj)

        visits = Visit.objects.filter(shortcode=shortcode_obj).order_by('-visited_at')
        
        response_data = {
            "shortcode": shortcode_obj.shortcode,
            "url": shortcode_obj.url,
            "created_at": shortcode_obj.created_at,
            "total_visits": visits.count(),
            "visits": visits,
            "creator_key": shortcode_obj.creator_api_key.key if shortcode_obj.creator_api_key else None,
            "text_fragment": shortcode_obj.text_fragment
        }

        serializer = AnalyticsResponseSerializer(response_data)
        return Response(serializer.data)


class APIKeyCreateView(APIView):
    """Create new API keys (master key required)"""
    permission_classes = [IsMasterApiKey]

    def post(self, request):
        """Create a new API key"""
        serializer = CreateAPIKeyRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        account = serializer.validated_data['account']
        description = serializer.validated_data.get('description', '')
        max_uses_total = serializer.validated_data.get('max_uses_total')
        max_uses_per_day = serializer.validated_data.get('max_uses_per_day')

        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=account,
            defaults={'email': f"{account}@example.com"}
        )

        new_api_key_value = generate_api_key()
        api_key = ApiKey.objects.create(
            key=new_api_key_value, name=account, description=description,
            user=user, max_uses_total=max_uses_total, max_uses_per_day=max_uses_per_day
        )

        response_data = {
            "api_key": new_api_key_value, "account": account, "description": description,
            "max_uses_total": max_uses_total, "max_uses_per_day": max_uses_per_day, "is_active": True
        }
        response_serializer = CreateAPIKeyResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class APIKeyUpdateView(APIView):
    """Update existing API keys (master key required)"""
    permission_classes = [IsMasterApiKey]

    def put(self, request, api_key):
        """Update an existing API key"""
        api_key_obj = get_object_or_404(ApiKey, key=api_key)
        serializer = UpdateAPIKeyRequestSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        for field, value in serializer.validated_data.items():
            setattr(api_key_obj, field, value)
        api_key_obj.save()

        return Response({"message": "API key updated successfully"})


# Admin views
@api_view(['DELETE'])
@permission_classes([IsMasterApiKey])
def clear_cache(request):
    """Clear all caches"""
    # This is a placeholder; implement actual cache clearing if using Django's cache framework.
    return Response({"message": "Cache clearing not implemented yet."})


@api_view(['GET'])
@permission_classes([]) # Public endpoint
def health_check(request):
    """Health check endpoint"""
    return Response({"status": "healthy"})


@api_view(['GET'])
@permission_classes([]) # Public endpoint
def get_info(request):
    """API info endpoint"""
    return Response({
        "service": "citis archive server",
        "archive_mode": settings.ARCHIVE_MODE,
        "prefix": settings.SERVER_URL_PREFIX or None
    })

