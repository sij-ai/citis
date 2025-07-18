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
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Run Development Server**
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

# Archive Engines  
ARCHIVE_MODE=singlefile  # singlefile, archivebox, or both
SINGLEFILE_EXECUTABLE_PATH=/path/to/single-file
SINGLEFILE_DATA_PATH=./archives

# Optional Services
STRIPE_SECRET_KEY=sk_test_...  # For billing
REDIS_URL=redis://localhost:6379  # For caching/Celery
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
