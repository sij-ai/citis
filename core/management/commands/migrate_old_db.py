"""
Django management command to incrementally migrate data from old deepcite database.
Handles de-duplication since some data may have already been migrated.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

from accounts.models import CustomUser
from archive.models import ApiKey, Shortcode, Visit


class Command(BaseCommand):
    help = 'Incrementally migrate data from old deepcite database with de-duplication'

    def add_arguments(self, parser):
        parser.add_argument(
            '--db-path',
            type=str,
            default='./old_deepcite.db',
            help='Path to the old deepcite database file',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )

    def handle(self, *args, **options):
        db_path = Path(options['db_path']).resolve()
        dry_run = options['dry_run']
        
        if not db_path.exists():
            raise CommandError(f'Database file not found: {db_path}')
        
        self.stdout.write(f'Migrating from: {db_path}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Connect to old database
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            with transaction.atomic():
                # Migrate API Keys and Users
                api_keys_migrated = self.migrate_api_keys(cursor, dry_run)
                
                # Migrate Shortcodes  
                shortcodes_migrated = self.migrate_shortcodes(cursor, dry_run)
                
                # Migrate Visits
                visits_migrated = self.migrate_visits(cursor, dry_run)
                
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'DRY RUN COMPLETE:\n'
                            f'  API Keys: {api_keys_migrated} would be migrated\n'
                            f'  Shortcodes: {shortcodes_migrated} would be migrated\n'
                            f'  Visits: {visits_migrated} would be migrated'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'MIGRATION COMPLETE:\n'
                            f'  API Keys: {api_keys_migrated} migrated\n'
                            f'  Shortcodes: {shortcodes_migrated} migrated\n'
                            f'  Visits: {visits_migrated} migrated'
                        )
                    )
                    
        except Exception as e:
            raise CommandError(f'Migration failed: {e}')
        finally:
            conn.close()

    def migrate_api_keys(self, cursor, dry_run):
        """Migrate API keys and create users, with de-duplication"""
        self.stdout.write('Migrating API keys...')
        
        cursor.execute("SELECT * FROM api_keys")
        migrated_count = 0
        
        for row in cursor.fetchall():
            api_key = row['api_key']
            account = row['account'] or f"legacy_user_{api_key[:6]}"
            description = row['description'] or 'Legacy Key'
            
            # Check if API key already exists
            if ApiKey.objects.filter(key=api_key).exists():
                self.stdout.write(f'  API key {api_key[:8]}... already exists, skipping')
                continue
                
            # Get or create user
            user, user_created = CustomUser.objects.get_or_create(
                username=account,
                defaults={'email': f"{account}@legacy.import"}
            )
            
            if not dry_run:
                ApiKey.objects.create(
                    key=api_key,
                    user=user,
                    name=description,
                    description='Migrated from legacy system'
                )
            
            status = "would create" if dry_run else "created"
            user_status = "new user" if user_created else "existing user"
            self.stdout.write(f'  {status} API key {api_key[:8]}... for {user_status} {account}')
            migrated_count += 1
            
        return migrated_count

    def migrate_shortcodes(self, cursor, dry_run):
        """Migrate shortcodes with de-duplication"""
        self.stdout.write('Migrating shortcodes...')
        
        cursor.execute("SELECT * FROM shortcodes")
        migrated_count = 0
        
        for row in cursor.fetchall():
            shortcode = row['shortcode']
            
            # Check if shortcode already exists
            if Shortcode.objects.filter(shortcode=shortcode).exists():
                self.stdout.write(f'  Shortcode {shortcode} already exists, skipping')
                continue
                
            # Parse created_at
            created_at_dt = timezone.now()
            if row['created_at']:
                try:
                    created_at_dt = datetime.fromisoformat(row['created_at'])
                    if created_at_dt.tzinfo is None:
                        created_at_dt = timezone.make_aware(created_at_dt)
                except (ValueError, TypeError):
                    pass
            
            # Find creator API key and user
            creator_api_key = None
            creator_user = None
            
            if row['creator_key']:
                try:
                    creator_api_key = ApiKey.objects.get(key=row['creator_key'])
                    creator_user = creator_api_key.user
                except ApiKey.DoesNotExist:
                    # Create anonymous user if API key not found
                    creator_user, _ = CustomUser.objects.get_or_create(
                        username='anonymous_legacy'
                    )
            else:
                # No creator key, use anonymous user
                creator_user, _ = CustomUser.objects.get_or_create(
                    username='anonymous_legacy'
                )
            
            if not dry_run:
                Shortcode.objects.create(
                    shortcode=shortcode,
                    url=row['url'],
                    created_at=created_at_dt,
                    creator_user=creator_user,
                    creator_api_key=creator_api_key,
                    creator_ip=row['creator_ip'] if 'creator_ip' in row.keys() else None,
                    text_fragment=row['text_fragment'] if 'text_fragment' in row.keys() else '',
                    archive_method=row['archive_method'] if 'archive_method' in row.keys() else 'singlefile'
                )
            
            status = "would create" if dry_run else "created"
            self.stdout.write(f'  {status} shortcode {shortcode} -> {row["url"][:50]}...')
            migrated_count += 1
            
        return migrated_count

    def migrate_visits(self, cursor, dry_run):
        """Migrate visits with de-duplication"""
        self.stdout.write('Migrating visits...')
        
        cursor.execute("SELECT * FROM visits")
        migrated_count = 0
        skipped_count = 0
        
        for row in cursor.fetchall():
            # Get shortcode
            try:
                shortcode_obj = Shortcode.objects.get(shortcode=row['shortcode'])
            except Shortcode.DoesNotExist:
                self.stdout.write(f'  Shortcode {row["shortcode"]} not found, skipping visit')
                skipped_count += 1
                continue
            
            # Parse visited_at
            visited_at_dt = timezone.now()
            if row['visited_at']:
                try:
                    visited_at_dt = datetime.fromisoformat(row['visited_at'])
                    if visited_at_dt.tzinfo is None:
                        visited_at_dt = timezone.make_aware(visited_at_dt)
                except (ValueError, TypeError):
                    pass
            
            # Check for duplicate visits (same shortcode, IP, and timestamp within 1 minute)
            ip_address = row['ip_address'] if 'ip_address' in row.keys() else None
            existing_visit = Visit.objects.filter(
                shortcode=shortcode_obj,
                ip_address=ip_address,
                visited_at__gte=visited_at_dt - timezone.timedelta(minutes=1),
                visited_at__lte=visited_at_dt + timezone.timedelta(minutes=1)
            ).first()
            
            if existing_visit:
                continue  # Skip duplicate
            
            if not dry_run:
                Visit.objects.create(
                    shortcode=shortcode_obj,
                    visited_at=visited_at_dt,
                    ip_address=ip_address,
                    user_agent=row['user_agent'] if 'user_agent' in row.keys() else '',
                    referer=row['referer'] if 'referer' in row.keys() else ''
                )
            
            migrated_count += 1
            
        if skipped_count > 0:
            self.stdout.write(f'  Skipped {skipped_count} visits due to missing shortcodes')
            
        return migrated_count 