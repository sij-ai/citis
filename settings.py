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
    'django_htmx',  # HTMX integration
    
    # Billing - Will add after installing
    # 'djstripe',
    
    # Utilities - Will add after installing
    # 'django_extensions',
    # 'taggit',
] 

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
    'django_htmx.middleware.HtmxMiddleware',  # HTMX middleware
] 