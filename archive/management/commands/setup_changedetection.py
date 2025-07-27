"""
Management command for setting up ChangeDetection.io integration.

This command performs the one-time setup required to integrate
with ChangeDetection.io for content integrity monitoring.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.changedetection_service import get_changedetection_service


class Command(BaseCommand):
    help = 'Set up ChangeDetection.io integration with webhook configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Verify current ChangeDetection.io configuration without making changes'
        )
        
        parser.add_argument(
            '--force',
            action='store_true', 
            help='Force setup even if already configured'
        )
    
    def handle(self, *args, **options):
        """Perform ChangeDetection.io setup."""
        
        # Check configuration
        service = get_changedetection_service()
        
        if not service.is_configured():
            self.stdout.write(
                self.style.ERROR(
                    'ChangeDetection.io is not properly configured. Please set:\n'
                    '- CHANGEDETECTION_ENABLED=True\n'
                    '- CHANGEDETECTION_BASE_URL=http://your-changedetection-host:5000\n'
                    '- CHANGEDETECTION_API_KEY=your-api-key'
                )
            )
            raise CommandError('ChangeDetection.io configuration incomplete')
        
        self.stdout.write('✓ ChangeDetection.io configuration validated')
        
        # If verify mode, just check configuration and exit
        if options['verify']:
            self._verify_configuration(service)
            return
        
        # Perform webhook setup
        self.stdout.write('Setting up ChangeDetection.io webhook...')
        
        success, message = service.setup_webhook_notification()
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Webhook setup successful: {message}')
            )
            
            # Show webhook URL for reference
            webhook_url = f"{settings.SERVER_BASE_URL}/api/internal/webhook/changedetection"
            self.stdout.write(f'Webhook URL: {webhook_url}')
            
            # Show frequency configuration
            self._show_frequency_configuration(service)
            
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ Webhook setup failed: {message}')
            )
            raise CommandError('Failed to set up ChangeDetection.io webhook')
    
    def _verify_configuration(self, service):
        """Verify current ChangeDetection.io configuration."""
        
        self.stdout.write('Verifying ChangeDetection.io configuration...')
        
        # Test API connectivity
        watches = service.get_all_watches()
        if watches is not None:
            self.stdout.write(
                self.style.SUCCESS(f'✓ API connectivity verified ({len(watches)} watches found)')
            )
        else:
            self.stdout.write(
                self.style.ERROR('✗ Failed to connect to ChangeDetection.io API')
            )
            return
        
        # Show current webhook URL
        webhook_url = f"{settings.SERVER_BASE_URL}/api/internal/webhook/changedetection"
        self.stdout.write(f'Current webhook URL: {webhook_url}')
        
        # Show frequency configuration
        self._show_frequency_configuration(service)
        
        self.stdout.write(
            self.style.SUCCESS('Configuration verification complete')
        )
    
    def _show_frequency_configuration(self, service):
        """Display the current frequency configuration for each plan tier."""
        
        self.stdout.write('\nPlan-based monitoring frequencies:')
        
        for plan in ['free', 'professional', 'sovereign']:
            # Content integrity frequency
            content_freq = service.get_plan_frequency(plan, 'content_integrity')
            content_seconds = service.convert_to_seconds(content_freq)
            
            # Link health frequency  
            health_freq = service.get_plan_frequency(plan, 'link_health')
            health_seconds = service.convert_to_seconds(health_freq)
            
            self.stdout.write(
                f'  {plan.capitalize():12}: '
                f'Content integrity every {self._format_interval(content_seconds)}, '
                f'Link health every {self._format_interval(health_seconds)}'
            )
    
    def _format_interval(self, seconds):
        """Format interval in seconds to human-readable format."""
        if seconds >= 86400:
            days = seconds // 86400
            return f'{days} day{"s" if days != 1 else ""}'
        elif seconds >= 3600:
            hours = seconds // 3600
            return f'{hours} hour{"s" if hours != 1 else ""}'
        elif seconds >= 60:
            minutes = seconds // 60
            return f'{minutes} minute{"s" if minutes != 1 else ""}'
        else:
            return f'{seconds} second{"s" if seconds != 1 else ""}' 