"""
Webhook views for receiving external notifications.

This module handles incoming webhooks from services like ChangeDetection.io
for content integrity monitoring.
"""

import logging
import json
from typing import Dict, Any, List
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from .models import Shortcode, HealthCheck
from core.changedetection_service import get_changedetection_service

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_http_methods(["POST"]), name='dispatch')
class ChangeDetectionWebhookView(View):
    """
    Webhook endpoint for receiving ChangeDetection.io notifications.
    
    Processes content change notifications and creates health check records
    for affected shortcodes.
    """
    
    def post(self, request):
        """
        Handle ChangeDetection.io webhook notifications.
        
        Expected payload format:
        {
            "watch_uuid": "cc0cfffa-f449-477b-83ea-0caafd1dc091",
            "source_url": "https://example.com/article", 
            "diff_plaintext": "Text showing changes...",
            "diff_html": "<span>HTML diff markup...</span>",
            "change_detected_at": "1677103794",
            "title": "Watch Title"
        }
        """
        try:
            # Parse JSON payload
            if request.content_type != 'application/json':
                logger.warning(f"Invalid content type: {request.content_type}")
                return JsonResponse({'error': 'Content-Type must be application/json'}, status=400)
            
            try:
                payload = json.loads(request.body)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON payload: {e}")
                return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
            
            # Extract required fields
            source_url = payload.get('source_url')
            watch_uuid = payload.get('watch_uuid')
            diff_plaintext = payload.get('diff_plaintext', '')
            diff_html = payload.get('diff_html', '')
            change_detected_at = payload.get('change_detected_at')
            
            if not source_url or not watch_uuid:
                logger.error(f"Missing required fields in webhook payload: {payload}")
                return JsonResponse({'error': 'Missing required fields: source_url, watch_uuid'}, status=400)
            
            # Log the notification
            logger.info(f"Received ChangeDetection.io notification for {source_url} (watch: {watch_uuid})")
            
            # Find all shortcodes for this URL
            affected_shortcodes = self._find_affected_shortcodes(source_url)
            
            if not affected_shortcodes:
                logger.info(f"No shortcodes found for URL: {source_url}")
                return JsonResponse({
                    'status': 'ok',
                    'message': 'No shortcodes found for this URL',
                    'affected_shortcodes': 0
                })
            
            # Process content integrity alerts
            results = self._process_content_changes(
                affected_shortcodes, 
                payload,
                diff_plaintext,
                diff_html,
                change_detected_at
            )
            
            logger.info(f"Processed ChangeDetection.io notification: {len(results)} shortcodes affected")
            
            return JsonResponse({
                'status': 'ok',
                'message': 'Notification processed successfully',
                'affected_shortcodes': len(results),
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error processing ChangeDetection.io webhook: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)
    
    def _find_affected_shortcodes(self, source_url: str) -> List[Shortcode]:
        """
        Find all shortcodes that archive the given URL.
        
        Args:
            source_url: The URL that changed
            
        Returns:
            List of Shortcode objects
        """
        try:
            return list(Shortcode.objects.filter(url=source_url).select_related('creator_user'))
        except Exception as e:
            logger.error(f"Error finding shortcodes for URL {source_url}: {e}")
            return []
    
    def _process_content_changes(
        self, 
        shortcodes: List[Shortcode], 
        payload: Dict[str, Any],
        diff_plaintext: str,
        diff_html: str,
        change_detected_at: str
    ) -> List[Dict[str, Any]]:
        """
        Process content changes for affected shortcodes.
        
        Args:
            shortcodes: List of affected Shortcode objects
            payload: Full webhook payload
            diff_plaintext: Plain text diff
            diff_html: HTML diff
            change_detected_at: Timestamp string
            
        Returns:
            List of processing results
        """
        results = []
        
        for shortcode in shortcodes:
            try:
                result = self._create_health_check_record(
                    shortcode, payload, diff_plaintext, diff_html, change_detected_at
                )
                results.append(result)
                
                # If this is a significant change, we might want to trigger additional actions
                # like notifying the user, re-archiving, etc.
                if result['status'] in ['major_changes']:
                    self._handle_significant_change(shortcode, result)
                    
            except Exception as e:
                logger.error(f"Error processing shortcode {shortcode.shortcode}: {e}")
                results.append({
                    'shortcode': shortcode.shortcode,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    def _create_health_check_record(
        self,
        shortcode: Shortcode,
        payload: Dict[str, Any], 
        diff_plaintext: str,
        diff_html: str,
        change_detected_at: str
    ) -> Dict[str, Any]:
        """
        Create a health check record for content integrity changes.
        
        Args:
            shortcode: Shortcode object
            payload: Full webhook payload
            diff_plaintext: Plain text diff
            diff_html: HTML diff  
            change_detected_at: Timestamp string
            
        Returns:
            Dictionary with processing result
        """
        try:
            # Convert timestamp
            try:
                if change_detected_at:
                    # Convert Unix timestamp to datetime
                    checked_at = datetime.fromtimestamp(int(change_detected_at), tz=timezone.utc)
                else:
                    checked_at = timezone.now()
            except (ValueError, TypeError):
                checked_at = timezone.now()
            
            # Analyze the severity of changes
            status, similarity_ratio = self._analyze_change_severity(diff_plaintext, diff_html)
            
            # Prepare detailed results
            details = {
                'watch_uuid': payload.get('watch_uuid'),
                'change_detected_at': change_detected_at,
                'diff_plaintext': diff_plaintext[:1000] if diff_plaintext else '',  # Truncate for storage
                'diff_html': diff_html[:2000] if diff_html else '',  # Truncate for storage
                'similarity_ratio': similarity_ratio,
                'source': 'changedetection.io',
                'title': payload.get('title', ''),
                'full_payload': payload
            }
            
            # Create health check record
            with transaction.atomic():
                health_check = HealthCheck.objects.create(
                    shortcode=shortcode,
                    check_type='content_integrity',
                    status=status,
                    details=details,
                    checked_at=checked_at
                )
            
            logger.info(f"Created health check record for {shortcode.shortcode}: {status}")
            
            return {
                'shortcode': shortcode.shortcode,
                'status': status,
                'similarity_ratio': similarity_ratio,
                'health_check_id': health_check.id,
                'user_plan': shortcode.creator_user.current_plan if shortcode.creator_user else 'unknown'
            }
            
        except Exception as e:
            logger.error(f"Error creating health check record: {e}")
            raise
    
    def _analyze_change_severity(self, diff_plaintext: str, diff_html: str) -> tuple[str, float]:
        """
        Analyze the severity of detected changes.
        
        Args:
            diff_plaintext: Plain text diff
            diff_html: HTML diff
            
        Returns:
            Tuple of (status, similarity_ratio)
        """
        try:
            # Simple heuristic-based analysis
            # In a production system, you might want more sophisticated NLP analysis
            
            diff_text = diff_plaintext or diff_html or ''
            diff_length = len(diff_text)
            
            # Count change indicators (rough heuristic)
            added_lines = diff_text.count('+ ') + diff_text.count('<ins>')
            removed_lines = diff_text.count('- ') + diff_text.count('<del>')
            total_changes = added_lines + removed_lines
            
            # Estimate similarity ratio (inverse of change ratio)
            if diff_length == 0:
                similarity_ratio = 1.0
                status = 'ok'
            elif total_changes > 50 or diff_length > 5000:
                similarity_ratio = 0.3
                status = 'major_changes'
            elif total_changes > 10 or diff_length > 1000:
                similarity_ratio = 0.7
                status = 'minor_changes'
            else:
                similarity_ratio = 0.9
                status = 'minor_changes'
            
            return status, similarity_ratio
            
        except Exception as e:
            logger.error(f"Error analyzing change severity: {e}")
            return 'minor_changes', 0.5
    
    def _handle_significant_change(self, shortcode: Shortcode, result: Dict[str, Any]):
        """
        Handle significant content changes that may require user notification.
        
        Args:
            shortcode: Affected shortcode
            result: Processing result with change details
        """
        try:
            logger.info(f"Significant change detected for {shortcode.shortcode}: {result['status']}")
            
            # For now, just log the significant change
            # In the future, this could:
            # - Send email notifications to users
            # - Trigger re-archiving for Sovereign plan users
            # - Create dashboard alerts
            # - Update shortcode metadata
            
            # Example of what we might do for Sovereign plan users:
            if (shortcode.creator_user and 
                shortcode.creator_user.current_plan == 'sovereign' and
                result['similarity_ratio'] < 0.5):
                
                logger.info(f"Major change for Sovereign user {shortcode.creator_user.email}, "
                           f"consider triggering re-archival for {shortcode.shortcode}")
                
                # TODO: Implement re-archival task for Sovereign plan
                # from archive.tasks import archive_url_task
                # archive_url_task.delay(shortcode.shortcode, requester_ip=None)
                
        except Exception as e:
            logger.error(f"Error handling significant change: {e}")


# Function-based view wrapper for URL routing compatibility
@csrf_exempt
@require_http_methods(["POST"])
def changedetection_webhook(request):
    """Function-based wrapper for the ChangeDetection webhook."""
    view = ChangeDetectionWebhookView()
    return view.post(request) 