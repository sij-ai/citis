"""
Django REST Framework serializers for archive-related API endpoints.

These serializers replace the original Pydantic models from the FastAPI implementation
and handle data validation, serialization, and deserialization for the archive API.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Shortcode, Visit, ApiKey


User = get_user_model()


class AddRequestSerializer(serializers.Serializer):
    """Serializer for archive creation requests"""
    url = serializers.URLField(max_length=2048)
    shortcode = serializers.CharField(max_length=20, required=False, allow_blank=True)
    text_fragment = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate_shortcode(self, value):
        """Validate that shortcode meets all requirements"""
        if not value:
            return value  # Empty/None is fine - will be auto-generated
        
        # Basic validation that doesn't require user context
        from core.utils import is_valid_base58, is_reserved_shortcode
        
        if not is_valid_base58(value):
            raise serializers.ValidationError(
                "Shortcode contains invalid characters. Only alphanumeric characters allowed (excluding I, l, 0, O)"
            )
        
        if is_reserved_shortcode(value):
            raise serializers.ValidationError(f"'{value}' is a reserved word and cannot be used as a shortcode")
        
        # Basic collision check (detailed validation with user context happens in view)
        if Shortcode.objects.filter(shortcode=value).exists():
            raise serializers.ValidationError("Shortcode already exists")
        
        return value


class AddResponseSerializer(serializers.Serializer):
    """Serializer for archive creation responses"""
    url = serializers.URLField()
    shortcode = serializers.CharField()
    archive_url = serializers.URLField()
    message = serializers.CharField()


class ShortcodeSerializer(serializers.ModelSerializer):
    """Serializer for shortcode details"""
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    creator_user = serializers.CharField(source='creator_user.username', read_only=True)
    creator_api_key = serializers.CharField(source='creator_api_key.key', read_only=True)
    total_visits = serializers.SerializerMethodField()

    class Meta:
        model = Shortcode
        fields = [
            'shortcode', 'url', 'created_at', 'text_fragment', 
            'archive_method', 'creator_user', 'creator_api_key', 'total_visits'
        ]

    def get_total_visits(self, obj):
        """Get total visit count for this shortcode"""
        return obj.visits.count()


class ShortcodeInfoSerializer(serializers.ModelSerializer):
    """Serializer for shortcode listing (minimal info)"""
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    creator_key = serializers.CharField(source='creator_api_key.key', read_only=True)
    total_visits = serializers.SerializerMethodField()

    class Meta:
        model = Shortcode
        fields = ['shortcode', 'url', 'created_at', 'total_visits', 'creator_key', 'text_fragment']

    def get_total_visits(self, obj):
        """Get total visit count for this shortcode"""
        return obj.visits.count()


class ListShortcodesResponseSerializer(serializers.Serializer):
    """Serializer for shortcode list responses"""
    shortcodes = ShortcodeInfoSerializer(many=True)
    total_count = serializers.IntegerField()
    access_level = serializers.CharField()


class UpdateShortcodeRequestSerializer(serializers.ModelSerializer):
    """Serializer for shortcode update requests"""
    shortcode = serializers.CharField(max_length=20, required=False)
    created_at = serializers.DateTimeField(required=False)
    creator_key = serializers.CharField(max_length=64, required=False)
    total_visits = serializers.IntegerField(required=False, read_only=True)

    class Meta:
        model = Shortcode
        fields = ['shortcode', 'url', 'created_at', 'creator_key', 'text_fragment', 'total_visits']
        extra_kwargs = {
            'url': {'required': False},
            'text_fragment': {'required': False},
        }

    def validate_shortcode(self, value):
        """Validate that new shortcode is unique if changing"""
        if value and value != self.instance.shortcode:
            if Shortcode.objects.filter(shortcode=value).exists():
                raise serializers.ValidationError("Shortcode already exists")
        return value


class UpdateShortcodeResponseSerializer(serializers.Serializer):
    """Serializer for shortcode update responses"""
    message = serializers.CharField()
    shortcode = serializers.CharField()
    updated_fields = serializers.ListField(child=serializers.CharField())


class VisitSerializer(serializers.ModelSerializer):
    """Serializer for visit details"""
    visited_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)

    class Meta:
        model = Visit
        fields = [
            'visited_at', 'ip_address', 'user_agent', 'referer', 
            'country', 'city', 'browser', 'platform'
        ]


class AnalyticsResponseSerializer(serializers.Serializer):
    """Serializer for analytics responses"""
    shortcode = serializers.CharField()
    url = serializers.URLField()
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ')
    total_visits = serializers.IntegerField()
    visits = VisitSerializer(many=True)
    creator_key = serializers.CharField(required=False, allow_null=True)
    text_fragment = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ApiKeySerializer(serializers.ModelSerializer):
    """Serializer for API key details"""
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    last_used = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    user = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ApiKey
        fields = [
            'key', 'name', 'description', 'user', 'max_uses_total', 
            'max_uses_per_day', 'is_active', 'created_at', 'last_used'
        ]
        extra_kwargs = {
            'key': {'read_only': True}
        }


class CreateAPIKeyRequestSerializer(serializers.Serializer):
    """Serializer for API key creation requests"""
    account = serializers.CharField(max_length=150)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    max_uses_total = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    max_uses_per_day = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class CreateAPIKeyResponseSerializer(serializers.Serializer):
    """Serializer for API key creation responses"""
    api_key = serializers.CharField()
    account = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    max_uses_total = serializers.IntegerField(required=False, allow_null=True)
    max_uses_per_day = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField()


class UpdateAPIKeyRequestSerializer(serializers.Serializer):
    """Serializer for API key update requests"""
    max_uses_total = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    max_uses_per_day = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    is_active = serializers.BooleanField(required=False) 