"""Overlay template management and CSS loading."""

import os
from pathlib import Path
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from bs4 import BeautifulSoup
import logging

from django.conf import settings
from django.template.loader import render_to_string
from archive.models import Shortcode, Visit
from core.utils import clean_text_fragment


logger = logging.getLogger(__name__)


def format_time_difference(time_diff: timedelta) -> str:
    """Format time difference with sensible units based on magnitude"""
    total_seconds = int(time_diff.total_seconds())
    
    if total_seconds < 120:  # Less than 2 minutes
        return f"{total_seconds} second{'s' if total_seconds != 1 else ''}"
    
    elif total_seconds < 7200:  # Less than 2 hours
        minutes = total_seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    
    elif total_seconds < 86400:  # Less than 1 day
        hours = total_seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    
    elif total_seconds < 604800:  # Less than 1 week
        days = total_seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"
    
    elif total_seconds < 3024000:  # Less than 5 weeks (35 days)
        weeks = total_seconds // 604800
        return f"{weeks} week{'s' if weeks != 1 else ''}"
    
    elif total_seconds < 31536000:  # Less than 1 year
        months = total_seconds // 2628000  # Approximate month (365.25 days / 12)
        return f"{months} month{'s' if months != 1 else ''}"
    
    elif total_seconds < 36720000:  # Less than 14 months (425 days)
        return "one year"
    
    else:
        return "over a year"


def generate_time_warning(requested_dt: datetime, actual_dt: datetime, timediff_warning_threshold: int) -> Optional[str]:
    """Generate warning text if time difference exceeds threshold"""
    if not requested_dt or not actual_dt:
        return None

    time_diff = abs(requested_dt - actual_dt)
    
    if time_diff > timedelta(seconds=timediff_warning_threshold):
        if requested_dt > actual_dt:
            # Archive is older than citation
            return f"archived {format_time_difference(time_diff)} before citation"
        else:
            # Archive is newer than citation  
            return f"archived {format_time_difference(time_diff)} after citation"
    
    return None


def truncate_text_fragment(text_fragment: str, max_chars: int = 50) -> str:
    """Truncate text fragment intelligently with ellipses"""
    if not text_fragment:
        return ""
    
    # Clean up the text fragment (remove URL encoding artifacts)
    cleaned = text_fragment.replace('%20', ' ').replace('%22', '"').replace('%27', "'")
    
    # Check if truncation is needed
    if len(cleaned) <= max_chars:
        return cleaned
    
    # Try to truncate at word boundary
    truncated = cleaned[:max_chars]
    last_space = truncated.rfind(' ')
    
    # If we found a space and it's not too far from the end, truncate there
    if last_space > max_chars * 0.7:
        return truncated[:last_space] + '...'
    
    # Otherwise just truncate at max_chars
    return truncated + '...'


def clean_url_for_display(url: str) -> str:
    """Remove protocol and www prefixes for cleaner display"""
    if not url:
        return ""
    
    display_url = url
    
    # Remove protocol (http:// or https://)
    if display_url.startswith('https://'):
        display_url = display_url[8:]
    elif display_url.startswith('http://'):
        display_url = display_url[7:]
    
    # Remove www. prefix
    if display_url.startswith('www.'):
        display_url = display_url[4:]
    
    return display_url


def format_hit_count(count: int) -> str:
    """Format hit count with k/m/b/t abbreviations, max 4 characters"""
    if count < 1000:
        return str(count)
    elif count < 10000:
        # 1.0k to 9.9k (show decimal for single digit)
        return f"{count/1000:.1f}k"
    elif count < 1000000:
        # 10k to 999k (no decimal)
        return f"{count//1000}k"
    elif count < 10000000:
        # 1.0m to 9.9m (show decimal for single digit)
        return f"{count/1000000:.1f}m"
    elif count < 1000000000:
        # 10m to 999m (no decimal)
        return f"{count//1000000}m"
    elif count < 10000000000:
        # 1.0b to 9.9b (show decimal for single digit)
        return f"{count/1000000000:.1f}b"
    elif count < 1000000000000:
        # 10b to 999b (no decimal)
        return f"{count//1000000000}b"
    elif count < 10000000000000:
        # 1.0t to 9.9t (show decimal for single digit)
        return f"{count/1000000000000:.1f}t"
    else:
        # 10t+ (no decimal)
        return f"{count//1000000000000}t"


def create_visit_graph(visit_dates: List[datetime], short_code: str) -> str:
    """Create a simple visit graph based on visit dates"""
    if not visit_dates:
        return ""
    
    now = datetime.now(timezone.utc)
    oldest_visit = min(visit_dates)
    age_days = (now - oldest_visit).days
    
    # Determine time bucket based on age
    if age_days <= 3:  # Less than 3 days: per hour
        bucket_hours = 1
        use_hourly = True
    elif age_days <= 14:  # Less than 2 weeks: per day
        bucket_days = 1
        use_hourly = False
    elif age_days <= 180:  # Less than 6 months: per week
        bucket_days = 7
        use_hourly = False
    elif age_days <= 365:  # Less than 1 year: per month
        bucket_days = 30
        use_hourly = False
    elif age_days <= 1095:  # Less than 3 years: per quarter
        bucket_days = 90
        use_hourly = False
    else:  # More than 3 years: per year 
        bucket_days = 365 
        use_hourly = False
    
    # Create buckets
    buckets = defaultdict(int)
    
    if use_hourly:
        # For hourly buckets, start from the hour of the oldest visit
        bucket_start = oldest_visit.replace(minute=0, second=0, microsecond=0)
        
        for visit_date in visit_dates:
            hours_since_start = int((visit_date - bucket_start).total_seconds() // 3600)
            bucket_index = hours_since_start // bucket_hours
            buckets[bucket_index] += 1
    else:
        # For daily/weekly/monthly buckets, start from the day of the oldest visit
        bucket_start = oldest_visit.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for visit_date in visit_dates:
            days_since_start = (visit_date - bucket_start).days
            bucket_index = days_since_start // bucket_days
            buckets[bucket_index] += 1
    
    if not buckets:
        return ""
    
    # Generate graph HTML (simple bar chart)
    max_bucket_index = max(buckets.keys())
    bucket_count = max_bucket_index + 1
    
    # Limit to reasonable number of bars
    if bucket_count > 12:
        # Merge buckets if too many
        merge_factor = (bucket_count + 11) // 12
        merged_buckets = defaultdict(int)
        for bucket_idx, count in buckets.items():
            merged_idx = bucket_idx // merge_factor
            merged_buckets[merged_idx] += count
        buckets = merged_buckets
        max_bucket_index = max(buckets.keys()) if buckets else 0
        bucket_count = max_bucket_index + 1
    
    if bucket_count < 3:
        return ""  # Too few data points
    
    # Calculate max_visits from actual bucket values (excluding 0s)
    actual_visit_counts = [buckets.get(i, 0) for i in range(bucket_count)]
    max_visits = max(actual_visit_counts) if actual_visit_counts else 1
    
    bars_html = ""
    for i in range(bucket_count):
        visit_count = buckets.get(i, 0)
        height_pct = (visit_count / max_visits * 100) if max_visits > 0 else 0
        bars_html += f'<div class="visit-bar" style="height: {height_pct:.1f}%" title="{visit_count} visits"></div>'
    
    return f"""
    <div class="visit-graph" onclick="toggleAnalytics()">
        <div class="visit-bars">{bars_html}</div>
    </div>
    """


def prepare_analytics_data(shortcode: Shortcode) -> Tuple[Dict, str, int, str]:
    """Prepare analytics data for the overlay"""
    visits = Visit.objects.filter(shortcode=shortcode)
    visit_dates = list(visits.values_list('visited_at', flat=True))
    total_visits = len(visit_dates)
    visit_graph = create_visit_graph(visit_dates, shortcode.shortcode)
    formatted_hits = f"{format_hit_count(total_visits)} hits"
    
    # Get detailed analytics data
    detailed_visits = list(visits.values('visited_at', 'country'))
    
    # Process analytics data for embedding
    analytics_data = {
        "shortcode": shortcode.shortcode,
        "url": shortcode.url,
        "total_visits": total_visits,
        "visits": []
    }
    
    for visit in detailed_visits:
        analytics_data["visits"].append({
            "visited_at": visit["visited_at"].isoformat(),
            "country": visit.get("country")
        })
    
    return analytics_data, visit_graph, total_visits, formatted_hits


def prepare_graphic_html(graphic_value: Optional[str], alt_text: str, css_class: str = "", link_url: Optional[str] = None) -> str:
    """Prepare HTML for a graphic (URL, local path, or direct content)"""
    if not graphic_value:
        return ""
    
    class_attr = f' class="{css_class}"' if css_class else ""
    
    # Check if it's a URL (starts with http:// or https://)
    if graphic_value.startswith(('http://', 'https://')):
        img_html = f'<img src="{graphic_value}"{class_attr} alt="{alt_text}">'
    # Check if it's a local path (contains a file extension)
    elif '.' in graphic_value and any(graphic_value.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']):
        img_html = f'<img src="{graphic_value}"{class_attr} alt="{alt_text}">'
    else:
        # Treat as direct content (text, emoji, etc.)
        img_html = graphic_value
    
    if link_url:
        return f'<a href="{link_url}" target="_blank">{img_html}</a>'
    else:
        return img_html


def prepare_server_info() -> Tuple[str, str]:
    """Prepare server icon and domain HTML for the overlay"""
    server_icon_html = ""
    server_domain_html = ""
    
    if settings.STYLE_ICON:
        server_icon_html = prepare_graphic_html(settings.STYLE_ICON, "Server Icon", css_class="server-icon", link_url=settings.SERVER_BASE_URL)
    
    if settings.SERVER_DOMAIN:
        server_domain_html = f'<a href="{settings.SERVER_BASE_URL}" target="_blank">{settings.SERVER_DOMAIN}</a>'
    
    return server_icon_html, server_domain_html


def prepare_copy_graphic() -> str:
    """Prepare copy graphic HTML"""
    if not settings.STYLE_COPY_GRAPHIC:
        return "📋"  # Default fallback
    
    return prepare_graphic_html(settings.STYLE_COPY_GRAPHIC, "Copy", css_class="copy-icon")


def prepare_url_line(original_url: str, archive_dt: datetime) -> Tuple[str, str]:
    """Prepare the URL line HTML and archive date text for the top row"""
    # Format archive date as YYYY.MM.DD
    archive_date_text = f"{archive_dt.strftime('%Y.%m.%d')}"
    
    # Create URL line - just use the cleaned URL for now
    cleaned_url = clean_url_for_display(original_url)
    url_line_html = f'<a href="{original_url}" target="_blank"><strong>{cleaned_url}</strong></a>'
    
    return url_line_html, archive_date_text


def prepare_overlay_links(shortcode: Shortcode, archive_dt: datetime) -> Tuple[str, str, str, str]:
    """Prepare the various links for the overlay"""
    # Format dates for desktop and mobile
    desktop_date = archive_dt.strftime("%B %d, %Y")  # "June 11, 2025"
    mobile_month_day = f"{archive_dt.month}.{archive_dt.day:02d}" # "06.11"
    mobile_year = archive_dt.strftime("%Y")  # "2025"
    
    # Archivebox link
    archivebox_link_html = ""
    if hasattr(settings, 'ARCHIVEBOX_EXPOSE_URL') and settings.ARCHIVEBOX_EXPOSE_URL and shortcode.archive_method in ('archivebox', 'both'):
        archive_timestamp = int(archive_dt.timestamp())
        archivebox_link = f"{settings.ARCHIVEBOX_BASE_URL}/archive/{archive_timestamp}/index.html"
        archivebox_link_html = f'<a href="{archivebox_link}" target="_blank">archivebox</a>'
    
    return desktop_date, mobile_month_day, mobile_year, archivebox_link_html


def create_text_fragment_html(cleaned_fragment: str) -> str:
    """Create the text fragment display HTML with protection against text fragment matching"""
    if not cleaned_fragment:
        return ""
    
    # Replace each space with: non-breaking space + regular space in 6pt font
    # This creates double spacing that won't collapse, but keeps the regular space for wrapping
    protected_text = ''
    for char in cleaned_fragment:
        if char == ' ':
            protected_text += '<span class="fragment-space-protection">&nbsp; </span>'
        else:
            protected_text += char
    
    return f'''
        <div class="perma-text-fragment">
            <div class="fragment-quote">❝</div>
            <div class="fragment-text-container"
                 title="{cleaned_fragment}"
                 onclick="highlightTextFragment()"
                 data-original-text="{cleaned_fragment}">
                <div class="fragment-text">{protected_text}</div>
            </div>
        </div>
    '''


def create_favicon_tag(soup: BeautifulSoup, shortcode: Shortcode, archive_dt: datetime) -> None:
    """Create and inject favicon tag into head"""
    head_tag = soup.find('head')
    if not head_tag:
        return
    
    # Remove any existing favicons first
    for existing_favicon in head_tag.find_all('link', rel=lambda x: x and 'icon' in x.lower()):
        existing_favicon.decompose()
    
    # Add theme-color meta tag for browser color matching
    theme_color_tag = soup.new_tag('meta')
    theme_color_tag.attrs['name'] = 'theme-color'
    theme_color_tag.attrs['content'] = settings.STYLE_BACKGROUND_COLOR
    head_tag.insert(0, theme_color_tag)
    
    # Create new favicon link
    favicon_link = soup.new_tag('link')
    favicon_link.attrs['rel'] = 'shortcut icon'
    favicon_link.attrs['type'] = 'image/x-icon'
    
    if shortcode.archive_method == 'singlefile':
        archive_base_path = Path(settings.SINGLEFILE_DATA_PATH)
        favicon_path = archive_base_path / shortcode.shortcode / "favicon.ico"
        if favicon_path.exists():
            prefix = f"/{settings.SERVER_URL_PREFIX}" if settings.SERVER_URL_PREFIX else ""
            favicon_link.attrs['href'] = f"{prefix}/{shortcode.shortcode}/favicon.ico"
        else:
            return
    else: # archivebox
        archive_timestamp = int(archive_dt.timestamp())
        if hasattr(settings, 'ARCHIVEBOX_DATA_PATH') and settings.ARCHIVEBOX_DATA_PATH:
            favicon_link.attrs['href'] = f"/archive/{archive_timestamp}/favicon.ico"
        else:
            favicon_link.attrs['href'] = f"{settings.ARCHIVEBOX_BASE_URL}/archive/{archive_timestamp}/favicon.ico"
    
    head_tag.insert(0, favicon_link)


async def inject_overlay(html_content: str, shortcode: Shortcode, requested_dt: datetime, actual_dt: datetime) -> str:
    """Main function to inject overlay into archived content"""
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        body_tag = soup.find('body')
        if not body_tag:
            return html_content
        
        # Create favicon
        create_favicon_tag(soup, shortcode, actual_dt)
        
        # Prepare analytics data
        analytics_data, visit_graph, total_visits, formatted_hits = prepare_analytics_data(shortcode)
        
        # Prepare overlay links
        desktop_date, mobile_month_day, mobile_year, archivebox_link_html = prepare_overlay_links(shortcode, actual_dt)
        
        # Prepare server info
        server_icon_html, server_domain_html = prepare_server_info()
        
        # Prepare copy graphic
        copy_graphic = prepare_copy_graphic()
        
        # Prepare URL line and archive date for top row
        url_line_html, archive_date_text = prepare_url_line(shortcode.url, actual_dt)
        
        # Generate warning if needed
        warning_text = generate_time_warning(requested_dt, actual_dt, settings.TIMEDIFF_WARNING_THRESHOLD)
        warning_html = f'<div class="perma-fallback-warning">note: {warning_text}</div>' if warning_text else ""
        
        # Prepare text fragment
        cleaned_fragment = clean_text_fragment(shortcode.text_fragment)
        text_fragment_html = create_text_fragment_html(cleaned_fragment)
        
        context = {
            'style_background_color': settings.STYLE_BACKGROUND_COLOR,
            'style_link_color': settings.STYLE_LINK_COLOR,
            'style_accent_color': settings.STYLE_ACCENT_COLOR,
            'original_url': shortcode.url,
            'desktop_date': desktop_date,
            'mobile_month_day': mobile_month_day,
            'mobile_year': mobile_year,
            'archivebox_link_html': archivebox_link_html,
            'warning_html': warning_html,
            'text_fragment_html': text_fragment_html,
            'visit_graph': visit_graph,
            'total_visits': total_visits,
            'formatted_hits': formatted_hits,
            'server_icon_html': server_icon_html,
            'server_domain_html': server_domain_html,
            'copy_graphic': copy_graphic,
            'url_line_html': url_line_html,
            'archive_date_text': archive_date_text,
            'analytics_data_json': json.dumps(analytics_data),
            'text_fragment': (shortcode.text_fragment or "").replace("'", "\\'").replace('"', '\\"'),
            'cleaned_fragment': cleaned_fragment.replace("'", "\\'").replace('"', '\\"'),
        }

        # Create overlay HTML using template
        overlay_html = render_to_string('web/partials/overlay.html', context)
        
        # Create script tag
        overlay_script = render_to_string('web/partials/overlay.js', context)
        padding_script_tag = soup.new_tag('script')
        padding_script_tag.string = overlay_script
        
        # Inject into page
        body_tag.insert(0, BeautifulSoup(overlay_html, 'html.parser'))
        body_tag.append(padding_script_tag)
        
        return str(soup)
        
    except Exception as e:
        logger.error(f"Error injecting overlay for {shortcode.shortcode}: {e}", exc_info=True)
        return html_content 