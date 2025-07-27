# ChangeDetection.io Integration Setup

This guide explains how to set up and configure ChangeDetection.io integration for content integrity monitoring in cit.is.

## Overview

The ChangeDetection.io integration provides automated content integrity monitoring for Professional and Sovereign plan users. When a user creates an archive, cit.is automatically sets up monitoring in ChangeDetection.io to detect when the original content changes.

## Plan-Based Features

- **Free Tier**: No content integrity monitoring (basic link health only)
- **Professional Tier**: Content integrity scans every hour, link health checks every 5 minutes
- **Sovereign Tier**: Content integrity scans every 5 minutes, link health checks every minute

## Configuration

Add these environment variables to your `.env` file:

```bash
# ChangeDetection.io Integration
CHANGEDETECTION_ENABLED=True
CHANGEDETECTION_BASE_URL=http://localhost:5000  # Or http://changedetection:5000 for Docker Compose
CHANGEDETECTION_API_KEY=your-api-key-here
CHANGEDETECTION_PORT=5000  # Port to expose ChangeDetection.io on
```

**Note**: When using Docker Compose (recommended), services communicate via internal Docker network. The `CHANGEDETECTION_BASE_URL` should be `http://changedetection:5000` for internal communication.

## Setup Steps

### 1. Install and Configure ChangeDetection.io

ChangeDetection.io is automatically managed via Docker Compose. Simply enable it in your configuration:

```bash
# Enable ChangeDetection.io in your .env file
CHANGEDETECTION_ENABLED=True
CHANGEDETECTION_API_KEY=your-api-key-here
```

The deployment script will automatically start ChangeDetection.io when you start your services:

```bash
# Start all services (including ChangeDetection.io if enabled)
./deploy.sh start

# Or start ChangeDetection.io individually
./deploy.sh start-changedetection
```

### 2. Start Services and Get API Key

1. Start ChangeDetection.io via the deployment script:
   ```bash
   ./deploy.sh start-changedetection
   ```

2. Open ChangeDetection.io web interface at http://localhost:5000
3. Go to Settings → API
4. Generate an API key
5. Add it to your `.env` file as `CHANGEDETECTION_API_KEY`
6. Restart the services to pick up the new API key:
   ```bash
   ./deploy.sh restart
   ```

### 3. Automatic Setup

When you start ChangeDetection.io with a configured API key, the deployment script automatically:
- Verifies the ChangeDetection.io configuration
- Sets up the webhook URL: `{SERVER_BASE_URL}/api/internal/webhook/changedetection`
- Displays setup status

For manual setup or verification:

```bash
python manage.py setup_changedetection
```

### 4. Verify Configuration

Check that everything is working:

```bash
python manage.py setup_changedetection --verify
```

Or check the service status:

```bash
./deploy.sh status
```

## Management Commands

### Deployment Script Commands

```bash
# Start all services (including ChangeDetection.io if enabled)
./deploy.sh start

# Start only ChangeDetection.io
./deploy.sh start-changedetection

# Stop ChangeDetection.io
./deploy.sh stop-changedetection

# Check service status
./deploy.sh status

# Restart all services
./deploy.sh restart
```

### Setup and Configuration

```bash
# Initial setup
python manage.py setup_changedetection

# Verify configuration
python manage.py setup_changedetection --verify
```

### Watch Management

```bash
# List all watches
python manage.py manage_changedetection_watches list

# Show statistics
python manage.py manage_changedetection_watches stats

# Sync existing shortcodes with ChangeDetection.io
python manage.py manage_changedetection_watches sync

# Dry run sync (show what would be done)
python manage.py manage_changedetection_watches sync --dry-run

# Sync only specific plan tier
python manage.py manage_changedetection_watches sync --plan professional

# Find orphaned watches
python manage.py manage_changedetection_watches orphaned

# Update watch frequency for specific URL
python manage.py manage_changedetection_watches update https://example.com professional
```

## How It Works

### Archive Creation Flow

1. User creates an archive (Professional/Sovereign plans only)
2. After successful archiving, cit.is calls ChangeDetection.io API
3. Checks if URL is already being monitored
4. If exists, updates frequency if current user's plan requires more frequent monitoring
5. If not exists, creates new watch with appropriate frequency
6. ChangeDetection.io monitors the URL and sends webhooks when changes are detected

### Webhook Processing

When ChangeDetection.io detects changes:

1. Sends POST request to `/api/internal/webhook/changedetection`
2. cit.is processes the notification:
   - Finds all shortcodes for the changed URL
   - Analyzes the severity of changes
   - Creates `HealthCheck` records
   - For significant changes on Sovereign plans, may trigger re-archival

### Frequency Configuration

The monitoring frequencies are configured in `settings.py`:

```python
CHANGEDETECTION_PLAN_FREQUENCIES = {
    'free': {'days': 1},              # Daily (not used for content integrity)
    'professional': {'hours': 1},     # Every hour
    'sovereign': {'minutes': 5}       # Every 5 minutes
}

CHANGEDETECTION_HEALTH_FREQUENCIES = {
    'free': {'days': 1},              # Daily health checks
    'professional': {'minutes': 5},   # Every 5 minutes
    'sovereign': {'minutes': 1}       # Every minute
}
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check `CHANGEDETECTION_BASE_URL` is correct
   - Verify ChangeDetection.io is running and accessible
   - Check firewall settings

2. **Authentication Failed**
   - Verify `CHANGEDETECTION_API_KEY` is correct
   - Check API key hasn't expired
   - Ensure API access is enabled in ChangeDetection.io settings

3. **Webhook Not Receiving Notifications**
   - Check webhook URL is accessible from ChangeDetection.io
   - Verify `SERVER_BASE_URL` is correct
   - Check logs for webhook processing errors

### Debug Commands

```bash
# Check configuration
python manage.py setup_changedetection --verify

# View watch statistics
python manage.py manage_changedetection_watches stats

# List all watches in JSON format
python manage.py manage_changedetection_watches list --format json
```

### Log Monitoring

Monitor these log entries:
- `Successfully created ChangeDetection.io watch` - Watch creation
- `Received ChangeDetection.io notification` - Webhook received
- `Created health check record` - Change processed

## Security Considerations

- Keep your ChangeDetection.io API key secure
- Ensure webhook endpoint is only accessible to ChangeDetection.io
- Monitor for webhook abuse or unexpected traffic
- Consider rate limiting on webhook endpoint for production

## Performance Notes

- ChangeDetection.io watches are only created for Professional and Sovereign users
- Multiple shortcodes for the same URL share a single watch
- Frequency is automatically updated to the highest tier requirement
- Webhook processing is asynchronous and doesn't block archive creation 