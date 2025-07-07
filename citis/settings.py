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

# =============================================================================
# CORE DJANGO SETTINGS
# =============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure--fxgqu2k@uxf_h6@p^o4=c2z$+8cu0$z)xnyep*e&#nxcnt2(j')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')

# Site configuration for django-allauth
SITE_ID = 1

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
    'django.contrib.sites',  # Required for django-allauth
]

THIRD_PARTY_APPS = [
    # API Framework
    'rest_framework',
    'corsheaders',
    'drf_spectacular',  # API documentation
    
    # Authentication
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.google',
    
    # Forms and UI
    'crispy_forms',
    'crispy_bootstrap5',
    'widget_tweaks',
    # 'django_htmx',  # Will add later
    
    # Billing - Will add after installing
    # 'djstripe',
    
    # Utilities - Will add after installing
    # 'django_extensions',
    # 'taggit',
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
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static file serving
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # django-allauth
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django_htmx.middleware.HtmxMiddleware',
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
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'citis.wsgi.application'

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Default to SQLite for development, PostgreSQL for production
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/db.sqlite3')

DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL)
}

# =============================================================================
# AUTHENTICATION & USER MODEL
# =============================================================================

AUTH_USER_MODEL = 'accounts.CustomUser'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# =============================================================================
# DJANGO-ALLAUTH CONFIGURATION
# =============================================================================

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Site configuration for django-allauth
SITE_ID = 1

# Account configuration (updated format)
ACCOUNT_LOGIN_METHODS = ['email']
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_SESSION_REMEMBER = True

# Redirect URLs
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = '/dashboard/'

# Form configuration
ACCOUNT_FORMS = {
    'signup': 'allauth.account.forms.SignupForm',
    'login': 'allauth.account.forms.LoginForm',
}

# Email configuration for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Crispy forms configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# =============================================================================
# DJANGO REST FRAMEWORK CONFIGURATION
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework_simplejwt.authentication.JWTAuthentication',  # Add JWT later
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# =============================================================================
# API DOCUMENTATION CONFIGURATION
# =============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'Citis Archive API',
    'DESCRIPTION': 'API for permanent web archiving and citation management',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# =============================================================================
# STATIC FILES & MEDIA CONFIGURATION
# =============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =============================================================================
# CACHE CONFIGURATION (Will configure after installing django-redis)
# =============================================================================

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': REDIS_URL,
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }

# =============================================================================
# CELERY CONFIGURATION (Will configure after installing Celery)
# =============================================================================

# CELERY_BROKER_URL = REDIS_URL
# CELERY_RESULT_BACKEND = REDIS_URL
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'UTC'

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'noreply@citis.example.com'

# =============================================================================
# STRIPE CONFIGURATION (Will configure after installing dj-stripe)
# =============================================================================

# STRIPE_LIVE_PUBLIC_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
# STRIPE_LIVE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
# STRIPE_TEST_PUBLIC_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
# STRIPE_TEST_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
# STRIPE_LIVE_MODE = not DEBUG
# 
# DJSTRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
# DJSTRIPE_USE_NATIVE_JSONFIELD = True
# DJSTRIPE_FOREIGN_KEY_TO_FIELD = 'id'

# =============================================================================
# CITIS-SPECIFIC SETTINGS (Ported from FastAPI config)
# =============================================================================

# Server Configuration
SERVER_BASE_URL = os.getenv('SERVER_BASE_URL', 'http://localhost:8000')
SERVER_URL_PREFIX = os.getenv('SERVER_URL_PREFIX', '')
SERVER_HOST = os.getenv('SERVER_HOST', '127.0.0.1')
SERVER_PORT = int(os.getenv('SERVER_PORT', '8000'))
SERVER_DOMAIN = os.getenv('SERVER_DOMAIN', 'localhost')
SERVER_REQUIRE_API_KEY = os.getenv('SERVER_REQUIRE_API_KEY', 'False').lower() in ['true', '1', 'yes']
MASTER_API_KEY = os.getenv('MASTER_API_KEY', '')  # Master API key for administrative access

# =============================================================================
# ARCHIVE CONFIGURATION
# =============================================================================

# General archive settings
ARCHIVE_MODE = os.getenv('ARCHIVE_MODE', 'singlefile')  # 'singlefile', 'archivebox', or 'both'
SHORTCODE_LENGTH = int(os.getenv('SHORTCODE_LENGTH', '5'))
TIMEDIFF_WARNING_THRESHOLD = int(os.getenv('TIMEDIFF_WARNING_THRESHOLD', '7200'))  # seconds

# SingleFile configuration
SINGLEFILE_EXECUTABLE_PATH = os.getenv('SINGLEFILE_EXECUTABLE_PATH', 'single-file')
SINGLEFILE_DATA_PATH = os.getenv('SINGLEFILE_DATA_PATH', str(BASE_DIR / 'archives'))
SINGLEFILE_TIMEOUT = int(os.getenv('SINGLEFILE_TIMEOUT', '60'))
SINGLEFILE_GENERATE_SCREENSHOT = os.getenv('SINGLEFILE_GENERATE_SCREENSHOT', 'False').lower() == 'true'
SINGLEFILE_GENERATE_PDF = os.getenv('SINGLEFILE_GENERATE_PDF', 'False').lower() == 'true'
SINGLEFILE_SCREENSHOT_WIDTH = int(os.getenv('SINGLEFILE_SCREENSHOT_WIDTH', '1920'))
SINGLEFILE_SCREENSHOT_HEIGHT = int(os.getenv('SINGLEFILE_SCREENSHOT_HEIGHT', '1080'))

# ArchiveBox configuration
ARCHIVEBOX_BASE_URL = os.getenv('ARCHIVEBOX_BASE_URL', 'http://localhost:8328')
ARCHIVEBOX_API_KEY = os.getenv('ARCHIVEBOX_API_KEY', '')
ARCHIVEBOX_DATA_PATH = os.getenv('ARCHIVEBOX_DATA_PATH', '')
ARCHIVEBOX_EXPOSE_URL = os.getenv('ARCHIVEBOX_EXPOSE_URL', 'False').lower() == 'true'
ARCHIVEBOX_EXTRACTORS = os.getenv('ARCHIVEBOX_EXTRACTORS', 'singlefile,pdf').split(',')

# Cache configuration
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))  # 5 minutes
CACHE_MAX_ENTRIES = int(os.getenv('CACHE_MAX_ENTRIES', '1000'))

# Banner configuration for archived pages
BANNER_ICON = os.getenv('BANNER_ICON', '')
BANNER_COPY_GRAPHIC = os.getenv('BANNER_COPY_GRAPHIC', '')
BANNER_BACKGROUND_COLOR = os.getenv('BANNER_BACKGROUND_COLOR', '#2563eb')
BANNER_LINK_COLOR = os.getenv('BANNER_LINK_COLOR', '#1e40af')
BANNER_ACCENT_COLOR = os.getenv('BANNER_ACCENT_COLOR', '#3b82f6')

# GeoIP configuration
GEOLITE_DATABASE_PATH = os.getenv('GEOLITE_DATABASE_PATH', '')

# External Services
GEOLITE_DB_PATH = os.getenv('GEOLITE_DB_PATH', '/opt/geoip2/GeoLite2-Country.mmdb')

# =============================================================================
# CORS CONFIGURATION
# =============================================================================

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    SERVER_BASE_URL,
]

CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() in ['true', '1', 'yes']
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if os.getenv('SECURE_PROXY_SSL_HEADER') else None
    
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ['true', '1', 'yes']
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() in ['true', '1', 'yes']

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'citis.log',
            'maxBytes': 1024*1024*5,  # 5MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'citis': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# =============================================================================
# DEFAULT FIELD CONFIGURATION
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# DEVELOPMENT SETTINGS (Will configure after installing debug toolbar)
# =============================================================================

# if DEBUG:
#     # Add django-debug-toolbar in development
#     try:
#         import debug_toolbar
#         INSTALLED_APPS.append('debug_toolbar')
#         MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
#         INTERNAL_IPS = ['127.0.0.1', 'localhost']
#     except ImportError:
#         pass

# =============================================================================
# SENTRY CONFIGURATION (Production Error Tracking - Will configure after installing)
# =============================================================================

# SENTRY_DSN = os.getenv('SENTRY_DSN')
# if SENTRY_DSN and not DEBUG:
#     import sentry_sdk
#     from sentry_sdk.integrations.django import DjangoIntegration
#     from sentry_sdk.integrations.celery import CeleryIntegration
#     
#     sentry_sdk.init(
#         dsn=SENTRY_DSN,
#         integrations=[
#             DjangoIntegration(auto_enabling=True),
#             CeleryIntegration(auto_enabling=True),
#         ],
#         traces_sample_rate=0.1,
#         send_default_pii=True,
#     )
