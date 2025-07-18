from django.urls import path
from . import views, stripe_views

app_name = 'web'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('pricing/', views.pricing_page, name='pricing'),
    path('about/', views.about_page, name='about'),
    
    # User-facing dashboard and archive management
    path('dashboard/', views.dashboard, name='dashboard'),
    path('archives/', views.shortcode_list, name='shortcode_list'),
    path('archives/create/', views.create_archive, name='create_archive'),
    path('archives/<str:shortcode>/', views.shortcode_detail, name='shortcode_detail'),
    
    # API Key Management
    path('api-keys/create/', views.create_api_key, name='create_api_key'),
    path('api-keys/<int:api_key_id>/delete/', views.delete_api_key, name='delete_api_key'),
    path('api-keys/<int:api_key_id>/update/', views.update_api_key, name='update_api_key'),

    # Stripe checkout and portal
    path('stripe/create-checkout-session/', stripe_views.create_checkout_session, name='create_checkout_session'),
    path('stripe/success/', stripe_views.subscription_success, name='subscription_success'),
    path('stripe/portal/', stripe_views.create_billing_portal_session, name='create_billing_portal_session'),
    path('stripe/cancel-subscription/', stripe_views.cancel_subscription, name='cancel_subscription'),

    # Shortcode redirect and favicon
    path('<str:shortcode>/favicon.ico', views.serve_favicon, name='serve_favicon'),
    path('<str:shortcode>/', views.shortcode_redirect, name='shortcode_redirect'),

] 