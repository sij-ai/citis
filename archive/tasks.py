"""
Archive service tasks for background processing.

This module contains Celery tasks for archiving URLs, extracting assets,
and performing health monitoring operations.
"""

import asyncio
import logging
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse, urljoin

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.contrib.gis.geoip2 import GeoIP2
from django.core.exceptions import ObjectDoesNotExist

from core.services import get_archive_managers, get_singlefile_manager
from core.changedetection_service import get_changedetection_service
from .models import Shortcode, Visit, HealthCheck

logger = logging.getLogger(__name__)


def calculate_directory_size_mb(directory_path: Path) -> float:
    """Calculate total size of directory in MB"""
    if not directory_path.exists() or not directory_path.is_dir():
        return 0.0
    
    total_size = 0
    try:
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    except (OSError, IOError) as e:
        logger.warning(f"Error calculating directory size for {directory_path}: {e}")
        return 0.0
    
    return total_size / (1024 * 1024)  # Convert bytes to MB


def calculate_archive_checksum(archive_path: Path) -> tuple[str, int]:
    """
    Calculate SHA256 checksum and total size of archived content.
    
    Returns:
        tuple: (hex_checksum, total_bytes)
    """
    if not archive_path.exists() or not archive_path.is_dir():
        return "", 0
    
    hasher = hashlib.sha256()
    total_bytes = 0
    
    try:
        # Get all files in directory, sorted for consistency
        files = sorted(archive_path.rglob('*'))
        
        for file_path in files:
            if file_path.is_file():
                try:
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            hasher.update(chunk)
                            total_bytes += len(chunk)
                except (OSError, IOError) as e:
                    logger.warning(f"Error reading file {file_path} for checksum: {e}")
                    continue
        
        return hasher.hexdigest(), total_bytes
        
    except Exception as e:
        logger.error(f"Error calculating checksum for {archive_path}: {e}")
        return "", 0


def generate_trust_timestamp(shortcode_obj):
    """
    Generate trusted timestamp based on user's plan.
    
    Args:
        shortcode_obj: Shortcode instance
        
    Returns:
        dict: Trust metadata with timestamp information
    """
    user = shortcode_obj.creator_user
    trust_metadata = {}
    
    if not user:
        # No user (master API key), use basic timestamp
        shortcode_obj.trust_timestamp = timezone.now()
        trust_metadata['type'] = 'basic'
        trust_metadata['source'] = 'server'
        
    elif user.current_plan == 'free':
        # Free tier: Basic server timestamp
        shortcode_obj.trust_timestamp = timezone.now()
        trust_metadata['type'] = 'basic'
        trust_metadata['source'] = 'server'
        
    elif user.current_plan == 'professional':
        # Professional tier: Enhanced timestamp (placeholder for TSA integration)
        shortcode_obj.trust_timestamp = timezone.now()
        trust_metadata['type'] = 'enhanced'
        trust_metadata['source'] = 'server_certified'
        trust_metadata['note'] = 'TSA integration coming soon'
        
    elif user.current_plan == 'sovereign':
        # Sovereign tier: Legal-grade timestamp (placeholder for commercial TSA)
        shortcode_obj.trust_timestamp = timezone.now()
        trust_metadata['type'] = 'legal_grade'
        trust_metadata['source'] = 'commercial_tsa'
        trust_metadata['note'] = 'Commercial TSA integration coming soon'
    
    shortcode_obj.trust_metadata = trust_metadata
    shortcode_obj.save(update_fields=['trust_timestamp', 'trust_metadata'])
    
    return trust_metadata


def enforce_archive_size_limit(shortcode_obj) -> bool:
    """
    Check if archive exceeds user's size limit and clean up if necessary.
    
    Returns:
        True if archive is within limits or no limit applies
        False if archive was deleted due to size limit
    """
    if not shortcode_obj.creator_user:
        return True  # No user = no limits (e.g., master API key)
    
    user = shortcode_obj.creator_user
    
    # Check if user has size limits (Sovereign has unlimited)
    if user.current_plan == 'sovereign':
        return True
    
    # Get archive path and check size
    archive_path = shortcode_obj.get_latest_archive_path()
    if not archive_path:
        return True  # No archive to check
    
    archive_size_mb = calculate_directory_size_mb(archive_path)
    max_size_mb = user.max_archive_size_mb
    
    logger.info(f"Archive {shortcode_obj.shortcode} size: {archive_size_mb:.2f}MB (limit: {max_size_mb}MB)")
    
    if archive_size_mb > max_size_mb:
        # Archive exceeds limit - delete it
        logger.warning(f"Archive {shortcode_obj.shortcode} exceeds size limit ({archive_size_mb:.2f}MB > {max_size_mb}MB), deleting")
        
        try:
            shutil.rmtree(archive_path)
            logger.info(f"Deleted oversized archive: {archive_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete oversized archive {archive_path}: {e}")
            return False
    
    return True


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def archive_url_task(self, shortcode_id, requester_ip=None):
    """
    Archive a URL using the configured archive managers.
    
    Args:
        shortcode_id: ID of the Shortcode instance to archive
        requester_ip: IP address of the requester for proxy selection
    """
    try:
        shortcode = Shortcode.objects.get(pk=shortcode_id)
        
        # Get archive managers
        managers = get_archive_managers()
        
        if not managers:
            logger.error("No archive managers configured")
            return {"success": False, "error": "No archive managers configured"}
        
        # Archive with configured methods
        archive_results = []
        
        for method_name, manager in managers.items():
            if shortcode.archive_method in [method_name, 'both']:
                try:
                    # Run async archive method in sync task with proxy support
                    if hasattr(manager, 'archive_url'):
                        # Check if the manager supports requester_ip parameter
                        import inspect
                        sig = inspect.signature(manager.archive_url)
                        if 'requester_ip' in sig.parameters:
                            result = asyncio.run(
                                manager.archive_url(shortcode.url, timezone.now(), requester_ip=requester_ip)
                            )
                        else:
                            # Fallback for managers that don't support proxy
                            result = asyncio.run(
                                manager.archive_url(shortcode.url, timezone.now())
                            )
                    else:
                        # Fallback for older manager interfaces
                        result = asyncio.run(
                            manager.archive_url(shortcode.url, timezone.now())
                        )
                    
                    archive_results.append(result)
                    
                    # Store proxy metadata in database if available
                    if 'proxy_metadata' in result and result['proxy_metadata']:
                        proxy_meta = result['proxy_metadata']
                        shortcode.proxy_ip = proxy_meta.get('proxy_ip')
                        shortcode.proxy_country = proxy_meta.get('proxy_country')
                        shortcode.proxy_provider = proxy_meta.get('proxy_provider')
                        shortcode.save(update_fields=['proxy_ip', 'proxy_country', 'proxy_provider'])
                        logger.info(f"Stored proxy metadata for {shortcode.shortcode}: {proxy_meta.get('proxy_ip')} ({proxy_meta.get('proxy_provider')})")
                    
                    logger.info(f"Archive created successfully for {shortcode.shortcode} using {method_name}")
                    
                except Exception as exc:
                    logger.error(f"Archive method {method_name} failed: {exc}")
                    archive_results.append({"error": str(exc), "method": method_name})
        
        # Check if at least one archive method succeeded
        success_count = sum(1 for result in archive_results if not result.get('error'))
        
        if success_count == 0:
            logger.error(f"All archive methods failed for {shortcode.shortcode}")
            return {
                "success": False, 
                "error": "All archive methods failed",
                "details": archive_results
            }
        
        # Enforce file size limits after successful archiving
        if not enforce_archive_size_limit(shortcode):
            logger.error(f"Archive {shortcode.shortcode} deleted due to size limit violation")
            return {
                "success": False,
                "error": f"Archive exceeds file size limit ({shortcode.creator_user.max_archive_size_mb}MB). Upgrade for larger limits.",
                "size_limit_exceeded": True
            }
        
        # Calculate and store archive checksum and metadata
        archive_path = shortcode.get_latest_archive_path()
        if archive_path:
            try:
                checksum, size_bytes = calculate_archive_checksum(archive_path)
                if checksum:
                    shortcode.archive_checksum = checksum
                    shortcode.archive_size_bytes = size_bytes
                    
                    # Generate trust timestamp based on user plan
                    trust_metadata = generate_trust_timestamp(shortcode)
                    
                    shortcode.save(update_fields=['archive_checksum', 'archive_size_bytes'])
                    
                    logger.info(f"Archive checksum calculated for {shortcode.shortcode}: {checksum[:16]}... ({size_bytes} bytes)")
                    logger.info(f"Trust metadata generated: {trust_metadata.get('type', 'basic')}")
                else:
                    logger.warning(f"Failed to calculate checksum for {shortcode.shortcode}")
                    
            except Exception as e:
                logger.error(f"Error calculating archive checksum for {shortcode.shortcode}: {e}")
        
        # Integrate with ChangeDetection.io for content integrity monitoring
        try:
            changedetection_service = get_changedetection_service()
            if changedetection_service.is_configured():
                logger.info(f"Setting up ChangeDetection.io monitoring for {shortcode.shortcode}")
                
                # Process archive creation with ChangeDetection.io
                success, message = changedetection_service.process_archive_creation(shortcode)
                
                if success:
                    logger.info(f"ChangeDetection.io integration successful for {shortcode.shortcode}: {message}")
                else:
                    logger.warning(f"ChangeDetection.io integration failed for {shortcode.shortcode}: {message}")
            else:
                logger.debug(f"ChangeDetection.io not configured, skipping monitoring setup for {shortcode.shortcode}")
                
        except Exception as e:
            logger.error(f"Error integrating with ChangeDetection.io for {shortcode.shortcode}: {e}")
        
        logger.info(f"Archive task completed successfully for {shortcode.shortcode}")
        return {
            "success": True,
            "results": archive_results,
            "methods_succeeded": success_count
        }
        
    except Shortcode.DoesNotExist:
        logger.error(f"Shortcode with ID {shortcode_id} not found")
        return {"success": False, "error": "Shortcode not found"}
    
    except Exception as exc:
        logger.error(f"Archive task failed: {exc}")
        
        # Retry the task with exponential backoff
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying archive task for shortcode {shortcode_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {"success": False, "error": str(exc)}


@shared_task
def extract_assets_task(shortcode_id):
    """
    Extract additional assets (favicon, screenshot, PDF) for an archive.
    
    This runs after the main archiving task to avoid blocking the user.
    """
    try:
        shortcode = Shortcode.objects.get(pk=shortcode_id)
        
        # Check if archive exists
        archive_path = shortcode.get_latest_archive_path()
        if not archive_path:
            logger.warning(f"No archive found for {shortcode.shortcode}, skipping asset extraction")
            return {"success": False, "error": "No archive found"}
        
        logger.info(f"Starting asset extraction for {shortcode.shortcode}")
        
        # Import here to avoid circular imports
        from core.services import AssetExtractor
        extractor = AssetExtractor()
        
        # Extract assets asynchronously
        tasks = []
        results = {}
        
        try:
            # Run the async asset extraction
            async def extract_all_assets():
                favicon_task = extractor.extract_favicon(shortcode.url, archive_path)
                screenshot_task = extractor.generate_screenshot(shortcode.url, archive_path)
                pdf_task = extractor.generate_pdf(shortcode.url, archive_path)
                
                return await asyncio.gather(
                    favicon_task, screenshot_task, pdf_task,
                    return_exceptions=True
                )
            
            favicon_result, screenshot_result, pdf_result = asyncio.run(extract_all_assets())
            
            results['favicon'] = not isinstance(favicon_result, Exception)
            results['screenshot'] = not isinstance(screenshot_result, Exception)
            results['pdf'] = not isinstance(pdf_result, Exception)
            
            if isinstance(favicon_result, Exception):
                logger.warning(f"Favicon extraction failed for {shortcode.shortcode}: {favicon_result}")
            if isinstance(screenshot_result, Exception):
                logger.warning(f"Screenshot generation failed for {shortcode.shortcode}: {screenshot_result}")
            if isinstance(pdf_result, Exception):
                logger.warning(f"PDF generation failed for {shortcode.shortcode}: {pdf_result}")
            
            logger.info(f"Asset extraction completed for {shortcode.shortcode}: {results}")
            
            return {"success": True, "assets": results}
            
        except Exception as e:
            logger.error(f"Asset extraction failed for {shortcode.shortcode}: {e}")
            return {"success": False, "error": str(e)}
        
    except Shortcode.DoesNotExist:
        logger.error(f"Shortcode with ID {shortcode_id} not found for asset extraction")
        return {"success": False, "error": "Shortcode not found"}
    
    except Exception as exc:
        logger.error(f"Asset extraction task failed: {exc}")
        return {"success": False, "error": str(exc)}


@shared_task
def check_link_health_task(shortcode_id):
    """
    Check if the original URL for a shortcode is still accessible.
    
    This implements the "Link Health Check" feature from pricing tiers.
    """
    import httpx
    
    try:
        shortcode = Shortcode.objects.get(pk=shortcode_id)
        
        logger.info(f"Checking link health for {shortcode.shortcode}: {shortcode.url}")
        
        # Check the original URL
        async def check_url_status():
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                try:
                    response = await client.head(shortcode.url)
                    return {
                        "status_code": response.status_code,
                        "accessible": 200 <= response.status_code < 400,
                        "redirect_url": str(response.url) if response.url != shortcode.url else None
                    }
                except httpx.TimeoutException:
                    return {"status_code": None, "accessible": False, "error": "Timeout"}
                except httpx.RequestError as e:
                    return {"status_code": None, "accessible": False, "error": str(e)}
        
        result = asyncio.run(check_url_status())
        
        # Create or update health check record
        from archive.models import HealthCheck
        health_check = HealthCheck.objects.create(
            shortcode=shortcode,
            check_type='link_health',
            status='ok' if result['accessible'] else 'broken',
            details=result,
            checked_at=timezone.now()
        )
        
        # Log status change
        if not result['accessible']:
            logger.warning(f"Link health check failed for {shortcode.shortcode}: {result.get('error', 'Unknown error')}")
        else:
            logger.info(f"Link health check passed for {shortcode.shortcode}")
        
        return {
            "success": True,
            "shortcode": shortcode.shortcode,
            "accessible": result['accessible'],
            "status_code": result.get('status_code'),
            "health_check_id": health_check.id
        }
        
    except Shortcode.DoesNotExist:
        logger.error(f"Shortcode with ID {shortcode_id} not found for health check")
        return {"success": False, "error": "Shortcode not found"}
    
    except Exception as exc:
        logger.error(f"Link health check failed: {exc}")
        return {"success": False, "error": str(exc)}


@shared_task  
def content_integrity_scan_task(shortcode_id):
    """
    Compare current content with archived content to detect changes.
    
    This implements the "Content Integrity Scan" feature from pricing tiers.
    """
    import httpx
    from difflib import SequenceMatcher
    from bs4 import BeautifulSoup
    
    try:
        shortcode = Shortcode.objects.get(pk=shortcode_id)
        
        # Get archived content
        archive_path = shortcode.get_latest_archive_path()
        if not archive_path:
            logger.warning(f"No archive found for integrity scan: {shortcode.shortcode}")
            return {"success": False, "error": "No archive found"}
        
        singlefile_path = archive_path / "singlefile.html"
        if not singlefile_path.exists():
            logger.warning(f"Archive file not found for integrity scan: {singlefile_path}")
            return {"success": False, "error": "Archive file not found"}
        
        logger.info(f"Starting content integrity scan for {shortcode.shortcode}")
        
        # Read archived content
        with open(singlefile_path, 'r', encoding='utf-8', errors='ignore') as f:
            archived_content = f.read()
        
        # Fetch current content
        async def fetch_current_content():
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                try:
                    response = await client.get(shortcode.url)
                    if 200 <= response.status_code < 400:
                        return response.text
                    else:
                        return None
                except Exception as e:
                    logger.warning(f"Failed to fetch current content for {shortcode.shortcode}: {e}")
                    return None
        
        current_content = asyncio.run(fetch_current_content())
        
        if current_content is None:
            # URL not accessible, create health check record instead
            from archive.models import HealthCheck
            health_check = HealthCheck.objects.create(
                shortcode=shortcode,
                check_type='content_integrity',
                status='broken',
                details={"error": "URL not accessible"},
                checked_at=timezone.now()
            )
            
            return {
                "success": True,
                "shortcode": shortcode.shortcode,
                "status": "broken",
                "health_check_id": health_check.id
            }
        
        # Extract text content for comparison (ignore styling changes)
        def extract_text_content(html_content):
            try:
                soup = BeautifulSoup(html_content, 'lxml')
                # Remove script and style elements
                for element in soup(['script', 'style', 'noscript']):
                    element.decompose()
                return soup.get_text(separator=' ', strip=True)
            except Exception:
                return html_content
        
        archived_text = extract_text_content(archived_content)
        current_text = extract_text_content(current_content)
        
        # Calculate similarity ratio
        similarity = SequenceMatcher(None, archived_text, current_text).ratio()
        
        # Determine status based on similarity threshold
        if similarity >= 0.95:
            status = 'ok'
        elif similarity >= 0.8:
            status = 'minor_changes'
        else:
            status = 'major_changes'
        
        # Create integrity check record
        from archive.models import HealthCheck
        health_check = HealthCheck.objects.create(
            shortcode=shortcode,
            check_type='content_integrity',
            status=status,
            details={
                "similarity_ratio": similarity,
                "content_length_archived": len(archived_text),
                "content_length_current": len(current_text)
            },
            checked_at=timezone.now()
        )
        
        if status != 'ok':
            logger.warning(f"Content integrity scan detected changes for {shortcode.shortcode}: {status} (similarity: {similarity:.3f})")
        else:
            logger.info(f"Content integrity scan passed for {shortcode.shortcode} (similarity: {similarity:.3f})")
        
        return {
            "success": True,
            "shortcode": shortcode.shortcode,
            "status": status,
            "similarity_ratio": similarity,
            "health_check_id": health_check.id
        }
        
    except Shortcode.DoesNotExist:
        logger.error(f"Shortcode with ID {shortcode_id} not found for integrity scan")
        return {"success": False, "error": "Shortcode not found"}
    
    except Exception as exc:
        logger.error(f"Content integrity scan failed: {exc}")
        return {"success": False, "error": str(exc)}


@shared_task
def bulk_health_monitoring_task(plan_filter=None, check_type='link_health'):
    """
    Run health monitoring for multiple shortcodes based on their user's plan.
    
    Args:
        plan_filter: Filter by user plan ('free', 'professional', 'sovereign')
        check_type: Type of check ('link_health' or 'content_integrity')
    """
    from django.contrib.auth import get_user_model
    from datetime import timedelta
    
    User = get_user_model()
    
    try:
        # Get users based on plan filter
        if plan_filter:
            users = User.objects.filter(current_plan=plan_filter)
        else:
            users = User.objects.all()
        
        # Get shortcodes for these users
        shortcode_query = Shortcode.objects.filter(creator_user__in=users)
        
        # Filter by last check time based on plan
        now = timezone.now()
        if plan_filter == 'free' and check_type == 'link_health':
            # Free tier: check once per day
            cutoff = now - timedelta(days=1)
        elif plan_filter == 'professional' and check_type == 'link_health':
            # Professional tier: check every 5 minutes  
            cutoff = now - timedelta(minutes=5)
        elif plan_filter == 'professional' and check_type == 'content_integrity':
            # Professional tier: check every hour
            cutoff = now - timedelta(hours=1)
        elif plan_filter == 'sovereign':
            # Sovereign tier: more frequent checks
            if check_type == 'content_integrity':
                cutoff = now - timedelta(minutes=5)
            else:
                cutoff = now - timedelta(minutes=1)  # Near real-time
        else:
            # Default fallback
            cutoff = now - timedelta(hours=24)
        
        # Find shortcodes that need checking
        from archive.models import HealthCheck
        recently_checked = HealthCheck.objects.filter(
            check_type=check_type,
            checked_at__gte=cutoff
        ).values_list('shortcode_id', flat=True)
        
        shortcodes_to_check = shortcode_query.exclude(
            shortcode__in=recently_checked
        )[:100]  # Limit batch size
        
        scheduled_count = 0
        for shortcode in shortcodes_to_check:
            if check_type == 'link_health':
                check_link_health_task.delay(shortcode.pk)
            elif check_type == 'content_integrity':
                content_integrity_scan_task.delay(shortcode.pk)
            scheduled_count += 1
        
        logger.info(f"Scheduled {scheduled_count} {check_type} checks for plan: {plan_filter or 'all'}")
        
        return {
            "success": True,
            "scheduled_count": scheduled_count,
            "plan_filter": plan_filter,
            "check_type": check_type
        }
        
    except Exception as exc:
        logger.error(f"Bulk health monitoring failed: {exc}")
        return {"success": False, "error": str(exc)}


@shared_task
def update_visit_analytics_task(visit_id):
    """
    Update visit analytics with geolocation data.
    
    Args:
        visit_id: ID of the Visit instance to update
    """
    try:
        visit = Visit.objects.get(pk=visit_id)
        
        # Update geolocation if we have an IP address
        if visit.ip_address and not visit.country:
            visit.update_geolocation()
        
        logger.debug(f"Updated analytics for visit {visit_id}")
        return {"success": True, "visit_id": visit_id}
        
    except Visit.DoesNotExist:
        logger.error(f"Visit with ID {visit_id} not found")
        return {"success": False, "error": "Visit not found"}
    
    except Exception as exc:
        logger.error(f"Analytics update failed: {exc}")
        return {"success": False, "error": str(exc)}


@shared_task
def cleanup_failed_archives_task():
    """
    Periodic task to clean up failed archive attempts.
    """
    from django.conf import settings
    
    # Clean up old failed archives (older than 24 hours)
    cutoff = timezone.now() - timezone.timedelta(hours=24)
    
    # Get all old shortcodes and check their archive status
    old_shortcodes = Shortcode.objects.filter(created_at__lt=cutoff)
    
    cleaned_count = 0
    for shortcode in old_shortcodes:
        try:
            # Only clean up if not properly archived
            if not shortcode.is_archived():
                # Look for any orphaned archive directories for this URL
                archive_paths = shortcode._get_archive_paths_for_url()
                for archive_path in archive_paths:
                    if archive_path.exists():
                        # Check if the archive is incomplete (no singlefile.html)
                        singlefile_path = archive_path / "singlefile.html"
                        if not singlefile_path.exists():
                            import shutil
                            shutil.rmtree(archive_path)
                            logger.info(f"Cleaned up incomplete archive: {archive_path}")
                            cleaned_count += 1
        except Exception as e:
            logger.error(f"Error cleaning up archive for {shortcode.shortcode}: {e}")
    
    logger.info(f"Cleaned up {cleaned_count} failed archives")
    return {"cleaned_count": cleaned_count} 