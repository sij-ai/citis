"""
Management command for managing ChangeDetection.io watches.

This command provides utilities for listing, creating, updating, and 
managing watches in ChangeDetection.io.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from core.changedetection_service import get_changedetection_service
from archive.models import Shortcode


class Command(BaseCommand):
    help = 'Manage ChangeDetection.io watches'
    
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Available actions')
        
        # List watches
        list_parser = subparsers.add_parser('list', help='List all watches')
        list_parser.add_argument(
            '--format',
            choices=['table', 'json'],
            default='table',
            help='Output format'
        )
        
        # Sync watches
        sync_parser = subparsers.add_parser('sync', help='Sync watches with shortcodes')
        sync_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        sync_parser.add_argument(
            '--plan',
            choices=['free', 'professional', 'sovereign'],
            help='Only sync for specific plan tier'
        )
        
        # Show stats
        subparsers.add_parser('stats', help='Show watch statistics')
        
        # Find orphaned watches
        subparsers.add_parser('orphaned', help='Find watches without matching shortcodes')
        
        # Update frequency for URL
        update_parser = subparsers.add_parser('update', help='Update watch frequency for a URL')
        update_parser.add_argument('url', help='URL to update')
        update_parser.add_argument('plan', choices=['free', 'professional', 'sovereign'], help='Plan tier')
    
    def handle(self, *args, **options):
        """Handle the management command."""
        
        service = get_changedetection_service()
        
        if not service.is_configured():
            raise CommandError('ChangeDetection.io is not configured')
        
        action = options.get('action')
        
        if action == 'list':
            self._list_watches(service, options)
        elif action == 'sync':
            self._sync_watches(service, options)
        elif action == 'stats':
            self._show_stats(service)
        elif action == 'orphaned':
            self._find_orphaned_watches(service)
        elif action == 'update':
            self._update_watch(service, options)
        else:
            self.stdout.write(self.style.ERROR('Please specify an action'))
            self.stdout.write('Available actions: list, sync, stats, orphaned, update')
    
    def _list_watches(self, service, options):
        """List all ChangeDetection.io watches."""
        
        self.stdout.write('Fetching ChangeDetection.io watches...')
        
        watches = service.get_all_watches()
        if watches is None:
            raise CommandError('Failed to fetch watches from ChangeDetection.io')
        
        if options['format'] == 'json':
            import json
            self.stdout.write(json.dumps(watches, indent=2))
            return
        
        # Table format
        self.stdout.write(f'\nFound {len(watches)} watches:')
        self.stdout.write('-' * 100)
        self.stdout.write(f'{"UUID":<36} {"URL":<50} {"Title":<20}')
        self.stdout.write('-' * 100)
        
        for uuid, watch_data in watches.items():
            url = watch_data.get('url', 'N/A')
            title = watch_data.get('title', 'N/A')
            
            # Truncate long URLs and titles
            url = url[:47] + '...' if len(url) > 50 else url
            title = title[:17] + '...' if len(title) > 20 else title
            
            self.stdout.write(f'{uuid:<36} {url:<50} {title:<20}')
    
    def _sync_watches(self, service, options):
        """Sync watches with shortcodes."""
        
        self.stdout.write('Syncing ChangeDetection.io watches with shortcodes...')
        
        # Get all shortcodes that should have watches (premium users only)
        shortcode_filter = {}
        if options.get('plan'):
            shortcode_filter['creator_user__current_plan'] = options['plan']
        
        # Only process shortcodes from professional and sovereign users
        shortcodes = Shortcode.objects.filter(
            creator_user__current_plan__in=['professional', 'sovereign'],
            **shortcode_filter
        ).select_related('creator_user')
        
        if not shortcodes:
            self.stdout.write('No shortcodes found for premium users')
            return
        
        self.stdout.write(f'Found {shortcodes.count()} shortcodes to process')
        
        processed = 0
        created = 0
        updated = 0
        errors = 0
        
        for shortcode in shortcodes:
            try:
                if options['dry_run']:
                    self.stdout.write(f'Would process: {shortcode.shortcode} ({shortcode.url})')
                    processed += 1
                    continue
                
                # Process the shortcode with ChangeDetection.io
                success, message = service.process_archive_creation(shortcode)
                
                if success:
                    if 'Created' in message:
                        created += 1
                        self.stdout.write(f'✓ Created watch for {shortcode.shortcode}')
                    elif 'Updated' in message:
                        updated += 1  
                        self.stdout.write(f'✓ Updated watch for {shortcode.shortcode}')
                    else:
                        self.stdout.write(f'✓ {shortcode.shortcode}: {message}')
                else:
                    errors += 1
                    self.stdout.write(f'✗ {shortcode.shortcode}: {message}')
                
                processed += 1
                
            except Exception as e:
                errors += 1
                self.stdout.write(f'✗ Error processing {shortcode.shortcode}: {e}')
        
        # Summary
        self.stdout.write('\nSync Summary:')
        self.stdout.write(f'  Processed: {processed}')
        self.stdout.write(f'  Created:   {created}')
        self.stdout.write(f'  Updated:   {updated}')
        self.stdout.write(f'  Errors:    {errors}')
    
    def _show_stats(self, service):
        """Show watch and shortcode statistics."""
        
        self.stdout.write('Gathering statistics...')
        
        # ChangeDetection.io watches
        watches = service.get_all_watches()
        if watches is None:
            raise CommandError('Failed to fetch watches from ChangeDetection.io')
        
        # Shortcode statistics
        shortcode_stats = Shortcode.objects.filter(
            creator_user__isnull=False
        ).values('creator_user__current_plan').annotate(count=Count('shortcode'))
        
        # ChangeDetection.io statistics
        self.stdout.write(f'\nChangeDetection.io Statistics:')
        self.stdout.write(f'  Total watches: {len(watches)}')
        
        # Find watches that match our shortcodes
        shortcode_urls = set(Shortcode.objects.values_list('url', flat=True))
        matching_watches = 0
        
        for watch_data in watches.values():
            if watch_data.get('url') in shortcode_urls:
                matching_watches += 1
        
        self.stdout.write(f'  Watches for our URLs: {matching_watches}')
        self.stdout.write(f'  Other watches: {len(watches) - matching_watches}')
        
        # Shortcode statistics by plan
        self.stdout.write(f'\nShortcode Statistics by Plan:')
        total_shortcodes = 0
        
        for stat in shortcode_stats:
            plan = stat['creator_user__current_plan'] or 'unknown'
            count = stat['count']
            total_shortcodes += count
            self.stdout.write(f'  {plan.capitalize():12}: {count:,}')
        
        self.stdout.write(f'  {"Total":12}: {total_shortcodes:,}')
        
        # Coverage analysis
        premium_shortcodes = sum(
            stat['count'] for stat in shortcode_stats 
            if stat['creator_user__current_plan'] in ['professional', 'sovereign']
        )
        
        if premium_shortcodes > 0:
            coverage = (matching_watches / premium_shortcodes) * 100
            self.stdout.write(f'\nMonitoring Coverage:')
            self.stdout.write(f'  Premium shortcodes: {premium_shortcodes:,}')
            self.stdout.write(f'  Monitored URLs: {matching_watches:,}')
            self.stdout.write(f'  Coverage: {coverage:.1f}%')
    
    def _find_orphaned_watches(self, service):
        """Find watches that don't have corresponding shortcodes."""
        
        self.stdout.write('Finding orphaned watches...')
        
        watches = service.get_all_watches()
        if watches is None:
            raise CommandError('Failed to fetch watches from ChangeDetection.io')
        
        # Get all shortcode URLs
        shortcode_urls = set(Shortcode.objects.values_list('url', flat=True))
        
        orphaned_watches = []
        
        for uuid, watch_data in watches.items():
            url = watch_data.get('url')
            if url and url not in shortcode_urls:
                orphaned_watches.append((uuid, watch_data))
        
        if not orphaned_watches:
            self.stdout.write('✓ No orphaned watches found')
            return
        
        self.stdout.write(f'Found {len(orphaned_watches)} orphaned watches:')
        self.stdout.write('-' * 100)
        self.stdout.write(f'{"UUID":<36} {"URL":<60}')
        self.stdout.write('-' * 100)
        
        for uuid, watch_data in orphaned_watches:
            url = watch_data.get('url', 'N/A')
            url = url[:57] + '...' if len(url) > 60 else url
            self.stdout.write(f'{uuid:<36} {url:<60}')
        
        self.stdout.write(f'\nNote: These watches may be monitoring external URLs or legacy data.')
    
    def _update_watch(self, service, options):
        """Update watch frequency for a specific URL."""
        
        url = options['url']
        plan = options['plan']
        
        self.stdout.write(f'Updating watch frequency for {url} to {plan} tier...')
        
        # Find the watch for this URL
        existing_watch = service.find_watch_for_url(url)
        
        if not existing_watch:
            raise CommandError(f'No watch found for URL: {url}')
        
        watch_uuid, watch_data = existing_watch
        
        # Update frequency
        success = service.update_watch_frequency(watch_uuid, plan)
        
        if success:
            frequency = service.get_plan_frequency(plan)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Updated watch {watch_uuid} to {plan} tier frequency: {frequency}')
            )
        else:
            raise CommandError(f'Failed to update watch frequency for {url}') 