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

DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/db.sqlite3')
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

# Default email addresses (will be updated after SERVER_BASE_URL is defined)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@localhost')
SERVER_EMAIL = os.getenv('SERVER_EMAIL', DEFAULT_FROM_EMAIL)


# =============================================================================
# STRIPE CONFIGURATION (dj-stripe)
# =============================================================================

# Basic Stripe settings (also used by our custom views)
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')

# dj-stripe specific settings
DJSTRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
DJSTRIPE_USE_NATIVE_JSONFIELD = True
DJSTRIPE_FOREIGN_KEY_TO_FIELD = 'id'

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
CORS_ALLOWED_ORIGINS = list(set(_trusted_origins))
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
# STRIPE CONFIGURATION
# =============================================================================

STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

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

# Server Configuration
SERVER_BASE_URL = os.getenv('SERVER_BASE_URL', 'http://localhost:8000')
SERVER_URL_PREFIX = os.getenv('SERVER_URL_PREFIX', '')
SERVER_REQUIRE_API_KEY = os.getenv('SERVER_REQUIRE_API_KEY', 'True').lower() in ['true', '1', 'yes']
MASTER_API_KEY = os.getenv('MASTER_API_KEY')

# Master user configuration (for master API key)
MASTER_USER_EMAIL = os.getenv('MASTER_USER_EMAIL', 'admin@example.com')
MASTER_USER_PASSWORD = os.getenv('MASTER_USER_PASSWORD', 'changeme123')

# Update email settings with proper domain if not explicitly set
if not os.getenv('DEFAULT_FROM_EMAIL'):
    _domain = os.getenv('SITE_DOMAIN')
    if not _domain:
        # Extract from SERVER_BASE_URL
        from urllib.parse import urlparse
        parsed = urlparse(SERVER_BASE_URL)
        _domain = parsed.netloc or 'localhost'
    DEFAULT_FROM_EMAIL = f'noreply@{_domain}'
    SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Archive Configuration
ARCHIVE_MODE = os.getenv('ARCHIVE_MODE', 'singlefile')
SHORTCODE_LENGTH = int(os.getenv('SHORTCODE_LENGTH', 8))
TIMEDIFF_WARNING_THRESHOLD = int(os.getenv('TIMEDIFF_WARNING_THRESHOLD', 7200))

# Overlay Configuration
OVERLAY_STYLE_BACKGROUND_COLOR = os.getenv('OVERLAY_STYLE_BACKGROUND_COLOR', '#000000')
OVERLAY_STYLE_LINK_COLOR = os.getenv('OVERLAY_STYLE_LINK_COLOR', '#ffe100')
OVERLAY_STYLE_ACCENT_COLOR = os.getenv('OVERLAY_STYLE_ACCENT_COLOR', '#ffe100')
OVERLAY_STYLE_ICON = os.getenv('OVERLAY_STYLE_ICON', '')
OVERLAY_STYLE_COPY_GRAPHIC = os.getenv('OVERLAY_STYLE_COPY_GRAPHIC', '📋')
OVERLAY_SERVER_DOMAIN = os.getenv('OVERLAY_SERVER_DOMAIN', '')

# Derived server domain for overlay display
if not OVERLAY_SERVER_DOMAIN:
    from urllib.parse import urlparse
    parsed = urlparse(SERVER_BASE_URL)
    OVERLAY_SERVER_DOMAIN = parsed.netloc or 'localhost'

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
# CELERY CONFIGURATION
# =============================================================================

# Celery Broker Configuration
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Celery Task Configuration
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Celery Worker Configuration
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True

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
