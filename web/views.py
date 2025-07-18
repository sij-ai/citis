"""
Web interface views for the citis application.

These views handle the user-facing web interface including marketing pages
and the authenticated user dashboard.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse, Http404, FileResponse
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
from core.services import get_archive_managers
from .overlay import inject_overlay
import asyncio


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
    return render(request, 'web/pricing.html')


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
    recent_shortcodes = user_shortcodes.order_by('-created_at')[:5]
    
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
    
    # Prepare chart data (last 30 days)
    chart_data = None
    if total_shortcodes > 0:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=29)
        
        # Get daily counts for the last 30 days
        daily_counts = []
        labels = []
        
        for i in range(30):
            date = start_date + timedelta(days=i)
            count = user_shortcodes.filter(created_at__date=date).count()
            daily_counts.append(count)
            labels.append(date.strftime('%m/%d'))
        
        import json
        chart_data = {
            'labels': json.dumps(labels),
            'data': json.dumps(daily_counts)
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
    List view for user's shortcodes with pagination and filtering.
    """
    user = request.user
    shortcodes = Shortcode.objects.filter(creator_user=user).order_by('-created_at')
    
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
    
    # Add visit counts
    for shortcode in page_obj:
        shortcode.visit_count = Visit.objects.filter(shortcode=shortcode).count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
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
    user = request.user
    
    # Calculate usage information for display
    current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_usage = Shortcode.objects.filter(
        creator_user=user,
        created_at__gte=current_month
    ).count()
    
    monthly_limit = user.monthly_shortcode_limit
    usage_percentage = min((monthly_usage / monthly_limit) * 100, 100) if monthly_limit > 0 else 0
    
    context = {
        'monthly_usage': monthly_usage,
        'monthly_limit': monthly_limit,
        'usage_percentage': usage_percentage,
    }
    
    if request.method == 'POST':
        url = request.POST.get('url', '').strip()
        text_fragment = request.POST.get('text_fragment', '').strip()
        
        if not url:
            messages.error(request, 'URL is required.')
            return render(request, 'web/create_archive.html', context)
        
        # Check monthly limits for free users
        if not user.is_premium:
            if monthly_usage >= monthly_limit:
                messages.error(request, 'Monthly archive limit reached. Upgrade to Premium for unlimited archives.')
                return render(request, 'web/create_archive.html', context)
        
        try:
            # Create the shortcode 
            shortcode = Shortcode.objects.create(
                url=url,
                text_fragment=text_fragment,
                creator_user=user,
                archive_method=user.default_archive_method,
                # Archive will be triggered by Celery task
            )
            
            # Trigger archiving task asynchronously
            from archive.tasks import archive_url_task, extract_assets_task
            
            # Start archiving task
            archive_task = archive_url_task.delay(shortcode.pk)
            
            # Start asset extraction after a short delay (gives archiving time to start)
            extract_assets_task.apply_async(args=[shortcode.pk], countdown=30)
            
            messages.success(
                request, 
                f'Archive created successfully! Shortcode: {shortcode.shortcode}. '
                f'Archiving is in progress and will complete shortly.'
            )
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
def delete_api_key(request, api_key_id):
    """
    HTMX endpoint to delete an API key.
    """
    try:
        api_key = get_object_or_404(ApiKey, id=api_key_id, user=request.user)
        api_key.delete()
        return HttpResponse('', status=200)
        
    except Exception as e:
        return HttpResponse(f'Error deleting API key: {str(e)}', status=400)


@login_required
@require_http_methods(["POST"])
def update_api_key(request, api_key_id):
    """
    HTMX endpoint to update an API key.
    """
    try:
        api_key = get_object_or_404(ApiKey, id=api_key_id, user=request.user)
        
        name = request.POST.get('name', '').strip()
        if name:
            api_key.name = name
            api_key.save()
        
        # Return the updated API key as HTML for HTMX
        context = {'api_key': api_key}
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


async def shortcode_redirect(request, shortcode):
    """
    Redirect to the archived page for a given shortcode, injecting an overlay.
    """
    shortcode_obj = get_object_or_404(Shortcode, pk=shortcode)

    # Track the visit
    visit = Visit.objects.create(
        shortcode=shortcode_obj,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        referer=request.META.get('HTTP_REFERER', ''),
    )
    # Trigger async task for analytics processing
    # from archive.tasks import update_visit_analytics_task
    # update_visit_analytics_task.delay(visit.id)

    # Determine the archive manager to use
    managers = get_archive_managers()
    if shortcode_obj.archive_method in managers:
        manager = managers[shortcode_obj.archive_method]
    elif managers:
        manager = next(iter(managers.values())) # fallback to first available
    else:
        raise Http404("No archive manager is configured.")

    # Get the timestamp from the query parameter or use the creation date
    ts_str = request.GET.get('ts')
    requested_dt = None
    if ts_str:
        try:
            requested_dt = timezone.datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except ValueError:
            pass # Ignore invalid timestamp

    # Find the most relevant archive
    archives = await manager.find_archives_for_url(shortcode_obj.url)
    if not archives:
        raise Http404("No archive found for this URL.")

    # Select the best match based on timestamp
    if requested_dt:
        # Find the archive closest to the requested timestamp
        best_archive = min(archives, key=lambda a: abs(a['timestamp'] - requested_dt))
    else:
        # Default to the most recent archive
        best_archive = max(archives, key=lambda a: a['timestamp'])
    
    actual_dt = best_archive['timestamp']

    # Get archive content
    html_content = await manager.get_archive_content(str(int(actual_dt.timestamp())))
    
    if html_content:
        # Inject the overlay
        html_with_overlay = await inject_overlay(html_content, shortcode_obj, requested_dt, actual_dt)
        return HttpResponse(html_with_overlay)
    
    raise Http404("Could not retrieve archived content.")


def serve_favicon(request, shortcode):
    """
    Serve the favicon for a given shortcode.
    """
    shortcode_obj = get_object_or_404(Shortcode, pk=shortcode)
    
    if shortcode_obj.archive_method == 'singlefile':
        archive_base_path = Path(settings.SINGLEFILE_DATA_PATH)
        favicon_path = archive_base_path / shortcode_obj.shortcode / "favicon.ico"
        
        if favicon_path.exists():
            return FileResponse(open(favicon_path, 'rb'), content_type='image/x-icon')

    # Fallback for other archive methods or if favicon not found in singlefile
    # This might involve another lookup or a default favicon
    raise Http404("Favicon not found.")
