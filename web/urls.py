from django.urls import path
from . import views

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
    
    # Shortcode serving - MUST be last to avoid conflicts
    path('<str:shortcode>', views.shortcode_redirect, name='shortcode_redirect'),
] 