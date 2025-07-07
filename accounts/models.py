"""
User models for the citis application.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.apps import apps


class CustomUser(AbstractUser):
    """
    Custom user model that extends Django's AbstractUser.
    
    Includes all standard Django auth fields (username, email, password, etc.)
    plus additional fields specific to citis.
    """
    
    # Additional user fields
    display_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Display name for the user (optional)"
    )
    
    # Account metadata
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the account was created"
    )
    
    # User preferences
    default_archive_method = models.CharField(
        max_length=20,
        choices=[
            ('archivebox', 'ArchiveBox'),
            ('singlefile', 'SingleFile'),
            ('both', 'Both Methods'),
        ],
        default='singlefile',
        help_text="Default archiving method for new shortcodes"
    )
    
    # Subscription and usage tracking
    is_premium = models.BooleanField(
        default=False,
        help_text="Whether the user has a premium subscription"
    )
    
    monthly_shortcode_limit = models.PositiveIntegerField(
        default=100,
        help_text="Maximum number of shortcodes per month for this user"
    )
    
    class Meta:
        db_table = 'accounts_customuser'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        
    def __str__(self):
        return self.display_name or self.username
    
    def get_full_display_name(self):
        """Get the best available display name."""
        if self.display_name:
            return self.display_name
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.username
    
    def get_monthly_shortcode_count(self):
        """Get the number of shortcodes created this month."""
        from datetime import datetime
        
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Use apps.get_model to avoid circular import
        Shortcode = apps.get_model('archive', 'Shortcode')
        
        return Shortcode.objects.filter(
            creator_user=self,
            created_at__gte=start_of_month
        ).count()
    
    def can_create_shortcode(self):
        """Check if user can create another shortcode this month."""
        if self.is_premium:
            return True  # Premium users have unlimited shortcodes
        
        return self.get_monthly_shortcode_count() < self.monthly_shortcode_limit
