from django.apps import AppConfig
import os


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    
    def ready(self):
        """
        Run startup tasks when the app is ready.
        
        This ensures superuser and master API key are set up automatically
        when Django starts, but only in certain conditions to avoid issues
        during migrations or other management commands.
        """
        # Only run auto setup in specific scenarios
        # Skip during migrations, testing, and other management commands
        import sys
        
        # Check if we're running a management command
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            # Only run auto setup for runserver and during normal app startup
            if command in ['runserver', 'gunicorn', 'uwsgi'] or 'runserver' in sys.argv:
                # Also check if we have the required environment variables
                from django.conf import settings
                
                master_email = getattr(settings, 'MASTER_USER_EMAIL', None)
                master_password = getattr(settings, 'MASTER_USER_PASSWORD', None)
                
                # Only run if we have proper configuration and not the example values
                if (master_email and master_password and 
                    master_email != 'admin@example.com' and 
                    master_password != 'changeme123'):
                    
                    try:
                        from django.core.management import call_command
                        call_command('auto_setup')
                    except Exception as e:
                        # Don't fail app startup if setup fails
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Auto setup failed during app startup: {e}")
