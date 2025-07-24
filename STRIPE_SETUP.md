# Stripe Integration Setup Guide

Complete setup guide for Stripe subscriptions with webhook integration.

## Overview

This guide covers:
1. Basic Stripe configuration (API keys, products, prices)
2. **Critical webhook setup** (the complex part)
3. Testing and troubleshooting

## Part 1: Basic Stripe Configuration

### 1.1 Create Stripe Products & Prices

1. Go to [Stripe Dashboard → Products](https://dashboard.stripe.com/products)
2. Click "Add product"
3. Create a product:
   - **Name**: "Professional Plan"
   - **Description**: "Premium features for power users"
4. Add pricing:
   - **Type**: Recurring
   - **Price**: $10.00
   - **Billing period**: Monthly
   - **Currency**: USD
5. Save and **copy the Price ID** (starts with `price_`)

### 1.2 Environment Variables

Add these to your `.env` file:

```bash
# Stripe API Keys
STRIPE_PUBLISHABLE_KEY=pk_live_...         # or pk_test_... for testing
STRIPE_SECRET_KEY=sk_live_...              # or sk_test_... for testing
STRIPE_WEBHOOK_SECRET=whsec_...            # Get this from webhook setup (Part 2)

# Stripe Price IDs (copy from step 1.1)
STRIPE_PRICE_PREMIUM_MONTHLY=price_1ABC123def456
STRIPE_PRICE_PREMIUM_YEARLY=price_1XYZ789ghi012
```

**Note**: The Django settings are already configured with `DJSTRIPE_WEBHOOK_VALIDATION = 'retrieve_event'` to avoid signature validation complexity.

## Part 2: Webhook Setup (Critical!)

⚠️ **This is the complex part that causes subscription failures if not done correctly.**

### 2.1 Initialize djstripe Database Objects

Run these commands **in order**:

```bash
# 1. Create API key in djstripe database
python manage.py shell -c "
from djstripe.models import APIKey
import os

secret_key = os.getenv('STRIPE_SECRET_KEY', '')
livemode = secret_key.startswith('sk_live_')

api_key, created = APIKey.objects.get_or_create(
    secret=secret_key,
    defaults={
        'livemode': livemode,
        'name': f'Auto-created {\"live\" if livemode else \"test\"} key'
    }
)
print(f'API Key: {api_key.name} (livemode: {api_key.livemode})')
"

# 2. Sync Stripe account
python manage.py djstripe_sync_models Account

# 3. Sync required models for webhook processing
python manage.py djstripe_sync_models Product Price Plan Invoice Customer

# 4. Associate webhook endpoint with account
python manage.py shell -c "
from djstripe.models import WebhookEndpoint, Account

account = Account.objects.first()
endpoint = WebhookEndpoint.objects.first()

if endpoint and account:
    endpoint.djstripe_owner_account = account
    endpoint.djstripe_validation_method = 'retrieve_event'
    endpoint.save()
    print(f'Webhook endpoint configured: {endpoint.url}')
    print(f'Associated with account: {account.id}')
else:
    print('ERROR: Missing webhook endpoint or account')
"
```

### 2.2 Get the Correct Webhook URL

```bash
python manage.py shell -c "
from djstripe.models import WebhookEndpoint
endpoint = WebhookEndpoint.objects.first()
print(f'Use this webhook URL in Stripe Dashboard:')
print(f'{endpoint.url}')
"
```

### 2.3 Configure Stripe Dashboard

1. Go to [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks)
2. Click your existing webhook or create a new one
3. **Set the endpoint URL to the output from step 2.2**
4. Select these events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Save the webhook
6. **Copy the Signing Secret** (starts with `whsec_`) and add it to your `.env` file as `STRIPE_WEBHOOK_SECRET`

### 2.4 Restart Application

```bash
./deploy.sh restart
# or
python manage.py runserver  # for development
```

## Part 3: Testing

### 3.1 Test Subscription Flow

1. Go to `/pricing/` while logged in
2. Click "Upgrade to Professional"
3. Complete test payment in Stripe Checkout
4. Verify user becomes premium:

```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(email='YOUR_EMAIL')
print(f'User {user.email} is_premium: {user.is_premium}')
"
```

### 3.2 Check Webhook Processing

```bash
# Check recent logs for successful webhook processing
tail -20 logs/citis.log | grep -E "(stripe|webhook)" -i

# Should see successful Stripe API calls with 200 responses
```

## Troubleshooting

### Error: "Subscription system is not properly configured"
- Missing Stripe price IDs in environment variables
- Add `STRIPE_PRICE_PREMIUM_MONTHLY` to your `.env` file

### Error: Webhook returns 404
- Wrong webhook URL in Stripe Dashboard  
- The webhook URL must use the `djstripe_uuid` field, not the `id` field
- Run step 2.2 to get the correct URL with proper `djstripe_uuid`

### Error: Webhook returns 500 "AttributeError: 'NoneType' object has no attribute 'default_api_key'"
- Missing account association
- Run steps 2.1 commands in order

### Error: "Invoice matching query does not exist" or "Plan matching query does not exist"
- Missing synced models
- Run: `python manage.py djstripe_sync_models Product Price Plan Invoice Customer`

### Error: "Cannot verify event signature without a secret"
- Webhook validation method is wrong
- Ensure `endpoint.djstripe_validation_method = 'retrieve_event'` is set

### User not becoming premium after successful payment
- Webhook not processing correctly
- Check logs with: `tail -50 logs/citis.log | grep -E "(error|stripe)" -i`
- Verify webhook URL is correct in Stripe Dashboard

## Development vs Production

### Test Mode (Development)
- Use `sk_test_` and `pk_test_` keys
- Webhook events are test events
- Use Stripe's test card numbers

### Live Mode (Production)
- Use `sk_live_` and `pk_live_` keys  
- Real payments and webhook events
- **Ensure webhook URL matches your production domain**

## Security Notes

- Never commit API keys to version control
- Use environment variables for all sensitive data
- Use `retrieve_event` validation to avoid signature complexity
- Monitor webhook failures in Stripe Dashboard

---

If you still have issues after following this guide, check the Django logs (`logs/citis.log`) for specific error messages and consult the troubleshooting section above. 