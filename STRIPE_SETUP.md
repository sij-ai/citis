# Stripe Setup Guide

## Quick Fix for Subscription Errors

If you're seeing "Subscription system is not properly configured" errors, you need to set up your Stripe Price IDs.

## Steps to Configure Stripe

### 1. Create Stripe Products & Prices

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

5. Save the product and **copy the Price ID** (starts with `price_`)

### 2. Environment Variables

Add these to your `.env` file:

```bash
# Stripe API Keys
STRIPE_PUBLISHABLE_KEY=pk_test_...         # or pk_live_...
STRIPE_SECRET_KEY=sk_test_...              # or sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...            # for dj-stripe webhooks

# Stripe Price IDs (copy from step 1)
STRIPE_PRICE_PREMIUM_MONTHLY=price_1ABC123def456
STRIPE_PRICE_PREMIUM_YEARLY=price_1XYZ789ghi012
```

### 3. Test the Integration

1. Restart your Django server
2. Go to the pricing page while logged in
3. Click "Upgrade to Professional" 
4. You should be redirected to Stripe Checkout

## Troubleshooting

**Error: "Invalid price selection"**
- Check that the price ID is correctly copied from Stripe Dashboard

**Error: "Payment system error"**
- Verify your Stripe API keys are correct
- Check that the price ID exists in your Stripe account

**Error: "Subscription system is not properly configured"**
- Missing Stripe price IDs in environment variables - add them to your `.env` file

## Development vs Production

- Use **test** keys (`sk_test_`, `pk_test_`) for development
- Use **live** keys (`sk_live_`, `pk_live_`) for production
- Never commit API keys to version control - use environment variables 