
# Ye Olde Overlay

Below, please find the old banner overlay code and styling. We want to bring this over into our new Django app. 

## web/overlay.py

```python
"""Overlay template management and CSS loading."""

import os
from pathlib import Path
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from bs4 import BeautifulSoup
import hashlib
from ..utils import clean_text_fragment

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
    
    css_path = Path(__file__).parent / "static" / "overlay.css"
    
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
    
    template_path = Path(__file__).parent / "static" / "overlay_template.html"
    
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
    
    template_path = Path(__file__).parent / "static" / "overlay_template.js"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            _overlay_js_template_cache = f.read()
        return _overlay_js_template_cache
    except FileNotFoundError:
        # Fallback - return empty string if file not found
        return ""

def generate_dynamic_overlay_css(config) -> str:
    """Generate overlay CSS with dynamic colors from config"""
    # Clear cache to ensure fresh CSS generation
    clear_overlay_caches()
    
    base_css = load_overlay_css()
    
    # Set CSS variables for dynamic colors
    css_vars = f"""
:root {{
    --style-background-color: {config.style_background_color} !important;
    --style-link-color: {config.style_link_color} !important;
    --style-accent-color: {config.style_accent_color} !important;
}}
"""
    
    # Prepend the CSS variables to the base CSS
    return css_vars + base_css

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
        # mobile_date=mobile_date,
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
    cleaned_fragment: str,
    config
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
        style_background_color=config.style_background_color,
        style_link_color=config.style_link_color,
        style_accent_color=config.style_accent_color
    )


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


def prepare_analytics_data(short_code: str, original_url: str, db) -> Tuple[Dict, str, int, str]:
    """Prepare analytics data for the overlay"""
    visit_dates = db.get_visits(short_code)
    total_visits = len(visit_dates)
    visit_graph = create_visit_graph(visit_dates, short_code)
    formatted_hits = f"{format_hit_count(total_visits)} hits"
    
    # Get detailed analytics data
    detailed_visits = db.get_detailed_visits(short_code)
    
    # Process analytics data for embedding
    analytics_data = {
        "shortcode": short_code,
        "url": original_url,
        "total_visits": total_visits,
        "visits": []
    }
    
    for visit in detailed_visits:
        analytics_data["visits"].append({
            "visited_at": visit["visited_at"],
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


def prepare_server_info(config) -> Tuple[str, str]:
    """Prepare server icon and domain HTML for the overlay"""
    server_icon_html = ""
    server_domain_html = ""
    
    if config.style_icon:
        server_icon_html = prepare_graphic_html(config.style_icon, "Server Icon", css_class="server-icon", link_url=config.server_base_url)
    
    if config.server_domain:
        server_domain_html = f'<a href="{config.server_base_url}" target="_blank">{config.server_domain}</a>'
    
    return server_icon_html, server_domain_html


def prepare_copy_graphic(config) -> str:
    """Prepare copy graphic HTML"""
    if not config.style_copy_graphic:
        return "📋"  # Default fallback
    
    return prepare_graphic_html(config.style_copy_graphic, "Copy", css_class="copy-icon")


def prepare_url_line(original_url: str, archive_dt: datetime) -> Tuple[str, str]:
    """Prepare the URL line HTML and archive date text for the top row"""
    # Format archive date as YYYY.MM.DD
    archive_date_text = f"{archive_dt.strftime('%Y.%m.%d')}"
    
    # Create URL line - just use the cleaned URL for now
    cleaned_url = clean_url_for_display(original_url)
    url_line_html = f'<a href="{original_url}" target="_blank"><strong>{cleaned_url}</strong></a>'
    
    return url_line_html, archive_date_text


def prepare_overlay_links(snapshot: Dict, short_code: str, config) -> Tuple[str, str, str, str]:
    """Prepare the various links for the overlay"""
    archive_timestamp = snapshot['timestamp']
    archive_dt = datetime.fromtimestamp(float(archive_timestamp), tz=timezone.utc)
    
    # Format dates for desktop and mobile
    desktop_date = archive_dt.strftime("%B %d, %Y")  # "June 11, 2025"
    mobile_month_day = f"{archive_dt.month}.{archive_dt.day:02d}" # "06.11"
    mobile_year = archive_dt.strftime("%Y")  # "2025"
    
    # Archivebox link
    archivebox_link_html = ""
    if config.archivebox_expose_url:
        archivebox_link = f"{config.archivebox_base_url}/archive/{archive_timestamp}/index.html"
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


def create_favicon_tag(soup, snapshot: Dict, short_code: str, config) -> None:
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
    theme_color_tag.attrs['content'] = config.style_background_color  # Match overlay background color
    head_tag.insert(0, theme_color_tag)
    
    # Create new favicon link
    favicon_link = soup.new_tag('link')
    favicon_link.attrs['rel'] = 'shortcut icon'
    favicon_link.attrs['type'] = 'image/x-icon'
    
    archive_method = snapshot.get('archive_method', 'archivebox')
    archive_timestamp = snapshot['timestamp']
    
    if archive_method == 'singlefile':
        # For SingleFile mode, check if favicon exists in archive
        archive_path = Path(snapshot['archive_path'])
        favicon_path = archive_path / "favicon.ico"
        if favicon_path.exists():
            # Use relative path construction that matches the serving logic
            prefix = f"/{config.server_url_prefix}" if config.server_url_prefix else ""
            # We'll need to serve favicon through a new endpoint
            favicon_link.attrs['href'] = f"{prefix}/{short_code}.favicon.ico"
        else:
            # Fallback to a generic favicon or remove the link
            return
    else:
        # ArchiveBox mode (original logic)
        if config.archivebox_data_path:
            favicon_link.attrs['href'] = f"/archive/{archive_timestamp}/favicon.ico"
        else:
            favicon_link.attrs['href'] = f"{config.archivebox_base_url}/archive/{archive_timestamp}/favicon.ico"
    
    # Insert at beginning of head for priority
    head_tag.insert(0, favicon_link)


async def inject_overlay(html_content: str, original_url: str, snapshot: Dict, 
                        requested_dt: datetime, actual_dt: datetime, short_code: str, 
                        url: str, text_fragment: Optional[str], config, db, logger) -> str:
    """Main function to inject overlay into archived content"""
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        body_tag = soup.find('body')
        if not body_tag:
            return html_content
        
        # Create favicon
        create_favicon_tag(soup, snapshot, short_code, config)
        
        # Prepare analytics data
        analytics_data, visit_graph, total_visits, formatted_hits = prepare_analytics_data(short_code, original_url, db)
        
        # Prepare overlay links
        desktop_date, mobile_month_day, mobile_year, archivebox_link_html = prepare_overlay_links(snapshot, short_code, config)
        
        # Prepare server info
        server_icon_html, server_domain_html = prepare_server_info(config)
        
        # Prepare copy graphic
        copy_graphic = prepare_copy_graphic(config)
        
        # Prepare URL line and archive date for top row
        archive_timestamp = snapshot['timestamp']
        archive_dt = datetime.fromtimestamp(float(archive_timestamp), tz=timezone.utc)
        url_line_html, archive_date_text = prepare_url_line(original_url, archive_dt)
        
        # Generate warning if needed
        warning_text = generate_time_warning(requested_dt, actual_dt, config.timediff_warning_threshold)
        warning_html = f'<div class="perma-fallback-warning">note: {warning_text}</div>' if warning_text else ""
        
        # Prepare text fragment
        cleaned_fragment = clean_text_fragment(text_fragment)
        text_fragment_html = create_text_fragment_html(cleaned_fragment)
        
        # Generate dynamic CSS with configured colors
        overlay_styles = generate_dynamic_overlay_css(config)
        
        # Create overlay HTML using template
        overlay_html = generate_overlay_html(
            original_url=original_url,
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
        padding_script_tag.string = generate_overlay_scripts(analytics_data, text_fragment, cleaned_fragment, config)
        
        # Inject into page
        body_tag.insert(0, BeautifulSoup(overlay_html, 'html.parser'))
        body_tag.append(padding_script_tag)
        
        return str(soup)
        
    except Exception as e:
        logger.error(f"Error injecting overlay: {e}", exc_info=True)
        return html_content 
```

## web/static/overlay.css

```css
/* CSS Variables for configurable colors - these get overridden by inline styles from config */
:root {
    --style-background-color: #000000;
    --style-link-color: #ffe100;
    --style-accent-color: #ffe100;
}

/* Mobile-specific styles */
@media (max-width: 768px) {
    .desktop-text { display: none !important; }
    .mobile-text { display: inline !important; }
    .mobile-hide { display: none !important; }
    .mobile-show { display: block !important; }
    
    /* Compact mobile layout */
    #perma-overlay .perma-timestamp { 
        min-width: 0px !important; 
        font-size: 12px !important;
    }
    #perma-overlay .perma-links-row { 
        gap: 8px !important; 
    }
    #perma-overlay .perma-actions { 
        gap: 6px !important; 
    }
    #perma-overlay .perma-content-area { 
        gap: 8px !important; 
    }
    #perma-overlay .perma-left { 
        padding: 0 10px !important; 
    }
    #perma-overlay .perma-right { 
        gap: 8px !important; 
    }
    #perma-overlay {
        padding: 4px 10px !important;
        font-size: 10px !important;
    }
}

@media (min-width: 769px) {
    .desktop-text { display: inline !important; }
    .mobile-text { display: none !important; }
    .mobile-hide { display: block !important; }
    .mobile-show { display: none !important; }
    
    /* Desktop-specific timestamp sizing */
    #perma-overlay .perma-timestamp {
        min-width: 80px !important;
    }
}

#perma-overlay {
    position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important;
    height: auto !important; min-height: 36px !important;
    padding: 6px 10px !important;
    background: var(--style-background-color) !important;
    color: #839496 !important;
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
    font-size: 14px !important;
    line-height: 1.3 !important;
    z-index: 2147483647 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.5) !important;
    box-sizing: border-box !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 5px !important;
    transition: all 0.3s ease !important;
}
#perma-overlay * {
    font-family: inherit !important;
    font-size: inherit !important;
    color: inherit !important;
    line-height: inherit !important;
    font-weight: normal !important;
}
#perma-overlay .perma-top-row {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 8px !important;
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
    margin-top: 4px !important;
    margin-left: 10px !important;
    margin-right: 10px !important;
    margin-bottom: 2px !important;
    width: calc(100% - 20px) !important;
    max-width: calc(100% - 20px) !important;
    box-sizing: border-box !important;
}
#perma-overlay .perma-url-info {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
#perma-overlay .perma-url-info a {
    font-weight: bold !important;
    font-size: 14px !important;
    font-style: normal !important;
}
#perma-overlay .perma-archive-date {
    flex: 0 0 auto !important;
    white-space: nowrap !important;
}
#perma-overlay .perma-server-icon {
    flex: 0 0 auto !important;
    display: flex !important;
    align-items: center !important;
}
#perma-overlay .server-icon {
    max-height: 32px !important;
}
#perma-overlay .perma-content-area {
    display: flex !important;
    align-items: stretch !important;
    gap: 8px !important;
    min-height: 28px !important;
}
#perma-overlay .perma-left {
    flex: 1 1 auto !important;
    padding: 0 4px 0 0 !important;
    min-width: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
}
#perma-overlay .perma-center {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    flex: 0 0 auto !important;
}
#perma-overlay .copy-button {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    min-height: 16px !important;
    max-height: 16px !important;
    padding: 0 8px !important;
    font-size: 16px !important;
    opacity: 0.75 !important;
}
#perma-overlay .copy-button img,
#perma-overlay .copy-icon {
    width: auto !important;
    height: auto !important;
    max-width: 24px !important;
    max-height: 16px !important;
}
#perma-overlay .copy-button:hover {
    opacity: 1 !important;
}
#perma-overlay .perma-right {
    display: flex !important;
    flex-direction: column !important;
    gap: 2px !important;
    flex: 0 0 auto !important;
}
#perma-overlay .perma-stats-upper,
#perma-overlay .perma-stats-lower {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    text-align: center !important;
}
#perma-overlay .perma-actions-stack {
    display: flex !important;
    flex-direction: column !important;
    gap: 2px !important;
    align-items: flex-end !important;
}
#perma-overlay .perma-actions-stack .perma-actions {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
}
#perma-overlay .perma-right .perma-actions-stack .perma-actions {
    justify-content: center !important;
    text-align: center !important;
}
#perma-overlay .perma-text-fragment {
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
    height: 100% !important;
    min-height: 24px !important;
}
#perma-overlay .fragment-label {
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
    font-style: normal !important;
    color: #586e75 !important;
    font-size: 10px !important;
    white-space: nowrap !important;
    padding-top: 2px !important;
}
#perma-overlay .fragment-quote {
    font-family: 'Garamond', 'Georgia', 'Baskerville', serif !important;
    font-weight: 400 !important;
    font-style: normal !important;
    color: rgba(147, 161, 161, 0.33) !important;
    font-size: 22px !important;
    line-height: 1 !important;
    flex-shrink: 0 !important;
    align-self: center !important;
    user-select: none !important;
}
#perma-overlay .fragment-text-container {
    display: flex !important;
    align-items: center !important;
    min-width: 0 !important;
    flex: 1 !important;
    cursor: pointer !important;
    position: relative !important;
}
#perma-overlay .fragment-text {
    font-family: 'Garamond', 'Georgia', 'Baskerville', serif !important;
    font-weight: 400 !important;
    font-style: italic !important;
    color: #93a1a1 !important;
    font-size: 13px !important;
    line-height: 1.2 !important;
    display: -webkit-box !important;
    -webkit-line-clamp: 2 !important;
    -webkit-box-orient: vertical !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    word-break: keep-all !important;
    overflow-wrap: anywhere !important;
    hyphens: none !important;
    text-decoration: none !important;
    transition: all 0.3s ease !important;
    background-size: 400% auto !important;
    background-image: linear-gradient(110deg, rgba(140, 160, 160, 1.0), rgba(100, 220, 240, 1.0), rgba(80, 180, 200, 1.0) 92%) !important;
    -webkit-background-clip: text !important;
    background-clip: text !important;
    background-position: 0% center !important;
    flex: 1 !important;
    min-width: 0 !important;
}
#perma-overlay .fragment-space-protection {
    font-size: 6pt !important;
}
#perma-overlay .fragment-text-container:hover .fragment-text {
    color: transparent !important;
    text-decoration: none !important;
    animation: shineText 0.8s ease-out forwards !important;
    text-shadow: 0 0 2px rgba(0, 160, 140, 0.15) !important;
}
@keyframes shineText {
    0% {
        background-position: 0% center;
    }
    100% {
        background-position: 200% center;
    }
}
#perma-overlay .perma-links {
    display: flex !important;
    flex-direction: column !important;
    gap: 1px !important;
}
#perma-overlay .perma-links-row {
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
}
#perma-overlay .perma-actions {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
}
#perma-overlay .perma-stats {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    gap: 2px !important;
    text-align: center !important;
}
#perma-overlay a {
    color: var(--style-link-color) !important;
    text-decoration: none !important;
    white-space: nowrap !important;
    cursor: pointer !important;
}
#perma-overlay a:hover {
    color: var(--style-link-color) !important;
    opacity: 0.8 !important;
}
#perma-overlay .deepcite-link {
    font-size: 18px !important;
    color: #93a1a1 !important;
    text-decoration: none !important;
    padding: 2px 6px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    min-height: 28px !important;
}
#perma-overlay .deepcite-link:hover {
    color: #eee8d5 !important;
    background: rgba(147, 161, 161, 0.1) !important;
    border-radius: 3px !important;
}
#perma-overlay .perma-fallback-warning {
    color: #b58900 !important;
    font-size: 10px !important;
}
#perma-overlay .visit-graph {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    gap: 2px !important;
    cursor: pointer !important;
}
#perma-overlay .visit-graph:hover .visit-bar {
    animation: barBump 0.5s ease-out !important;
}
#perma-overlay .visit-graph:hover .visit-bar:nth-child(1) { animation-delay: 0s !important; }
#perma-overlay .visit-graph:hover .visit-bar:nth-child(2) { animation-delay: 0.05s !important; }
#perma-overlay .visit-graph:hover .visit-bar:nth-child(3) { animation-delay: 0.1s !important; }
#perma-overlay .visit-graph:hover .visit-bar:nth-child(4) { animation-delay: 0.15s !important; }
#perma-overlay .visit-graph:hover .visit-bar:nth-child(5) { animation-delay: 0.2s !important; }
#perma-overlay .visit-graph:hover .visit-bar:nth-child(6) { animation-delay: 0.25s !important; }
#perma-overlay .visit-graph:hover .visit-bar:nth-child(7) { animation-delay: 0.3s !important; }
#perma-overlay .visit-graph:hover .visit-bar:nth-child(8) { animation-delay: 0.35s !important; }
#perma-overlay .visit-graph:hover .visit-bar:nth-child(9) { animation-delay: 0.4s !important; }
#perma-overlay .visit-graph:hover .visit-bar:nth-child(10) { animation-delay: 0.45s !important; }
@keyframes barBump {
    0%, 100% {
        transform: scaleY(1);
    }
    50% {
        transform: scaleY(1.25);
    }
}
#perma-overlay .visit-bars {
    display: flex !important;
    align-items: end !important;
    gap: 1px !important;
    height: 16px !important;
}
#perma-overlay .visit-bar {
    width: 3px !important;
    background: var(--style-accent-color) !important;
    min-height: 1px !important;
    border-radius: 1px !important;
    cursor: pointer !important;
    transform-origin: bottom !important;
}
#perma-overlay .visit-label {
    font-size: 11px !important;
    color: var(--style-accent-color) !important;
    cursor: pointer !important;
    transition: color 0.2s ease !important;
}
#perma-overlay .visit-label:hover {
    color: var(--style-accent-color) !important;
    opacity: 0.8 !important;
}
#perma-overlay a::after {
    content: none !important;
    display: none !important;
}
#perma-overlay a[href^="http"]::after {
    content: none !important;
    display: none !important;
}
/* Analytics Expanded View */
#analytics-section {
    position: fixed !important;
    left: 0 !important;
    right: 0 !important;
    display: none !important;
    background: var(--style-background-color) !important;
    padding-top: 10px !important;
    padding-left: 10px !important;
    padding-right: 10px !important;
    padding-bottom: 10px !important;
    opacity: 0 !important;
    transition: opacity 0.3s ease !important;
    z-index: 2147483646 !important;
    box-sizing: border-box !important;
}
#analytics-section.active {
    display: block !important;
    opacity: 1 !important;
}
.analytics-content {
    display: flex !important;
    gap: 20px !important;
    align-items: flex-start !important;
}
.analytics-left {
    flex: 2 !important;
}
.analytics-right {
    flex: 1 !important;
    min-width: 150px !important;
}
.analytics-title {
    color: #93a1a1 !important;
    font-size: 10px !important;
    margin-bottom: 5px !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}
.line-chart {
    height: 80px !important;
    background: var(--style-background-color) !important;
    border-radius: 3px !important;
    position: relative !important;
    margin-bottom: 10px !important;
    padding: 5px !important;
}
.line-chart svg {
    width: 100% !important;
    height: 100% !important;
}
.line-chart path {
    fill: none !important;
    stroke: var(--style-accent-color) !important;
    stroke-width: 2 !important;
}
.country-list {
    display: flex !important;
    flex-direction: column !important;
    gap: 3px !important;
}
.country-item {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    background: var(--style-background-color) !important;
    padding: 3px 6px !important;
    border-radius: 2px !important;
    font-size: 9px !important;
}
.country-bar {
    width: 30px !important;
    height: 8px !important;
    background: var(--style-accent-color) !important;
    border-radius: 1px !important;
    margin-left: 5px !important;
}
.close-analytics {
    color: #586e75 !important;
    cursor: pointer !important;
    float: right !important;
    font-size: 12px !important;
    margin-left: 10px !important;
}
.close-analytics:hover {
    color: #93a1a1 !important;
} 
```
## web/static/overlay_template.html
```html
<div id="perma-overlay-container">
    <style>{overlay_styles}</style>
    <div id="perma-overlay">
        <!-- Top row: Server icon, URL info, and archive date -->
        <div class="perma-top-row">
            <div class="perma-server-icon">
                {server_icon_html}
            </div>
            <div class="perma-url-info">
                {url_line_html}
            </div>
            <div class="perma-archive-date">
                {archive_date_text}
            </div>
        </div>
        
        <!-- Content rows: Text fragment + copy icon + stats -->
        <div class="perma-content-area">
            <div class="perma-left">
                {text_fragment_html}
                {warning_html}
            </div>
            <div class="perma-center">
                <a href="#" onclick="copyCiteToClipboard(); return false;" class="copy-button">{copy_graphic}</a>
            </div>
            <div class="perma-right">
                <div class="perma-stats-upper">
                    {visit_graph}
                </div>
                <div class="perma-stats-lower">
                    <div class="visit-label" onclick="toggleAnalytics()" style="cursor: pointer !important;">{formatted_hits}</div>
                </div>
            </div>
        </div>
        {archivebox_link_html}
    </div>
        
        <!-- Analytics Expanded Section -->
        <div id="analytics-section">
            <div class="analytics-title">
                Link Analytics
                <span class="close-analytics" onclick="toggleAnalytics()">×</span>
            </div>
            <div class="analytics-content">
                <div class="analytics-left">
                    <div class="analytics-title">Visits Over Time</div>
                    <div class="line-chart" id="visits-chart">
                        <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #586e75;">
                            Ready to load
                        </div>
                    </div>
                </div>
                <div class="analytics-right">
                    <div class="analytics-title">Top Countries</div>
                    <div class="country-list" id="country-list">
                        <div style="color: #586e75;">Ready to load</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div> 
```

## web/static/overlay_template.js

```javascript
(function() {{
    var overlay = document.getElementById('perma-overlay');
    if (overlay) {{
        var height = overlay.offsetHeight + 'px';
        document.body.style.setProperty('padding-top', height, 'important');
    }}
    // Update favicon
    var favicon = document.querySelector('link[rel*="icon"]');
    if (favicon) {{
        favicon.href = favicon.href;
    }}
}})();

function highlightTextFragment() {{
    var textFragment = '{text_fragment}';
    if (!textFragment) return;
    if (!textFragment.startsWith('#:~:text=')) {{
        textFragment = '#:~:text=' + textFragment;
    }}
    var currentUrl = window.location.href.split('#')[0];
    window.location.replace(currentUrl + textFragment);
    // Manual fallback
    setTimeout(function() {{
        var searchText = '{cleaned_fragment}'.toLowerCase();
        if (!searchText) return;
        function findAndHighlight(searchText) {{
            var found = window.find(searchText, false, false, true, false, true, false);
            if (found) {{
                var selection = window.getSelection();
                if (selection.rangeCount > 0) {{
                    var range = selection.getRangeAt(0);
                    var rect = range.getBoundingClientRect();
                    var overlayHeight = document.getElementById('perma-overlay').offsetHeight;
                    window.scrollTo({{
                        top: rect.top + window.pageYOffset - overlayHeight - 20,
                        behavior: 'smooth'
                    }});
                    var span = document.createElement('span');
                    span.style.backgroundColor = '#b58900';
                    span.style.color = '#002b36';
                    span.style.transition = 'all 0.5s ease';
                    try {{
                        range.surroundContents(span);
                        setTimeout(function() {{
                            span.style.backgroundColor = 'transparent';
                            span.style.color = 'inherit';
                            setTimeout(function() {{
                                var parent = span.parentNode;
                                while (span.firstChild) {{
                                    parent.insertBefore(span.firstChild, span);
                                }}
                                parent.removeChild(span);
                            }}, 500);
                        }}, 3000);
                    }} catch(e) {{
                        // Just scroll if surroundContents fails
                    }}
                }}
            }}
        }}
        findAndHighlight(searchText);
    }}, 100);
}}

// Handle clicks on the fragment container + auto-highlight on load
document.addEventListener('DOMContentLoaded', function() {{
    var fragmentContainer = document.querySelector('.fragment-text-container');
    if (fragmentContainer) {{
        fragmentContainer.addEventListener('click', highlightTextFragment);
        
        // Auto-highlight text fragment on page load if it exists
        var textFragment = '{text_fragment}';
        if (textFragment && textFragment.trim()) {{
            // Small delay to ensure page content is fully rendered
            setTimeout(function() {{
                highlightTextFragment();
            }}, 500);
        }}
    }}
}});

var analyticsData = {analytics_data_json};
var analyticsExpanded = false;

// Configurable colors from server
var styleBackgroundColor = '{style_background_color}';
var styleLinkColor = '{style_link_color}';
var styleAccentColor = '{style_accent_color}';

function copyCiteToClipboard() {{
    try {{
        var pageTitle = document.title;
        var textFragment = '{cleaned_fragment}';
        var currentDate = new Date();
        var month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][currentDate.getMonth()];
        var formattedDate = month + ' ' + currentDate.getDate() + ', ' + currentDate.getFullYear();
        var currentUrl = window.location.href.split('#')[0]; // Remove any existing fragment
        
        // Add text fragment to URL if it exists
        var urlWithFragment = currentUrl;
        if (textFragment && textFragment.trim()) {{
            var encodedFragment = encodeURIComponent(textFragment);
            urlWithFragment = currentUrl + '#:~:text=' + encodedFragment;
        }}
        
        var citationText = '';
        if (textFragment && textFragment.trim()) {{
            citationText = '"' + textFragment + '" ';
        }}
        
        var tempDiv = document.createElement('div');
        tempDiv.appendChild(document.createTextNode(citationText));
        
        var link = document.createElement('a');
        link.href = urlWithFragment;
        link.textContent = pageTitle;
        tempDiv.appendChild(link);
        
        tempDiv.appendChild(document.createTextNode(' (last accessed ' + formattedDate + ').'));
        
        tempDiv.style.position = 'absolute';
        tempDiv.style.left = '-9999px';
        tempDiv.setAttribute('contenteditable', 'true');
        document.body.appendChild(tempDiv);
        
        var range = document.createRange();
        range.selectNodeContents(tempDiv);
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        
        var copySuccessful = document.execCommand('copy');
        document.body.removeChild(tempDiv);
        
        if (copySuccessful) {{
            showCopySuccessIndicator();
        }} else {{
            alert('Unable to copy to clipboard');
        }}
    }} catch (error) {{
        console.error('Error copying citation:', error);
        alert('Error copying citation: ' + error.message);
    }}
}}

function showCopySuccessIndicator() {{
    var indicator = document.createElement("div");
    indicator.textContent = "📋 Citation copied to clipboard";
    indicator.style.cssText = 'position: fixed; top: 50px; right: 20px; background: #4CAF50; color: white; padding: 10px 20px; border-radius: 5px; z-index: 2147483648; font-family: system-ui, -apple-system, sans-serif; font-size: 14px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); transition: all 0.3s ease;';
    
    document.body.appendChild(indicator);
    
    setTimeout(function() {{
        indicator.style.opacity = "0";
        setTimeout(function() {{ 
            if (indicator.parentNode) {{
                indicator.parentNode.removeChild(indicator); 
            }}
        }}, 300);
    }}, 3000);
}}

function toggleAnalytics() {{
    var section = document.getElementById('analytics-section');
    var overlay = document.getElementById('perma-overlay');
    if (!section || !overlay) return;
    analyticsExpanded = !analyticsExpanded;
    if (analyticsExpanded) {{
        // Position the analytics section right below the main overlay
        var overlayHeight = overlay.offsetHeight;
        section.style.top = overlayHeight + 'px';
        section.style.display = 'block';
        setTimeout(function() {{
            section.classList.add('active');
            // Update body padding to account for both overlay and analytics
            var totalHeight = overlay.offsetHeight + section.offsetHeight + 'px';
            document.body.style.setProperty('padding-top', totalHeight, 'important');
        }}, 10);
        renderAnalytics(analyticsData);
    }} else {{
        section.classList.remove('active');
        setTimeout(function() {{
            section.style.display = 'none';
            // Reset body padding to just the overlay height
            var height = overlay.offsetHeight + 'px';
            document.body.style.setProperty('padding-top', height, 'important');
        }}, 300);
    }}
}}

function renderAnalytics(data) {{
    renderLineChart(data.visits);
    renderPieChart(data.visits);
}}

function renderLineChart(visits) {{
    var chart = document.getElementById('visits-chart');
    if (!chart) return;
    
    if (!visits || visits.length === 0) {{
        chart.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #586e75;">No visit data</div>';
        return;
    }}

    // Group visits by date
    var visitsByDate = {{}};
    var dateFormat = new Intl.DateTimeFormat('en-US');
    
    visits.forEach(function(visit) {{
        var visitDate = new Date(visit.visited_at);
        var dateKey = visitDate.toISOString().split('T')[0]; // YYYY-MM-DD format
        visitsByDate[dateKey] = (visitsByDate[dateKey] || 0) + 1;
    }});

    var sortedDates = Object.keys(visitsByDate).sort();
    
    if (sortedDates.length === 0) {{
        chart.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #586e75;">No valid visit data</div>';
        return;
    }}

    if (sortedDates.length === 1) {{
        var visitCount = visitsByDate[sortedDates[0]];
        var displayDate = new Date(sortedDates[0]).toLocaleDateString();
        chart.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: ' + styleAccentColor + '; flex-direction: column; text-align: center;">' +
            '<div style="font-size: 24px; font-weight: bold; margin-bottom: 4px;">' + visitCount + '</div>' +
            '<div style="font-size: 10px; color: #586e75;">visits on</div>' +
            '<div style="font-size: 11px; color: #93a1a1;">' + displayDate + '</div>' +
            '</div>';
        return;
    }}

    // Fill in missing dates for smoother chart
    var startDate = new Date(sortedDates[0]);
    var endDate = new Date(sortedDates[sortedDates.length - 1]);
    var dayDiff = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
    
    // If more than 90 days, group by week instead of day
    var useWeekly = dayDiff > 90;
    var finalData = {{}};
    
    if (useWeekly) {{
        // Group by week
        Object.keys(visitsByDate).forEach(function(dateKey) {{
            var date = new Date(dateKey);
            var weekStart = new Date(date);
            weekStart.setDate(date.getDate() - date.getDay()); // Start of week (Sunday)
            var weekKey = weekStart.toISOString().split('T')[0];
            finalData[weekKey] = (finalData[weekKey] || 0) + visitsByDate[dateKey];
        }});
    }} else {{
        finalData = visitsByDate;
    }}

    var finalDates = Object.keys(finalData).sort();
    var maxVisits = Math.max.apply(Math, Object.values(finalData));

    var chartWidth = 280;
    var chartHeight = 60;
    var padding = 10;

    if (maxVisits === 0) {{
        chart.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #586e75;">No visits found</div>';
        return;
    }}

    var svg = '<svg width="' + chartWidth + '" height="' + chartHeight + '" viewBox="0 0 ' + chartWidth + ' ' + chartHeight + '">';
    
    // Grid lines
    for (var i = 0; i <= 4; i++) {{
        var y = padding + (i / 4) * (chartHeight - 2 * padding);
        svg += '<line x1="' + padding + '" y1="' + y + '" x2="' + (chartWidth - padding) + '" y2="' + y + '" stroke="#073642" stroke-width="1" opacity="0.3"/>';
    }}

    // Plot points
    var points = [];
    finalDates.forEach(function(date, index) {{
        var x = padding + (index / Math.max(1, finalDates.length - 1)) * (chartWidth - 2 * padding);
        var visitCount = finalData[date] || 0;
        var y = (chartHeight - padding) - ((visitCount / maxVisits) * (chartHeight - 2 * padding));
        points.push([x, y, visitCount]);
    }});

    // Draw area under curve
    if (points.length >= 2) {{
        var areaPath = 'M' + points[0][0] + ',' + (chartHeight - padding);
        points.forEach(function(point) {{
            areaPath += ' L' + point[0] + ',' + point[1];
        }});
        areaPath += ' L' + points[points.length - 1][0] + ',' + (chartHeight - padding) + ' Z';
        svg += '<path d="' + areaPath + '" fill="' + styleAccentColor + '" opacity="0.1"/>';
    }}

    // Draw line
    if (points.length >= 2) {{
        var linePath = 'M' + points[0][0] + ',' + points[0][1];
        for (var i = 1; i < points.length; i++) {{
            linePath += ' L' + points[i][0] + ',' + points[i][1];
        }}
        svg += '<path d="' + linePath + '" fill="none" stroke="' + styleAccentColor + '" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>';
    }}

    // Draw points with hover info
    points.forEach(function(point, index) {{
        var date = finalDates[index];
        var displayDate = new Date(date).toLocaleDateString();
        var visitCount = point[2];
                    svg += '<circle cx="' + point[0] + '" cy="' + point[1] + '" r="3" fill="' + styleAccentColor + '" stroke="' + styleBackgroundColor + '" stroke-width="1">';
        svg += '<title>' + displayDate + ': ' + visitCount + ' visit' + (visitCount !== 1 ? 's' : '') + '</title>';
        svg += '</circle>';
    }});

    // Y-axis labels
    for (var i = 0; i <= 2; i++) {{
        var labelValue = Math.round((maxVisits * (2 - i)) / 2);
        var y = padding + (i / 2) * (chartHeight - 2 * padding);
        svg += '<text x="' + (padding - 2) + '" y="' + (y + 3) + '" font-family="monospace" font-size="8" fill="#586e75" text-anchor="end">' + labelValue + '</text>';
    }}

    svg += '</svg>';
    
    var timeUnit = useWeekly ? 'weeks' : 'days';
    chart.innerHTML = svg + '<div style="text-align: center; font-size: 9px; color: #586e75; margin-top: 2px;">Time unit: ' + timeUnit + '</div>';
}}

function renderPieChart(visits) {{
    var countryList = document.getElementById('country-list');
    if (!countryList) return;
    var countries = {{}};
    visits.forEach(function(visit) {{
        if (visit.country) {{
            countries[visit.country] = (countries[visit.country] || 0) + 1;
        }}
    }});
    var sortedCountries = Object.keys(countries).map(function(country) {{
        return [country, countries[country]];
    }}).sort(function(a, b) {{
        return b[1] - a[1];
    }}).slice(0, 6);
    if (sortedCountries.length === 0) {{
        countryList.innerHTML = '<div style="color: #586e75;">No country data</div>';
        return;
    }}
    var totalVisits = sortedCountries.reduce(function(sum, item) {{ return sum + item[1]; }}, 0);
    var radius = 35;
    var centerX = 40;
    var centerY = 40;
    var colors = ['rgb(255, 225, 0)', 'rgb(255, 200, 0)', 'rgb(255, 175, 0)', 'rgb(255, 150, 0)', 'rgb(255, 125, 0)', 'rgb(255, 100, 0)'];
    var svg = '<svg width="80" height="80" viewBox="0 0 80 80">';
    var currentAngle = 0;
    sortedCountries.forEach(function(item, index) {{
        var country = item[0];
        var count = item[1];
        var percentage = (count / totalVisits) * 100;
        var sliceAngle = (count / totalVisits) * 2 * Math.PI;
        var x1 = centerX + radius * Math.cos(currentAngle);
        var y1 = centerY + radius * Math.sin(currentAngle);
        var x2 = centerX + radius * Math.cos(currentAngle + sliceAngle);
        var y2 = centerY + radius * Math.sin(currentAngle + sliceAngle);
        var largeArcFlag = sliceAngle > Math.PI ? 1 : 0;
        var pathData = [
            'M', centerX, centerY,
            'L', x1, y1,
            'A', radius, radius, 0, largeArcFlag, 1, x2, y2,
            'Z'
        ].join(' ');
        svg += '<path d="' + pathData + '" fill="' + colors[index % colors.length] + '"/>';
        currentAngle += sliceAngle;
    }});
    svg += '</svg>';
    var legendHtml = '';
    sortedCountries.forEach(function(item, index) {{
        var country = item[0];
        var count = item[1];
        var percentage = Math.round((count / totalVisits) * 100);
        legendHtml += '<div class="country-item" style="justify-content: flex-start; gap: 8px;">' +
            '<div style="width: 12px; height: 12px; background: ' + colors[index % colors.length] + '; border-radius: 2px; flex-shrink: 0;"></div>' +
            '<span style="flex: 1;">' + country + '</span>' +
            '<span style="color: #93a1a1;">' + count + ' (' + percentage + '%)</span>' +
            '</div>';
    }});
    countryList.innerHTML = '<div style="display: flex; gap: 15px; align-items: flex-start;">' +
        '<div style="flex-shrink: 0;">' + svg + '</div>' +
        '<div style="flex: 1; display: flex; flex-direction: column; gap: 3px;">' + legendHtml + '</div>' +
        '</div>';
}} 
```