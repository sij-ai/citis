"""
Celery tasks for archive operations.
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from celery import shared_task
from django.utils import timezone

from .models import Shortcode, Visit
from core.services import get_archive_managers
from core.utils import get_client_ip

logger = logging.getLogger(__name__)


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
                                manager.archive_url(shortcode.url, datetime.now(timezone.utc), requester_ip=requester_ip)
                            )
                        else:
                            # Fallback for managers that don't support proxy
                            result = asyncio.run(
                                manager.archive_url(shortcode.url, datetime.now(timezone.utc))
                            )
                    else:
                        # Fallback for older manager interfaces
                        result = asyncio.run(
                            manager.archive_url(shortcode.url, datetime.now(timezone.utc))
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
                    
                except Exception as e:
                    logger.error(f"Archive failed with {method_name}: {e}")
                    archive_results.append({"error": str(e), "method": method_name})
        
        # Check if archiving succeeded using filesystem
        archive_successful = any(r.get('archive_path') for r in archive_results)
        if archive_successful:
            logger.info(f"Successfully archived {shortcode.url} -> {shortcode.shortcode}")
        else:
            logger.error(f"All archive methods failed for {shortcode.url}")
        
        return {
            "success": archive_successful,
            "shortcode": shortcode.shortcode,
            "results": archive_results
        }
        
    except Shortcode.DoesNotExist:
        logger.error(f"Shortcode with ID {shortcode_id} not found")
        return {"success": False, "error": "Shortcode not found"}
    
    except Exception as exc:
        logger.error(f"Archiving task failed: {exc}")
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying archive task for shortcode {shortcode_id}")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        # Final failure - archive status will be determined by filesystem
        
        return {"success": False, "error": str(exc)}


@shared_task(bind=True, max_retries=2)
def extract_assets_task(self, shortcode_id):
    """
    Extract additional assets (favicon, screenshot, PDF) for an archived URL.
    
    Args:
        shortcode_id: ID of the Shortcode instance
    """
    try:
        shortcode = Shortcode.objects.get(pk=shortcode_id)
        
        if not shortcode.is_archived():
            logger.warning(f"No archive found for shortcode {shortcode.shortcode}")
            return {"success": False, "error": "No archive found"}
        
        archive_path = shortcode.get_latest_archive_path()
        if not archive_path or not archive_path.exists():
            logger.warning(f"Archive path does not exist: {archive_path}")
            return {"success": False, "error": "Archive path not found"}
        
        # Import here to avoid circular imports
        from core.services import AssetExtractor
        
        asset_extractor = AssetExtractor()
        results = {}
        
        # Extract assets asynchronously
        async def extract_all():
            tasks = [
                asset_extractor.extract_favicon(shortcode.url, archive_path),
                asset_extractor.generate_screenshot(shortcode.url, archive_path),
                asset_extractor.generate_pdf(shortcode.url, archive_path)
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        favicon_result, screenshot_result, pdf_result = asyncio.run(extract_all())
        
        results['favicon'] = favicon_result if not isinstance(favicon_result, Exception) else str(favicon_result)
        results['screenshot'] = screenshot_result if not isinstance(screenshot_result, Exception) else str(screenshot_result)
        results['pdf'] = pdf_result if not isinstance(pdf_result, Exception) else str(pdf_result)
        
        logger.info(f"Asset extraction completed for {shortcode.shortcode}")
        return {"success": True, "results": results}
        
    except Exception as exc:
        logger.error(f"Asset extraction failed: {exc}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30)
        
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