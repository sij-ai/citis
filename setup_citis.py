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
    """Create master superuser if configured in environment."""
    print_status("Setting up master user...")
    
    try:
        email = getattr(settings, 'MASTER_USER_EMAIL', None)
        password = getattr(settings, 'MASTER_USER_PASSWORD', None)
        
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
            return True
        
        with transaction.atomic():
            # Create superuser
            user = User.objects.create_user(
                username='admin',
                email=email,
                password=password,
                is_superuser=True,
                is_staff=True
            )
            
            # Mark email as verified
            EmailAddress.objects.create(
                user=user,
                email=email,
                verified=True,
                primary=True
            )
            
            print_status(f"Created master superuser: {email} (email verified)", "SUCCESS")
            
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