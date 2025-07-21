# Residential Proxy Configuration

This guide shows how to configure cit.is with residential proxy support for location-aware web archiving.

## Overview

When enabled, cit.is will automatically select residential proxies near the requester's location, providing more geographically accurate web archives. This is particularly useful for:

- Capturing region-specific content
- Bypassing geo-blocking
- More accurate archiving of location-sensitive websites
- Compliance with data locality requirements

## Configuration

### 1. Basic Setup

Add these settings to your `.env` file:

```bash
# Enable residential proxy functionality
RESIDENTIAL_PROXY_ENABLED=True

# Choose your proxy provider
RESIDENTIAL_PROXY_PROVIDER=brightdata  # brightdata, smartproxy, or custom

# GeoIP database for location detection (required)
GEOLITE_DB_PATH=/path/to/GeoLite2-City.mmdb
```

### 2. Bright Data Configuration

Sign up at [Bright Data](https://brightdata.com/) and add:

```bash
BRIGHTDATA_USERNAME=your_brightdata_username
BRIGHTDATA_PASSWORD=your_brightdata_password
BRIGHTDATA_ENDPOINT=brd.superproxy.io
BRIGHTDATA_PORT=22225
```

### 3. Fallback Configuration

Set a fallback proxy for when location-specific proxies fail:

```bash
# Format: http://username:password@proxy-server:port
FALLBACK_PROXY_URL=http://user:pass@fallback-proxy.example.com:8080
```

### 4. Proxy Selection Strategy

```bash
# How to choose which proxy to use
PROXY_SELECTION_STRATEGY=closest  # closest, country_match, random

# Maximum distance in kilometers for "closest" strategy
PROXY_MAX_DISTANCE_KM=500
```

## GeoIP Database Setup

Download the MaxMind GeoLite2 database:

```bash
# Register at https://dev.maxmind.com/geoip/accounts/current/license-key
# Then download:
wget -O GeoLite2-City.tar.gz "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=YOUR_LICENSE_KEY&suffix=tar.gz"
tar -xzf GeoLite2-City.tar.gz
mv GeoLite2-City_*/GeoLite2-City.mmdb /opt/geoip/
```

Update your `.env`:
```bash
GEOLITE_DB_PATH=/opt/geoip/GeoLite2-City.mmdb
```

## Testing Proxy Configuration

Test your proxy setup:

```bash
python manage.py shell
```

```python
from core.proxy_manager import ProxyManager

# Initialize proxy manager
pm = ProxyManager()

# Test with a known IP (Google's DNS)
proxy = pm.get_optimal_proxy('8.8.8.8')

if proxy:
    print(f"Proxy: {proxy.server} in {proxy.country_code}")
    print(f"Provider: {proxy.provider}")
    
    # Test if proxy is working
    success = pm.test_proxy(proxy)
    print(f"Test result: {'✓ Working' if success else '✗ Failed'}")
else:
    print("No proxy configured or available")
```

## How It Works

1. **Request Arrives**: User creates archive via API/web interface
2. **Location Detection**: System determines requester's location from IP using GeoIP
3. **Proxy Selection**: Chooses optimal residential proxy near requester
4. **Archive Creation**: SingleFile uses proxy to archive the URL
5. **Metadata Storage**: Proxy information saved with archive

## Proxy Metadata

Each archive stores proxy metadata in two places:

1. **JSON File**: `{archive_path}/proxy_metadata.json`
```json
{
  "proxy_server": "brd.superproxy.io:22225",
  "proxy_country": "US",
  "proxy_city": "New York",
  "proxy_lat": 40.7128,
  "proxy_lon": -74.0060,
  "proxy_provider": "brightdata",
  "proxy_ip": "192.168.1.100",
  "proxy_configured": true
}
```

2. **Database Fields**: On the `Shortcode` model
   - `proxy_ip`: IP address used for archiving
   - `proxy_country`: Country code of proxy
   - `proxy_provider`: Provider name

## Admin Interface

The Django admin shows proxy information:

- **List View**: Proxy country and provider
- **Detail View**: Full proxy metadata
- **Filtering**: By proxy provider and country

## Failsafe Behavior

The system is designed to always work, even if proxy configuration fails:

1. **Proxy Disabled**: Archives directly without proxy
2. **Proxy Config Invalid**: Falls back to direct connection
3. **Proxy Unreachable**: Uses fallback proxy or direct
4. **GeoIP Unavailable**: Uses fallback proxy or direct

## Complete Example Configuration

```bash
# Core Settings
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:pass@localhost/citis
REDIS_URL=redis://localhost:6379/0

# Server
SERVER_BASE_URL=https://yourdomain.com
MASTER_API_KEY=your-master-api-key

# Archive
ARCHIVE_MODE=singlefile
SINGLEFILE_EXECUTABLE_PATH=/usr/local/bin/single-file
SINGLEFILE_DATA_PATH=./archives

# Proxy Configuration
RESIDENTIAL_PROXY_ENABLED=True
RESIDENTIAL_PROXY_PROVIDER=brightdata
BRIGHTDATA_USERNAME=your_username
BRIGHTDATA_PASSWORD=your_password
GEOLITE_DB_PATH=/opt/geoip/GeoLite2-City.mmdb
FALLBACK_PROXY_URL=http://user:pass@backup-proxy.com:8080
```

## Performance Considerations

- **Proxy Selection**: Cached for 5 minutes per IP
- **GeoIP Lookups**: Minimal overhead (~1ms)
- **Proxy Testing**: Only when explicitly requested
- **Failover**: Automatic with <1s delay

## Security Notes

- Proxy credentials never logged
- IP addresses stored according to privacy settings
- Proxy metadata can be disabled if not needed
- All connections use HTTPS where possible

## Troubleshooting

### Common Issues

1. **"Proxy not configured"**
   - Check `RESIDENTIAL_PROXY_ENABLED=True`
   - Verify provider credentials

2. **"GeoIP lookup failed"**
   - Ensure GeoLite2 database exists at `GEOLITE_DB_PATH`
   - Check file permissions

3. **"Proxy test failed"**
   - Verify proxy credentials
   - Check network connectivity
   - Try fallback proxy

### Debug Logging

Enable detailed proxy logging:

```bash
# In settings.py or .env
LOG_LEVEL=DEBUG
```

Check logs for proxy-related messages:
```bash
tail -f logs/citis.log | grep -i proxy
``` 