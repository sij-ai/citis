"""
Core utility functions for the citis Django application.

These utilities handle common tasks like text fragment processing,
caching, shortcode generation, and client IP extraction.
"""

import base64
import hashlib
from datetime import datetime
from typing import Optional, Any
import random
import re
import string
from urllib.parse import unquote
from django.utils import timezone
from django.conf import settings


def get_client_ip(request: Any) -> Optional[str]:
    """
    Get client IP from request, handling proxy headers.
    """
    # Check for X-Forwarded-For header
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # The header can contain a comma-separated list of IPs.
        # The client's IP is typically the first one.
        return x_forwarded_for.split(",")[0].strip()
    
    # Check for X-Real-IP header
    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()
    
    # Final fallback - Django's remote IP
    return request.META.get("REMOTE_ADDR")


def is_valid_base58(text: str) -> bool:
    """Check if a string is valid Base58."""
    # Base58 alphabet used by Flickr and others
    base58_chars = "123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
    return all(c in base58_chars for c in text)


def is_reserved_shortcode(text: str) -> bool:
    """Check if a shortcode is a reserved word."""
    # Common web paths to avoid conflicts
    reserved_words = {
        "admin", "api", "static", "media", "dashboard", "login", "logout",
        "signup", "pricing", "about", "contact", "terms", "privacy",
        "settings", "profile", "accounts", "billing", "docs", "help"
    }
    return text.lower() in reserved_words


def clean_text_fragment(text_fragment: Optional[str]) -> str:
    """Clean and validate a text fragment."""
    if not text_fragment:
        return ""
    
    # Remove URL fragment prefix if present
    if text_fragment.startswith('#:~:text='):
        text_fragment = text_fragment[9:]
    
    # URL decode
    decoded = unquote(text_fragment)
    
    # Basic sanitization
    # Remove potentially harmful characters, but allow common punctuation
    sanitized = re.sub(r'[^\w\s.,!?-]', '', decoded)
    
    return sanitized.strip()


def parse_ts_str(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse a timestamp string into a timezone-aware datetime object."""
    if not ts_str:
        return None
    try:
        # Handle Unix timestamps (integer or float)
        if ts_str.isdigit() or ('.' in ts_str and all(c.isdigit() or c == '.' for c in ts_str)):
            return datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
        
        # Handle ISO 8601 format
        # The 'Z' suffix is not always handled correctly, so we replace it
        if ts_str.endswith('Z'):
            ts_str = ts_str[:-1] + '+00:00'
        return datetime.fromisoformat(ts_str)
    
    except (ValueError, TypeError):
        return None


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))


def generate_shortcode(length: int) -> str:
    """Generate a random shortcode of a given length."""
    # Base58 alphabet is human-readable and avoids ambiguous characters
    charset = "123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
    return ''.join(random.choice(charset) for _ in range(length))


def generate_unique_shortcode(length: int, max_attempts: int = 10) -> Optional[str]:
    """
    Generate a unique shortcode that doesn't already exist in the database.
    
    Returns the unique shortcode, or None if it fails after max_attempts.
    """
    from archive.models import Shortcode # Local import to avoid circular dependency
    
    for _ in range(max_attempts):
        candidate = generate_shortcode(length)
        if not Shortcode.objects.filter(pk=candidate).exists():
            return candidate
    
    return None # Failed to generate a unique shortcode


def validate_shortcode(shortcode: str, required_length: int) -> tuple[bool, str]:
    """
    Validate a custom shortcode against all business rules.
    """
    if len(shortcode) != required_length:
        return False, f"Shortcode must be exactly {required_length} characters long."
    
    if not is_valid_base58(shortcode):
        return False, "Shortcode contains invalid characters. Please use only alphanumeric characters, excluding 0, O, I, and l."
        
    if is_reserved_shortcode(shortcode):
        return False, f"'{shortcode}' is a reserved word and cannot be used."
    
    return True, ""


def url_to_safe_filename(url: str) -> str:
    """
    Converts a URL to a string that is safe for use as a filename.
    
    Replaces non-alphanumeric characters with underscores and ensures the
    filename is not excessively long.
    """
    # Remove protocol and www
    url = re.sub(r'^https?:\/\/(www\.)?', '', url)
    
    # Replace invalid filename characters with underscores
    safe_name = re.sub(r'[^a-zA-Z0-9\.\-]', '_', url)
    
    # Truncate to a reasonable length
    return safe_name[:100]


def generate_csrf_token() -> str:
    """
    Generate a secure, URL-safe CSRF token.
    """
    # 32 bytes of randomness is recommended for CSRF tokens
    token_bytes = os.urandom(32)
    # Base64 encode and make it URL-safe
    token = base64.urlsafe_b64encode(token_bytes).decode('utf-8')
    # The result may have padding '=' characters, which we can remove
    return token.rstrip("=") 