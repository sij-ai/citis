# Generated manually for trust verification system

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0002_add_healthcheck_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shortcode',
            name='proxy_country',
            field=models.CharField(blank=True, help_text='Country of proxy used for archiving', max_length=100),
        ),
        migrations.AlterField(
            model_name='shortcode',
            name='proxy_provider',
            field=models.CharField(blank=True, help_text='Proxy provider used for archiving', max_length=100),
        ),
        migrations.AddField(
            model_name='shortcode',
            name='archive_checksum',
            field=models.CharField(blank=True, help_text='SHA256 checksum of archived content for integrity verification', max_length=64),
        ),
        migrations.AddField(
            model_name='shortcode',
            name='archive_size_bytes',
            field=models.PositiveIntegerField(blank=True, help_text='Size of archived content in bytes', null=True),
        ),
        migrations.AddField(
            model_name='shortcode',
            name='trust_certificate',
            field=models.TextField(blank=True, help_text='Digital certificate or timestamp token for verification'),
        ),
        migrations.AddField(
            model_name='shortcode',
            name='trust_metadata',
            field=models.JSONField(default=dict, help_text='Additional trust verification metadata (TSA, chain-of-custody, etc.)'),
        ),
        migrations.AddField(
            model_name='shortcode',
            name='trust_timestamp',
            field=models.DateTimeField(blank=True, help_text='Trusted timestamp for professional/sovereign plans', null=True),
        ),
    ] 