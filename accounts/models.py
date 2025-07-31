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
        default=5,  # Changed from 100 to 5 for free tier
        help_text="Maximum number of shortcodes per month for this user"
    )
    
    shortcode_length = models.PositiveIntegerField(
        default=8,  # Changed from 6 to 8 for free tier
        help_text="Length of shortcodes this user is allowed to create"
    )
    
    # Additional quota fields for pricing tiers
    monthly_redirect_limit = models.PositiveIntegerField(
        default=25,
        help_text="Maximum number of redirects per month for this user"
    )
    
    max_archive_size_mb = models.PositiveIntegerField(
        default=5,
        help_text="Maximum archive file size in MB"
    )
    
    # Student status and bonuses
    is_student = models.BooleanField(
        default=False,
        help_text="Whether the user is verified as a student"
    )
    
    student_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When student status was verified"
    )
    
    # Plan tier tracking
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('professional', 'Professional'),
        ('sovereign', 'Sovereign'),
    ]
    
    current_plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default='free',
        help_text="Current subscription plan"
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
        
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Use apps.get_model to avoid circular import
        Shortcode = apps.get_model('archive', 'Shortcode')
        
        return Shortcode.objects.filter(
            creator_user=self,
            created_at__gte=start_of_month
        ).count()
    
    def can_create_shortcode(self):
        """Check if user can create another shortcode this month."""
        if self.current_plan == 'sovereign':
            return True  # Sovereign users have unlimited shortcodes
        
        monthly_count = self.get_monthly_shortcode_count()
        effective_limit = self.get_effective_monthly_limit()
        return monthly_count < effective_limit
    
    def get_effective_monthly_limit(self):
        """Get the effective monthly shortcode limit including student bonus."""
        base_limit = self.monthly_shortcode_limit
        if self.is_student and self.current_plan == 'free':
            # Add 20 bonus archives for students on free plan
            return base_limit + 20
        return base_limit
    
    def get_monthly_redirect_count(self):
        """Get the number of redirects this month (same as shortcodes for now)."""
        return self.get_monthly_shortcode_count()
    
    def can_create_redirect(self):
        """Check if user can create another redirect this month."""
        if self.current_plan == 'sovereign':
            return True  # Sovereign users have unlimited redirects
        
        return self.get_monthly_redirect_count() < self.monthly_redirect_limit
    
    def can_upload_file_size(self, size_mb):
        """Check if user can upload a file of the given size."""
        if self.current_plan == 'sovereign':
            return True  # Sovereign users have no file size limit
        
        return size_mb <= self.max_archive_size_mb
    
    @classmethod
    def is_academic_email(cls, email):
        """Check if an email address belongs to an academic institution."""
        if not email:
            return False
        
        email = email.lower()
        academic_domains = [
            '.edu',       # US educational institutions
            '.ac.uk',     # UK academic institutions
            '.ac.za',     # South African academic institutions
            '.edu.au',    # Australian educational institutions
            '.edu.ca',    # Canadian educational institutions
            '.ac.nz',     # New Zealand academic institutions
            '.edu.sg',    # Singapore educational institutions
            '.ac.in',     # Indian academic institutions
            '.edu.br',    # Brazilian educational institutions
            '.ac.jp',     # Japanese academic institutions
            '.edu.mx',    # Mexican educational institutions
            '.ac.kr',     # South Korean academic institutions
            '.edu.ar',    # Argentinian educational institutions
            '.ac.il',     # Israeli academic institutions
            '.edu.co',    # Colombian educational institutions
            '.uni-',      # German university domains (uni-*.de)
        ]
        
        # Check for direct domain matches
        for domain in academic_domains:
            if email.endswith(domain):
                return True
        
        # Check for German university pattern (uni-*.de)
        if '.uni-' in email and email.endswith('.de'):
            return True
        
        # Additional common academic patterns
        academic_patterns = [
            '.university.',
            '.college.',
            '.school.',
            '.instituto.',
            '.universidade.',
            '.universite.',
            '.universitet.',
        ]
        
        for pattern in academic_patterns:
            if pattern in email:
                return True
        
        return False
    
    def update_student_status(self):
        """Update student status based on email domain."""
        was_student = self.is_student
        self.is_student = self.is_academic_email(self.email)
        
        if self.is_student and not was_student:
            # Just became a student
            self.student_verified_at = timezone.now()
        elif not self.is_student and was_student:
            # No longer a student
            self.student_verified_at = None
        
        self.save(update_fields=['is_student', 'student_verified_at'])
        return self.is_student
    
    def update_plan_quotas(self):
        """Update quota limits based on current plan."""
        if self.current_plan == 'free':
            self.monthly_shortcode_limit = 5
            self.monthly_redirect_limit = 25
            self.max_archive_size_mb = 5
            self.shortcode_length = 8
        elif self.current_plan == 'professional':
            self.monthly_shortcode_limit = 100
            self.monthly_redirect_limit = 250
            self.max_archive_size_mb = 25
            self.shortcode_length = 6
        elif self.current_plan == 'sovereign':
            # Sovereign plans have unlimited usage
            self.monthly_shortcode_limit = 999999  # Effectively unlimited
            self.monthly_redirect_limit = 999999  # Effectively unlimited
            self.max_archive_size_mb = 999999     # Effectively unlimited
            self.shortcode_length = 5
        
        self.save(update_fields=[
            'monthly_shortcode_limit', 'monthly_redirect_limit', 
            'max_archive_size_mb', 'shortcode_length'
        ])

    def update_premium_status(self):
        """Update is_premium and current_plan based on dj-stripe subscription status."""
        from djstripe.models import Customer
        
        old_plan = self.current_plan
        
        try:
            customer = Customer.objects.get(subscriber=self)
            # Check if user has any active subscriptions
            active_subscriptions = customer.subscriptions.filter(
                status__in=['active', 'trialing']
            )
            
            if active_subscriptions.exists():
                self.is_premium = True
                # For now, assume premium means professional plan
                # This can be enhanced later to detect plan type from subscription
                self.current_plan = 'professional'
            else:
                self.is_premium = False
                self.current_plan = 'free'
                
        except Customer.DoesNotExist:
            # No Stripe customer means no subscription
            self.is_premium = False
            self.current_plan = 'free'
        
        # Update quotas if plan changed
        if old_plan != self.current_plan:
            self.update_plan_quotas()
        else:
            self.save(update_fields=['is_premium', 'current_plan'])
