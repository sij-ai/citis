"""
Django admin configuration for the archive app.

This module configures the admin interface for managing archives, visits,
and API keys, providing comprehensive tools for system administration.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Shortcode, Visit, ApiKey, HealthCheck

# Import TaskResult for Celery monitoring
try:
    from django_celery_results.models import TaskResult
except ImportError:
    TaskResult = None


# Enhanced TaskResult admin for Celery task monitoring
class TaskResultAdmin(admin.ModelAdmin):
    """
    Admin interface for monitoring Celery task execution.
    """
    list_display = ('task_id', 'task_name', 'status', 'worker', 'date_created', 'date_done', 'result_display')
    list_filter = ('status', 'task_name', 'worker', 'date_created')
    search_fields = ('task_id', 'task_name', 'worker')
    readonly_fields = ('task_id', 'task_name', 'status', 'worker', 'result', 'traceback', 'date_created', 'date_done')
    ordering = ('-date_created',)
    date_hierarchy = 'date_created'
    
    def result_display(self, obj):
        """Display task result with formatting"""
        if obj.result:
            result_str = str(obj.result)[:100]
            if obj.status == 'SUCCESS':
                return format_html('<span style="color: green;">{}</span>', result_str)
            elif obj.status == 'FAILURE':
                return format_html('<span style="color: red;">{}</span>', result_str)
            else:
                return result_str
        return '-'
    result_display.short_description = 'Result'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


class VisitInline(admin.TabularInline):
    """
    Inline admin for showing recent visits to a shortcode.
    """
    model = Visit
    extra = 0
    readonly_fields = ('visited_at', 'ip_address', 'user_agent', 'referer', 'country', 'city')
    fields = ('visited_at', 'ip_address', 'country', 'city', 'referer')
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-visited_at')[:10]


class HealthCheckInline(admin.TabularInline):
    """
    Inline admin for showing recent health checks for a shortcode.
    """
    model = HealthCheck
    extra = 0
    readonly_fields = ('check_type', 'status', 'checked_at', 'details')
    fields = ('check_type', 'status', 'checked_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-checked_at')[:5]


@admin.register(Shortcode)
class ShortcodeAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Shortcode model.
    
    Provides comprehensive management of shortcodes with analytics,
    archive status, and health monitoring information.
    """
    
    # List display
    list_display = (
        'shortcode', 'formatted_url', 'creator_display', 'visit_count', 
        'archive_status', 'health_status', 'created_at'
    )
    
    # List filters
    list_filter = (
        'created_at', 'archive_method', 'creator_user__current_plan',
        'health_checks__status', 'health_checks__check_type'
    )
    
    # Search fields
    search_fields = ('shortcode', 'url', 'creator_user__email', 'creator_user__username')
    
    # Detail view configuration
    fieldsets = (
        ('Basic Information', {
            'fields': ('shortcode', 'url', 'text_fragment')
        }),
        ('Creator Information', {
            'fields': ('creator_user', 'creator_api_key', 'creator_ip'),
            'classes': ('collapse',)
        }),
        ('Archive Configuration', {
            'fields': ('archive_method',),
        }),
        ('Proxy Information', {
            'fields': ('proxy_ip', 'proxy_country', 'proxy_provider'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)
    inlines = [HealthCheckInline, VisitInline]
    
    # Ordering
    ordering = ('-created_at',)
    
    # Pagination
    list_per_page = 50
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch and annotations."""
        return super().get_queryset(request).select_related(
            'creator_user', 'creator_api_key'
        ).prefetch_related('visits', 'health_checks').annotate(
            visit_count_annotation=Count('visits'),
            latest_health_check=Count('health_checks', filter=Q(health_checks__status='ok'))
        )
    
    def formatted_url(self, obj):
        """Display URL with clickable link and truncation."""
        if len(obj.url) > 50:
            display_url = obj.url[:47] + '...'
        else:
            display_url = obj.url
        return format_html('<a href="{}" target="_blank" title="{}">{}</a>', 
                         obj.url, obj.url, display_url)
    formatted_url.short_description = 'URL'
    formatted_url.admin_order_field = 'url'
    
    def creator_display(self, obj):
        """Display creator information with plan badge."""
        if obj.creator_user:
            plan_color = {
                'free': '#6c757d',      # Gray
                'professional': '#0d6efd',  # Blue  
                'sovereign': '#6f42c1'       # Purple
            }.get(obj.creator_user.current_plan, '#6c757d')
            
            plan_badge = format_html(
                '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">{}</span>',
                plan_color,
                obj.creator_user.current_plan.upper()
            )
            
            student_badge = ''
            if obj.creator_user.is_student:
                student_badge = format_html(
                    ' <span style="background-color: #198754; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">STUDENT</span>'
                )
            
            return format_html('{} {}{}<br><small>{}</small>', 
                             obj.creator_user.get_full_display_name(), 
                             plan_badge, student_badge,
                             obj.creator_user.email)
        elif obj.creator_api_key:
            return f'API Key: {obj.creator_api_key.name}'
        else:
            return 'Anonymous'
    creator_display.short_description = 'Creator'
    creator_display.admin_order_field = 'creator_user__email'
    
    def visit_count(self, obj):
        """Display visit count with analytics link."""
        count = getattr(obj, 'visit_count_annotation', obj.visits.count())
        if count > 0:
            return format_html('{} <small>visits</small>', count)
        return '0'
    visit_count.short_description = 'Visits'
    visit_count.admin_order_field = 'visit_count_annotation'
    
    def archive_status(self, obj):
        """Display archive status with visual indicator."""
        if obj.is_archived():
            return format_html(
                '<span style="color: #198754;">✓ Archived</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545;">✗ Not Archived</span>'
            )
    archive_status.short_description = 'Archive Status'
    
    def health_status(self, obj):
        """Display latest health check status."""
        latest_health = obj.health_checks.order_by('-checked_at').first()
        if latest_health:
            status_colors = {
                'ok': '#198754',
                'broken': '#dc3545',
                'minor_changes': '#ffc107',
                'major_changes': '#fd7e14'
            }
            color = status_colors.get(latest_health.status, '#6c757d')
            return format_html(
                '<span style="color: {};">{}</span><br><small>{}</small>',
                color,
                latest_health.get_status_display(),
                latest_health.get_check_type_display()
            )
        return format_html('<span style="color: #6c757d;">No checks</span>')
    health_status.short_description = 'Health Status'
    
    def get_readonly_fields(self, request, obj=None):
        """Make shortcode readonly when editing existing objects."""
        if obj:  # Editing existing object
            return self.readonly_fields + ('shortcode',)
        return self.readonly_fields
    
    actions = ['run_health_check', 'run_integrity_scan']
    
    def run_health_check(self, request, queryset):
        """Admin action to run health checks on selected shortcodes."""
        from .tasks import check_link_health_task
        
        count = 0
        for shortcode in queryset:
            check_link_health_task.delay(shortcode.pk)
            count += 1
        
        self.message_user(request, f'Scheduled health checks for {count} shortcodes.')
    run_health_check.short_description = "Run health check on selected shortcodes"
    
    def run_integrity_scan(self, request, queryset):
        """Admin action to run content integrity scans on selected shortcodes."""
        from .tasks import content_integrity_scan_task
        
        count = 0
        for shortcode in queryset:
            content_integrity_scan_task.delay(shortcode.pk)
            count += 1
        
        self.message_user(request, f'Scheduled integrity scans for {count} shortcodes.')
    run_integrity_scan.short_description = "Run integrity scan on selected shortcodes"


@admin.register(HealthCheck)
class HealthCheckAdmin(admin.ModelAdmin):
    """
    Admin interface for health check results.
    """
    
    list_display = (
        'shortcode', 'check_type', 'status_display', 'checked_at', 'similarity_display'
    )
    
    list_filter = (
        'check_type', 'status', 'checked_at',
        'shortcode__creator_user__current_plan'
    )
    
    search_fields = ('shortcode__shortcode', 'shortcode__url', 'shortcode__creator_user__email')
    
    readonly_fields = ('shortcode', 'check_type', 'status', 'details', 'checked_at')
    
    ordering = ('-checked_at',)
    
    list_per_page = 100
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'shortcode', 'shortcode__creator_user'
        )
    
    def status_display(self, obj):
        """Display status with color coding."""
        status_colors = {
            'ok': '#198754',
            'broken': '#dc3545', 
            'minor_changes': '#ffc107',
            'major_changes': '#fd7e14'
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def similarity_display(self, obj):
        """Display similarity ratio for content integrity checks."""
        if obj.check_type == 'content_integrity':
            ratio = obj.get_similarity_ratio()
            if ratio is not None:
                percentage = f"{ratio * 100:.1f}%"
                if ratio >= 0.95:
                    color = '#198754'  # Green
                elif ratio >= 0.8:
                    color = '#ffc107'  # Yellow
                else:
                    color = '#dc3545'  # Red
                return format_html(
                    '<span style="color: {};">{}</span>',
                    color, percentage
                )
        return '-'
    similarity_display.short_description = 'Similarity'


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    """
    Admin interface for visit analytics.
    """
    
    # List display
    list_display = (
        'shortcode_link', 'visited_at', 'ip_address', 'location', 
        'browser_info', 'platform_info'
    )
    
    # List filters
    list_filter = (
        'visited_at', 'country', 'shortcode__creator_user__current_plan'
    )
    
    # Search fields
    search_fields = (
        'shortcode__shortcode', 'shortcode__url', 'ip_address', 
        'country', 'city', 'user_agent'
    )
    
    # Read-only fields (visits shouldn't be edited)
    readonly_fields = (
        'shortcode', 'visited_at', 'ip_address', 'user_agent', 
        'referer', 'country', 'city'
    )
    
    # Detail view
    fieldsets = (
        ('Visit Information', {
            'fields': ('shortcode', 'visited_at', 'ip_address')
        }),
        ('Location Information', {
            'fields': ('country', 'city'),
        }),
        ('Browser Information', {
            'fields': ('user_agent', 'referer'),
            'classes': ('collapse',)
        }),
    )
    
    # Ordering
    ordering = ('-visited_at',)
    
    # Pagination
    list_per_page = 100
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('shortcode')
    
    def shortcode_link(self, obj):
        """Display shortcode as link to its admin page."""
        url = reverse('admin:archive_shortcode_change', args=[obj.shortcode.pk])
        return format_html('<a href="{}">{}</a>', url, obj.shortcode.shortcode)
    shortcode_link.short_description = 'Shortcode'
    shortcode_link.admin_order_field = 'shortcode__shortcode'
    
    def location(self, obj):
        """Display location information."""
        if obj.country and obj.city:
            return f'{obj.city}, {obj.country}'
        elif obj.country:
            return obj.country
        elif obj.city:
            return obj.city
        else:
            return 'Unknown'
    location.short_description = 'Location'
    location.admin_order_field = 'country'
    
    def browser_info(self, obj):
        """Display browser information."""
        return obj.get_browser_info()
    browser_info.short_description = 'Browser'
    
    def platform_info(self, obj):
        """Display platform information."""
        return obj.get_platform_info()
    platform_info.short_description = 'Platform'
    
    def has_add_permission(self, request):
        """Disable adding visits through admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing visits through admin."""
        return False


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    """
    Admin interface for API key management.
    """
    
    # List display
    list_display = (
        'name', 'user_display', 'masked_key', 'usage_info', 
        'is_active', 'created_at', 'last_used'
    )
    
    # List filters
    list_filter = ('is_active', 'created_at', 'last_used', 'user__current_plan')
    
    # Search fields
    search_fields = ('name', 'user__email', 'user__username', 'key')
    
    # Detail view
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'user', 'key', 'is_active')
        }),
        ('Usage Limits', {
            'fields': ('max_uses_total', 'max_uses_per_day'),
            'description': 'Leave blank for unlimited usage'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_used'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'last_used')
    
    # Ordering
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user').annotate(
            total_usage=Count('shortcodes'),
            daily_usage=Count('shortcodes', filter=Q(
                shortcodes__created_at__gte=timezone.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            ))
        )
    
    def user_display(self, obj):
        """Display user with plan information."""
        if obj.user:
            plan_color = {
                'free': '#6c757d',
                'professional': '#0d6efd', 
                'sovereign': '#6f42c1'
            }.get(obj.user.current_plan, '#6c757d')
            
            plan_badge = format_html(
                '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">{}</span>',
                plan_color,
                obj.user.current_plan.upper()
            )
            
            return format_html('{} {}<br><small>{}</small>', 
                             obj.user.get_full_display_name(), plan_badge, obj.user.email)
        return 'No user assigned'
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__email'
    
    def masked_key(self, obj):
        """Display masked API key for security."""
        if obj.key:
            return f'{obj.key[:8]}...{obj.key[-4:]}'
        return 'No key'
    masked_key.short_description = 'API Key'
    
    def usage_info(self, obj):
        """Display usage statistics."""
        total = getattr(obj, 'total_usage', obj.get_total_uses())
        daily = getattr(obj, 'daily_usage', obj.get_daily_uses())
        
        usage_text = f'Total: {total}'
        if obj.max_uses_total:
            usage_text += f'/{obj.max_uses_total}'
        
        usage_text += f'<br>Today: {daily}'
        if obj.max_uses_per_day:
            usage_text += f'/{obj.max_uses_per_day}'
        
        return format_html(usage_text)
    usage_info.short_description = 'Usage'


# Register TaskResult admin safely
if TaskResult is not None:
    try:
        admin.site.unregister(TaskResult)
    except admin.sites.NotRegistered:
        pass
    admin.site.register(TaskResult, TaskResultAdmin)
