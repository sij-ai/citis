"""
Django admin configuration for the archive app.

This module configures the admin interface for managing archives, visits,
and API keys, providing comprehensive tools for system administration.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count
from .models import Shortcode, Visit, ApiKey


@admin.register(Shortcode)
class ShortcodeAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Shortcode model.
    
    Provides comprehensive management tools for archived URLs.
    """
    
    # Fields to display in the shortcode list
    list_display = (
        'shortcode', 'url_display', 'creator_user', 'created_at', 
        'archive_method', 'archived_status', 'proxy_display', 'visit_count', 'view_archive_link'
    )
    
    # Fields that can be used for filtering
    list_filter = (
        'archive_method', 'proxy_provider', 'proxy_country', 'created_at', 
        'creator_user', 'creator_api_key'
    )
    
    # Fields that can be searched
    search_fields = (
        'shortcode', 'url', 'text_fragment', 
        'creator_user__email', 'creator_user__username'
    )
    
    # Default ordering (newest first)
    ordering = ('-created_at',)
    
    # Fields that should be read-only
    readonly_fields = (
        'shortcode', 'created_at', 'creator_ip', 'visit_count_display',
        'archive_path_display', 'proxy_ip', 'proxy_country', 'proxy_provider'
    )
    
    # Add date hierarchy for easy filtering by creation date
    date_hierarchy = 'created_at'
    
    # Organize fields in fieldsets
    fieldsets = (
        ('Archive Information', {
            'fields': ('shortcode', 'url', 'archived_status', 'archive_method')
        }),
        ('Content', {
            'fields': ('text_fragment', 'archive_path_display'),
            'classes': ('wide',),
        }),
        ('Creator Information', {
            'fields': ('creator_user', 'creator_api_key', 'creator_ip'),
            'classes': ('collapse',),
        }),
        ('Proxy Information', {
            'fields': ('proxy_ip', 'proxy_country', 'proxy_provider'),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'visit_count_display'),
            'classes': ('collapse',),
        }),
    )
    
    def url_display(self, obj):
        """Display URL with truncation and link"""
        if len(obj.url) > 50:
            display_url = obj.url[:47] + "..."
        else:
            display_url = obj.url
        return format_html(
            '<a href="{}" target="_blank" title="{}">{}</a>',
            obj.url, obj.url, display_url
        )
    url_display.short_description = 'URL'
    
    def visit_count(self, obj):
        """Display visit count for the shortcode"""
        return obj.visits.count()
    visit_count.short_description = 'Visits'
    visit_count.admin_order_field = 'visit_count'
    
    def visit_count_display(self, obj):
        """Display visit count with link to visits"""
        count = obj.visits.count()
        if count > 0:
            url = reverse('admin:archive_visit_changelist') + f'?shortcode__shortcode={obj.shortcode}'
            return format_html('<a href="{}">{} visits</a>', url, count)
        return '0 visits'
    visit_count_display.short_description = 'Visit Count'
    
    def archived_status(self, obj):
        """Display archive status using filesystem check"""
        is_archived = obj.is_archived()
        if is_archived:
            return format_html('<span style="color: green;">✓ Archived</span>')
        else:
            return format_html('<span style="color: red;">✗ Not Archived</span>')
    archived_status.short_description = 'Archive Status'
    archived_status.admin_order_field = 'shortcode'  # Allow sorting by shortcode
    
    def view_archive_link(self, obj):
        """Display link to view the archived page"""
        return format_html(
            '<a href="/{}" target="_blank" class="button">View Archive</a>',
            obj.shortcode
        )
    view_archive_link.short_description = 'Actions'
    
    def archive_path_display(self, obj):
        """Display archive path information"""
        if obj.archive_path:
            return format_html('<code>{}</code>', obj.archive_path)
        return 'Not set'
    archive_path_display.short_description = 'Archive Path'
    
    def proxy_display(self, obj):
        """Display proxy information"""
        proxy_meta = obj.get_proxy_metadata()
        
        if proxy_meta.get('proxy_configured', False):
            proxy_ip = proxy_meta.get('proxy_ip', 'Unknown')
            proxy_country = proxy_meta.get('proxy_country', '??')
            proxy_provider = proxy_meta.get('proxy_provider', 'Unknown')
            
            return format_html(
                '<span title="Provider: {}, IP: {}">{} ({})</span>',
                proxy_provider,
                proxy_ip,
                proxy_ip[:12] + '...' if len(proxy_ip) > 15 else proxy_ip,
                proxy_country
            )
        return format_html('<span style="color: #999;">Direct</span>')
    proxy_display.short_description = 'Proxy Used'
    
    # Add annotations for efficient querying
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('creator_user', 'creator_api_key').annotate(
            visit_count=Count('visits')
        )


class VisitInline(admin.TabularInline):
    """
    Inline admin for displaying visits on the shortcode admin page.
    """
    model = Visit
    extra = 0
    readonly_fields = ('visited_at', 'ip_address', 'user_agent', 'referer', 'country', 'city')
    fields = ('visited_at', 'ip_address', 'country', 'user_agent')
    
    def has_add_permission(self, request, obj=None):
        """Prevent adding visits through admin"""
        return False


# Add visits inline to ShortcodeAdmin
ShortcodeAdmin.inlines = [VisitInline]


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Visit model.
    
    Provides comprehensive analytics and monitoring tools.
    """
    
    # Fields to display in the visit list
    list_display = (
        'shortcode_link', 'visited_at', 'ip_address', 
        'country', 'browser_info', 'platform_info'
    )
    
    # Fields that can be used for filtering
    list_filter = (
        'visited_at', 'country', 'shortcode__archive_method',
        'shortcode__creator_user'
    )
    
    # Fields that can be searched
    search_fields = (
        'shortcode__shortcode', 'shortcode__url', 'ip_address', 
        'user_agent', 'referer', 'country', 'city'
    )
    
    # Default ordering (newest first)
    ordering = ('-visited_at',)
    
    # All fields should be read-only for visits
    readonly_fields = (
        'shortcode', 'visited_at', 'ip_address', 'user_agent', 
        'referer', 'country', 'city', 'browser_info', 'platform_info'
    )
    
    # Add date hierarchy for easy filtering by visit date
    date_hierarchy = 'visited_at'
    
    # Organize fields in fieldsets
    fieldsets = (
        ('Visit Information', {
            'fields': ('shortcode', 'visited_at')
        }),
        ('Client Information', {
            'fields': ('ip_address', 'user_agent', 'browser_info', 'platform_info'),
            'classes': ('wide',),
        }),
        ('Location & Referrer', {
            'fields': ('country', 'city', 'referer'),
            'classes': ('wide',),
        }),
    )
    
    def shortcode_link(self, obj):
        """Display shortcode as a link to the shortcode admin page"""
        url = reverse('admin:archive_shortcode_change', args=[obj.shortcode.shortcode])
        return format_html('<a href="{}">{}</a>', url, obj.shortcode.shortcode)
    shortcode_link.short_description = 'Shortcode'
    shortcode_link.admin_order_field = 'shortcode__shortcode'
    
    def browser_info(self, obj):
        """Display browser information from user agent"""
        return obj.get_browser_info()
    browser_info.short_description = 'Browser'
    
    def platform_info(self, obj):
        """Display platform information from user agent"""
        return obj.get_platform_info()
    platform_info.short_description = 'Platform'
    
    def has_add_permission(self, request):
        """Prevent adding visits through admin"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing visits through admin"""
        return False
    
    # Add efficient querying
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('shortcode', 'shortcode__creator_user')


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for ApiKey model.
    
    Provides comprehensive management tools for API access.
    """
    
    # Fields to display in the API key list
    list_display = (
        'key_display', 'user_link', 'name', 'is_active', 
        'usage_stats', 'created_at', 'last_used'
    )
    
    # Fields that can be used for filtering
    list_filter = (
        'is_active', 'created_at', 'last_used', 'user'
    )
    
    # Fields that can be searched
    search_fields = (
        'key', 'name', 'description', 'user__email', 'user__username'
    )
    
    # Default ordering (newest first)
    ordering = ('-created_at',)
    
    # Fields that should be read-only
    readonly_fields = (
        'key', 'created_at', 'last_used', 'usage_stats_display'
    )
    
    # Add date hierarchy for easy filtering by creation date
    date_hierarchy = 'created_at'
    
    # Organize fields in fieldsets
    fieldsets = (
        ('API Key Information', {
            'fields': ('key', 'user', 'name', 'description', 'is_active')
        }),
        ('Usage Limits', {
            'fields': ('max_uses_total', 'max_uses_per_day', 'usage_stats_display'),
            'classes': ('wide',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'last_used'),
            'classes': ('collapse',),
        }),
    )
    
    def key_display(self, obj):
        """Display truncated API key"""
        return f"{obj.key[:8]}{'*' * 24}"
    key_display.short_description = 'API Key'
    key_display.admin_order_field = 'key'
    
    def user_link(self, obj):
        """Display user as a link to the user admin page"""
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'
    
    def usage_stats(self, obj):
        """Display usage statistics"""
        total_uses = obj.get_total_uses()
        daily_uses = obj.get_daily_uses()
        
        if obj.max_uses_total:
            total_display = f"{total_uses}/{obj.max_uses_total}"
        else:
            total_display = str(total_uses)
            
        if obj.max_uses_per_day:
            daily_display = f"{daily_uses}/{obj.max_uses_per_day}"
        else:
            daily_display = str(daily_uses)
            
        return f"Total: {total_display}, Daily: {daily_display}"
    usage_stats.short_description = 'Usage'
    
    def usage_stats_display(self, obj):
        """Display detailed usage statistics"""
        total_uses = obj.get_total_uses()
        daily_uses = obj.get_daily_uses()
        
        total_limit = obj.max_uses_total or "Unlimited"
        daily_limit = obj.max_uses_per_day or "Unlimited"
        
        return format_html(
            '<strong>Total:</strong> {} / {}<br><strong>Today:</strong> {} / {}',
            total_uses, total_limit, daily_uses, daily_limit
        )
    usage_stats_display.short_description = 'Usage Statistics'
    
    # Add efficient querying
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user')


# Inline for displaying user's shortcodes on the API key admin page
class ShortcodeInline(admin.TabularInline):
    """
    Inline admin for displaying shortcodes created by an API key.
    """
    model = Shortcode
    extra = 0
    readonly_fields = ('shortcode', 'url', 'created_at', 'archived_status')
    fields = ('shortcode', 'url', 'created_at', 'archived_status')
    
    def archived_status(self, obj):
        """Display archive status using filesystem check"""
        is_archived = obj.is_archived()
        if is_archived:
            return format_html('<span style="color: green;">✓ Archived</span>')
        else:
            return format_html('<span style="color: red;">✗ Not Archived</span>')
    archived_status.short_description = 'Archive Status'
    
    def has_add_permission(self, request, obj=None):
        """Prevent adding shortcodes through admin"""
        return False


# Add shortcodes inline to ApiKeyAdmin
ApiKeyAdmin.inlines = [ShortcodeInline]
