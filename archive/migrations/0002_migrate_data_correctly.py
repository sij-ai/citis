# In archive/migrations/0003_migrate_data_correctly.py (or whatever the new file is named)

from django.db import migrations
import sqlite3
from pathlib import Path
from django.utils import timezone
from datetime import datetime

# --- THIS IS THE CORRECT, HARDCODED PATH ---
OLD_DB_PATH = '/home/sij/deepcite/server/deepcite.db'

def migrate_data(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    ApiKey = apps.get_model('archive', 'ApiKey')
    Shortcode = apps.get_model('archive', 'Shortcode')
    Visit = apps.get_model('archive', 'Visit')

    if not Path(OLD_DB_PATH).exists():
        print(f"ERROR: Legacy database not found at {OLD_DB_PATH}")
        return

    print(f"SUCCESS: Found legacy database. Migrating data from {OLD_DB_PATH}")
    conn = sqlite3.connect(OLD_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # --- Migrate API Keys and Create Users ---
    # Create a default user for items with no creator
    anon_user, _ = CustomUser.objects.get_or_create(username='anonymous_legacy')
    api_key_map = {}
    cursor.execute("SELECT * FROM api_keys")
    for row in cursor.fetchall():
        user, _ = CustomUser.objects.get_or_create(
            username=row['account'] or f"legacy_user_{row['api_key'][:6]}",
            defaults={'email': f"{row['account']}@legacy.import"}
        )
        key = ApiKey.objects.create(
            key=row['api_key'], user=user, name=row['description'] or 'Legacy Key'
        )
        api_key_map[row['api_key']] = key

    # --- Migrate Shortcodes ---
    cursor.execute("SELECT * FROM shortcodes")
    for row in cursor.fetchall():
        creator_key = api_key_map.get(row['creator_key'])
        creator_user = creator_key.user if creator_key else anon_user
        created_at_dt = datetime.fromisoformat(row['created_at']) if row['created_at'] else timezone.now()
        
        Shortcode.objects.create(
            shortcode=row['shortcode'], url=row['url'],
            created_at=created_at_dt, creator_user=creator_user,
            creator_api_key=creator_key, creator_ip=row['creator_ip'],
            text_fragment=row['text_fragment'] or '',
            archive_method=row['archive_method'] or 'singlefile'
        )
    
    # --- Migrate Visits ---
    cursor.execute("SELECT * FROM visits")
    for row in cursor.fetchall():
        shortcode_instance = Shortcode.objects.filter(shortcode=row['shortcode']).first()
        if shortcode_instance:
            visited_at_dt = datetime.fromisoformat(row['visited_at']) if row['visited_at'] else timezone.now()
            Visit.objects.create(
                shortcode=shortcode_instance, visited_at=visited_at_dt,
                ip_address=row['ip_address'], user_agent=row['user_agent'] or '',
                referer=row['referer'] or ''
            )

    conn.close()
    print("Legacy data migration completed.")


def reverse_migrate_data(apps, schema_editor):
    # This reverse migration is intentionally simple to avoid accidental data loss
    # on complex schemas. It assumes you will restore from backup if needed.
    print("Reversing data migration. Models will be emptied.")
    apps.get_model('archive', 'Visit').objects.all().delete()
    apps.get_model('archive', 'Shortcode').objects.all().delete()
    apps.get_model('archive', 'ApiKey').objects.all().delete()
    apps.get_model('accounts', 'CustomUser').objects.filter(username__contains='legacy').delete()


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0001_initial"),
        ("accounts", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(migrate_data, reverse_migrate_data),
    ]

