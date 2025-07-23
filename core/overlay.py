"""Overlay template management and CSS loading for Django."""

import os
from pathlib import Path
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from collections import defaultdict
from bs4 import BeautifulSoup
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from .utils import clean_text_fragment

# Cache for templates
_overlay_css_cache: Optional[str] = None
_overlay_html_template_cache: Optional[str] = None
_overlay_js_template_cache: Optional[str] = None


def clear_overlay_caches():
    """Clear all overlay template caches"""
    global _overlay_css_cache, _overlay_html_template_cache, _overlay_js_template_cache
    _overlay_css_cache = None
    _overlay_html_template_cache = None
    _overlay_js_template_cache = None


def load_overlay_css() -> str:
    """Load the CSS styles for the overlay from static file with caching"""
    global _overlay_css_cache
    
    if _overlay_css_cache is not None:
        return _overlay_css_cache
    
    css_path = Path(settings.BASE_DIR) / "static" / "overlay.css"
    
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            _overlay_css_cache = f.read()
        return _overlay_css_cache
    except FileNotFoundError:
        # Fallback - return empty string if file not found
        return ""


def load_overlay_html_template() -> str:
    """Load the HTML template for the overlay from static file with caching"""
    global _overlay_html_template_cache
    
    if _overlay_html_template_cache is not None:
        return _overlay_html_template_cache
    
    template_path = Path(settings.BASE_DIR) / "static" / "overlay_template.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            _overlay_html_template_cache = f.read()
        return _overlay_html_template_cache
    except FileNotFoundError:
        # Fallback - return empty string if file not found
        return ""


def load_overlay_js_template() -> str:
    """Load the JavaScript template for the overlay from static file with caching"""
    global _overlay_js_template_cache
    
    if _overlay_js_template_cache is not None:
        return _overlay_js_template_cache
    
    template_path = Path(settings.BASE_DIR) / "static" / "overlay_template.js"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            _overlay_js_template_cache = f.read()
        return _overlay_js_template_cache
    except FileNotFoundError:
        # Fallback - return empty string if file not found
        return ""


def generate_dynamic_overlay_css() -> str:
    """Generate overlay CSS with dynamic colors from Django settings"""
    # Clear cache to ensure fresh CSS generation
    clear_overlay_caches()
    
    base_css = load_overlay_css()
    
    # Set CSS variables for dynamic colors
    css_vars = f"""
:root {{
    --style-background-color: {settings.OVERLAY_STYLE_BACKGROUND_COLOR} !important;
    --style-link-color: {settings.OVERLAY_STYLE_LINK_COLOR} !important;
    --style-accent-color: {settings.OVERLAY_STYLE_ACCENT_COLOR} !important;
}}
"""
    
    # Prepend the CSS variables to the base CSS
    return css_vars + base_css


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


def generate_time_warning(requested_dt: datetime, actual_dt: datetime) -> Optional[str]:
    """Generate warning text if time difference exceeds threshold"""
    time_diff = abs(requested_dt - actual_dt)
    threshold = timedelta(seconds=settings.TIMEDIFF_WARNING_THRESHOLD)
    
    if time_diff > threshold:
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
    
    now = timezone.now()
    oldest_visit = min(visit_dates)
    age_days = (now - oldest_visit).days
    
    # Determine time bucket based on age
    if age_days <= 3:  # Less than 3 days: per hour
        bucket_hours = 1
        bucket_label = "hour"
        use_hourly = True
    elif age_days <= 14:  # Less than 2 weeks: per day
        bucket_days = 1
        bucket_label = "day"
        use_hourly = False
    elif age_days <= 180:  # Less than 6 months: per week
        bucket_days = 7
        bucket_label = "week"
        use_hourly = False
    elif age_days <= 365:  # Less than 1 year: per month
        bucket_days = 30
        bucket_label = "month"
        use_hourly = False
    elif age_days <= 1095:  # Less than 3 years: per quarter
        bucket_days = 90
        bucket_label = "quarter"
        use_hourly = False
    else:  # More than 3 years: per year 
        bucket_days = 365 
        bucket_label = "year"
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


def prepare_analytics_data(shortcode_obj, visits):
    """Prepare analytics data for the overlay"""
    visit_dates = [visit.visited_at for visit in visits]
    total_visits = len(visit_dates)
    visit_graph = create_visit_graph(visit_dates, shortcode_obj.shortcode)
    formatted_hits = f"{format_hit_count(total_visits)} hits"
    
    # Process analytics data for embedding
    analytics_data = {
        "shortcode": shortcode_obj.shortcode,
        "url": shortcode_obj.url,
        "total_visits": total_visits,
        "visits": []
    }
    
    for visit in visits:
        analytics_data["visits"].append({
            "visited_at": visit.visited_at.isoformat(),
            "country": visit.country or None
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
        # Use Django's static function for local assets
        static_url = static(graphic_value)
        img_html = f'<img src="{static_url}"{class_attr} alt="{alt_text}">'
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
    
    if settings.OVERLAY_STYLE_ICON:
        server_icon_html = prepare_graphic_html(
            settings.OVERLAY_STYLE_ICON, 
            "Server Icon", 
            css_class="server-icon", 
            link_url=settings.SERVER_BASE_URL
        )
    
    if settings.OVERLAY_SERVER_DOMAIN:
        server_domain_html = f'<a href="{settings.SERVER_BASE_URL}" target="_blank">{settings.OVERLAY_SERVER_DOMAIN}</a>'
    
    return server_icon_html, server_domain_html


def prepare_copy_graphic() -> str:
    """Prepare copy graphic HTML"""
    if not settings.OVERLAY_STYLE_COPY_GRAPHIC:
        return "📋"  # Default fallback
    
    return prepare_graphic_html(settings.OVERLAY_STYLE_COPY_GRAPHIC, "Copy", css_class="copy-icon")


def prepare_url_line(original_url: str, archive_dt: datetime) -> Tuple[str, str]:
    """Prepare the URL line HTML and archive date text for the top row"""
    # Format archive date as YYYY.MM.DD
    archive_date_text = f"{archive_dt.strftime('%Y.%m.%d')}"
    
    # Create URL line - just use the cleaned URL for now
    cleaned_url = clean_url_for_display(original_url)
    url_line_html = f'<a href="{original_url}" target="_blank"><strong>{cleaned_url}</strong></a>'
    
    return url_line_html, archive_date_text


def prepare_overlay_links(shortcode_obj, archive_dt: datetime) -> Tuple[str, str, str, str]:
    """Prepare the various links for the overlay"""
    # Format dates for desktop and mobile
    desktop_date = archive_dt.strftime("%B %d, %Y")  # "June 11, 2025"
    mobile_month_day = f"{archive_dt.month}.{archive_dt.day:02d}" # "06.11"
    mobile_year = archive_dt.strftime("%Y")  # "2025"
    
    # Archivebox link
    archivebox_link_html = ""
    if settings.ARCHIVEBOX_EXPOSE_URL and archive_dt:
        # Convert datetime to timestamp for archivebox URL
        archive_timestamp = str(int(archive_dt.timestamp()))
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


def create_favicon_tag(soup, shortcode_obj) -> None:
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
    theme_color_tag.attrs['content'] = settings.OVERLAY_STYLE_BACKGROUND_COLOR
    head_tag.insert(0, theme_color_tag)
    
    # Create new favicon link
    favicon_link = soup.new_tag('link')
    favicon_link.attrs['rel'] = 'shortcut icon'
    favicon_link.attrs['type'] = 'image/x-icon'
    
    # For SingleFile mode, check if favicon exists in archive using filesystem
    if shortcode_obj.is_archived():
        archive_path = shortcode_obj.get_latest_archive_path()
        if archive_path:
            favicon_path = archive_path / "favicon.ico"
            if favicon_path.exists():
                # Use relative path construction that matches the serving logic
                prefix = f"/{settings.SERVER_URL_PREFIX}" if settings.SERVER_URL_PREFIX else ""
                # We'll need to serve favicon through a new endpoint
                favicon_link.attrs['href'] = f"{prefix}/{shortcode_obj.shortcode}.favicon.ico"
            else:
                # No favicon available, remove link
                return
        else:
            # No archive path, remove link
            return
    else:
        # No archive available, remove link
        return
    
    # Insert at beginning of head for priority
    head_tag.insert(0, favicon_link)


def generate_overlay_html(
    original_url: str,
    desktop_date: str,
    mobile_month_day: str,
    mobile_year: str,
    archivebox_link_html: str,
    warning_html: str,
    text_fragment_html: str,
    visit_graph: str,
    total_visits: int,
    overlay_styles: str,
    formatted_hits: str,
    server_icon_html: str,
    server_domain_html: str,
    copy_graphic: str,
    url_line_html: str,
    archive_date_text: str
) -> str:
    """Generate the overlay HTML from template"""
    template = load_overlay_html_template()
    
    return template.format(
        overlay_styles=overlay_styles,
        original_url=original_url,
        desktop_date=desktop_date,
        mobile_month_day=mobile_month_day,
        mobile_year=mobile_year,
        archivebox_link_html=archivebox_link_html,
        warning_html=warning_html,
        text_fragment_html=text_fragment_html,
        visit_graph=visit_graph,
        total_visits=total_visits,
        formatted_hits=formatted_hits,
        server_icon_html=server_icon_html,
        server_domain_html=server_domain_html,
        copy_graphic=copy_graphic,
        url_line_html=url_line_html,
        archive_date_text=archive_date_text
    )


def generate_overlay_scripts(
    analytics_data: Dict[str, Any],
    text_fragment: Optional[str],
    cleaned_fragment: str
) -> str:
    """Generate the overlay JavaScript from template"""
    template = load_overlay_js_template()
    
    # Escape text fragments for JavaScript
    text_fragment_escaped = (text_fragment or "").replace("'", "\\'").replace('"', '\\"')
    cleaned_fragment_escaped = cleaned_fragment.replace("'", "\\'").replace('"', '\\"')
    
    return template.format(
        text_fragment=text_fragment_escaped,
        cleaned_fragment=cleaned_fragment_escaped,
        analytics_data_json=json.dumps(analytics_data),
        style_background_color=settings.OVERLAY_STYLE_BACKGROUND_COLOR,
        style_link_color=settings.OVERLAY_STYLE_LINK_COLOR,
        style_accent_color=settings.OVERLAY_STYLE_ACCENT_COLOR
    )


def inject_overlay(html_content: str, shortcode_obj, archive_dt: datetime, 
                  requested_dt: Optional[datetime], visits) -> str:
    """Main function to inject overlay into archived content"""
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        body_tag = soup.find('body')
        if not body_tag:
            return html_content
        
        # Create favicon
        create_favicon_tag(soup, shortcode_obj)
        
        # Prepare analytics data
        analytics_data, visit_graph, total_visits, formatted_hits = prepare_analytics_data(shortcode_obj, visits)
        
        # Prepare overlay links
        desktop_date, mobile_month_day, mobile_year, archivebox_link_html = prepare_overlay_links(shortcode_obj, archive_dt)
        
        # Prepare server info
        server_icon_html, server_domain_html = prepare_server_info()
        
        # Prepare copy graphic
        copy_graphic = prepare_copy_graphic()
        
        # Prepare URL line and archive date for top row
        url_line_html, archive_date_text = prepare_url_line(shortcode_obj.url, archive_dt)
        
        # Generate warning if needed
        warning_text = None
        if requested_dt:
            warning_text = generate_time_warning(requested_dt, archive_dt)
        warning_html = f'<div class="perma-fallback-warning">note: {warning_text}</div>' if warning_text else ""
        
        # Prepare text fragment
        cleaned_fragment = clean_text_fragment(shortcode_obj.text_fragment)
        text_fragment_html = create_text_fragment_html(cleaned_fragment)
        
        # Generate dynamic CSS with configured colors
        overlay_styles = generate_dynamic_overlay_css()
        
        # Create overlay HTML using template
        overlay_html = generate_overlay_html(
            original_url=shortcode_obj.url,
            desktop_date=desktop_date,
            mobile_month_day=mobile_month_day,
            mobile_year=mobile_year,
            archivebox_link_html=archivebox_link_html,
            warning_html=warning_html,
            text_fragment_html=text_fragment_html,
            visit_graph=visit_graph,
            total_visits=total_visits,
            overlay_styles=overlay_styles,
            formatted_hits=formatted_hits,
            server_icon_html=server_icon_html,
            server_domain_html=server_domain_html,
            copy_graphic=copy_graphic,
            url_line_html=url_line_html,
            archive_date_text=archive_date_text
        )
        
        # Create script tag
        padding_script_tag = soup.new_tag('script')
        padding_script_tag.string = generate_overlay_scripts(analytics_data, shortcode_obj.text_fragment, cleaned_fragment)
        
        # Inject into page
        body_tag.insert(0, BeautifulSoup(overlay_html, 'html.parser'))
        body_tag.append(padding_script_tag)
        
        return str(soup)
        
    except Exception as e:
        # Log the error but don't break the page serving
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error injecting overlay: {e}", exc_info=True)
        return html_content 