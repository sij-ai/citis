# =============================================================================
# cit.is Environment Configuration Example
# =============================================================================
# Copy this file to .env and update with your own values
# NEVER commit .env to version control!

# =============================================================================
# CORE DJANGO SETTINGS
# =============================================================================

# Secret key for Django - generate a new one for production!
# Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=django-insecure-your-secret-key-here

# Debug mode - set to False in production
DEBUG=True

# Comma-separated list of allowed hosts
ALLOWED_HOSTS=localhost,127.0.0.1

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database URL - defaults to SQLite, use PostgreSQL in production
# Examples:
# - sqlite:///path/to/db.sqlite3
# - postgres://user:pass@localhost/dbname
DATABASE_URL=sqlite:///db.sqlite3

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

# Email backend - use 'django.core.mail.backends.smtp.EmailBackend' for production
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# SMTP Configuration (for production)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password

# Default email addresses
DEFAULT_FROM_EMAIL=noreply@localhost
SERVER_EMAIL=server@localhost

# =============================================================================
# STRIPE CONFIGURATION
# =============================================================================

# Stripe API keys (get from https://dashboard.stripe.com)
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key
STRIPE_SECRET_KEY=sk_test_your_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# =============================================================================
# CITIS-SPECIFIC SETTINGS
# =============================================================================

# Server Configuration
SERVER_BASE_URL=http://localhost:8000
SERVER_URL_PREFIX=
SERVER_REQUIRE_API_KEY=True
MASTER_API_KEY=your-master-api-key-here

# Master user configuration (for initial setup)
MASTER_USER_EMAIL=admin@example.com
MASTER_USER_PASSWORD=changeme123

# Site domain (used for email generation if DEFAULT_FROM_EMAIL not set)
SITE_DOMAIN=localhost

# Archive Configuration
ARCHIVE_MODE=singlefile
SHORTCODE_LENGTH=8
TIMEDIFF_WARNING_THRESHOLD=7200

# =============================================================================
# OVERLAY CONFIGURATION
# =============================================================================

# Overlay styling
OVERLAY_STYLE_BACKGROUND_COLOR=#000000
OVERLAY_STYLE_LINK_COLOR=#ffe100
OVERLAY_STYLE_ACCENT_COLOR=#ffe100
OVERLAY_STYLE_ICON=
OVERLAY_STYLE_COPY_GRAPHIC=📋
OVERLAY_SERVER_DOMAIN=

# =============================================================================
# ARCHIVEBOX CONFIGURATION (OPTIONAL)
# =============================================================================

# ArchiveBox integration
ARCHIVEBOX_EXPOSE_URL=False
ARCHIVEBOX_BASE_URL=
ARCHIVEBOX_DATA_PATH=

# =============================================================================
# SINGLEFILE CONFIGURATION
# =============================================================================

# SingleFile executable path and settings
SINGLEFILE_EXECUTABLE_PATH=single-file
SINGLEFILE_DATA_PATH=./archives
SINGLEFILE_TIMEOUT=60
SINGLEFILE_GENERATE_SCREENSHOT=False
SINGLEFILE_GENERATE_PDF=False
SINGLEFILE_SCREENSHOT_WIDTH=1920
SINGLEFILE_SCREENSHOT_HEIGHT=1080

# =============================================================================
# GEOLOCATION CONFIGURATION
# =============================================================================

# Path to GeoLite2 database file (optional, for analytics)
GEOLITE_DB_PATH=

# =============================================================================
# RESIDENTIAL PROXY CONFIGURATION
# =============================================================================

# Enable residential proxy support
RESIDENTIAL_PROXY_ENABLED=False
RESIDENTIAL_PROXY_PROVIDER=brightdata

# Bright Data proxy configuration
# For legacy auth: use your account username
# For zone auth: use format like 'brd-customer-c_12345678-zone-residential'
BRIGHTDATA_USERNAME=
# Your Brightdata password or zone password
BRIGHTDATA_PASSWORD=
BRIGHTDATA_ENDPOINT=brd.superproxy.io
BRIGHTDATA_PORT=22225

# Fallback proxy URL (leave empty to disable)
FALLBACK_PROXY_URL=

# Proxy selection strategy: closest, random, or specific country code
PROXY_SELECTION_STRATEGY=closest
PROXY_MAX_DISTANCE_KM=500

# =============================================================================
# CELERY & REDIS CONFIGURATION
# =============================================================================

# Redis URL for Celery broker and result backend
REDIS_URL=redis://localhost:6379/0 