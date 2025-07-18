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
def archive_url_task(self, shortcode_id):
    """
    Archive a URL using the configured archive managers.
    
    Args:
        shortcode_id: ID of the Shortcode instance to archive
    """
    try:
        shortcode = Shortcode.objects.get(pk=shortcode_id)
        
        # Get archive managers
        managers = get_archive_managers()
        
        if not managers:
            logger.error("No archive managers configured")
            shortcode.is_archived = False
            shortcode.save()
            return {"success": False, "error": "No archive managers configured"}
        
        # Archive with configured methods
        archive_results = []
        
        for method_name, manager in managers.items():
            if shortcode.archive_method in [method_name, 'both']:
                try:
                    # Run async archive method in sync task
                    result = asyncio.run(
                        manager.archive_url(shortcode.url, datetime.now(timezone.utc))
                    )
                    archive_results.append(result)
                    
                    # Update shortcode with archive path from first successful result
                    if not shortcode.archive_path and result.get('archive_path'):
                        shortcode.archive_path = result['archive_path']
                    
                except Exception as e:
                    logger.error(f"Archive failed with {method_name}: {e}")
                    archive_results.append({"error": str(e), "method": method_name})
        
        # Mark as archived if any method succeeded
        if any(r.get('archive_path') for r in archive_results):
            shortcode.is_archived = True
            logger.info(f"Successfully archived {shortcode.url} -> {shortcode.shortcode}")
        else:
            shortcode.is_archived = False
            logger.error(f"All archive methods failed for {shortcode.url}")
        
        shortcode.save()
        
        return {
            "success": shortcode.is_archived,
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
        
        # Final failure - mark shortcode as failed
        try:
            shortcode = Shortcode.objects.get(pk=shortcode_id)
            shortcode.is_archived = False
            shortcode.save()
        except Shortcode.DoesNotExist:
            pass
        
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
        
        if not shortcode.archive_path:
            logger.warning(f"No archive path for shortcode {shortcode.shortcode}")
            return {"success": False, "error": "No archive path"}
        
        archive_path = Path(shortcode.archive_path)
        if not archive_path.exists():
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
    
    failed_archives = Shortcode.objects.filter(
        is_archived=False,
        created_at__lt=cutoff,
        archive_path__isnull=False
    )
    
    cleaned_count = 0
    for shortcode in failed_archives:
        try:
            if shortcode.archive_path:
                archive_path = Path(shortcode.archive_path)
                if archive_path.exists():
                    import shutil
                    shutil.rmtree(archive_path)
                    logger.info(f"Cleaned up failed archive: {archive_path}")
                    cleaned_count += 1
                
                # Clear the archive path
                shortcode.archive_path = ''
                shortcode.save()
        except Exception as e:
            logger.error(f"Error cleaning up archive {shortcode.archive_path}: {e}")
    
    logger.info(f"Cleaned up {cleaned_count} failed archives")
    return {"cleaned_count": cleaned_count} 