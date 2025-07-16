"""
Django admin configuration for the accounts app.

This module configures the admin interface for user management,
providing comprehensive tools for managing user accounts and related data.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    """
    Enhanced admin interface for CustomUser model.
    
    Extends Django's default UserAdmin to include citis-specific fields
    and provide better management capabilities.
    """
    
    # Fields to display in the user list
    list_display = (
        'email', 'username', 'display_name', 'is_premium', 
        'monthly_shortcode_limit', 'is_staff', 'is_active', 'created_at'
    )
    
    # Fields that can be used for filtering
    list_filter = (
        'is_premium', 'is_staff', 'is_active', 'is_superuser',
        'default_archive_method', 'created_at', 'last_login'
    )
    
    # Fields that can be searched
    search_fields = ('email', 'username', 'display_name', 'first_name', 'last_name')
    
    # Default ordering
    ordering = ('-created_at',)
    
    # Fields that should be read-only
    readonly_fields = ('created_at', 'last_login', 'date_joined')
    
    # Add date hierarchy for easy filtering by creation date
    date_hierarchy = 'created_at'
    
    # Customize the fieldsets for the user detail page
    fieldsets = UserAdmin.fieldsets + (
        ('cit.is Settings', {
            'fields': (
                'display_name', 'default_archive_method', 'is_premium', 
                'monthly_shortcode_limit', 'created_at'
            ),
            'classes': ('wide',),
        }),
    )
    
    # Customize the fieldsets for adding new users
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('cit.is Settings', {
            'fields': (
                'display_name', 'default_archive_method', 'is_premium',
                'monthly_shortcode_limit'
            ),
            'classes': ('wide',),
        }),
    )
    
    def get_monthly_usage(self, obj):
        """Display current monthly shortcode usage"""
        return obj.get_monthly_shortcode_count()
    get_monthly_usage.short_description = 'Monthly Usage'
    
    def premium_status(self, obj):
        """Display premium status with visual indicator"""
        if obj.is_premium:
            return format_html(
                '<span style="color: #28a745;"><strong>Premium</strong></span>'
            )
        return format_html(
            '<span style="color: #6c757d;">Free</span>'
        )
    premium_status.short_description = 'Plan'
    
    # Add custom fields to list display
    list_display = list_display + ('get_monthly_usage', 'premium_status')


# Inline for displaying user's API keys on the user admin page
class ApiKeyInline(admin.TabularInline):
    """
    Inline admin for displaying API keys on the user admin page.
    """
    from archive.models import ApiKey
    model = ApiKey
    extra = 0
    readonly_fields = ('key', 'created_at', 'last_used')
    fields = ('name', 'key', 'is_active', 'max_uses_total', 'max_uses_per_day', 'created_at', 'last_used')
    
    def has_add_permission(self, request, obj=None):
        """Allow adding new API keys through the inline"""
        return True


# Add the inline to the CustomUserAdmin
CustomUserAdmin.inlines = [ApiKeyInline]

# Register the CustomUser model with the enhanced admin
admin.site.register(CustomUser, CustomUserAdmin)

# Customize the admin site header and title
admin.site.site_header = 'cit.is Administration'
admin.site.site_title = 'cit.is Admin'
admin.site.index_title = 'Welcome to cit.is Administration'
