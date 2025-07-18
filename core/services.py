"""
Core archiving services for the citis Django application.

These services handle the business logic for web archiving using SingleFile
and ArchiveBox, as well as asset extraction (favicons, screenshots, PDFs).
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from django.conf import settings
from django.http import HttpResponse
from functools import lru_cache
import logging
import sqlite3
import subprocess
from typing import Any, Dict, List, Optional
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


@sync_to_async
def read_file_async(path: Path) -> str:
    """Asynchronously reads a file and returns its content."""
    if not path.exists():
        return ""
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

class AssetExtractor:
    """Handles extraction of favicons, screenshots, and PDFs from websites"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    async def extract_favicon(self, url: str, archive_path: Path, force: bool = False) -> bool:
        """Extract favicon from the website and save it"""
        favicon_path = archive_path / "favicon.ico"
        
        if favicon_path.exists() and not force:
            logger.debug(f"Favicon already exists: {favicon_path}")
            return True
            
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Step 1: Try common favicon locations
                favicon_urls = [
                    f"{base_url}/favicon.ico",
                    f"{base_url}/apple-touch-icon.png", 
                    f"{base_url}/favicon.png",
                    f"{base_url}/apple-touch-icon-precomposed.png"
                ]
                
                for favicon_url in favicon_urls:
                    try:
                        response = await client.get(favicon_url)
                        if response.status_code == 200 and len(response.content) > 0:
                            with open(favicon_path, 'wb') as f:
                                f.write(response.content)
                            logger.info(f"Favicon saved from {favicon_url}")
                            return True
                    except Exception as e:
                        logger.debug(f"Failed to fetch favicon from {favicon_url}: {e}")
                        continue
                
                # Step 2: Parse HTML for favicon links in <head>
                singlefile_path = archive_path / "singlefile.html"
                if singlefile_path.exists():
                    favicon_urls_from_html = self._extract_favicon_urls_from_html(singlefile_path, base_url)
                    
                    for favicon_url in favicon_urls_from_html:
                        try:
                            response = await client.get(favicon_url)
                            if response.status_code == 200 and len(response.content) > 0:
                                with open(favicon_path, 'wb') as f:
                                    f.write(response.content)
                                logger.info(f"Favicon extracted from HTML: {favicon_url}")
                                return True
                        except Exception as e:
                            logger.debug(f"Failed to fetch favicon from HTML link {favicon_url}: {e}")
                            continue
                
                # Step 3: Try fetching directly from the live site's HTML
                logger.debug(f"Attempting to fetch live HTML from {url} for favicon links")
                try:
                    response = await client.get(url, timeout=5.0)  # Shorter timeout for live site
                    if response.status_code == 200:
                        favicon_urls_from_live = self._extract_favicon_urls_from_content(response.text, base_url)
                        
                        for favicon_url in favicon_urls_from_live:
                            try:
                                favicon_response = await client.get(favicon_url)
                                if favicon_response.status_code == 200 and len(favicon_response.content) > 0:
                                    with open(favicon_path, 'wb') as f:
                                        f.write(favicon_response.content)
                                    logger.info(f"Favicon extracted from live HTML: {favicon_url}")
                                    return True
                            except Exception as e:
                                logger.debug(f"Failed to fetch favicon from live HTML link {favicon_url}: {e}")
                                continue
                except Exception as e:
                    logger.debug(f"Failed to fetch live HTML: {e}")
            
            logger.warning(f"Could not extract favicon for {url}")
            return False
            
        except Exception as e:
            logger.warning(f"Favicon extraction failed for {url}: {e}")
            return False
    
    def _extract_favicon_urls_from_html(self, html_path: Path, base_url: str) -> List[str]:
        """Extract favicon URLs from SingleFile HTML"""
        try:
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return self._extract_favicon_urls_from_content(content, base_url)
        except Exception as e:
            logger.debug(f"Failed to parse HTML file {html_path}: {e}")
            return []
    
    def _extract_favicon_urls_from_content(self, content: str, base_url: str) -> List[str]:
        """Extract favicon URLs from HTML content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            favicon_urls = []
            
            # Find all favicon-related link tags
            favicon_links = soup.find_all('link', rel=lambda x: x and any(
                keyword in x.lower() for keyword in ['icon', 'shortcut icon', 'apple-touch-icon']
            ))
            
            for link in favicon_links:
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith('//'):
                        href = f"{urlparse(base_url).scheme}:{href}"
                    elif href.startswith('/'):
                        href = f"{base_url}{href}"
                    elif not href.startswith('http'):
                        href = f"{base_url}/{href}"
                    
                    favicon_urls.append(href)
            
            return favicon_urls
        except Exception as e:
            logger.debug(f"Failed to parse favicon URLs from content: {e}")
            return []
    
    async def generate_screenshot(self, url: str, archive_path: Path, 
                                width: int = 1920, height: int = 1080, 
                                timeout: int = 60, force: bool = False) -> bool:
        """Generate a screenshot using Python Playwright"""
        screenshot_path = archive_path / "screenshot.png"
        
        if screenshot_path.exists() and not force:
            logger.debug(f"Screenshot already exists: {screenshot_path}")
            return True
            
        try:
            from playwright.async_api import async_playwright
            
            logger.info(f"Generating screenshot: {screenshot_path}")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': width, 'height': height}
                )
                page = await context.new_page()
                
                page.set_default_timeout(timeout * 1000)
                await page.goto(url, wait_until='domcontentloaded')
                await page.screenshot(path=str(screenshot_path))
                
                await browser.close()
            
            if not screenshot_path.exists():
                logger.error("Screenshot output not created")
                return False
            
            logger.info(f"Screenshot generated successfully: {screenshot_path}")
            return True
            
        except ImportError:
            logger.error("Python Playwright not installed. Install with: pip3 install playwright && python3 -m playwright install")
            return False
        except Exception as e:
            logger.error(f"Screenshot generation error: {e}")
            return False
    
    async def generate_pdf(self, url: str, archive_path: Path, 
                          timeout: int = 60, force: bool = False) -> bool:
        """Generate a PDF using Python Playwright"""
        pdf_path = archive_path / "output.pdf"
        
        if pdf_path.exists() and not force:
            logger.debug(f"PDF already exists: {pdf_path}")
            return True
            
        try:
            from playwright.async_api import async_playwright
            
            logger.info(f"Generating PDF: {pdf_path}")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                page.set_default_timeout(timeout * 1000)
                await page.goto(url, wait_until='domcontentloaded')
                await page.pdf(path=str(pdf_path), format='A4', print_background=True)
                
                await browser.close()
            
            if not pdf_path.exists():
                logger.error("PDF output not created")
                return False
            
            logger.info(f"PDF generated successfully: {pdf_path}")
            return True
            
        except ImportError:
            logger.error("Python Playwright not installed. Install with: pip3 install playwright && python3 -m playwright install")
            return False
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            return False


class SingleFileManager:
    """Manages SingleFile archiving operations"""
    
    def __init__(self):
        # In a real-world scenario, you might pass a config object
        # but for now, we'll rely on Django settings.
        # Ensure the base archive path exists
        self.archive_base_path = Path(settings.SINGLEFILE_DATA_PATH)
        self.archive_base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"SingleFile archive path: {self.archive_base_path}")

    def _url_to_base62_hash(self, url: str) -> str:
        """Convert URL to a base62 hash."""
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        hash_bytes = hashlib.sha256(url.encode('utf-8')).digest()
        hash_int = int.from_bytes(hash_bytes[:8], byteorder='big')
        
        if hash_int == 0:
            return alphabet[0]
        
        result = ""
        while hash_int > 0:
            result = alphabet[hash_int % 62] + result
            hash_int //= 62
        return result

    def _get_archive_path(self, url: str, timestamp: datetime) -> Path:
        """Generate archive path from URL and timestamp."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        url_hash = self._url_to_base62_hash(url)
        
        year = timestamp.strftime('%Y')
        mmdd = timestamp.strftime('%m%d')
        hhmmss = timestamp.strftime('%H%M%S')
        
        return self.archive_base_path / domain / url_hash / year / mmdd / hhmmss
    
    def _extract_url_from_singlefile(self, file_path: Path) -> Optional[str]:
        """Extract original URL from SingleFile HTML header comment"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(8192)  # Read first 8KB
            
            # Look for SingleFile comment with URL
            pattern = r'<!--\s*Page saved with SingleFile.*?url:\s*([^\s]+).*?-->'
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            
            if match:
                return match.group(1)
            
            # Fallback: try saved-url meta tag
            soup = BeautifulSoup(content, 'html.parser')
            saved_url_meta = soup.find('meta', attrs={'name': 'saved-url'})
            if saved_url_meta and saved_url_meta.get('content'):
                return saved_url_meta['content']
            
            # Final fallback: metadata.json
            metadata_path = file_path.parent / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    return metadata.get('url')
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract URL from {file_path}: {e}")
            return None
    
    def _files_are_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files are identical by comparing hashes"""
        try:
            with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
                h1 = hashlib.sha256(f1.read()).hexdigest()
                h2 = hashlib.sha256(f2.read()).hexdigest()
                return h1 == h2
        except Exception as e:
            logger.debug(f"Could not compare files {file1} and {file2}: {e}")
            return False
    
    async def find_archives_for_url(self, url: str) -> List[Dict[str, Any]]:
        """Find all SingleFile archives for a given URL"""
        logger.debug(f"SingleFileManager.find_archives_for_url called with URL: {url}")
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        url_hash = self._url_to_base62_hash(url)
        logger.debug(f"Domain: {domain}, URL hash: {url_hash}")
        
        domain_path = self.archive_base_path / domain / url_hash
        logger.debug(f"Looking for archives in: {domain_path}")
        if not domain_path.exists():
            logger.debug(f"Domain path does not exist: {domain_path}")
            return []
        
        archives = []
        for year_dir in domain_path.iterdir():
            if not year_dir.is_dir():
                continue
                
            year = year_dir.name
            for mmdd_dir in year_dir.iterdir():
                if not mmdd_dir.is_dir():
                    continue
                    
                mmdd = mmdd_dir.name
                for hhmmss_dir in mmdd_dir.iterdir():
                    if not hhmmss_dir.is_dir():
                        continue
                        
                    hhmmss = hhmmss_dir.name
                    singlefile_path = hhmmss_dir / "singlefile.html"
                    
                    if singlefile_path.exists():
                        timestamp_str = f"{year}{mmdd}{hhmmss}"
                        try:
                            timestamp_dt = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                            timestamp_dt = timestamp_dt.replace(tzinfo=timezone.utc)
                            
                            archives.append({
                                "timestamp": str(int(timestamp_dt.timestamp())),
                                "url": url,
                                "archive_path": str(hhmmss_dir),
                                "archive_method": "singlefile"
                            })
                        except ValueError:
                            logger.debug(f"Invalid timestamp format: {timestamp_str}")
                            continue
        
        # Sort by timestamp (newest first)
        sorted_archives = sorted(archives, key=lambda x: float(x["timestamp"]), reverse=True)
        logger.debug(f"Total archives found for {url}: {len(sorted_archives)}")
        return sorted_archives
    
    def _check_for_duplicate(self, new_archive_path: Path, url: str) -> Optional[Path]:
        """Check if an identical archive already exists for this URL"""
        singlefile_path = new_archive_path / "singlefile.html"
        if not singlefile_path.exists():
            return None
        
        # Find all existing archives for this URL
        existing_archives = self.find_archives_for_url(url)
        
        for archive in existing_archives:
            existing_path = Path(archive["archive_path"])
            if existing_path == new_archive_path:
                continue  # Skip the one we just created
            
            existing_singlefile = existing_path / "singlefile.html"
            if existing_singlefile.exists():
                if self._files_are_identical(singlefile_path, existing_singlefile):
                    logger.info(f"Found identical archive at {existing_path}")
                    return existing_path
        
        return None
    
    async def get_archive_content(self, archive_details: Dict[str, Any]) -> str:
        """
        Get the HTML content of a SingleFile archive.
        """
        archive_path = archive_details.get("archive_path")
        if not archive_path:
            return ""
        
        # The archive_path is the directory; we need to read the HTML file within it.
        html_file_path = Path(archive_path) / "singlefile.html"
        return await read_file_async(html_file_path)

    async def _extract_favicon(self, url: str, archive_path: Path) -> bool:
        """Extract favicon using shared AssetExtractor"""
        return await self.asset_extractor.extract_favicon(url, archive_path)

    async def _generate_screenshot(self, url: str, archive_path: Path) -> bool:
        """Generate screenshot using shared AssetExtractor"""
        if not settings.SINGLEFILE_GENERATE_SCREENSHOT:
            return False
        return await self.asset_extractor.generate_screenshot(
            url, archive_path,
            width=settings.SINGLEFILE_SCREENSHOT_WIDTH,
            height=settings.SINGLEFILE_SCREENSHOT_HEIGHT,
            timeout=settings.SINGLEFILE_TIMEOUT
        )

    async def _generate_pdf(self, url: str, archive_path: Path) -> bool:
        """Generate PDF using shared AssetExtractor"""
        if not settings.SINGLEFILE_GENERATE_PDF:
            return False
        return await self.asset_extractor.generate_pdf(
            url, archive_path,
            timeout=settings.SINGLEFILE_TIMEOUT
        )

    async def archive_url(self, url: str, timestamp: datetime) -> Dict[str, Any]:
        """Archive a URL using SingleFile CLI with deduplication"""
        archive_path = self._get_archive_path(url, timestamp)
        archive_path.mkdir(parents=True, exist_ok=True)
        
        singlefile_path = archive_path / "singlefile.html"
        
        # Build command
        cmd = [
            settings.SINGLEFILE_EXECUTABLE_PATH,
            url,
            str(singlefile_path)
        ]
        
        logger.info(f"Executing SingleFile: {' '.join(cmd)}")
        
        try:
            # Get environment with proper PATH for the Node.js version
            env = os.environ.copy()
            executable_dir = Path(settings.SINGLEFILE_EXECUTABLE_PATH).parent
            if str(executable_dir) not in env.get("PATH", ""):
                env["PATH"] = f"{executable_dir}:{env.get('PATH', '')}"
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=settings.SINGLEFILE_TIMEOUT
            )
            
            if process.returncode != 0:
                logger.error(f"SingleFile error: {stderr.decode()}")
                raise Exception(f"SingleFile failed: {stderr.decode()}")
            
            if not singlefile_path.exists():
                raise Exception("SingleFile output not created")
            
            # Generate additional assets in parallel
            tasks = [
                self._extract_favicon(url, archive_path),
                self._generate_screenshot(url, archive_path),
                self._generate_pdf(url, archive_path)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results but don't fail if any individual task fails
            favicon_success, screenshot_success, pdf_success = results
            if isinstance(favicon_success, Exception):
                logger.warning(f"Favicon extraction failed: {favicon_success}")
            if isinstance(screenshot_success, Exception):
                logger.warning(f"Screenshot generation failed: {screenshot_success}")
            if isinstance(pdf_success, Exception):
                logger.warning(f"PDF generation failed: {pdf_success}")
            
            # Check for duplicates
            duplicate_path = self._check_for_duplicate(archive_path, url)
            if duplicate_path:
                logger.info(f"Duplicate content detected, removing new archive {archive_path}")
                # Remove the newly created archive since it's identical
                shutil.rmtree(archive_path)
                
                # Extract timestamp from the duplicate path
                path_parts = duplicate_path.parts
                year = path_parts[-3]
                mmdd = path_parts[-2]
                hhmmss = path_parts[-1]
                timestamp_str = f"{year}{mmdd}{hhmmss}"
                timestamp_dt = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                timestamp_dt = timestamp_dt.replace(tzinfo=timezone.utc)
                
                return {
                    "timestamp": str(int(timestamp_dt.timestamp())),
                    "url": url,
                    "archive_path": str(duplicate_path),
                    "archive_method": "singlefile",
                    "was_duplicate": True
                }
            
            logger.info(f"SingleFile archive created successfully at {archive_path}")
            
            return {
                "timestamp": str(int(timestamp.timestamp())),
                "url": url,
                "archive_path": str(archive_path),
                "archive_method": "singlefile",
                "was_duplicate": False
            }
            
        except asyncio.TimeoutError:
            # Clean up on timeout
            if archive_path.exists():
                shutil.rmtree(archive_path)
            raise Exception(f"SingleFile timed out after {settings.SINGLEFILE_TIMEOUT}s")
        except Exception as e:
            # Clean up on any other error
            if archive_path.exists():
                shutil.rmtree(archive_path)
            raise e


class ArchiveBoxManager:
    """Manages ArchiveBox archiving operations"""
    
    def __init__(self):
        self.data_path = Path(settings.ARCHIVEBOX_DATA_PATH) if settings.ARCHIVEBOX_DATA_PATH else None

    async def find_archives_for_url(self, url: str) -> List[Dict[str, Any]]:
        """Find all ArchiveBox archives for a given URL"""
        if not settings.ARCHIVEBOX_API_KEY:
            return []
            
        try:
            async with httpx.AsyncClient() as client:
                params = {"url": url}
                headers = {"X-ArchiveBox-API-Key": settings.ARCHIVEBOX_API_KEY}
                api_url = f"{settings.ARCHIVEBOX_BASE_URL}/api/v1/core/snapshots"
                
                response = await client.get(api_url, params=params, headers=headers)
                response.raise_for_status()
                
                snapshots = response.json().get("items", [])
                for snap in snapshots:
                    snap["archive_method"] = "archivebox"
                
                return snapshots
                
        except Exception as e:
            logger.warning(f"Could not fetch ArchiveBox snapshots: {e}")
            return []
    
    async def archive_url(self, url: str, timestamp: datetime) -> Dict[str, Any]:
        """Archive a URL using ArchiveBox API"""
        if not settings.ARCHIVEBOX_API_KEY:
            raise Exception("ArchiveBox API key not configured")
            
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {
                "X-ArchiveBox-API-Key": settings.ARCHIVEBOX_API_KEY,
                "Content-Type": "application/json"
            }
            
            # Convert extractors list to comma-separated string
            extractors_str = ",".join(settings.ARCHIVEBOX_EXTRACTORS) if settings.ARCHIVEBOX_EXTRACTORS else "singlefile"
            
            payload = {
                "urls": [url],
                "tag": "citis",
                "parser": "url_list",
                "extractors": extractors_str
            }
            
            logger.info(f"Sending ArchiveBox request for URL: {url}")
            
            response = await client.post(
                f"{settings.ARCHIVEBOX_BASE_URL}/api/v1/cli/add",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            
            return {
                "timestamp": str(int(timestamp.timestamp())),
                "url": url,
                "archive_method": "archivebox",
                "was_duplicate": False
            }
    
    async def get_archive_content(self, archive_details: Dict[str, Any]) -> str:
        """
        Get the HTML content of an archived page from ArchiveBox.
        """
        archive_timestamp_dt = archive_details.get("timestamp")
        if not archive_timestamp_dt:
            raise ValueError("Timestamp missing from archive details")
        
        archive_timestamp = str(int(archive_timestamp_dt.timestamp()))

        if not self.data_path:
            raise ValueError("ARCHIVEBOX_DATA_PATH not set")

        archive_dir = self.data_path / "archive" / archive_timestamp
        html_file = archive_dir / "index.html"

        return await read_file_async(html_file)
    
    async def serve_pdf(self, archive_timestamp: str, shortcode: str) -> HttpResponse:
        """Serve PDF with proper download headers"""
        try:
            if settings.ARCHIVEBOX_DATA_PATH:
                # File mode - read from disk
                pdf_path = Path(settings.ARCHIVEBOX_DATA_PATH) / "archive" / archive_timestamp / "output.pdf"
                if not pdf_path.exists():
                    raise Exception("PDF not found")
                
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()
            else:
                # Proxy mode - fetch from ArchiveBox via HTTP
                async with httpx.AsyncClient(timeout=30.0) as client:
                    headers = {"X-ArchiveBox-API-Key": settings.ARCHIVEBOX_API_KEY}
                    pdf_url = f"{settings.ARCHIVEBOX_BASE_URL}/archive/{archive_timestamp}/output.pdf"
                    
                    response = await client.get(pdf_url, headers=headers)
                    if response.status_code == 404:
                        raise Exception("PDF not found")
                    response.raise_for_status()
                    pdf_content = response.content
            
            # Set headers to force download with shortcode as filename
            response = HttpResponse(pdf_content, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{shortcode}.pdf"'
            response["Cache-Control"] = "public, max-age=31536000, immutable"
            
            return response
        
        except Exception as e:
            logger.error(f"Error serving PDF: {e}")
            raise e


# Service factory functions
def get_singlefile_manager() -> Optional[SingleFileManager]:
    """Get SingleFile manager if configured"""
    if settings.ARCHIVE_MODE in ["singlefile", "both"]:
        return SingleFileManager()
    return None


def get_archivebox_manager() -> Optional[ArchiveBoxManager]:
    """Get ArchiveBox manager if configured"""
    if settings.ARCHIVE_MODE in ["archivebox", "both"]:
        return ArchiveBoxManager()
    return None


def get_archive_managers() -> Dict[str, Any]:
    """Get all configured archive managers"""
    managers = {}
    
    if settings.ARCHIVE_MODE in ["singlefile", "both"]:
        managers["singlefile"] = SingleFileManager()
    
    if settings.ARCHIVE_MODE in ["archivebox", "both"]:
        managers["archivebox"] = ArchiveBoxManager()
    
    return managers 