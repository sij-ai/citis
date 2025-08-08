"""
Django management command to fix anonymous shortcodes by reassigning them to users.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from archive.models import Shortcode

User = get_user_model()


class Command(BaseCommand):
    help = 'Fix anonymous shortcodes by reassigning them to appropriate users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--assign-to-superuser',
            action='store_true',
            help='Assign all anonymous shortcodes to the first superuser',
        )
        parser.add_argument(
            '--assign-to-email',
            type=str,
            help='Assign all anonymous shortcodes to user with this email',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        assign_to_superuser = options['assign_to_superuser']
        assign_to_email = options['assign_to_email']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Find all anonymous shortcodes
        anonymous_shortcodes = Shortcode.objects.filter(creator_user__isnull=True)
        count = anonymous_shortcodes.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No anonymous shortcodes found!')
            )
            return
        
        self.stdout.write(f'Found {count} anonymous shortcodes')
        
        # Determine target user
        target_user = None
        
        if assign_to_superuser:
            target_user = User.objects.filter(is_superuser=True).first()
            if not target_user:
                self.stdout.write(
                    self.style.ERROR('No superuser found. Please create a superuser first.')
                )
                return
            self.stdout.write(f'Will assign to superuser: {target_user.email}')
            
        elif assign_to_email:
            try:
                target_user = User.objects.get(email=assign_to_email)
                self.stdout.write(f'Will assign to user: {target_user.email}')
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with email "{assign_to_email}" not found.')
                )
                return
        else:
            self.stdout.write(
                self.style.ERROR('Please specify either --assign-to-superuser or --assign-to-email')
            )
            return
        
        # Show some examples of what will be changed
        self.stdout.write('\nExamples of anonymous shortcodes to be reassigned:')
        for shortcode in anonymous_shortcodes[:5]:
            creator_info = 'Anonymous'
            if shortcode.creator_api_key:
                creator_info = f'API Key: {shortcode.creator_api_key.name}'
            
            self.stdout.write(f'  {shortcode.shortcode} - {shortcode.url[:50]}... - {creator_info}')
        
        if count > 5:
            self.stdout.write(f'  ... and {count - 5} more')
        
        if not dry_run:
            # Confirm before proceeding
            confirm = input(f'\nReassign {count} anonymous shortcodes to {target_user.email}? (y/N): ')
            if confirm.lower() not in ['y', 'yes']:
                self.stdout.write('Operation cancelled.')
                return
            
            # Perform the reassignment
            updated = anonymous_shortcodes.update(creator_user=target_user)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully reassigned {updated} shortcodes to {target_user.email}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would reassign {count} shortcodes to {target_user.email}')
            )
