# Generated manually for health monitoring system

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HealthCheck',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('check_type', models.CharField(choices=[('link_health', 'Link Health Check'), ('content_integrity', 'Content Integrity Scan')], help_text='Type of health check performed', max_length=20)),
                ('status', models.CharField(choices=[('ok', 'OK'), ('broken', 'Broken'), ('minor_changes', 'Minor Changes'), ('major_changes', 'Major Changes')], help_text='Result status of the health check', max_length=20)),
                ('details', models.JSONField(default=dict, help_text='Detailed check results and metadata')),
                ('checked_at', models.DateTimeField(default=django.utils.timezone.now, help_text='When this health check was performed')),
                ('shortcode', models.ForeignKey(help_text='The shortcode that was checked', on_delete=django.db.models.deletion.CASCADE, related_name='health_checks', to='archive.shortcode')),
            ],
            options={
                'verbose_name': 'Health Check',
                'verbose_name_plural': 'Health Checks',
                'db_table': 'archive_healthcheck',
                'ordering': ['-checked_at'],
            },
        ),
        migrations.AddIndex(
            model_name='healthcheck',
            index=models.Index(fields=['shortcode', 'check_type', 'checked_at'], name='archive_hea_shortco_7b1234_idx'),
        ),
        migrations.AddIndex(
            model_name='healthcheck',
            index=models.Index(fields=['check_type', 'status'], name='archive_hea_check_t_ab5678_idx'),
        ),
        migrations.AddIndex(
            model_name='healthcheck',
            index=models.Index(fields=['checked_at'], name='archive_hea_checked_cd9012_idx'),
        ),
    ] 