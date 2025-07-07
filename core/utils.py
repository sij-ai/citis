"""
Core utility functions for the citis Django application.

These utilities handle common tasks like text fragment processing,
caching, shortcode generation, and client IP extraction.
"""

import urllib.parse
import time
import random
import string
from datetime import datetime, timezone
from typing import Optional, Dict, Any


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
    """Generate a random Base-62 shortcode"""
    charset = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return ''.join(random.choice(charset) for _ in range(length))


def generate_api_key() -> str:
    """Generate a secure API key"""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))


def parse_ts_str(ts_str: str) -> datetime:
    """Parse timestamp string to datetime"""
    return datetime.strptime(ts_str, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)


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