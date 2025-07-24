"""
Core archive models for the citis application.

These models handle the main functionality of web archiving, shortcode management,
and visit tracking.
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, List, Dict, Any
import string
import random
import hashlib
import json


User = get_user_model()


class ApiKey(models.Model):
    """
    API keys for programmatic access to the citis service.
    
    Each API key belongs to a user and has usage limits.
    """
    
    # API key is the primary identifier
    key = models.CharField(
        max_length=64,
        primary_key=True,
        help_text="The actual API key string"
    )
    
    # Link to user who owns this API key
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys',
        help_text="User who owns this API key"
    )
    
    # Key metadata
    name = models.CharField(
        max_length=100,
        help_text="Human-readable name for this API key"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Optional description of what this key is used for"
    )
    
    # Usage limits
    max_uses_total = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum total uses for this API key (null = unlimited)"
    )
    
    max_uses_per_day = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum daily uses for this API key (null = unlimited)"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this API key is currently active"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this API key was created"
    )
    
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this API key was last used"
    )
    
    class Meta:
        db_table = 'archive_apikey'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} ({self.key[:8]}...)"
    
    @classmethod
    def generate_key(cls):
        """Generate a secure random API key."""
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    def get_total_uses(self):
        """Get total number of shortcodes created with this API key."""
        return self.shortcodes.count()
    
    def get_daily_uses(self):
        """Get number of shortcodes created today with this API key."""
        today = timezone.now().date()
        return self.shortcodes.filter(created_at__date=today).count()
    
    def can_create_shortcode(self):
        """Check if this API key can create another shortcode."""
        if not self.is_active:
            return False
        
        # Check total limit
        if self.max_uses_total is not None:
            if self.get_total_uses() >= self.max_uses_total:
                return False
        
        # Check daily limit
        if self.max_uses_per_day is not None:
            if self.get_daily_uses() >= self.max_uses_per_day:
                return False
        
        return True
    
    def update_last_used(self):
        """Update the last_used timestamp."""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])


class Shortcode(models.Model):
    """
    A shortcode that redirects to a specific URL with archiving.
    
    This is the core model of the citis application.
    """
    
    ARCHIVE_METHOD_CHOICES = [
        ('archivebox', 'ArchiveBox'),
        ('singlefile', 'SingleFile'),
        ('both', 'Both Methods'),
    ]
    
    # Shortcode is the primary identifier
    shortcode = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="The short identifier for this URL"
    )
    
    # Target URL
    url = models.URLField(
        max_length=2000,
        help_text="The URL this shortcode redirects to"
    )
    
    # Creation metadata
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this shortcode was created"
    )
    
    # Creator information
    creator_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shortcodes',
        help_text="User who created this shortcode"
    )
    
    creator_api_key = models.ForeignKey(
        ApiKey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shortcodes',
        help_text="API key used to create this shortcode"
    )
    
    creator_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the creator"
    )
    
    # Text fragment for highlighting
    text_fragment = models.TextField(
        blank=True,
        help_text="Text fragment to highlight in the archived page"
    )
    
    # Archiving method
    archive_method = models.CharField(
        max_length=20,
        choices=ARCHIVE_METHOD_CHOICES,
        default='singlefile',
        help_text="Method used to archive this URL"
    )
    
    # Archive status and path are determined dynamically from filesystem
    
    # Proxy metadata
    proxy_ip = models.GenericIPAddressField(
        null=True, blank=True,
        help_text="IP address of proxy used for archiving"
    )
    
    proxy_country = models.CharField(
        max_length=100, blank=True,
        help_text="Country of proxy used for archiving"
    )
    
    proxy_provider = models.CharField(
        max_length=100, blank=True,
        help_text="Proxy provider used for archiving"
    )
    
    # Trust and verification metadata
    archive_checksum = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 checksum of archived content for integrity verification"
    )
    
    archive_size_bytes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Size of archived content in bytes"
    )
    
    trust_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Trusted timestamp for professional/sovereign plans"
    )
    
    trust_certificate = models.TextField(
        blank=True,
        help_text="Digital certificate or timestamp token for verification"
    )
    
    trust_metadata = models.JSONField(
        default=dict,
        help_text="Additional trust verification metadata (TSA, chain-of-custody, etc.)"
    )
    
    class Meta:
        db_table = 'archive_shortcode'
        verbose_name = 'Shortcode'
        verbose_name_plural = 'Shortcodes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['creator_user']),
            models.Index(fields=['creator_api_key']),
        ]
        
    def __str__(self):
        return f"{self.shortcode} → {self.url}"
    
    @classmethod
    def generate_shortcode(cls, length=6):
        """Generate a unique shortcode."""
        charset = string.ascii_letters + string.digits
        max_attempts = 10
        
        for _ in range(max_attempts):
            candidate = ''.join(random.choice(charset) for _ in range(length))
            if not cls.objects.filter(shortcode=candidate).exists():
                return candidate
        
        raise ValueError("Could not generate unique shortcode")
    
    def get_absolute_url(self):
        """Get the URL for this shortcode."""
        return reverse('shortcode_redirect', kwargs={'shortcode': self.shortcode})
    
    def get_visits_count(self):
        """Get the total number of visits to this shortcode."""
        return self.visits.count()
    
    def get_recent_visits(self, days=30):
        """Get visits from the last N days."""
        cutoff = timezone.now() - timedelta(days=days)
        return self.visits.filter(visited_at__gte=cutoff)
    
    def get_top_countries(self, limit=10):
        """Get the top countries by visit count."""
        from django.db.models import Count
        return (
            self.visits.exclude(country__isnull=True)
            .exclude(country='')
            .values('country')
            .annotate(count=Count('id'))
            .order_by('-count')[:limit]
        )
    
    # Filesystem-based archive checking methods
    def _url_to_base62_hash(self) -> str:
        """Convert URL to base62 hash (same as migrate_archive.py)"""
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        hash_bytes = hashlib.sha256(self.url.encode('utf-8')).digest()
        hash_int = int.from_bytes(hash_bytes[:8], byteorder='big')
        
        if hash_int == 0:
            return alphabet[0]
        
        result = ""
        while hash_int > 0:
            result = alphabet[hash_int % 62] + result
            hash_int //= 62
        return result
    
    def _get_archive_base_path(self) -> Path:
        """Get the base archive path from settings"""
        data_path = Path(settings.SINGLEFILE_DATA_PATH)
        if data_path.is_absolute():
            return data_path
        else:
            # Resolve relative to project root
            return Path(settings.BASE_DIR) / data_path
    
    def _get_archive_paths_for_url(self) -> List[Path]:
        """Get all possible archive paths for this URL"""
        parsed_url = urlparse(self.url)
        domain = parsed_url.netloc.lower()
        url_hash = self._url_to_base62_hash()
        
        archive_base_path = self._get_archive_base_path()
        domain_path = archive_base_path / domain / url_hash
        
        if not domain_path.exists():
            return []
        
        archive_paths = []
        for year_dir in domain_path.iterdir():
            if not year_dir.is_dir():
                continue
            
            for mmdd_dir in year_dir.iterdir():
                if not mmdd_dir.is_dir():
                    continue
                
                for hhmmss_dir in mmdd_dir.iterdir():
                    if not hhmmss_dir.is_dir():
                        continue
                    
                    singlefile_path = hhmmss_dir / "singlefile.html"
                    if singlefile_path.exists():
                        archive_paths.append(hhmmss_dir)
        
        # Sort by timestamp (newest first)
        archive_paths.sort(key=lambda p: p.name, reverse=True)
        return archive_paths
    
    def get_latest_archive_path(self) -> Optional[Path]:
        """Get the path to the most recent archive for this URL"""
        archive_paths = self._get_archive_paths_for_url()
        return archive_paths[0] if archive_paths else None
    
    def is_archived(self) -> bool:
        """Check if this URL has been successfully archived"""
        return self.get_latest_archive_path() is not None
    
    def get_archive_path(self) -> Optional[str]:
        """Get the path to the archived content (for compatibility)"""
        latest_path = self.get_latest_archive_path()
        return str(latest_path) if latest_path else None
    
    def find_archives_for_url(self) -> List[Dict[str, Any]]:
        """Find all archives for this URL with metadata"""
        archive_paths = self._get_archive_paths_for_url()
        archives = []
        
        for archive_path in archive_paths:
            try:
                # Extract timestamp from path structure: year/mmdd/hhmmss
                path_parts = archive_path.parts
                year = path_parts[-3]
                mmdd = path_parts[-2]
                hhmmss = path_parts[-1]
                
                timestamp_str = f"{year}{mmdd}{hhmmss}"
                timestamp_dt = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                timestamp_dt = timezone.make_aware(timestamp_dt)
                
                archives.append({
                    "timestamp": str(int(timestamp_dt.timestamp())),
                    "url": self.url,
                    "archive_path": str(archive_path),
                    "archive_method": self.archive_method
                })
            except Exception:
                # Skip malformed paths
                continue
        
        return sorted(archives, key=lambda x: float(x["timestamp"]), reverse=True)
    
    def get_proxy_metadata(self) -> Dict[str, Any]:
        """Get proxy metadata from filesystem or database"""
        # First try to load from JSON file
        archive_path = self.get_latest_archive_path()
        if archive_path:
            metadata_path = archive_path / "proxy_metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        return json.load(f)
                except Exception:
                    pass
        
        # Fallback to database fields
        if self.proxy_ip:
            return {
                'proxy_ip': self.proxy_ip,
                'proxy_country': self.proxy_country,
                'proxy_provider': self.proxy_provider,
                'proxy_configured': True
            }
        
        return {'proxy_configured': False}
    
    def clean_text_fragment(self):
        """Clean and validate the text fragment."""
        if not self.text_fragment:
            return ""
        
        # Remove URL fragment prefix if present
        if self.text_fragment.startswith('#:~:text='):
            self.text_fragment = self.text_fragment[9:]
        
        # URL decode
        from urllib.parse import unquote
        decoded = unquote(self.text_fragment)
        
        # Check minimum length
        words = decoded.split()
        if len(decoded) < 15 and len(words) < 3:
            return ""
        
        return decoded
    
    def save(self, *args, **kwargs):
        """Override save to clean text fragment."""
        if self.text_fragment:
            self.text_fragment = self.clean_text_fragment()
        super().save(*args, **kwargs)


class Visit(models.Model):
    """
    A visit/access to a shortcode.
    
    Tracks analytics data for each time a shortcode is accessed.
    """
    
    # Link to the shortcode that was visited
    shortcode = models.ForeignKey(
        Shortcode,
        on_delete=models.CASCADE,
        related_name='visits',
        help_text="The shortcode that was visited"
    )
    
    # Visit timestamp
    visited_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this visit occurred"
    )
    
    # Client information
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the visitor"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string of the visitor's browser"
    )
    
    referer = models.URLField(
        max_length=2000,
        blank=True,
        help_text="Referer URL (where the visitor came from)"
    )
    
    # Geolocation (populated from IP)
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Country of the visitor (derived from IP)"
    )
    
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text="City of the visitor (derived from IP)"
    )
    
    class Meta:
        db_table = 'archive_visit'
        verbose_name = 'Visit'
        verbose_name_plural = 'Visits'
        ordering = ['-visited_at']
        indexes = [
            models.Index(fields=['shortcode', 'visited_at']),
            models.Index(fields=['visited_at']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        return f"Visit to {self.shortcode.shortcode} at {self.visited_at}"
    
    def get_browser_info(self):
        """Extract browser information from user agent."""
        # This is a simplified version - in production you'd use a proper user agent parser
        if not self.user_agent:
            return "Unknown"
        
        ua = self.user_agent.lower()
        if 'chrome' in ua:
            return 'Chrome'
        elif 'firefox' in ua:
            return 'Firefox'
        elif 'safari' in ua:
            return 'Safari'
        elif 'edge' in ua:
            return 'Edge'
        else:
            return 'Other'
    
    def get_platform_info(self):
        """Extract platform information from user agent."""
        if not self.user_agent:
            return "Unknown"
        
        ua = self.user_agent.lower()
        if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
            return 'Mobile'
        elif 'tablet' in ua or 'ipad' in ua:
            return 'Tablet'
        else:
            return 'Desktop'
    
    def update_geolocation(self):
        """Update country and city from IP address."""
        if not self.ip_address:
            return
        
        # Import here to avoid circular imports
        try:
            from core.services import get_country_from_ip
            self.country = get_country_from_ip(self.ip_address)
            self.save(update_fields=['country'])
        except ImportError:
            # GeoIP service not available
            pass


class HealthCheck(models.Model):
    """
    Health monitoring and content integrity check results.
    
    Tracks the results of periodic health checks and content integrity scans
    for shortcodes based on user plan tier.
    """
    
    CHECK_TYPE_CHOICES = [
        ('link_health', 'Link Health Check'),
        ('content_integrity', 'Content Integrity Scan'),
    ]
    
    STATUS_CHOICES = [
        ('ok', 'OK'),
        ('broken', 'Broken'),
        ('minor_changes', 'Minor Changes'),
        ('major_changes', 'Major Changes'),
    ]
    
    # Link to the shortcode being monitored
    shortcode = models.ForeignKey(
        Shortcode,
        on_delete=models.CASCADE,
        related_name='health_checks',
        help_text="The shortcode that was checked"
    )
    
    # Type of check performed
    check_type = models.CharField(
        max_length=20,
        choices=CHECK_TYPE_CHOICES,
        help_text="Type of health check performed"
    )
    
    # Status result
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        help_text="Result status of the health check"
    )
    
    # Detailed results
    details = models.JSONField(
        default=dict,
        help_text="Detailed check results and metadata"
    )
    
    # When the check was performed
    checked_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this health check was performed"
    )
    
    class Meta:
        db_table = 'archive_healthcheck'
        verbose_name = 'Health Check'
        verbose_name_plural = 'Health Checks'
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['shortcode', 'check_type', 'checked_at']),
            models.Index(fields=['check_type', 'status']),
            models.Index(fields=['checked_at']),
        ]
    
    def __str__(self):
        return f"{self.get_check_type_display()} for {self.shortcode.shortcode}: {self.get_status_display()}"
    
    def is_healthy(self):
        """Check if the health check result indicates a healthy status."""
        return self.status == 'ok'
    
    def has_changes(self):
        """Check if content integrity scan detected changes."""
        return self.status in ['minor_changes', 'major_changes']
    
    def get_similarity_ratio(self):
        """Get similarity ratio for content integrity scans."""
        if self.check_type == 'content_integrity' and 'similarity_ratio' in self.details:
            return self.details['similarity_ratio']
        return None
