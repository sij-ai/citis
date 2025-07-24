# cit.is - Permanent Web Archiving

A Django-based SaaS for creating permanent, citable archives of web content. Perfect for researchers, journalists, and anyone who needs reliable citations that won't break.

## Features

- **Permanent Archives**: SingleFile and ArchiveBox integration for complete page preservation
- **Short URLs**: Generate memorable shortcodes for easy citation  
- **Text Highlighting**: Cite specific passages with fragment highlighting
- **Analytics**: Track archive views and usage patterns
- **REST API**: Full programmatic access for automation
- **User Management**: Accounts, subscription tiers, and team collaboration

## Quick Start

1. **Setup Environment**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   # Edit .env with your configuration (see Configuration section below)
   # At minimum, set: SERVER_BASE_URL, MASTER_USER_EMAIL, MASTER_USER_PASSWORD, MASTER_API_KEY
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Automated Setup**
   ```bash
   python setup_citis.py
   ```
   This single command handles migrations, site configuration, and superuser creation automatically from your `.env` settings.

4. **Stripe Billing Setup (Optional)**
   If you need subscription billing, follow the complete setup guide in [`STRIPE_SETUP.md`](STRIPE_SETUP.md) after completing the basic setup above.

5. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

Visit `http://localhost:8000` to access the web interface, or `/admin/` for administration.

## Configuration

Key environment variables in `.env`:

```bash
# Core Settings
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
SERVER_BASE_URL=https://yourdomain.com

# Master User (for API key authentication)
MASTER_USER_EMAIL=admin@yourdomain.com
MASTER_USER_PASSWORD=your-secure-password
MASTER_API_KEY=your-master-api-key

# Contact Information (optional)
SALES_EMAIL=sales@yourdomain.com

# Archive Engines  
ARCHIVE_MODE=singlefile  # singlefile, archivebox, or both
SINGLEFILE_EXECUTABLE_PATH=/path/to/single-file
SINGLEFILE_DATA_PATH=./archives

# Stripe Integration (Required for billing)
STRIPE_PUBLISHABLE_KEY=pk_live_...  # or pk_test_... for testing
STRIPE_SECRET_KEY=sk_live_...       # or sk_test_... for testing
STRIPE_WEBHOOK_SECRET=whsec_...     # From Stripe webhook configuration
STRIPE_PRICE_PREMIUM_MONTHLY=price_1ABC123def456
STRIPE_PRICE_PREMIUM_YEARLY=price_1XYZ789ghi012

# Optional Services  
REDIS_URL=redis://localhost:6379  # For caching/Celery

# Overlay Styling (optional)
OVERLAY_STYLE_BACKGROUND_COLOR=#000000
OVERLAY_STYLE_LINK_COLOR=#ffe100
OVERLAY_STYLE_ACCENT_COLOR=#ffe100
```

## Architecture

### Django Apps
- **`accounts/`** - User authentication and subscription management
- **`archive/`** - Core archiving functionality and shortcode management  
- **`analytics/`** - Visit tracking and usage statistics
- **`core/`** - Shared services and utilities
- **`web/`** - Web interface templates and views

### Key Models
- **`Shortcode`** - Archived URLs with metadata and analytics
- **`Visit`** - Analytics tracking for each archive access
- **`ApiKey`** - API access tokens with usage limits
- **`CustomUser`** - Extended user model with subscription details

### Services
- **`SingleFileManager`** - Complete page archiving with embedded resources
- **`ArchiveBoxManager`** - Multi-format archiving (HTML, PDF, screenshots)
- **`AssetExtractor`** - Favicon, screenshot, and PDF generation

## API Usage

```bash
# Create archive
curl -X POST "http://localhost:8000/api/v1/add" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"url": "https://example.com"}'

# List archives  
curl "http://localhost:8000/api/v1/shortcodes" \
  -H "Authorization: Bearer YOUR_API_KEY"

# Get analytics
curl "http://localhost:8000/api/v1/analytics/abc123" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Full API documentation available at `/api/docs/`

## Stripe Billing Setup

For subscription billing, you must configure Stripe integration including webhooks. This process has several complex steps that must be completed in the correct order.

**⚠️ Important**: Follow the complete guide in [`STRIPE_SETUP.md`](STRIPE_SETUP.md) - the webhook setup is particularly critical and will cause subscription failures if not configured properly.

Quick overview:
1. Set up Stripe products and prices in Stripe Dashboard
2. Configure environment variables (`STRIPE_*` keys above)
3. **Critical**: Run djstripe initialization commands to set up webhook processing
4. Configure webhook endpoint in Stripe Dashboard with correct URL
5. Test subscription flow

Common issues:
- Users don't become premium after payment → webhook misconfiguration
- 404 webhook errors → wrong webhook URL in Stripe Dashboard  
- 500 webhook errors → missing djstripe database objects

## Production Deployment

### Required Services
- **PostgreSQL** - Primary database
- **Redis** - Caching and Celery message broker  
- **Celery Workers** - Background task processing
- **SingleFile/ArchiveBox** - Archive generation engines

### Environment Setup
```bash
# Production settings
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://redis:6379/0

# Static files
STATIC_ROOT=/var/www/static
MEDIA_ROOT=/var/www/media

# Email
EMAIL_HOST=smtp.mailgun.org
EMAIL_HOST_USER=postmaster@yourdomain.com
EMAIL_HOST_PASSWORD=your-password
```

### Docker Deployment
```yaml
# docker-compose.yml example
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/citis
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  celery:
    build: .
    command: celery -A citis worker -l info
    depends_on:
      - db  
      - redis
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: citis
      POSTGRES_PASSWORD: password
  
  redis:
    image: redis:7-alpine
```

## Development Status

✅ **Completed**
- Django project structure and core models
- User authentication with django-allauth  
- REST API with Django REST Framework
- Web interface with Bootstrap 5 + HTMX
- Archive service integration (SingleFile/ArchiveBox)
- Admin interface and analytics

🚧 **In Progress**  
- Celery integration for background processing
- Stripe billing integration
- Enhanced analytics and reporting

📋 **Planned**
- Team collaboration features
- Webhook notifications
- Custom domain support
- Enhanced text fragment highlighting

## Contributing

This project is in active development. The core archiving functionality is complete, with ongoing work on scalability and additional features.

## License

*License to be determined*

---

**cit.is** - anchor your cites in time 
