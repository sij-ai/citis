"""
ChangeDetection.io API integration service.

This service handles all interactions with the ChangeDetection.io API
for content integrity monitoring based on user plan tiers.
"""

import logging
import requests
import json
from typing import Dict, Any, Optional, List, Tuple
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


class ChangeDetectionService:
    """
    Service for integrating with ChangeDetection.io API.
    
    Handles watch creation, updates, and frequency management
    based on user plan tiers.
    """
    
    def __init__(self):
        self.base_url = settings.CHANGEDETECTION_BASE_URL.rstrip('/')
        self.api_key = settings.CHANGEDETECTION_API_KEY
        self.enabled = settings.CHANGEDETECTION_ENABLED
        
        # Plan frequency mappings from settings
        self.plan_frequencies = settings.CHANGEDETECTION_PLAN_FREQUENCIES
        self.health_frequencies = settings.CHANGEDETECTION_HEALTH_FREQUENCIES
        
        # Headers for API requests
        self.headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def is_configured(self) -> bool:
        """Check if ChangeDetection.io is properly configured."""
        return (
            self.enabled and 
            bool(self.base_url) and 
            bool(self.api_key)
        )
    
    def convert_to_seconds(self, time_obj: Dict[str, int]) -> int:
        """
        Convert time object to total seconds.
        
        Args:
            time_obj: Dictionary with keys like 'weeks', 'days', 'hours', 'minutes', 'seconds'
            
        Returns:
            Total seconds as integer
        """
        return (
            time_obj.get('weeks', 0) * 604800 +
            time_obj.get('days', 0) * 86400 +
            time_obj.get('hours', 0) * 3600 +
            time_obj.get('minutes', 0) * 60 +
            time_obj.get('seconds', 0)
        )
    
    def get_plan_frequency(self, plan: str, check_type: str = 'content_integrity') -> Dict[str, int]:
        """
        Get frequency configuration for a plan tier.
        
        Args:
            plan: User's plan tier ('free', 'professional', 'sovereign')
            check_type: Type of check ('content_integrity' or 'link_health')
            
        Returns:
            Dictionary with time units for ChangeDetection.io
        """
        if check_type == 'link_health':
            return self.health_frequencies.get(plan, self.health_frequencies['free'])
        else:
            return self.plan_frequencies.get(plan, self.plan_frequencies['free'])
    
    def setup_webhook_notification(self) -> Tuple[bool, str]:
        """
        One-time setup: Configure ChangeDetection.io to send notifications to our webhook.
        
        Returns:
            Tuple of (success, message)
        """
        if not self.is_configured():
            return False, "ChangeDetection.io not configured"
        
        try:
            # Construct webhook URL
            webhook_url = f"json://{settings.SERVER_BASE_URL}/api/internal/webhook/changedetection"
            
            # Register webhook URL
            url = f"{self.base_url}/api/v1/notifications"
            data = {
                "notification_urls": [webhook_url]
            }
            
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully configured ChangeDetection.io webhook: {webhook_url}")
                return True, "Webhook configured successfully"
            else:
                error_msg = f"Failed to configure webhook: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error configuring ChangeDetection.io webhook: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_all_watches(self) -> Optional[Dict[str, Any]]:
        """
        Get all existing watches from ChangeDetection.io.
        
        Returns:
            Dictionary of watches keyed by UUID, or None if error
        """
        if not self.is_configured():
            return None
        
        try:
            url = f"{self.base_url}/api/v1/watch"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get watches: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting watches from ChangeDetection.io: {str(e)}")
            return None
    
    def find_watch_for_url(self, target_url: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Find existing watch for a specific URL.
        
        Args:
            target_url: URL to search for
            
        Returns:
            Tuple of (uuid, watch_data) if found, None otherwise
        """
        watches = self.get_all_watches()
        if not watches:
            return None
        
        for uuid, watch_data in watches.items():
            if watch_data.get('url') == target_url:
                return uuid, watch_data
        
        return None
    
    def get_watch_details(self, watch_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific watch.
        
        Args:
            watch_uuid: UUID of the watch
            
        Returns:
            Watch details including frequency information
        """
        if not self.is_configured():
            return None
        
        try:
            url = f"{self.base_url}/api/v1/watch/{watch_uuid}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get watch details: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting watch details from ChangeDetection.io: {str(e)}")
            return None
    
    def create_watch(self, url: str, plan: str, check_type: str = 'content_integrity') -> Optional[str]:
        """
        Create a new watch in ChangeDetection.io.
        
        Args:
            url: URL to monitor
            plan: User's plan tier
            check_type: Type of check to configure
            
        Returns:
            Watch UUID if created successfully, None otherwise
        """
        if not self.is_configured():
            return None
        
        try:
            frequency = self.get_plan_frequency(plan, check_type)
            
            # Prepare notification body template (JSON string with escaping)
            notification_body = json.dumps({
                "watch_uuid": "{{watch_uuid}}",
                "source_url": "{{watch_url}}",
                "change_detected_at": "{{last_changed}}",
                "diff_plaintext": "{{diff_plaintext}}",
                "diff_html": "{{diff}}",
                "title": "{{title}}"
            }).replace('"', '\\"')
            
            # Prepare watch data
            watch_data = {
                "url": url,
                "title": f"Citis Archive Monitor: {url}",
                "time_between_check": frequency,
                "notification_format": "json",
                "notification_body": notification_body
            }
            
            # Create watch
            create_url = f"{self.base_url}/api/v1/watch"
            response = requests.post(create_url, headers=self.headers, json=watch_data, timeout=30)
            
            if response.status_code in [200, 201]:
                # Extract UUID from response if available, or find it by URL
                response_data = response.json() if response.content else {}
                watch_uuid = response_data.get('uuid')
                
                if not watch_uuid:
                    # Find the newly created watch
                    result = self.find_watch_for_url(url)
                    if result:
                        watch_uuid = result[0]
                
                if watch_uuid:
                    logger.info(f"Successfully created ChangeDetection.io watch for {url} (plan: {plan})")
                    return watch_uuid
                else:
                    logger.warning(f"Watch created but UUID not found for {url}")
                    return "unknown"
            else:
                error_msg = f"Failed to create watch: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return None
                
        except Exception as e:
            logger.error(f"Error creating ChangeDetection.io watch: {str(e)}")
            return None
    
    def update_watch_frequency(self, watch_uuid: str, plan: str, check_type: str = 'content_integrity') -> bool:
        """
        Update the frequency of an existing watch.
        
        Args:
            watch_uuid: UUID of the watch to update
            plan: User's plan tier  
            check_type: Type of check
            
        Returns:
            True if updated successfully, False otherwise
        """
        if not self.is_configured():
            return False
        
        try:
            frequency = self.get_plan_frequency(plan, check_type)
            
            update_data = {
                "time_between_check": frequency
            }
            
            url = f"{self.base_url}/api/v1/watch/{watch_uuid}"
            response = requests.put(url, headers=self.headers, json=update_data, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Successfully updated ChangeDetection.io watch {watch_uuid} frequency for plan {plan}")
                return True
            else:
                error_msg = f"Failed to update watch frequency: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return False
                
        except Exception as e:
            logger.error(f"Error updating ChangeDetection.io watch frequency: {str(e)}")
            return False
    
    def process_archive_creation(self, shortcode_obj) -> Tuple[bool, str]:
        """
        Main workflow: Process archive creation by managing ChangeDetection.io watches.
        
        This implements the complete workflow from the implementation plan:
        1. Check if URL is already monitored
        2. If exists, evaluate and update frequency if needed
        3. If not exists, create new watch
        
        Args:
            shortcode_obj: Shortcode model instance
            
        Returns:
            Tuple of (success, message)
        """
        if not self.is_configured():
            return True, "ChangeDetection.io monitoring disabled"
        
        if not shortcode_obj.creator_user:
            return True, "No user associated with shortcode"
        
        url = shortcode_obj.url
        user_plan = shortcode_obj.creator_user.current_plan
        
        # Skip monitoring for free tier (content integrity not included)
        if user_plan == 'free':
            return True, "Content integrity monitoring not available for free tier"
        
        try:
            # Step 1: Check if URL is already monitored
            existing_watch = self.find_watch_for_url(url)
            
            if existing_watch:
                watch_uuid, watch_data = existing_watch
                
                # Step 2: Evaluate and update frequency if needed
                watch_details = self.get_watch_details(watch_uuid)
                if not watch_details:
                    return False, "Failed to get existing watch details"
                
                current_frequency = watch_details.get('time_between_check', {})
                required_frequency = self.get_plan_frequency(user_plan)
                
                current_seconds = self.convert_to_seconds(current_frequency)
                required_seconds = self.convert_to_seconds(required_frequency)
                
                # Update if current interval is longer (less frequent) than required
                if current_seconds > required_seconds:
                    success = self.update_watch_frequency(watch_uuid, user_plan)
                    if success:
                        return True, f"Updated existing watch frequency for {user_plan} plan"
                    else:
                        return False, "Failed to update watch frequency"
                else:
                    return True, f"Existing watch frequency already sufficient for {user_plan} plan"
            
            else:
                # Step 3: Create new watch
                watch_uuid = self.create_watch(url, user_plan)
                if watch_uuid:
                    return True, f"Created new ChangeDetection.io watch for {user_plan} plan"
                else:
                    return False, "Failed to create new watch"
                    
        except Exception as e:
            error_msg = f"Error processing ChangeDetection.io integration: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


# Global service instance
_changedetection_service = None

def get_changedetection_service() -> ChangeDetectionService:
    """Get the global ChangeDetection.io service instance."""
    global _changedetection_service
    if _changedetection_service is None:
        _changedetection_service = ChangeDetectionService()
    return _changedetection_service 