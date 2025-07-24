"""
Signal handlers for syncing subscription status with dj-stripe.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from djstripe.models import Subscription, Customer
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Subscription)
def sync_subscription_status(sender, instance, **kwargs):
    """
    Sync user premium status when subscription changes.
    
    This is triggered whenever dj-stripe processes a webhook that
    creates or updates a subscription.
    """
    try:
        # Get the user from the subscription's customer
        if instance.customer and instance.customer.subscriber:
            user = instance.customer.subscriber
            old_premium_status = user.is_premium
            user.update_premium_status()
            
            if old_premium_status != user.is_premium:
                logger.info(
                    f"User {user.id} premium status changed from "
                    f"{old_premium_status} to {user.is_premium} "
                    f"due to subscription {instance.id} status: {instance.status}"
                )
    except Exception as e:
        logger.error(f"Error syncing subscription status: {str(e)}")


@receiver(post_delete, sender=Subscription)
def sync_subscription_deletion(sender, instance, **kwargs):
    """
    Sync user premium status when subscription is deleted.
    """
    try:
        if instance.customer and instance.customer.subscriber:
            user = instance.customer.subscriber
            user.update_premium_status()
            logger.info(f"User {user.id} premium status updated due to subscription deletion")
    except Exception as e:
        logger.error(f"Error syncing subscription deletion: {str(e)}")


@receiver(post_save, sender=Customer)
def sync_customer_creation(sender, instance, created, **kwargs):
    """
    Ensure premium status is correct when customer is created.
    """
    if created and instance.subscriber:
        try:
            user = instance.subscriber
            user.update_premium_status()
            logger.info(f"Premium status synced for new Stripe customer: User {user.id}")
        except Exception as e:
            logger.error(f"Error syncing new customer: {str(e)}")


# Import CustomUser model
from django.contrib.auth import get_user_model
User = get_user_model()


@receiver(post_save, sender=User)
def handle_user_creation_and_updates(sender, instance, created, **kwargs):
    """
    Handle user creation and email updates for student detection and quota updates.
    """
    try:
        if created:
            # New user created - set up initial quotas and check student status
            instance.update_student_status()
            instance.update_plan_quotas()
            logger.info(f"User {instance.id} created with plan: {instance.current_plan}, student: {instance.is_student}")
        else:
            # User updated - check if email changed and update student status
            # We need to check if email changed by looking at the previous value
            # Since we don't have access to the old values in post_save, we'll
            # update student status on every save (it's idempotent)
            old_student_status = instance.is_student
            instance.update_student_status()
            
            if old_student_status != instance.is_student:
                logger.info(f"User {instance.id} student status changed from {old_student_status} to {instance.is_student}")
                
    except Exception as e:
        logger.error(f"Error handling user creation/update for user {instance.id}: {str(e)}")


# Also add a signal to handle when EmailAddress is verified in django-allauth
try:
    from allauth.account.models import EmailAddress
    
    @receiver(post_save, sender=EmailAddress)
    def handle_email_verification(sender, instance, created, **kwargs):
        """
        Update student status when email is verified.
        """
        try:
            if instance.verified and instance.primary and instance.user:
                old_student_status = instance.user.is_student
                instance.user.update_student_status()
                
                if old_student_status != instance.user.is_student:
                    logger.info(f"User {instance.user.id} student status updated after email verification: {instance.user.is_student}")
                    
        except Exception as e:
            logger.error(f"Error updating student status after email verification: {str(e)}")
            
except ImportError:
    # django-allauth not available
    logger.warning("django-allauth not available - email verification signals not registered") 