import asyncio
import tempfile
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List
import logging

from .asset_extractor import AssetExtractor

logger = logging.getLogger(__name__)

class SingleFileManager:
    def __init__(self, config):
        self.config = config
        self.asset_extractor = AssetExtractor(timeout=10)
        
        # Resolve archive data path relative to server directory if it's relative
        data_path = Path(config.singlefile_data_path)
        if data_path.is_absolute():
            self.archive_base_path = data_path
        else:
            # Resolve relative to server directory
            server_dir = Path(__file__).parent.parent  # Go up from core/ to server/
            self.archive_base_path = (server_dir / data_path).resolve()
        
        logger.info(f"SingleFile archive path: {self.archive_base_path}")
        logger.info(f"SingleFile config: generate_screenshot={config.singlefile_generate_screenshot}, generate_pdf={config.singlefile_generate_pdf}")
        
    def _url_to_base62_hash(self, url: str) -> str:
        """Convert URL to base62 hash (same as migrate_archive.py)"""
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
        """Generate archive path using same structure as migrate_archive.py"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        url_hash = self._url_to_base62_hash(url)
        
        year = timestamp.strftime('%Y')
        mmdd = timestamp.strftime('%m%d')
        hhmmss = timestamp.strftime('%H%M%S')
        
        return self.archive_base_path / domain / url_hash / year / mmdd / hhmmss
    
    def _extract_url_from_singlefile(self, file_path: Path) -> Optional[str]:
        """Extract original URL from SingleFile HTML header comment or fallback to directory structure"""
        try:
            # First, try to extract from the file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read only the first few KB to find the header
                content = f.read(8192)
            
            # SingleFile adds a comment like: <!-- Page saved with SingleFile ... url: https://example.com ... -->
            # Look for the URL in the comment
            pattern = r'<!--\s*Page saved with SingleFile.*?url:\s*([^\s]+).*?-->'
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            
            if match:
                return match.group(1)
            
            # Fallback: try to extract from the saved-url meta tag that SingleFile sometimes adds
            soup = BeautifulSoup(content, 'html.parser')
            saved_url_meta = soup.find('meta', attrs={'name': 'saved-url'})
            if saved_url_meta and saved_url_meta.get('content'):
                return saved_url_meta['content']
            
            # Final fallback: if there's a metadata.json file, use it
            metadata_path = file_path.parent / "metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    return metadata.get("original_url")
                except Exception:
                    pass
            
            # If all else fails, log a warning but don't fail completely
            logger.warning(f"Could not extract URL from {file_path}, using placeholder")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting URL from SingleFile {file_path}: {e}")
            return None
    
    def _extract_singlefile_content(self, file_path: Path) -> str:
        """Extract content from SingleFile HTML, removing the metadata header"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Remove the SingleFile metadata header
            # Pattern matches: <!DOCTYPE html> <html...><!-- Page saved with SingleFile ... -->
            pattern = r'<!DOCTYPE html>\s*<html[^>]*><!--\s*Page saved with SingleFile[^>]*-->'
            content_without_header = re.sub(pattern, '<!DOCTYPE html><html>', content, flags=re.DOTALL | re.IGNORECASE)
            
            return content_without_header
        except Exception as e:
            logger.error(f"Error reading SingleFile content from {file_path}: {e}")
            return ""
    
    def _files_are_identical(self, file1_path: Path, file2_path: Path) -> bool:
        """Compare two SingleFile HTML files, ignoring the metadata header"""
        content1 = self._extract_singlefile_content(file1_path)
        content2 = self._extract_singlefile_content(file2_path)
        
        if not content1 or not content2:
            return False
        
        # Compare the cleaned content
        return content1 == content2
    
    def find_archives_for_url(self, url: str) -> List[Dict[str, Any]]:
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
                        # Extract timestamp from path
                        try:
                            # Combine year, mmdd, and hhmmss to create timestamp
                            timestamp_str = f"{year}{mmdd}{hhmmss}"
                            timestamp_dt = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                            timestamp_dt = timestamp_dt.replace(tzinfo=timezone.utc)
                            timestamp_unix = int(timestamp_dt.timestamp())
                            
                            # Since we're searching by URL and the directory structure is based on URL hash,
                            # we can trust that archives in this directory are for the requested URL
                            archive_info = {
                                "timestamp": str(timestamp_unix),
                                "url": url,  # Use the URL we're searching for
                                "archive_path": str(hhmmss_dir),
                                "archive_method": "singlefile"
                            }
                            logger.debug(f"Found archive: {archive_info}")
                            archives.append(archive_info)
                        except Exception as e:
                            logger.warning(f"Could not process archive at {hhmmss_dir}: {e}")
        
        sorted_archives = sorted(archives, key=lambda x: float(x["timestamp"]))
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
    
    async def _extract_favicon(self, url: str, archive_path: Path) -> bool:
        """Extract favicon using shared AssetExtractor"""
        return await self.asset_extractor.extract_favicon(url, archive_path)

    async def _generate_screenshot(self, url: str, archive_path: Path) -> bool:
        """Generate screenshot using shared AssetExtractor"""
        logger.debug(f"Screenshot generation config: generate_screenshot={self.config.singlefile_generate_screenshot}")
        if not self.config.singlefile_generate_screenshot:
            logger.debug("Screenshot generation disabled in config")
            return False
        logger.debug(f"Attempting to generate screenshot for {url}")
        return await self.asset_extractor.generate_screenshot(
            url, archive_path,
            width=self.config.singlefile_screenshot_width,
            height=self.config.singlefile_screenshot_height,
            timeout=self.config.singlefile_timeout
        )

    async def _generate_pdf(self, url: str, archive_path: Path) -> bool:
        """Generate PDF using shared AssetExtractor"""
        logger.debug(f"PDF generation config: generate_pdf={self.config.singlefile_generate_pdf}")
        if not self.config.singlefile_generate_pdf:
            logger.debug("PDF generation disabled in config")
            return False
        logger.debug(f"Attempting to generate PDF for {url}")
        return await self.asset_extractor.generate_pdf(
            url, archive_path,
            timeout=self.config.singlefile_timeout
        )

    async def archive_url(self, url: str, timestamp: datetime) -> Dict[str, Any]:
        """Archive a URL using SingleFile CLI with deduplication"""
        archive_path = self._get_archive_path(url, timestamp)
        archive_path.mkdir(parents=True, exist_ok=True)
        
        singlefile_path = archive_path / "singlefile.html"
        
        # Build command
        cmd = [
            self.config.singlefile_executable_path,
            url,
            str(singlefile_path)
        ]
        
        logger.info(f"Executing SingleFile: {' '.join(cmd)}")
        
        try:
            # Get environment with proper PATH for the Node.js version
            env = os.environ.copy()
            # Derive the Node.js bin directory from the configured executable path
            executable_dir = Path(self.config.singlefile_executable_path).parent
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
                timeout=self.config.singlefile_timeout
            )
            
            if process.returncode != 0:
                logger.error(f"SingleFile error: {stderr.decode()}")
                raise Exception(f"SingleFile failed: {stderr.decode()}")
            
            if not singlefile_path.exists():
                raise Exception("SingleFile output not created")
            
            # Generate additional assets (favicon, screenshot, PDF) in parallel
            tasks = [
                self._extract_favicon(url, archive_path),
                self._generate_screenshot(url, archive_path),
                self._generate_pdf(url, archive_path)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results (but don't fail if any individual task fails)
            favicon_success, screenshot_success, pdf_success = results
            logger.info(f"Asset generation results: favicon={favicon_success}, screenshot={screenshot_success}, pdf={pdf_success}")
            if isinstance(favicon_success, Exception):
                logger.warning(f"Favicon extraction failed: {favicon_success}")
            else:
                logger.info(f"Favicon extraction: {'succeeded' if favicon_success else 'skipped or failed'}")
            if isinstance(screenshot_success, Exception):
                logger.warning(f"Screenshot generation failed: {screenshot_success}")
            else:
                logger.info(f"Screenshot generation: {'succeeded' if screenshot_success else 'skipped or failed'}")
            if isinstance(pdf_success, Exception):
                logger.warning(f"PDF generation failed: {pdf_success}")
            else:
                logger.info(f"PDF generation: {'succeeded' if pdf_success else 'skipped or failed'}")
            
            # Check for duplicates
            duplicate_path = self._check_for_duplicate(archive_path, url)
            if duplicate_path:
                logger.info(f"Duplicate content detected, removing new archive {archive_path}")
                # Remove the newly created archive since it's identical
                shutil.rmtree(archive_path)
                
                # Extract timestamp from the duplicate path
                # Path format: .../year/mmdd/hhmmss
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
            
            # Return snapshot info in ArchiveBox-compatible format
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
            raise Exception(f"SingleFile timed out after {self.config.singlefile_timeout}s")
        except FileNotFoundError:
            # Clean up on error
            if archive_path.exists():
                shutil.rmtree(archive_path)
            raise Exception("SingleFile CLI not found. Install with: npm install -g single-file-cli")
        except Exception as e:
            # Clean up on any error
            if archive_path.exists():
                shutil.rmtree(archive_path)
            logger.error(f"SingleFile error: {e}")
            raise 