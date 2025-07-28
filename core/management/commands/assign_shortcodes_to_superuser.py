"""
Django management command to assign all existing shortcodes to the superuser.
This is a one-off script for data migration.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from archive.models import Shortcode


class Command(BaseCommand):
    help = 'Assign all existing shortcodes to the superuser (one-off script)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force assignment even if shortcodes already have owners',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        dry_run = options['dry_run']
        force = options['force']
        
        # Find the superuser
        try:
            superuser = User.objects.filter(is_superuser=True).first()
            if not superuser:
                self.stdout.write(
                    self.style.ERROR('No superuser found. Run ensure_superuser command first.')
                )
                return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error finding superuser: {e}')
            )
            return

        self.stdout.write(f'Found superuser: {superuser.username} ({superuser.email})')

        # Get shortcodes to update
        if force:
            # Update all shortcodes regardless of current owner
            shortcodes_to_update = Shortcode.objects.all()
            update_message = "all shortcodes"
        else:
            # Only update shortcodes with no current owner
            shortcodes_to_update = Shortcode.objects.filter(creator_user__isnull=True)
            update_message = "shortcodes with no owner"

        total_count = shortcodes_to_update.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING(f'No {update_message} found to update.')
            )
            return

        self.stdout.write(f'Found {total_count} {update_message} to assign to superuser.')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN: No changes will be made. Use --force to actually update.')
            )
            # Show sample of what would be updated
            sample_shortcodes = shortcodes_to_update[:5]
            for shortcode in sample_shortcodes:
                current_owner = shortcode.creator_user.username if shortcode.creator_user else "None"
                self.stdout.write(f'  - {shortcode.shortcode} ({shortcode.url[:50]}...) - Current owner: {current_owner}')
            
            if total_count > 5:
                self.stdout.write(f'  ... and {total_count - 5} more shortcodes')
            return

        # Confirm before making changes
        if not force:
            confirm = input(f'Are you sure you want to assign {total_count} shortcodes to {superuser.username}? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write('Operation cancelled.')
                return

        # Update shortcodes in a transaction
        try:
            with transaction.atomic():
                updated_count = shortcodes_to_update.update(creator_user=superuser)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully assigned {updated_count} shortcodes to superuser {superuser.username}'
                    )
                )
                
                # Show some statistics
                total_shortcodes = Shortcode.objects.count()
                owned_by_superuser = Shortcode.objects.filter(creator_user=superuser).count()
                unowned_shortcodes = Shortcode.objects.filter(creator_user__isnull=True).count()
                
                self.stdout.write(f'\nStatistics after update:')
                self.stdout.write(f'  Total shortcodes: {total_shortcodes}')
                self.stdout.write(f'  Owned by superuser: {owned_by_superuser}')
                self.stdout.write(f'  Unowned shortcodes: {unowned_shortcodes}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating shortcodes: {e}')
            ) 