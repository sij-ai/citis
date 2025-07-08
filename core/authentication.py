from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework import exceptions

from archive.models import ApiKey

User = get_user_model()

class ApiKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class for API keys.
    Handles both the MASTER_API_KEY and user-specific ApiKey models.
    """
    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).decode('utf-8')
        if not auth_header or not auth_header.lower().startswith('bearer '):
            return None  # No bearer token, authentication will fail.

        token = auth_header[7:] # Remove "Bearer " prefix

        # Case 1: Check for the Master API Key
        if settings.MASTER_API_KEY and token == settings.MASTER_API_KEY:
            # For the master key, we can return the first superuser as the "user"
            # Or you could create a specific system user.
            try:
                user = User.objects.filter(is_superuser=True).first()
                if not user:
                    raise exceptions.AuthenticationFailed('Master API key is valid, but no superuser exists to act as the request user.')
                return (user, 'master_key')
            except User.DoesNotExist:
                 raise exceptions.AuthenticationFailed('No superuser found for master key authentication.')

        # Case 2: Check for a standard user API key in the database
        try:
            api_key = ApiKey.objects.select_related('user').get(key=token)
        except ApiKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API Key.')

        if not api_key.user:
            raise exceptions.AuthenticationFailed('API Key is not associated with a user.')
            
        if not api_key.is_active or not api_key.user.is_active:
            raise exceptions.AuthenticationFailed('API Key or associated user is inactive.')

        # You could add usage limit checks here as well

        return (api_key.user, token)

    def authenticate_header(self, request):
        return 'Bearer'
