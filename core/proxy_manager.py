"""
Residential proxy management for location-aware web archiving.
Uses SingleFile's native proxy CLI options.
"""

import logging
import requests
import json
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from django.conf import settings
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Try to import GeoIP2 with graceful fallback
try:
    import geoip2.database
    import geoip2.errors
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False
    logger.info("GeoIP2 not available - proxy location detection disabled")


@dataclass
class ProxyConfig:
    """Proxy configuration for SingleFile with native CLI options"""
    server: str  # For --http-proxy-server
    username: Optional[str] = None  # For --http-proxy-username
    password: Optional[str] = None  # For --http-proxy-password
    country_code: str = ''
    city: str = ''
    lat: float = 0.0
    lon: float = 0.0
    provider: str = ''
    
    def to_singlefile_args(self) -> list:
        """Convert to SingleFile CLI arguments"""
        args = ['--http-proxy-server', self.server]
        if self.username:
            args.extend(['--http-proxy-username', self.username])
        if self.password:
            args.extend(['--http-proxy-password', self.password])
        return args
    
    def get_proxy_ip(self) -> Optional[str]:
        """Get the actual IP address of this proxy"""
        try:
            # Build proxy URL for requests
            if self.username and self.password:
                proxy_url = f'http://{self.username}:{self.password}@{self.server}'
            else:
                proxy_url = f'http://{self.server}'
                
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('origin')
        except Exception as e:
            logger.debug(f"Could not determine proxy IP: {e}")
        return None
    
    def to_metadata(self) -> Dict[str, Any]:
        """Convert to metadata dictionary for storage"""
        proxy_ip = self.get_proxy_ip()
        return {
            'proxy_server': self.server,
            'proxy_country': self.country_code,
            'proxy_city': self.city,
            'proxy_lat': self.lat,
            'proxy_lon': self.lon,
            'proxy_provider': self.provider,
            'proxy_ip': proxy_ip,
            'proxy_configured': True
        }


class ProxyManager:
    """Manages residential proxy selection based on requester location"""
    
    def __init__(self):
        self.geoip_reader = self._init_geoip_reader() if GEOIP2_AVAILABLE else None
        self.proxy_enabled = self._check_proxy_configuration()
        
    def _check_proxy_configuration(self) -> bool:
        """Check if proxy functionality is properly configured"""
        if not getattr(settings, 'RESIDENTIAL_PROXY_ENABLED', False):
            logger.debug("Residential proxy disabled in settings")
            return False
            
        provider = getattr(settings, 'RESIDENTIAL_PROXY_PROVIDER', '').lower()
        
        if provider == 'brightdata':
            if not all([
                getattr(settings, 'BRIGHTDATA_USERNAME', ''),
                getattr(settings, 'BRIGHTDATA_PASSWORD', ''),
                getattr(settings, 'BRIGHTDATA_ENDPOINT', ''),
                getattr(settings, 'BRIGHTDATA_PORT', 0)
            ]):
                logger.warning("Bright Data proxy configured but missing credentials")
                return False
                
        elif provider == 'smartproxy':
            # Add SmartProxy validation when implemented
            pass
            
        elif provider and not getattr(settings, 'FALLBACK_PROXY_URL', ''):
            logger.warning(f"Unknown proxy provider '{provider}' and no fallback configured")
            return False
            
        return True
        
    def _init_geoip_reader(self):
        """Initialize GeoIP2 reader if available"""
        if not GEOIP2_AVAILABLE:
            return None
            
        geolite_path = getattr(settings, 'GEOLITE_DB_PATH', '')
        if not geolite_path:
            logger.debug("GEOLITE_DB_PATH not configured")
            return None
            
        try:
            return geoip2.database.Reader(geolite_path)
        except Exception as e:
            logger.warning(f"Could not initialize GeoIP reader: {e}")
            return None
    
    def get_location_from_ip(self, ip_address: str) -> Optional[Tuple[str, str, float, float]]:
        """Get country, city, lat, lon from IP address"""
        if not self.geoip_reader or not ip_address:
            return None
            
        try:
            response = self.geoip_reader.city(ip_address)
            return (
                response.country.iso_code or '',
                response.city.name or '',
                float(response.location.latitude or 0),
                float(response.location.longitude or 0)
            )
        except geoip2.errors.AddressNotFoundError:
            logger.debug(f"Location not found for IP: {ip_address}")
            return None
        except Exception as e:
            logger.debug(f"GeoIP lookup failed for {ip_address}: {e}")
            return None
    
    def get_optimal_proxy(self, requester_ip: Optional[str]) -> Optional[ProxyConfig]:
        """Get the optimal proxy based on requester location"""
        # Early return if proxy not configured
        if not self.proxy_enabled:
            logger.debug("Proxy not configured or disabled")
            return None
            
        if not requester_ip:
            logger.debug("No requester IP provided, trying fallback proxy")
            return self._get_fallback_proxy()
        
        # Get requester location
        location = self.get_location_from_ip(requester_ip)
        if not location:
            logger.debug(f"Could not determine location for IP: {requester_ip}, trying fallback")
            return self._get_fallback_proxy()
        
        country_code, city, lat, lon = location
        logger.info(f"Requester location: {country_code} ({city})")
        
        # Get proxy based on provider
        provider = getattr(settings, 'RESIDENTIAL_PROXY_PROVIDER', '').lower()
        
        if provider == 'brightdata':
            proxy_config = self._get_brightdata_proxy(country_code, city, lat, lon)
        elif provider == 'smartproxy':
            proxy_config = self._get_smartproxy_proxy(country_code, city, lat, lon)
        else:
            logger.debug(f"Unknown provider '{provider}', trying fallback")
            proxy_config = self._get_fallback_proxy()
            
        if proxy_config:
            logger.info(f"Selected proxy: {proxy_config.provider} in {proxy_config.country_code}")
        else:
            logger.debug("No proxy configuration available")
            
        return proxy_config
    
    def _get_brightdata_proxy(self, country_code: str, city: str, lat: float, lon: float) -> Optional[ProxyConfig]:
        """Get Bright Data proxy for the specified location"""
        username = getattr(settings, 'BRIGHTDATA_USERNAME', '')
        password = getattr(settings, 'BRIGHTDATA_PASSWORD', '')
        endpoint = getattr(settings, 'BRIGHTDATA_ENDPOINT', '')
        port = getattr(settings, 'BRIGHTDATA_PORT', 0)
        
        if not all([username, password, endpoint, port]):
            logger.warning("Bright Data credentials incomplete")
            return self._get_fallback_proxy()
        
        # Bright Data session with country targeting
        session_username = f"{username}-country-{country_code.lower()}"
        
        return ProxyConfig(
            server=f"{endpoint}:{port}",
            username=session_username,
            password=password,
            country_code=country_code,
            city=city,
            lat=lat,
            lon=lon,
            provider='brightdata'
        )
    
    def _get_smartproxy_proxy(self, country_code: str, city: str, lat: float, lon: float) -> Optional[ProxyConfig]:
        """Get SmartProxy proxy for the specified location"""
        # TODO: Implement SmartProxy configuration
        logger.info("SmartProxy not yet implemented, using fallback")
        return self._get_fallback_proxy()
    
    def _get_fallback_proxy(self) -> Optional[ProxyConfig]:
        """Get fallback proxy configuration"""
        fallback_url = getattr(settings, 'FALLBACK_PROXY_URL', '')
        if not fallback_url:
            logger.debug("No fallback proxy configured")
            return None
            
        try:
            parsed = urlparse(fallback_url)
            if not parsed.hostname or not parsed.port:
                logger.warning(f"Invalid fallback proxy URL: {fallback_url}")
                return None
                
            return ProxyConfig(
                server=f"{parsed.hostname}:{parsed.port}",
                username=parsed.username,
                password=parsed.password,
                provider='fallback'
            )
        except Exception as e:
            logger.warning(f"Error parsing fallback proxy URL: {e}")
            return None
    
    def test_proxy(self, proxy_config: ProxyConfig) -> bool:
        """Test if a proxy is working"""
        try:
            # Build proxy URL for requests
            if proxy_config.username and proxy_config.password:
                proxy_url = f'http://{proxy_config.username}:{proxy_config.password}@{proxy_config.server}'
            else:
                proxy_url = f'http://{proxy_config.server}'
                
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=proxies,
                timeout=10
            )
            
            success = response.status_code == 200
            if success:
                logger.info(f"Proxy test successful: {proxy_config.provider}")
            else:
                logger.warning(f"Proxy test failed: {response.status_code}")
            return success
            
        except Exception as e:
            logger.warning(f"Proxy test failed for {proxy_config.provider}: {e}")
            return False 