# Superuser and Master API Key Setup

This document explains how cit.is automatically sets up superuser accounts and master API keys.

## Automatic Setup

### Environment Configuration

Set these variables in your `.env` file:

```bash
MASTER_USER_EMAIL=admin@yourdomain.com
MASTER_USER_PASSWORD=your_secure_password
MASTER_API_KEY=your_master_api_key_here
```

**Important:** Do not use the example values (`admin@example.com`, `changeme123`). The system will skip setup if it detects these placeholder values.

### How It Works

1. **Automatic Startup**: When Django starts (via `runserver`, `gunicorn`, etc.), the system automatically:
   - Creates a superuser with the configured email/password
   - Sets the superuser's plan to "sovereign" with unlimited privileges
   - Creates an API key record in the database linked to the superuser
   - Verifies the superuser's email address

2. **Manual Setup**: You can also run setup manually:
   ```bash
   # Run the comprehensive setup script
   python setup_citis.py
   
   # Or run just the auto setup command
   python manage.py auto_setup
   
   # Force update existing superuser
   python manage.py auto_setup --force
   ```

### Superuser Privileges

Superusers automatically get:
- **Plan**: Sovereign (unlimited access)
- **API Keys**: Can create unlimited API keys
- **Archives**: Unlimited archive creation
- **Dashboard**: Shows "Administrator Account" instead of plan upgrade options
- **Pricing Page**: Shows "Administrator Account" instead of subscription options

### Master API Key Linking

The master API key (from `MASTER_API_KEY` environment variable) is:
- Stored as an actual `ApiKey` record in the database
- Linked to the superuser account
- Given unlimited usage (no daily/total limits)
- Named "Master API Key" with appropriate description

This means all archives created with the master API key will appear in the superuser's dashboard.

## Security Notes

1. **Change Default Credentials**: Always use real credentials, not the example values
2. **Secure API Key**: Generate a strong, unique master API key
3. **Email Verification**: The system automatically marks the superuser's email as verified
4. **Environment Variables**: Keep your `.env` file secure and out of version control

## Troubleshooting

### Setup Not Running
- Check that your environment variables are set correctly
- Ensure you're not using placeholder values
- Verify Django can connect to the database

### Superuser Already Exists
- The system will update existing superusers to have sovereign privileges
- Use `--force` flag to force update credentials
- Check database for existing superuser accounts

### API Key Issues
- Master API key is created automatically if `MASTER_API_KEY` is set
- Check the admin panel under "API Keys" to see all keys
- Ensure the master key is linked to the correct superuser

### Dashboard Shows Wrong Plan
- Run `python manage.py auto_setup --force` to update superuser privileges
- Check that `current_plan` is set to 'sovereign' in the database
- Verify `is_premium` is set to `True` for the superuser
