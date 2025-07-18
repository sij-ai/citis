from django.urls import path, include
from . import views
from . import stripe_views

app_name = 'web'

urlpatterns = [
    # Marketing pages
    path('', views.landing_page, name='landing'),
    path('pricing/', views.pricing_page, name='pricing'),
    path('about/', views.about_page, name='about'),
    
    # Dashboard and authenticated pages
    path('dashboard/', views.dashboard, name='dashboard'),
    path('shortcodes/', views.shortcode_list, name='shortcode_list'),
    path('shortcodes/<str:shortcode>/', views.shortcode_detail, name='shortcode_detail'),
    path('create/', views.create_archive, name='create_archive'),
    
    # HTMX endpoints for API key management
    path('api-keys/create/', views.create_api_key, name='create_api_key'),
    path('api-keys/<int:api_key_id>/update/', views.update_api_key, name='update_api_key'),
    path('api-keys/<int:api_key_id>/delete/', views.delete_api_key, name='delete_api_key'),
    
    # Utility endpoints
    path('highlight/', views.highlight_text, name='highlight_text'),
    
    # Stripe subscription endpoints
    path('stripe/create-checkout-session/', stripe_views.create_checkout_session, name='create_checkout_session'),
    path('stripe/subscription-success/', stripe_views.subscription_success, name='subscription_success'),
    path('stripe/billing-portal/', stripe_views.create_billing_portal_session, name='billing_portal'),
    path('stripe/cancel-subscription/', stripe_views.cancel_subscription, name='cancel_subscription'),
    
    # dj-stripe webhook endpoint (replaces our custom webhook)
    path('stripe/', include('djstripe.urls', namespace='djstripe')),
    
    # Favicon serving for shortcodes
    path('<str:shortcode>.favicon.ico', views.shortcode_favicon, name='shortcode_favicon'),
    
    # Shortcode serving - MUST be last to avoid conflicts
    path('<str:shortcode>', views.shortcode_redirect, name='shortcode_redirect'),
] 