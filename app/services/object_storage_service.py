"""
Object Storage Service for ORO Backend.

This module provides functions to interact with OCI Object Storage using PAR (Pre-Authenticated Request).
It includes functions for uploading, downloading, and listing objects in the bucket.
"""

import os
import requests
import urllib.parse
import mimetypes
import tempfile
import shutil
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get PAR base URL from environment
PAR_BASE_URL = os.getenv("PAR_BASE_URL")
if not PAR_BASE_URL:
    raise RuntimeError("PAR_BASE_URL not found in environment variables. Please set it in .env file.")


class ObjectStorageService:
    """Service class for object storage operations."""
    
    def __init__(self, par_base_url: str = None):
        """
        Initialize the object storage service.
        
        Args:
            par_base_url: Base PAR URL (optional, uses environment variable if not provided)
        """
        self.par_base_url = par_base_url or PAR_BASE_URL
    
    def list_objects(self, prefix: str = "data/", limit: int = 1000, timeout: int = 30) -> List[str]:
        """
        List objects using the native JSON endpoint (/o) with pagination.
        
        Args:
            prefix: Prefix ('folder') to list (default: data/)
            limit: Objects per page (default: 1000)
            timeout: Timeout in seconds (default: 30)
            
        Returns:
            List of object names
            
        Raises:
            RuntimeError: If the request fails
        """
        base = self.par_base_url.rstrip("/") + "/o"
        params = {"prefix": prefix, "limit": limit}
        items = []
        start = None

        while True:
            q = params.copy()
            if start:
                q["start"] = start
            url = f"{base}/?{urllib.parse.urlencode(q)}"
            r = requests.get(url, headers={"Accept": "application/json"}, timeout=timeout)
            if not r.ok:
                snippet = r.text[:200].replace("\n", " ")
                raise RuntimeError(f"HTTP {r.status_code} while listing: {snippet}")

            payload = r.json()
            for obj in payload.get("objects", []):
                name = obj.get("name") or obj.get("Key")
                if name:
                    items.append(name)

            start = payload.get("nextStartWith") or payload.get("next_start_with")
            if not start:
                break

        return items

    def upload_object(self, local_path: str, object_name: str, 
                     content_type: str = None, timeout: int = 600) -> Dict[str, Any]:
        """
        Upload a file to the bucket using a write-enabled PAR.
        
        Args:
            local_path: Path to the local file to upload
            object_name: Destination object name in the bucket
            content_type: Content-Type header (auto-detected if None)
            timeout: Timeout in seconds (default: 600)
            
        Returns:
            Dictionary with upload information
            
        Raises:
            FileNotFoundError: If the local file doesn't exist
            RuntimeError: If the upload fails
        """
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")

        if content_type is None:
            guessed, _ = mimetypes.guess_type(local_path)
            if guessed is None and local_path.lower().endswith((".tif", ".tiff")):
                guessed = "image/tiff"
            content_type = guessed or "application/octet-stream"

        base_o = self.par_base_url.rstrip("/") + "/o"
        target_url = f"{base_o}/" + urllib.parse.quote(object_name, safe="")
        file_size = os.path.getsize(local_path)
        headers = {"Content-Type": content_type}

        with open(local_path, "rb") as f:
            r = requests.put(target_url, data=f, headers=headers, timeout=timeout)

        if r.status_code not in (200, 201, 204):
            snippet = r.text[:300].replace("\n", " ")
            raise RuntimeError(f"Upload failed (HTTP {r.status_code}): {snippet}")

        return {"status": r.status_code, "object": object_name, "bytes": file_size}

    def download_object(self, object_name: str, download_dir: str = "download_test", 
                       timeout: int = 120) -> Dict[str, Any]:
        """
        Download an object from an OCI Object Storage bucket using a PAR.
        
        Args:
            object_name: Full object key (e.g., "data/sample2.tif")
            download_dir: Local folder to save the file (default: download_test)
            timeout: HTTP timeout in seconds (default: 120)
            
        Returns:
            Dictionary with download information
            
        Raises:
            RuntimeError: If the download fails
        """
        base_o = self.par_base_url.rstrip("/") + "/o"
        object_url = f"{base_o}/" + urllib.parse.quote(object_name, safe="")

        os.makedirs(download_dir, exist_ok=True)
        local_path = os.path.join(download_dir, os.path.basename(object_name))

        with requests.get(object_url, stream=True, timeout=timeout) as r:
            if not r.ok:
                snippet = r.text[:200].replace("\n", " ")
                raise RuntimeError(f"Download failed (HTTP {r.status_code}): {snippet}")

            total_bytes = 0
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)

        return {"status": r.status_code, "object": object_name, "saved_to": local_path, "bytes": total_bytes}

    def object_exists(self, object_name: str) -> bool:
        """
        Check if an object exists in the bucket.
        
        Args:
            object_name: Full object key (e.g., "data/sample2.tif")
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            # Try to get object metadata by making a HEAD request
            base_o = self.par_base_url.rstrip("/") + "/o"
            object_url = f"{base_o}/" + urllib.parse.quote(object_name, safe="")
            
            r = requests.head(object_url, timeout=30)
            return r.status_code == 200
        except:
            return False

    def get_object_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an object in the bucket.
        
        Args:
            object_name: Full object key (e.g., "data/sample2.tif")
            
        Returns:
            Dictionary with object information or None if not found
        """
        try:
            base_o = self.par_base_url.rstrip("/") + "/o"
            object_url = f"{base_o}/" + urllib.parse.quote(object_name, safe="")
            
            r = requests.head(object_url, timeout=30)
            if r.status_code == 200:
                return {
                    "name": object_name,
                    "size": int(r.headers.get("content-length", 0)),
                    "last_modified": r.headers.get("last-modified"),
                    "content_type": r.headers.get("content-type"),
                    "etag": r.headers.get("etag")
                }
            return None
        except:
            return None

    def upload_file_from_memory(self, file_content: bytes, object_name: str, 
                               content_type: str = None, timeout: int = 600) -> Dict[str, Any]:
        """
        Upload file content from memory to the bucket.
        
        Args:
            file_content: File content as bytes
            object_name: Destination object name in the bucket
            content_type: Content-Type header (auto-detected if None)
            timeout: Timeout in seconds (default: 600)
            
        Returns:
            Dictionary with upload information
            
        Raises:
            RuntimeError: If the upload fails
        """
        if content_type is None:
            # Try to guess content type from object name
            guessed, _ = mimetypes.guess_type(object_name)
            if guessed is None and object_name.lower().endswith((".tif", ".tiff")):
                guessed = "image/tiff"
            content_type = guessed or "application/octet-stream"

        base_o = self.par_base_url.rstrip("/") + "/o"
        target_url = f"{base_o}/" + urllib.parse.quote(object_name, safe="")
        file_size = len(file_content)
        headers = {"Content-Type": content_type}

        r = requests.put(target_url, data=file_content, headers=headers, timeout=timeout)

        if r.status_code not in (200, 201, 204):
            snippet = r.text[:300].replace("\n", " ")
            raise RuntimeError(f"Upload failed (HTTP {r.status_code}): {snippet}")

        return {"status": r.status_code, "object": object_name, "bytes": file_size}
