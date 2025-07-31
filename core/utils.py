"""
Core utility functions for the citis Django application.

These utilities handle common tasks like text fragment processing,
caching, shortcode generation, and client IP extraction.
"""

import urllib.parse
import time
import random
import string
import re
from datetime import datetime
from typing import Optional, Dict, Any, Set


# Base58 character set (excludes I, l, 0, O for clarity)
BASE58_CHARSET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

# Reserved words that cannot be used as shortcodes
RESERVED_SHORTCODES = {
    # Web interface URLs
    'pricing', 'about', 'dashboard', 'shortcodes', 'create',
    # Authentication URLs
    'accounts', 'login', 'logout', 'signup', 'password',
    # API URLs (without underscores)
    'api', 'docs', 'schema', 'add', 'analytics', 'keys', 'cache', 'health', 'info',
    # Admin URLs
    'admin', 'staff',
    # Static/media URLs
    'static', 'media', 'favicon',
    # Common system words
    'www', 'mail', 'ftp', 'blog', 'shop', 'store', 'help', 'support',
    'contact', 'info', 'news', 'legal', 'privacy', 'terms', 'cookies',
    # Technical endpoints
    'health', 'status', 'robots', 'sitemap', 'manifest',
    # Potential future features
    'analytics', 'stats', 'export', 'import', 'backup', 'restore',
}


def is_valid_base58(text: str) -> bool:
    """Check if text contains only Base58 characters."""
    if not text:
        return False
    return all(c in BASE58_CHARSET for c in text)


def is_reserved_shortcode(shortcode: str) -> bool:
    """Check if shortcode is in the reserved words list."""
    return shortcode.lower() in RESERVED_SHORTCODES


def validate_shortcode_format(shortcode: str, min_length: int, is_admin: bool = False) -> tuple[bool, str]:
    """
    Validate shortcode format against requirements.
    
    Args:
        shortcode: The shortcode to validate
        min_length: Minimum required length based on user's plan
        is_admin: Whether the user is an admin (bypasses length restrictions)
    
    Returns (is_valid, error_message)
    """
    if not shortcode:
        return False, "Shortcode cannot be empty"
    
    # Admins can create shortcodes of any length
    if not is_admin:
        if len(shortcode) < min_length:
            return False, f"Shortcode must be at least {min_length} characters long for your plan"
    
    if not is_valid_base58(shortcode):
        return False, "Shortcode contains invalid characters. Only alphanumeric characters allowed (excluding I, l, 0, O)"
    
    if is_reserved_shortcode(shortcode):
        return False, f"'{shortcode}' is a reserved word and cannot be used as a shortcode"
    
    return True, ""


def validate_shortcode_collision(shortcode: str) -> tuple[bool, str]:
    """
    Check if shortcode collides with existing shortcodes.
    
    Returns (is_available, error_message)
    """
    # Import here to avoid circular imports
    from archive.models import Shortcode
    
    if Shortcode.objects.filter(shortcode=shortcode).exists():
        return False, f"Shortcode '{shortcode}' is already taken"
    
    return True, ""


def validate_shortcode(shortcode: str, min_length: int, is_admin: bool = False) -> tuple[bool, str]:
    """
    Complete shortcode validation including format and collision checks.
    
    Args:
        shortcode: The shortcode to validate
        min_length: Minimum required length based on user's plan  
        is_admin: Whether the user is an admin (bypasses length restrictions)
    
    Returns (is_valid, error_message)
    """
    # Check format first
    is_valid_format, format_error = validate_shortcode_format(shortcode, min_length, is_admin)
    if not is_valid_format:
        return False, format_error
    
    # Check for collisions
    is_available, collision_error = validate_shortcode_collision(shortcode)
    if not is_available:
        return False, collision_error
    
    return True, ""


def clean_text_fragment(text_fragment: str) -> str:
    """Clean and prepare text fragment for display"""
    if not text_fragment:
        return ""
    
    # Remove the text fragment prefix if present
    if text_fragment.startswith('#:~:text='):
        text_fragment = text_fragment[9:]
    
    # Properly URL decode the text
    decoded = urllib.parse.unquote(text_fragment)
    
    # Check if it meets minimum display requirements
    words = decoded.split()
    if len(decoded) < 15 and len(words) < 3:
        return ""  # Too short to display
    
    return decoded


class TTLCache:
    """Time-to-live cache with maximum entry limit"""
    
    def __init__(self, ttl_seconds: int, max_entries: int):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self.cache: Dict[str, tuple] = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry: 
                return value
            else: 
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        if len(self.cache) >= self.max_entries:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        self.cache[key] = (value, time.time() + self.ttl)
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)


def generate_shortcode(length: int) -> str:
    """Generate a random Base58 shortcode"""
    return ''.join(random.choice(BASE58_CHARSET) for _ in range(length))


def generate_unique_shortcode(length: int, max_attempts: int = 100) -> Optional[str]:
    """
    Generate a unique Base58 shortcode that doesn't collide with existing ones or reserved words.
    
    Returns None if unable to generate after max_attempts.
    """
    for _ in range(max_attempts):
        candidate = generate_shortcode(length)
        
        # Check if it's valid (not reserved and not taken)
        is_valid, _ = validate_shortcode(candidate, length)
        if is_valid:
            return candidate
    
    return None


def generate_api_key() -> str:
    """Generate a secure API key"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))


def parse_ts_str(ts_str: str) -> datetime:
    """Parse timestamp string to datetime"""
    from django.utils import timezone
    dt = datetime.strptime(ts_str, "%Y%m%d%H%M")
    return timezone.make_aware(dt)


def get_client_ip(request) -> Optional[str]:
    """
    Extract client IP from Django request - optimized for Cloudflare + Caddy setup
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        Client IP address as string or None if not found
    """
    # Cloudflare always sets this header with the real client IP
    cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
    if cf_ip:
        return cf_ip
    
    # Fallback to other headers (in case CF header is missing)
    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip
    
    # X-Forwarded-For as last resort
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    
    # Final fallback - Django's remote IP
    return request.META.get("REMOTE_ADDR") 