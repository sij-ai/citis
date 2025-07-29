"""
Web interface views for the citis application.

These views handle the user-facing web interface including marketing pages
and the authenticated user dashboard.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from pathlib import Path

from archive.models import Shortcode, Visit, ApiKey
from core.utils import generate_api_key, get_client_ip


User = get_user_model()


def landing_page(request):
    """
    Landing page for the application.
    
    Shows marketing content and site statistics.
    """
    # Get some basic statistics for the landing page
    total_archives = Shortcode.objects.count()
    total_users = User.objects.count()
    total_visits = Visit.objects.count()
    
    context = {
        'site_stats': {
            'total_archives': total_archives,
            'total_users': total_users,
            'total_visits': total_visits,
        }
    }
    
    return render(request, 'web/landing.html', context)


def pricing_page(request):
    """
    Pricing page showing available plans.
    """
    from django.conf import settings
    
    context = {
        'sales_email': settings.SALES_EMAIL
    }
    
    # Add user subscription status if authenticated
    if request.user.is_authenticated:
        context['user_is_authenticated'] = True
        context['user_is_premium'] = request.user.is_premium
        context['user_current_plan'] = request.user.current_plan
        context['user_is_student'] = request.user.is_student
        
        # Get current subscription info if premium
        if request.user.is_premium:
            try:
                from djstripe.models import Customer
                customer = Customer.objects.get(subscriber=request.user)
                active_subscriptions = customer.subscriptions.filter(
                    status__in=['active', 'trialing']
                )
                if active_subscriptions.exists():
                    context['current_subscription'] = active_subscriptions.first()
            except Customer.DoesNotExist:
                pass
    else:
        context['user_is_authenticated'] = False
        
    return render(request, 'web/pricing.html', context)


def about_page(request):
    """
    About page with information about the service.
    """
    return render(request, 'web/about.html')


@login_required
def dashboard(request):
    """
    Main dashboard for authenticated users.
    
    Shows user statistics, recent archives, and API key management.
    """
    user = request.user
    
    # Get user's shortcodes and statistics
    user_shortcodes = Shortcode.objects.filter(creator_user=user)
    recent_shortcodes = user_shortcodes.order_by('-created_at')[:10]
    
    # Calculate user statistics
    total_shortcodes = user_shortcodes.count()
    total_visits = Visit.objects.filter(shortcode__creator_user=user).count()
    
    # Get user's API keys
    user_api_keys = ApiKey.objects.filter(user=user)
    api_keys_count = user_api_keys.count()
    
    # Calculate monthly usage (current month)
    current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_usage = user_shortcodes.filter(created_at__gte=current_month).count()
    
    # Add visit counts to shortcodes
    for shortcode in recent_shortcodes:
        shortcode.visit_count = Visit.objects.filter(shortcode=shortcode).count()
    
    # Prepare chart data (last 30 days) - always generate data
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)
    
    # Get daily counts for the last 30 days
    daily_artifact_counts = []
    daily_view_counts = []
    labels = []
    
    for i in range(30):
        date = start_date + timedelta(days=i)
        # Count artifacts created on this date
        artifact_count = user_shortcodes.filter(created_at__date=date).count()
        daily_artifact_counts.append(artifact_count)
        
        # Count views on this date
        view_count = Visit.objects.filter(
            shortcode__creator_user=user,
            visited_at__date=date
        ).count()
        daily_view_counts.append(view_count)
        
        labels.append(date.strftime('%m/%d'))
    
    import json
    chart_data = {
        'labels': json.dumps(labels),
        'artifact_data': json.dumps(daily_artifact_counts),
        'view_data': json.dumps(daily_view_counts)
    }
    
    user_stats = {
        'total_shortcodes': total_shortcodes,
        'total_visits': total_visits,
        'api_keys_count': api_keys_count,
        'monthly_usage': monthly_usage,
        'chart_data': chart_data,
    }
    
    context = {
        'user_stats': user_stats,
        'recent_shortcodes': recent_shortcodes,
        'user_api_keys': user_api_keys,
    }
    
    return render(request, 'web/dashboard.html', context)


@login_required
def shortcode_list(request):
    """
    List view for user's shortcodes with pagination, filtering, and sorting.
    """
    user = request.user
    shortcodes = Shortcode.objects.filter(creator_user=user)
    
    # Handle sorting with toggle functionality
    sort_by = request.GET.get('sort', '-created_at')  # Default to newest first
    
    valid_sorts = {
        'shortcode': 'shortcode',
        '-shortcode': '-shortcode',
        'url': 'url',
        '-url': '-url',
        'text_fragment': 'text_fragment',
        '-text_fragment': '-text_fragment',
        'visit_count': 'visit_count',  # This will be handled after adding visit counts
        '-visit_count': '-visit_count',
        'created_at': 'created_at',
        '-created_at': '-created_at',
    }
    
    if sort_by in valid_sorts and not sort_by.replace('-', '') == 'visit_count':
        shortcodes = shortcodes.order_by(sort_by)
    else:
        shortcodes = shortcodes.order_by('-created_at')  # Default sort
    
    # Add search functionality
    search_query = request.GET.get('q', '').strip()
    if search_query:
        shortcodes = shortcodes.filter(
            Q(url__icontains=search_query) | 
            Q(shortcode__icontains=search_query) |
            Q(text_fragment__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(shortcodes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Add visit counts and handle visit_count sorting
    for shortcode in page_obj:
        shortcode.visit_count = Visit.objects.filter(shortcode=shortcode).count()
    
    # Sort by visit count if requested (after counts are added)
    if sort_by == 'visit_count':
        page_obj.object_list = sorted(page_obj.object_list, key=lambda x: x.visit_count, reverse=False)
    elif sort_by == '-visit_count':
        page_obj.object_list = sorted(page_obj.object_list, key=lambda x: x.visit_count, reverse=True)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'current_sort': sort_by,
    }
    
    return render(request, 'web/shortcode_list.html', context)


@login_required
def shortcode_detail(request, shortcode):
    """
    Detail view for a specific shortcode.
    """
    shortcode_obj = get_object_or_404(Shortcode, shortcode=shortcode, creator_user=request.user)
    
    # Get visit statistics
    visits = Visit.objects.filter(shortcode=shortcode_obj).order_by('-visited_at')
    visit_count = visits.count()
    
    # Get recent visits (last 10)
    recent_visits = visits[:10]
    
    # Get daily visit counts for the last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)
    
    daily_visits = []
    labels = []
    
    for i in range(30):
        date = start_date + timedelta(days=i)
        count = visits.filter(visited_at__date=date).count()
        daily_visits.append(count)
        labels.append(date.strftime('%m/%d'))
    
    import json
    chart_data = {
        'labels': json.dumps(labels),
        'data': json.dumps(daily_visits)
    }
    
    context = {
        'shortcode': shortcode_obj,
        'visit_count': visit_count,
        'recent_visits': recent_visits,
        'chart_data': chart_data,
    }
    
    return render(request, 'web/shortcode_detail.html', context)


@login_required
def create_archive(request):
    """
    Create a new archive page with form.
    """
    from .forms import CreateArchiveForm
    
    user = request.user
    
    # Calculate usage information for display using new quota system
    monthly_usage = user.get_monthly_shortcode_count()
    effective_limit = user.get_effective_monthly_limit()
    
    usage_percentage = min((monthly_usage / effective_limit) * 100, 100) if effective_limit > 0 else 0
    
    # Calculate threshold for warning (80% of limit)
    usage_warning_threshold = int(effective_limit * 0.8) if effective_limit > 0 else 0
    
    # Initialize form
    form = CreateArchiveForm()
    
    context = {
        'form': form,
        'monthly_usage': monthly_usage,
        'monthly_limit': effective_limit,
        'usage_percentage': usage_percentage,
        'usage_warning_threshold': usage_warning_threshold,
        'user_can_use_custom_shortcodes': user.current_plan in ['professional', 'sovereign'],  # Professional+ plans get custom slugs
        'user_shortcode_length': user.shortcode_length,
        'user_plan': user.current_plan,
        'is_student': user.is_student,
        'max_file_size_mb': user.max_archive_size_mb,
    }
    
    if request.method == 'POST':
        form = CreateArchiveForm(request.POST)
        context['form'] = form  # Update context with the bound form
        
        if not form.is_valid():
            return render(request, 'web/create_archive.html', context)
        
        # Extract cleaned data from form
        url = form.cleaned_data['url']
        text_fragment = form.cleaned_data.get('text_fragment', '').strip()
        archive_method = form.cleaned_data['archive_method']
        custom_shortcode = form.cleaned_data.get('custom_shortcode', '').strip()
        
        # Check if user can create another shortcode using new quota system
        if not user.can_create_shortcode():
            if user.current_plan == 'free':
                if user.is_student:
                    limit_msg = f"Monthly archive limit reached ({effective_limit} including student bonus)."
                else:
                    limit_msg = f"Monthly archive limit reached ({effective_limit})."
                limit_msg += " Upgrade to Professional for 100 archives per month, or Sovereign for unlimited."
            else:
                limit_msg = "Monthly archive limit reached. Contact support if you need a higher limit."
            
            messages.error(request, limit_msg)
            return render(request, 'web/create_archive.html', context)
        
        # Check redirect quota (for now same as archive quota, but separate for future)
        if not user.can_create_redirect():
            messages.error(request, f'Monthly redirect limit reached ({user.monthly_redirect_limit}). Upgrade for higher limits.')
            return render(request, 'web/create_archive.html', context)
        
        try:
            
            # Check if user can use custom shortcodes
            if custom_shortcode and user.current_plan not in ['professional', 'sovereign']:
                messages.error(request, 'Custom shortcodes are only available for Professional and Sovereign plans.')
                return render(request, 'web/create_archive.html', context)
            
            # Generate or validate shortcode
            if custom_shortcode:
                # Validate custom shortcode
                from core.utils import validate_shortcode
                is_valid, error_message = validate_shortcode(
                    custom_shortcode, 
                    user.shortcode_length, 
                    is_admin=user.is_staff or user.is_superuser
                )
                if not is_valid:
                    messages.error(request, error_message)
                    return render(request, 'web/create_archive.html', context)
                shortcode_value = custom_shortcode
            else:
                # Generate unique shortcode
                from core.utils import generate_unique_shortcode
                shortcode_value = generate_unique_shortcode(user.shortcode_length)
                if not shortcode_value:
                    messages.error(request, 'Could not generate a unique shortcode. Please try again.')
                    return render(request, 'web/create_archive.html', context)
            
            # Create the shortcode object
            shortcode = Shortcode.objects.create(
                shortcode=shortcode_value,
                url=url,
                text_fragment=text_fragment,
                creator_user=user,
                archive_method=archive_method,
                # Archive will be triggered by Celery task
            )
            
            # Trigger archiving task asynchronously
            from archive.tasks import archive_url_task, extract_assets_task
            
            # Start archiving task
            archive_task = archive_url_task.delay(shortcode.pk)
            
            # Start asset extraction after a short delay (gives archiving time to start)
            extract_assets_task.apply_async(args=[shortcode.pk], countdown=30)
            
            success_msg = f'Archive created successfully! Shortcode: {shortcode.shortcode}. Archiving is in progress and will complete shortly.'
            if user.is_student and user.current_plan == 'free':
                success_msg += f' (Student bonus: {monthly_usage + 1}/{effective_limit} used this month)'
            
            messages.success(request, success_msg)
            return redirect('web:shortcode_detail', shortcode=shortcode.shortcode)
            
        except Exception as e:
            messages.error(request, f'Error creating archive: {str(e)}')
            return render(request, 'web/create_archive.html', context)
    
    return render(request, 'web/create_archive.html', context)


@login_required
@require_http_methods(["POST"])
def create_api_key(request):
    """
    HTMX endpoint to create a new API key.
    """
    # Check if user has premium access
    if not request.user.is_premium:
        return HttpResponse('API key creation requires a premium subscription.', status=403)
    
    try:
        api_key = ApiKey.objects.create(
            user=request.user,
            key=generate_api_key(),
            name=f"API Key {ApiKey.objects.filter(user=request.user).count() + 1}",
            max_uses_total=1000 if not request.user.is_premium else None,
        )
        
        # Return the new API key as HTML for HTMX
        context = {'api_key': api_key}
        return render(request, 'web/partials/api_key_card.html', context)
        
    except Exception as e:
        return HttpResponse(f'Error creating API key: {str(e)}', status=400)


@login_required
@require_http_methods(["DELETE"])
def delete_api_key(request, api_key):
    """
    HTMX endpoint to delete an API key.
    """
    try:
        api_key_obj = get_object_or_404(ApiKey, key=api_key, user=request.user)
        api_key_obj.delete()
        return HttpResponse('', status=200)
        
    except Exception as e:
        return HttpResponse(f'Error deleting API key: {str(e)}', status=400)


@login_required
@require_http_methods(["POST"])
def update_api_key(request, api_key):
    """
    HTMX endpoint to update an API key.
    """
    try:
        api_key_obj = get_object_or_404(ApiKey, key=api_key, user=request.user)
        
        name = request.POST.get('name', '').strip()
        if name:
            api_key_obj.name = name
            api_key_obj.save()
        
        # Return the updated API key as HTML for HTMX
        context = {'api_key': api_key_obj}
        return render(request, 'web/partials/api_key_card.html', context)
        
    except Exception as e:
        return HttpResponse(f'Error updating API key: {str(e)}', status=400)


# Utility view for text fragment highlighting
def highlight_text(request):
    """
    Utility endpoint for text fragment highlighting.
    Used by the overlay JavaScript.
    """
    text_fragment = request.GET.get('text_fragment', '')
    
    if not text_fragment:
        return JsonResponse({'error': 'No text fragment provided'}, status=400)
    
    # Clean the text fragment
    from core.utils import clean_text_fragment
    cleaned_fragment = clean_text_fragment(text_fragment)
    
    return JsonResponse({
        'original': text_fragment,
        'cleaned': cleaned_fragment,
        'valid': bool(cleaned_fragment)
    })


def shortcode_redirect(request, shortcode):
    """
    Serve archived content for a given shortcode.
    This is the main view that handles /{shortcode} URLs.
    """
    # Look up the shortcode
    try:
        shortcode_obj = Shortcode.objects.get(shortcode=shortcode)
    except Shortcode.DoesNotExist:
        raise Http404(f"Shortcode '{shortcode}' not found")
    
    # Record the visit for analytics
    visit = Visit.objects.create(
        shortcode=shortcode_obj,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        referer=request.META.get('HTTP_REFERER', ''),
    )
    
    # Update analytics asynchronously
    from archive.tasks import update_visit_analytics_task
    update_visit_analytics_task.delay(visit.pk)
    
    # Check if archived content exists using filesystem
    if shortcode_obj.is_archived():
        try:
            # Get the archive path dynamically from filesystem
            archive_path = shortcode_obj.get_latest_archive_path()
            singlefile_path = archive_path / "singlefile.html"
            
            if singlefile_path.exists():
                with open(singlefile_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Inject overlay banner
                try:
                    from core.overlay import inject_overlay
                    from datetime import datetime, timezone
                    
                    # Get visits for analytics
                    visits = shortcode_obj.visits.all().order_by('-visited_at')
                    
                    # Determine archive date from file modification time or creation time
                    from django.utils import timezone as dj_timezone
                    archive_dt = datetime.fromtimestamp(singlefile_path.stat().st_mtime)
                    archive_dt = dj_timezone.make_aware(archive_dt)
                    
                    # Inject the overlay
                    content = inject_overlay(
                        html_content=content,
                        shortcode_obj=shortcode_obj,
                        archive_dt=archive_dt,
                        requested_dt=None,  # We don't have a specific request time for this case
                        visits=visits
                    )
                    
                except Exception as e:
                    # Log overlay injection error but don't break page serving
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error injecting overlay for {shortcode}: {e}", exc_info=True)
                
                response = HttpResponse(content, content_type='text/html')
                response['Cache-Control'] = 'public, max-age=31536000'  # Cache for 1 year
                return response
            else:
                # Archive file not found, redirect to original
                return redirect(shortcode_obj.url)
        except Exception as e:
            # Error reading archive, redirect to original
            return redirect(shortcode_obj.url)
    else:
        # No archive path, redirect to original URL
        return redirect(shortcode_obj.url)


def shortcode_favicon(request, shortcode):
    """
    Serve favicon for a given shortcode.
    This handles URLs like /{shortcode}.favicon.ico
    """
    # Remove .favicon.ico suffix to get the actual shortcode
    if shortcode.endswith('.favicon.ico'):
        shortcode = shortcode[:-12]  # Remove .favicon.ico
    
    try:
        shortcode_obj = Shortcode.objects.get(shortcode=shortcode)
    except Shortcode.DoesNotExist:
        raise Http404(f"Shortcode '{shortcode}' not found")
    
    if shortcode_obj.is_archived():
        archive_path = shortcode_obj.get_latest_archive_path()
        favicon_path = archive_path / "favicon.ico"
        
        if favicon_path.exists():
            try:
                with open(favicon_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='image/x-icon')
                    response['Cache-Control'] = 'public, max-age=31536000'  # Cache for 1 year
                    return response
            except Exception as e:
                raise Http404("Favicon not accessible")
    
    # No favicon found
    raise Http404("Favicon not found")
