"""
Django management command to automatically set up cit.is on startup.

This command performs essential setup tasks automatically:
- Creates superuser with sovereign plan privileges
- Links master API key to superuser
- Ensures proper email verification
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction
from allauth.account.models import EmailAddress

User = get_user_model()


class Command(BaseCommand):
    help = 'Automatically set up cit.is superuser and master API key'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if superuser already exists',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        try:
            email = getattr(settings, 'MASTER_USER_EMAIL', None)
            password = getattr(settings, 'MASTER_USER_PASSWORD', None)
            master_api_key = getattr(settings, 'MASTER_API_KEY', None)
            
            if not email or not password:
                if email == 'admin@example.com':
                    self.stdout.write(
                        self.style.WARNING('Please configure real MASTER_USER_EMAIL in .env')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('MASTER_USER_EMAIL and MASTER_USER_PASSWORD not configured')
                    )
                return
            
            # Check if superuser already exists
            existing_superuser = User.objects.filter(is_superuser=True).first()
            
            if existing_superuser and not force:
                # Just ensure the superuser has correct privileges
                needs_update = False
                
                if existing_superuser.current_plan != 'sovereign':
                    existing_superuser.current_plan = 'sovereign'
                    needs_update = True
                
                if not existing_superuser.is_premium:
                    existing_superuser.is_premium = True
                    needs_update = True
                
                if needs_update:
                    existing_superuser.save(update_fields=['current_plan', 'is_premium'])
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated superuser {existing_superuser.email} to sovereign plan')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Superuser {existing_superuser.email} already has sovereign privileges')
                    )
                
                user = existing_superuser
                
            else:
                # Create or recreate superuser
                if existing_superuser and force:
                    self.stdout.write(
                        self.style.WARNING(f'Force updating existing superuser: {existing_superuser.email}')
                    )
                    user = existing_superuser
                    user.email = email
                    user.set_password(password)
                    user.current_plan = 'sovereign'
                    user.is_premium = True
                    user.save()
                else:
                    # Create new superuser
                    with transaction.atomic():
                        user = User.objects.create_user(
                            username='admin',
                            email=email,
                            password=password,
                            is_superuser=True,
                            is_staff=True,
                            current_plan='sovereign',
                            is_premium=True
                        )
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'Created superuser: {email} with sovereign plan')
                        )
                
                # Ensure email is verified
                email_address, created = EmailAddress.objects.get_or_create(
                    user=user,
                    email=email,
                    defaults={'verified': True, 'primary': True}
                )
                if created or not email_address.verified:
                    email_address.verified = True
                    email_address.primary = True
                    email_address.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Verified email address: {email}')
                    )
            
            # Create or link master API key if configured
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
                    self.stdout.write(
                        self.style.SUCCESS('Created master API key record linked to superuser')
                    )
                else:
                    # Update existing master API key to ensure it's linked to superuser
                    if master_api_record.user != user:
                        master_api_record.user = user
                        master_api_record.save()
                        self.stdout.write(
                            self.style.SUCCESS('Updated master API key to link to superuser')
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS('Master API key already linked to superuser')
                        )
            
            self.stdout.write(
                self.style.SUCCESS('Automatic setup completed successfully')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Setup failed: {e}')
            )
            raise
