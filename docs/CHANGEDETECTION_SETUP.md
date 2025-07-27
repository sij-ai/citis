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
CHANGEDETECTION_BASE_URL=http://localhost:5000
CHANGEDETECTION_API_KEY=your-api-key-here
```

## Setup Steps

### 1. Install and Configure ChangeDetection.io

First, set up your ChangeDetection.io instance. You can use Docker:

```bash
# Run ChangeDetection.io
docker run -d \
  --name changedetection \
  -p 5000:5000 \
  -v datastore-volume:/datastore \
  ghcr.io/dgtlmoon/changedetection.io
```

### 2. Get API Key

1. Open ChangeDetection.io web interface (http://localhost:5000)
2. Go to Settings → API
3. Generate an API key
4. Add it to your `.env` file as `CHANGEDETECTION_API_KEY`

### 3. Configure Webhook

Run the setup command to configure ChangeDetection.io to send notifications to cit.is:

```bash
python manage.py setup_changedetection
```

This will:
- Verify your ChangeDetection.io configuration
- Set up the webhook URL: `{SERVER_BASE_URL}/api/internal/webhook/changedetection`
- Display the plan-based frequency configuration

### 4. Verify Configuration

Check that everything is working:

```bash
python manage.py setup_changedetection --verify
```

## Management Commands

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