"""
Django REST Framework views for archive-related API endpoints.

These views replace the original FastAPI routes and provide the main archiving
functionality including shortcode creation, content serving, and analytics.
"""

import asyncio
from datetime import datetime, timezone
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
    IsOwnerOrMasterKey, IsPublicOrAuthenticated
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

        # Get user from API key for shortcode length
        api_key = getattr(request, 'api_key', None)
        creator_user = api_key.user if api_key else None
        
        # Get user's allowed shortcode length
        if creator_user:
            shortcode_length = creator_user.shortcode_length
        else:
            shortcode_length = settings.SHORTCODE_LENGTH  # fallback for anonymous users

        # Generate shortcode if not provided
        if custom_shortcode:
            # Validate custom shortcode with user's length requirement
            is_valid, error_message = validate_shortcode(custom_shortcode, shortcode_length)
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

        # Get client IP from request
        client_ip = get_client_ip(request)

        # Determine archive method based on settings and API key preferences
        archive_method = settings.ARCHIVE_MODE
        if hasattr(creator_user, 'default_archive_method'):
            archive_method = creator_user.default_archive_method

        # Perform archiving
        try:
            timestamp = datetime.now(timezone.utc)
            managers = get_archive_managers()
            
            # Select the appropriate manager, with fallback
            manager_to_use = None
            if archive_method in managers:
                manager_to_use = managers[archive_method]
            elif "singlefile" in managers:
                manager_to_use = managers["singlefile"]
                archive_method = "singlefile"
            
            if manager_to_use:
                archive_result = asyncio.run(manager_to_use.archive_url(url, timestamp))
            else:
                return Response(
                    {"error": f"No archive method available for mode: {archive_method}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            message = "Archive created."
            if archive_result.get("was_duplicate"):
                message = "Archive already exists (identical content found)."

        except Exception as e:
            return Response(
                {"error": f"Archive creation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Create shortcode record
        shortcode_obj = Shortcode.objects.create(
            shortcode=shortcode,
            url=url,
            text_fragment=clean_text_fragment(text_fragment),
            archive_method=archive_method,
            creator_user=creator_user,
            creator_api_key=api_key,
            creator_ip=client_ip,
            archive_path=archive_result.get("archive_path", ""),
            is_archived=True if archive_result.get("archive_path") else False
        )

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

