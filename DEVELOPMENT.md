# Development Guide

## Running cit.is with Celery

### Prerequisites

1. **Redis Server** - Required for Celery message broker
   ```bash
   # Install Redis (Ubuntu/Debian)
   sudo apt install redis-server
   
   # Install Redis (macOS)
   brew install redis
   
   # Start Redis
   redis-server
   ```

2. **Environment Setup**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Add Redis URL to .env
   echo "REDIS_URL=redis://localhost:6379/0" >> .env
   ```

### Development Workflow

#### Terminal 1: Django Development Server
```bash
python manage.py runserver
```

#### Terminal 2: Celery Worker (All Queues)
```bash
celery -A citis worker --loglevel=info
```

#### Terminal 3: Celery Beat (Periodic Tasks)
```bash
celery -A citis beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Production Setup

#### Dedicated Workers by Queue
```bash
# Archive worker (CPU intensive)
celery -A citis worker -Q archive --loglevel=info --concurrency=2

# Assets worker (I/O intensive) 
celery -A citis worker -Q assets --loglevel=info --concurrency=4

# Analytics worker (lightweight)
celery -A citis worker -Q analytics --loglevel=info --concurrency=2
```

#### Using the Helper Script
```bash
# Start general worker
python manage_celery.py worker

# Start archive-specific worker
python manage_celery.py worker --queue archive --concurrency 2

# Start beat scheduler
python manage_celery.py beat

# Monitor with Flower (install with: pip install flower)
python manage_celery.py flower
```

### Monitoring

#### Celery Flower Web UI
```bash
# Install Flower
pip install flower

# Start monitoring (available at http://localhost:5555)
celery -A citis flower
```

#### Check Worker Status
```bash
# List active tasks
celery -A citis inspect active

# Worker statistics  
celery -A citis inspect stats

# Registered tasks
celery -A citis inspect registered
```

### Task Management

#### Archive Flow
1. User creates archive → `Shortcode` created immediately
2. `archive_url_task` triggered asynchronously → Archives URL
3. `extract_assets_task` triggered after 30s → Screenshots, PDFs, favicons
4. User gets immediate response, archiving happens in background

#### Visit Analytics
1. User visits shortcode → `Visit` record created immediately  
2. `update_visit_analytics_task` triggered → GeoIP lookup
3. Page loads immediately, analytics processed in background

### Troubleshooting

#### Worker Not Picking Up Tasks
```bash
# Check Redis connection
redis-cli ping

# Purge all tasks
celery -A citis purge

# Restart workers
pkill -f "celery worker"
python manage_celery.py worker
```

#### Failed Tasks
```bash
# Monitor failed tasks in Django admin
# Visit: http://localhost:8000/admin/django_celery_results/taskresult/

# Check logs
tail -f logs/citis.log
```

#### Memory Issues
```bash
# Limit worker memory (restart after 100 tasks)
celery -A citis worker --max-tasks-per-child=100

# Monitor memory usage
celery -A citis events
```

### Environment Variables

Add to your `.env` file:
```bash
# Required for Celery
REDIS_URL=redis://localhost:6379/0

# Optional: Celery monitoring
CELERY_FLOWER_PASSWORD=your-flower-password
``` 