# Generated manually for comprehensive quota system

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='monthly_redirect_limit',
            field=models.PositiveIntegerField(default=25, help_text='Maximum number of redirects per month for this user'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='max_archive_size_mb',
            field=models.PositiveIntegerField(default=5, help_text='Maximum archive file size in MB'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='is_student',
            field=models.BooleanField(default=False, help_text='Whether the user is verified as a student'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='student_verified_at',
            field=models.DateTimeField(blank=True, help_text='When student status was verified', null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='current_plan',
            field=models.CharField(
                choices=[('free', 'Free'), ('professional', 'Professional'), ('sovereign', 'Sovereign')],
                default='free',
                help_text='Current subscription plan',
                max_length=20
            ),
        ),
        # Update defaults for existing fields to match new free tier limits
        migrations.AlterField(
            model_name='customuser',
            name='monthly_shortcode_limit',
            field=models.PositiveIntegerField(default=5, help_text='Maximum number of shortcodes per month for this user'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='shortcode_length',
            field=models.PositiveIntegerField(default=8, help_text='Length of shortcodes this user is allowed to create'),
        ),
    ] 