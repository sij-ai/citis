"""
Django management command to ensure a superuser exists for the master API key.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings


class Command(BaseCommand):
    help = 'Ensure a superuser exists for the master API key'

    def handle(self, *args, **options):
        User = get_user_model()
        
        email = settings.MASTER_USER_EMAIL
        password = settings.MASTER_USER_PASSWORD
        
        if not email or not password:
            self.stdout.write(
                self.style.WARNING('MASTER_USER_EMAIL and MASTER_USER_PASSWORD must be set in environment')
            )
            return
        
        # Check if a superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.SUCCESS('Superuser already exists')
            )
            return
        
        # Create the superuser
        try:
            user = User.objects.create_user(
                username='admin',
                email=email,
                password=password,
                is_superuser=True,
                is_staff=True
            )
            
            # Mark email as verified to skip confirmation
            from allauth.account.models import EmailAddress
            EmailAddress.objects.get_or_create(
                user=user,
                email=email,
                defaults={'verified': True, 'primary': True}
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Created superuser: {user.email} (email verified)')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {e}')
            ) 