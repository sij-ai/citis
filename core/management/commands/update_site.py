"""
Django management command to update the Site domain and name from environment variables.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings


class Command(BaseCommand):
    help = 'Update Site domain and name from environment variables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            type=str,
            help='Domain name to set (overrides environment)',
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Site name to set (overrides environment)',
        )

    def handle(self, *args, **options):
        # Get domain from command line, environment, or fallback
        domain = options.get('domain')
        if not domain:
            domain = os.getenv('SITE_DOMAIN')
            if not domain:
                # Extract domain from SERVER_BASE_URL
                base_url = settings.SERVER_BASE_URL
                if base_url:
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url)
                    domain = parsed.netloc
                else:
                    domain = 'localhost:8000'

        # Get site name from command line or environment
        name = options.get('name')
        if not name:
            name = os.getenv('SITE_NAME', 'cit.is')

        try:
            # Update or create the site
            site, created = Site.objects.get_or_create(pk=settings.SITE_ID)
            
            old_domain = site.domain
            old_name = site.name
            
            site.domain = domain
            site.name = name
            site.save()
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created new site: {domain} ({name})')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated site: {old_domain} -> {domain}, {old_name} -> {name}'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating site: {e}')
            ) 