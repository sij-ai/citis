"""
Stripe integration views using dj-stripe for robust subscription management.
"""

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from djstripe.models import Customer
import logging

logger = logging.getLogger(__name__)

# Set Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

# Product/Price configuration loaded from settings
PRICE_LOOKUP = {
    'premium_monthly': settings.STRIPE_PRICE_PREMIUM_MONTHLY,
    'premium_yearly': settings.STRIPE_PRICE_PREMIUM_YEARLY,
}


@login_required
@require_POST
def create_checkout_session(request):
    """Create a Stripe checkout session for subscription using dj-stripe."""
    try:
        price_lookup_key = request.POST.get('price_id')
        if price_lookup_key not in PRICE_LOOKUP:
            return JsonResponse({'error': 'Invalid price selection'}, status=400)
        
        stripe_price_id = PRICE_LOOKUP[price_lookup_key]
        
        # Check for missing configuration
        if not stripe_price_id:
            logger.error(f"Stripe price ID not configured for {price_lookup_key}")
            return JsonResponse({
                'error': 'Subscription system is not properly configured. Please contact support.',
                'dev_error': f'Missing Stripe price ID for {price_lookup_key}. Set STRIPE_PRICE_PREMIUM_MONTHLY in environment variables.'
            }, status=500)
        
        # Get or create dj-stripe customer
        customer, created = Customer.get_or_create(subscriber=request.user)
        if created:
            logger.info(f"Created new Stripe customer for user {request.user.id}")
        
        # Create checkout session using dj-stripe customer
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri(reverse('web:subscription_success')),
            cancel_url=request.build_absolute_uri(reverse('web:pricing')),
            metadata={'user_id': request.user.id}
        )
        
        return JsonResponse({'checkout_url': checkout_session.url})
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        return JsonResponse({
            'error': 'Payment system error. Please try again or contact support.',
            'dev_error': str(e)
        }, status=500)
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return JsonResponse({
            'error': 'Failed to create checkout session. Please try again.',
            'dev_error': str(e)
        }, status=500)


@login_required
def subscription_success(request):
    """Handle successful subscription - dj-stripe will sync via webhooks."""
    # The webhook will handle updating the user's premium status
    return redirect('web:dashboard')


@login_required
@require_POST
def create_billing_portal_session(request):
    """Create a Stripe billing portal session using dj-stripe customer."""
    try:
        # Get dj-stripe customer
        try:
            customer = Customer.objects.get(subscriber=request.user)
        except Customer.DoesNotExist:
            return JsonResponse({'error': 'No subscription found'}, status=400)
        
        session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url=request.build_absolute_uri(reverse('web:dashboard')),
        )
        
        return JsonResponse({'portal_url': session.url})
        
    except Exception as e:
        logger.error(f"Error creating billing portal session: {str(e)}")
        return JsonResponse({'error': 'Failed to access billing portal'}, status=500)


@login_required
@require_POST
def cancel_subscription(request):
    """Cancel the user's subscription using dj-stripe models."""
    try:
        customer = Customer.objects.get(subscriber=request.user)
        active_subscriptions = customer.subscriptions.filter(
            status__in=['active', 'trialing']
        )
        
        if not active_subscriptions.exists():
            return JsonResponse({'error': 'No active subscription found'}, status=400)
        
        # Cancel the first active subscription (most users have only one)
        subscription = active_subscriptions.first()
        
        # Use Stripe API to cancel at period end
        stripe.Subscription.modify(
            subscription.id,
            cancel_at_period_end=True
        )
        
        # Sync the change back to dj-stripe
        subscription.sync_from_stripe_data(
            stripe.Subscription.retrieve(subscription.id)
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Subscription will cancel at the end of your billing period'
        })
        
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'No subscription found'}, status=400)
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        return JsonResponse({'error': 'Failed to cancel subscription'}, status=500) 