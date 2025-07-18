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