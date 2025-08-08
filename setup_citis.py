#!/usr/bin/env python
"""
Comprehensive setup script for cit.is Django application.

Run this after configuring your .env file to initialize everything automatically.

Usage:
    python setup_citis.py
"""

import os
import sys
import django
from pathlib import Path

# Add project directory to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'citis.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction
from allauth.account.models import EmailAddress
from urllib.parse import urlparse

User = get_user_model()


def print_status(message, status="INFO"):
    """Print formatted status message."""
    colors = {
        "INFO": "\033[94m",  # Blue
        "SUCCESS": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
    }
    reset = "\033[0m"
    print(f"{colors.get(status, '')}{status}: {message}{reset}")


def run_migrations():
    """Run Django migrations."""
    print_status("Running database migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate', '--verbosity=1'])
        print_status("Database migrations completed successfully", "SUCCESS")
        return True
    except Exception as e:
        print_status(f"Migration failed: {e}", "ERROR")
        return False


def setup_site_configuration():
    """Configure Django site from SERVER_BASE_URL."""
    print_status("Configuring site settings...")
    
    try:
        # Get domain from SERVER_BASE_URL
        base_url = settings.SERVER_BASE_URL
        if base_url:
            parsed = urlparse(base_url)
            domain = parsed.netloc or 'localhost'
        else:
            domain = 'localhost'
        
        site_name = 'cit.is'
        
        with transaction.atomic():
            site, created = Site.objects.get_or_create(pk=settings.SITE_ID)
            old_domain, old_name = site.domain, site.name
            
            site.domain = domain
            site.name = site_name
            site.save()
            
            if created:
                print_status(f"Created site configuration: {domain} ({site_name})", "SUCCESS")
            elif old_domain != domain or old_name != site_name:
                print_status(f"Updated site: {old_domain} -> {domain}, {old_name} -> {site_name}", "SUCCESS")
            else:
                print_status(f"Site configuration already correct: {domain} ({site_name})", "SUCCESS")
                
        return True
        
    except Exception as e:
        print_status(f"Failed to configure site: {e}", "ERROR")
        return False


def setup_master_user():
    """Create master superuser and master API key if configured in environment."""
    print_status("Setting up master user and API key...")
    
    try:
        email = getattr(settings, 'MASTER_USER_EMAIL', None)
        password = getattr(settings, 'MASTER_USER_PASSWORD', None)
        master_api_key = getattr(settings, 'MASTER_API_KEY', None)
        
        if not email or not password:
            print_status("MASTER_USER_EMAIL and MASTER_USER_PASSWORD not configured - skipping", "WARNING")
            return True
            
        if email == 'admin@example.com':
            print_status("Please configure real MASTER_USER_EMAIL in .env - skipping", "WARNING")
            return True
        
        # Check if superuser already exists
        existing_superuser = User.objects.filter(is_superuser=True).first()
        
        if existing_superuser:
            # Ensure existing superuser has verified email
            if existing_superuser.email:
                email_address, created = EmailAddress.objects.get_or_create(
                    user=existing_superuser,
                    email=existing_superuser.email,
                    defaults={'verified': True, 'primary': True}
                )
                if created or not email_address.verified:
                    email_address.verified = True
                    email_address.primary = True
                    email_address.save()
                    print_status(f"Marked superuser email {existing_superuser.email} as verified", "SUCCESS")
                else:
                    print_status(f"Superuser {existing_superuser.email} already exists and verified", "SUCCESS")
            
            # Ensure superuser has unlimited privileges
            existing_superuser.current_plan = 'sovereign'
            existing_superuser.is_premium = True
            existing_superuser.save(update_fields=['current_plan', 'is_premium'])
            print_status(f"Updated superuser plan to sovereign with unlimited privileges", "SUCCESS")
            
            user = existing_superuser
        else:
            with transaction.atomic():
                # Create superuser
                user = User.objects.create_user(
                    username='admin',
                    email=email,
                    password=password,
                    is_superuser=True,
                    is_staff=True,
                    current_plan='sovereign',  # Superusers get unlimited sovereign plan
                    is_premium=True
                )
                
                # Mark email as verified
                EmailAddress.objects.create(
                    user=user,
                    email=email,
                    verified=True,
                    primary=True
                )
                
                print_status(f"Created master superuser: {email} (email verified, sovereign plan)", "SUCCESS")
        
        # Create or update master API key if configured
        if master_api_key:
            from archive.models import ApiKey
            
            master_api_record, created = ApiKey.objects.get_or_create(
                key=master_api_key,
                defaults={
                    'user': user,
                    'name': 'Master API Key',
                    'description': 'System master API key for administrative access',
                    'max_uses_total': None,  # Unlimited
                    'max_uses_per_day': None,  # Unlimited
                    'is_active': True
                }
            )
            
            if created:
                print_status(f"Created master API key record linked to superuser", "SUCCESS")
            else:
                # Update existing master API key to ensure it's linked to superuser
                if master_api_record.user != user:
                    master_api_record.user = user
                    master_api_record.save()
                    print_status(f"Updated master API key to link to superuser", "SUCCESS")
                else:
                    print_status(f"Master API key already linked to superuser", "SUCCESS")
        else:
            print_status("MASTER_API_KEY not configured - skipping API key creation", "WARNING")
            
        return True
        
    except Exception as e:
        print_status(f"Failed to setup master user: {e}", "ERROR")
        return False


def collect_static_files():
    """Collect static files for production."""
    if not settings.DEBUG:
        print_status("Collecting static files...")
        try:
            execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
            print_status("Static files collected successfully", "SUCCESS")
        except Exception as e:
            print_status(f"Failed to collect static files: {e}", "WARNING")


def main():
    """Run complete setup process."""
    print_status("=" * 50)
    print_status("cit.is Django Application Setup")
    print_status("=" * 50)
    
    success = True
    
    # Step 1: Run migrations
    if not run_migrations():
        success = False
    
    # Step 2: Configure site
    if not setup_site_configuration():
        success = False
    
    # Step 3: Setup master user
    if not setup_master_user():
        success = False
    
    # Step 4: Collect static files (if production)
    collect_static_files()
    
    print_status("=" * 50)
    if success:
        print_status("Setup completed successfully!", "SUCCESS")
        print_status("Your cit.is installation is ready to use.", "SUCCESS")
        print_status("", "INFO")
        print_status("Next steps:", "INFO")
        print_status("1. Start your Django server: python manage.py runserver", "INFO")
        print_status("2. Start Celery workers: python manage_celery.py worker", "INFO")
        print_status("3. Visit your site and test the functionality", "INFO")
    else:
        print_status("Setup completed with some errors. Check the messages above.", "WARNING")
    print_status("=" * 50)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main()) 