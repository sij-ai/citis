# Generated migration to remove incorrectly added archive fields

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0002_migrate_data_correctly'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='shortcode',
            name='archive_path',
        ),
        migrations.RemoveField(
            model_name='shortcode',
            name='is_archived',
        ),
    ] 