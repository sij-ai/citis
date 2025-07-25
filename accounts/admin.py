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
        'email', 'username', 'display_name', 'current_plan', 'is_student',
        'monthly_shortcode_limit', 'is_staff', 'is_active', 'created_at'
    )
    
    # Fields that can be used for filtering
    list_filter = (
        'current_plan', 'is_premium', 'is_student', 'is_staff', 'is_active', 'is_superuser',
        'default_archive_method', 'created_at', 'last_login'
    )
    
    # Fields that can be searched
    search_fields = ('email', 'username', 'display_name', 'first_name', 'last_name')
    
    # Default ordering
    ordering = ('-created_at',)
    
    # Fields that should be read-only
    readonly_fields = ('created_at', 'last_login', 'date_joined', 'student_verified_at')
    
    # Add date hierarchy for easy filtering by creation date
    date_hierarchy = 'created_at'
    
    # Customize the fieldsets for the user detail page
    fieldsets = UserAdmin.fieldsets + (
        ('cit.is Plan & Settings', {
            'fields': (
                'display_name', 'default_archive_method', 'current_plan', 'is_premium'
            ),
            'classes': ('wide',),
        }),
        ('Quota Management', {
            'fields': (
                'monthly_shortcode_limit', 'monthly_redirect_limit', 
                'max_archive_size_mb', 'shortcode_length'
            ),
            'classes': ('wide',),
        }),
        ('Student Status', {
            'fields': (
                'is_student', 'student_verified_at'
            ),
            'classes': ('wide',),
        }),
        ('Additional Timestamps', {
            'fields': (
                'created_at',
            ),
            'classes': ('wide',),
        }),
    )
    
    # Customize the fieldsets for adding new users
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('cit.is Settings', {
            'fields': (
                'display_name', 'default_archive_method', 'current_plan',
                'monthly_shortcode_limit', 'monthly_redirect_limit',
                'max_archive_size_mb', 'shortcode_length'
            ),
            'classes': ('wide',),
        }),
    )
    
    def get_monthly_usage(self, obj):
        """Display current monthly shortcode usage"""
        usage = obj.get_monthly_shortcode_count()
        limit = obj.get_effective_monthly_limit()
        return f"{usage}/{limit}"
    get_monthly_usage.short_description = 'Monthly Usage'
    
    def plan_status(self, obj):
        """Display plan status with visual indicator"""
        plan_colors = {
            'free': '#6c757d',
            'professional': '#0d6efd', 
            'sovereign': '#6f42c1'
        }
        color = plan_colors.get(obj.current_plan, '#6c757d')
        plan_name = obj.get_current_plan_display()
        
        if obj.is_student and obj.current_plan == 'free':
            return format_html(
                '<span style="color: {};"><strong>{}</strong></span> '
                '<span style="color: #28a745; font-size: 0.8em;">📚 Student</span>',
                color, plan_name
            )
        
        return format_html(
            '<span style="color: {};"><strong>{}</strong></span>',
            color, plan_name
        )
    plan_status.short_description = 'Plan'
    
    def student_badge(self, obj):
        """Display student status with badge"""
        if obj.is_student:
            return format_html(
                '<span style="color: #28a745;">📚 Student</span>'
            )
        return '-'
    student_badge.short_description = 'Student'
    
    def quota_summary(self, obj):
        """Display quota summary"""
        return format_html(
            'Archives: {}/{}<br>'
            'Size: {}MB<br>' 
            'Length: {}',
            obj.get_monthly_shortcode_count(),
            obj.get_effective_monthly_limit(),
            obj.max_archive_size_mb,
            obj.shortcode_length
        )
    quota_summary.short_description = 'Quota Summary'
    
    # Update list display to include new methods
    list_display = (
        'email', 'username', 'display_name', 'plan_status', 'student_badge',
        'get_monthly_usage', 'is_staff', 'is_active', 'created_at'
    )


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
