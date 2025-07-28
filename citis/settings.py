"""
Django settings for citis project.

This configuration supports both development and production environments.
Sensitive settings are loaded from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Ensure the logs directory exists
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)


# =============================================================================
# CORE DJANGO SETTINGS
# =============================================================================

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-development-key')
DEBUG = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'crispy_forms',
    'crispy_tailwind',
    'django_htmx',
    'djstripe',
    'django_celery_beat',
    'django_celery_results',
]

LOCAL_APPS = [
    'core',
    'accounts',
    'archive',
    'analytics',
    'web',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'citis.urls'


# =============================================================================
# TEMPLATE CONFIGURATION
# =============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'citis.wsgi.application'


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Determine database type and construct URL dynamically
DB_TYPE = os.getenv('DB_TYPE', 'sqlite').lower()

if DB_TYPE in ['postgres', 'postgresql']:
    # PostgreSQL configuration
    PG_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    PG_PORT = os.getenv('POSTGRES_PORT', '5433')  # Use 5433 to avoid conflict with system PostgreSQL
    PG_DB = os.getenv('POSTGRES_DB', 'citis')
    PG_USER = os.getenv('POSTGRES_USER', 'citis')
    PG_PASS = os.getenv('POSTGRES_PASSWORD', '')
    
    DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
else:
    # SQLite configuration (default)
    SQLITE_PATH = os.getenv('SQLITE_PATH', str(BASE_DIR / 'db.sqlite3'))
    DATABASE_URL = f"sqlite:///{SQLITE_PATH}"

# Use dj-database-url to parse the constructed URL
DATABASES = {'default': dj_database_url.config(default=DATABASE_URL)}

# =============================================================================
# AUTHENTICATION & USER MODEL
# =============================================================================

AUTH_USER_MODEL = 'accounts.CustomUser'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
SITE_ID = 1


# =============================================================================
# DJANGO-ALLAUTH CONFIGURATION
# =============================================================================

ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_SESSION_REMEMBER = True
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Email template configuration
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[cit.is] '
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https' if not DEBUG else 'http'


# =============================================================================
# DJANGO REST FRAMEWORK, CRISPY FORMS, ETC.
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'core.authentication.ApiKeyAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

SPECTACULAR_SETTINGS = {
    'TITLE': 'cit.is Archive API',
    'DESCRIPTION': 'API for permanent web archiving and citation management',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# =============================================================================
# STATIC FILES & MEDIA CONFIGURATION
# =============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')

EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ['true', '1']
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

# Email addresses - must be explicitly configured in .env, no automatic inference
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@localhost')
SERVER_EMAIL = os.getenv('SERVER_EMAIL', DEFAULT_FROM_EMAIL)


# =============================================================================
# STRIPE CONFIGURATION (dj-stripe)
# =============================================================================

# Basic Stripe settings (also used by our custom views)
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# Stripe Price IDs for subscription plans
STRIPE_PRICE_PREMIUM_MONTHLY = os.getenv('STRIPE_PRICE_PREMIUM_MONTHLY', '')
STRIPE_PRICE_PREMIUM_YEARLY = os.getenv('STRIPE_PRICE_PREMIUM_YEARLY', '')

# dj-stripe specific settings
DJSTRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
DJSTRIPE_USE_NATIVE_JSONFIELD = True
DJSTRIPE_FOREIGN_KEY_TO_FIELD = 'id'
# Use retrieve_event to avoid signature validation complexity
# This fetches events from Stripe API instead of validating webhook signatures
DJSTRIPE_WEBHOOK_VALIDATION = 'retrieve_event'

# Test vs Live mode detection based on key prefix
# Provide fallbacks for development without Stripe keys
if STRIPE_SECRET_KEY and STRIPE_SECRET_KEY.startswith('sk_test_'):
    DJSTRIPE_TEST_API_KEY = STRIPE_SECRET_KEY
    DJSTRIPE_LIVE_API_KEY = ''
elif STRIPE_SECRET_KEY and STRIPE_SECRET_KEY.startswith('sk_live_'):
    DJSTRIPE_TEST_API_KEY = ''
    DJSTRIPE_LIVE_API_KEY = STRIPE_SECRET_KEY
else:
    # Fallback for development - use test mode with placeholder
    DJSTRIPE_TEST_API_KEY = 'sk_test_placeholder'
    DJSTRIPE_LIVE_API_KEY = ''


# =============================================================================
# SECURITY & ORIGIN CONFIGURATION
# =============================================================================

# Dynamically generate trusted origins from ALLOWED_HOSTS in .env
_trusted_origins = [f"https://{host}" for host in ALLOWED_HOSTS if host not in ['testserver']]
if DEBUG:
    _trusted_origins.extend([f"http://{host}" for host in ALLOWED_HOSTS if host not in ['testserver']])
    _trusted_origins.extend(['http://localhost:8000', 'http://127.0.0.1:8000'])

CSRF_TRUSTED_ORIGINS = list(set(_trusted_origins))
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True




# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'verbose': {'format': '%(levelname)s %(asctime)s %(module)s %(message)s'}},
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'citis.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 2,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': os.getenv('LOG_LEVEL', 'INFO'),
    },
}


# =============================================================================
# CITIS-SPECIFIC SETTINGS
# =============================================================================

# =============================================================================
# SITE DOMAIN & SERVER CONFIGURATION  
# =============================================================================

# Core site domain - all other domain-related settings derive from this
SITE_DOMAIN = os.getenv('SITE_DOMAIN', 'localhost:8000')

# Server Configuration
# If SERVER_BASE_URL not explicitly set, derive from SITE_DOMAIN
if os.getenv('SERVER_BASE_URL'):
    SERVER_BASE_URL = os.getenv('SERVER_BASE_URL')
else:
    # Use HTTPS in production, HTTP in development
    protocol = 'https' if not DEBUG else 'http'
    SERVER_BASE_URL = f'{protocol}://{SITE_DOMAIN}'

SERVER_URL_PREFIX = os.getenv('SERVER_URL_PREFIX', '')
SERVER_REQUIRE_API_KEY = os.getenv('SERVER_REQUIRE_API_KEY', 'True').lower() in ['true', '1', 'yes']
MASTER_API_KEY = os.getenv('MASTER_API_KEY')

# Master user configuration (for master API key)
MASTER_USER_EMAIL = os.getenv('MASTER_USER_EMAIL', 'admin@example.com')
MASTER_USER_PASSWORD = os.getenv('MASTER_USER_PASSWORD', 'changeme123')

# Archive Configuration
ARCHIVE_MODE = os.getenv('ARCHIVE_MODE', 'singlefile')
SHORTCODE_LENGTH = int(os.getenv('SHORTCODE_LENGTH', 8))
TIMEDIFF_WARNING_THRESHOLD = int(os.getenv('TIMEDIFF_WARNING_THRESHOLD', 7200))

# Overlay Configuration
OVERLAY_STYLE_BACKGROUND_COLOR = os.getenv('OVERLAY_STYLE_BACKGROUND_COLOR', '#000000')
OVERLAY_STYLE_LINK_COLOR = os.getenv('OVERLAY_STYLE_LINK_COLOR', '#ffe100')
OVERLAY_STYLE_ICON = os.getenv('OVERLAY_STYLE_ICON', '')
OVERLAY_STYLE_COPY_GRAPHIC = os.getenv('OVERLAY_STYLE_COPY_GRAPHIC', '📋')

# UI Color Configuration
ACCENT_COLOR = os.getenv('ACCENT_COLOR', '#4ECDC4')  # Main accent color (cyan/teal)
BUTTON_COLOR = os.getenv('BUTTON_COLOR', '#3BA8A1')  # Slightly dimmed accent for button resting state

# Contact email for sales/support - must be explicitly configured
SALES_EMAIL = os.getenv('SALES_EMAIL', f'sales@{SITE_DOMAIN}')

# ArchiveBox Configuration (for overlay links)
ARCHIVEBOX_EXPOSE_URL = os.getenv('ARCHIVEBOX_EXPOSE_URL', 'False').lower() == 'true'
ARCHIVEBOX_BASE_URL = os.getenv('ARCHIVEBOX_BASE_URL', '')
ARCHIVEBOX_DATA_PATH = os.getenv('ARCHIVEBOX_DATA_PATH', '')

# SingleFile Configuration
SINGLEFILE_EXECUTABLE_PATH = os.getenv('SINGLEFILE_EXECUTABLE_PATH', 'single-file')
SINGLEFILE_DATA_PATH = os.getenv('SINGLEFILE_DATA_PATH', str(BASE_DIR / 'archives'))
SINGLEFILE_TIMEOUT = int(os.getenv('SINGLEFILE_TIMEOUT', 60))
SINGLEFILE_GENERATE_SCREENSHOT = os.getenv('SINGLEFILE_GENERATE_SCREENSHOT', 'False').lower() == 'true'
SINGLEFILE_GENERATE_PDF = os.getenv('SINGLEFILE_GENERATE_PDF', 'False').lower() == 'true'
SINGLEFILE_SCREENSHOT_WIDTH = int(os.getenv('SINGLEFILE_SCREENSHOT_WIDTH', 1920))
SINGLEFILE_SCREENSHOT_HEIGHT = int(os.getenv('SINGLEFILE_SCREENSHOT_HEIGHT', 1080))

# GeoIP Configuration
GEOLITE_DB_PATH = os.getenv('GEOLITE_DB_PATH')

# =============================================================================
# CHANGEDETECTION.IO CONFIGURATION
# =============================================================================

# ChangeDetection.io API configuration
CHANGEDETECTION_ENABLED = os.getenv('CHANGEDETECTION_ENABLED', 'False').lower() == 'true'

# Support both new and legacy environment variable names
# Determine if we're running inside Docker or on host system
def _get_changedetection_url():
    # Check for explicit environment variables first
    if os.getenv('CHANGEDETECTION_BASE_URL'):
        return os.getenv('CHANGEDETECTION_BASE_URL')
    
    # Try Docker internal URL if set, but fall back to localhost if hostname resolution fails
    internal_url = os.getenv('CHANGEDETECTION_INTERNAL_URL')
    if internal_url:
        try:
            import socket
            hostname = internal_url.split('://')[1].split(':')[0]
            socket.gethostbyname(hostname)
            return internal_url  # Docker hostname resolves, use internal URL
        except (socket.gaierror, IndexError):
            pass  # Fall back to localhost
    
    # Default to localhost for host-based management commands
    return f'http://localhost:{os.getenv("CHANGEDETECTION_EXTERNAL_PORT", "5001")}'

CHANGEDETECTION_BASE_URL = _get_changedetection_url()

CHANGEDETECTION_API_KEY = os.getenv('CHANGEDETECTION_API_KEY', '')

# External access configuration (for documentation and setup)
CHANGEDETECTION_EXTERNAL_PORT = os.getenv('CHANGEDETECTION_EXTERNAL_PORT', '5001')
CHANGEDETECTION_EXTERNAL_URL = os.getenv('CHANGEDETECTION_EXTERNAL_URL', f'http://localhost:{CHANGEDETECTION_EXTERNAL_PORT}')

# Plan-based monitoring frequency configuration (in seconds)
CHANGEDETECTION_PLAN_FREQUENCIES = {
    'free': {'days': 1},              # Daily checks (86400 seconds)
    'professional': {'hours': 1},     # Every hour for content integrity
    'sovereign': {'minutes': 5}       # Every 5 minutes
}

# Link health check frequencies (separate from content integrity)
CHANGEDETECTION_HEALTH_FREQUENCIES = {
    'free': {'days': 1},              # Daily health checks
    'professional': {'minutes': 5},   # Every 5 minutes
    'sovereign': {'minutes': 1}       # Real-time (every minute)
}

# =============================================================================
# RESIDENTIAL PROXY CONFIGURATION
# =============================================================================

RESIDENTIAL_PROXY_ENABLED = os.getenv('RESIDENTIAL_PROXY_ENABLED', 'False').lower() == 'true'
RESIDENTIAL_PROXY_PROVIDER = os.getenv('RESIDENTIAL_PROXY_PROVIDER', 'brightdata')

# Bright Data configuration
BRIGHTDATA_USERNAME = os.getenv('BRIGHTDATA_USERNAME', '')
BRIGHTDATA_PASSWORD = os.getenv('BRIGHTDATA_PASSWORD', '')
BRIGHTDATA_ENDPOINT = os.getenv('BRIGHTDATA_ENDPOINT', 'brd.superproxy.io')
BRIGHTDATA_PORT = int(os.getenv('BRIGHTDATA_PORT', 22225))

# Proxy selection
FALLBACK_PROXY_URL = os.getenv('FALLBACK_PROXY_URL', '')
PROXY_SELECTION_STRATEGY = os.getenv('PROXY_SELECTION_STRATEGY', 'closest')
PROXY_MAX_DISTANCE_KM = int(os.getenv('PROXY_MAX_DISTANCE_KM', 500))


# =============================================================================
# CELERY CONFIGURATION
# =============================================================================

# Construct Redis URL dynamically
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
REDIS_DB = os.getenv('REDIS_DB', '0')  # Redis database number (0-15), most apps use 0

if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Celery Broker Configuration
CELERY_BROKER_URL = os.getenv('REDIS_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', REDIS_URL)

# Celery Task Configuration
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Celery Worker Configuration
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True

# Celery Logging Configuration
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# Celery Beat Configuration (for periodic tasks)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Task Routing
CELERY_TASK_ROUTES = {
    'archive.tasks.archive_url_task': {'queue': 'archive'},
    'archive.tasks.extract_assets_task': {'queue': 'assets'},
    'archive.tasks.update_visit_analytics_task': {'queue': 'analytics'},
}

# Task Time Limits
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes
