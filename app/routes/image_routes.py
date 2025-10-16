"""
Image API routes.

This module defines the REST API endpoints for image operations,
including upload and list operations for GeoTIFF images in object storage.
"""

import os
import tempfile
import shutil
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Form
from fastapi.responses import FileResponse

from ..models import (
    ImageUploadResponse,
    ImageListResponse,
    ImageListRequest,
    ImageInfo,
    ErrorResponse,
    SuccessResponse
)
from ..services.object_storage_service import ObjectStorageService

router = APIRouter(prefix="/images", tags=["images"])

# Initialize object storage service
object_storage = ObjectStorageService()


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(..., description="GeoTIFF file to upload"),
    content_type: Optional[str] = Query(None, description="Content-Type of the file (auto-detected if omitted)"),
    timeout: int = Query(600, ge=30, le=3600, description="Upload timeout in seconds")
):
    """
    Upload a GeoTIFF image to the object storage bucket.
    
    This endpoint uploads a GeoTIFF file to the object storage bucket.
    The file will be automatically stored in the "data/" prefix.
    
    Args:
        file: GeoTIFF file to upload (multipart/form-data)
        content_type: Content-Type header (optional, auto-detected if omitted)
        timeout: Upload timeout in seconds (default: 600)
        
    Returns:
        Upload response with success status and file information
        
    Raises:
        HTTPException: If upload fails or file is invalid
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided"
        )
    
    # Check if it's a GeoTIFF file
    if not file.filename.lower().endswith(('.tif', '.tiff')):
        raise HTTPException(
            status_code=400,
            detail="Only GeoTIFF files (.tif, .tiff) are allowed"
        )
    
    # Create temporary file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        # Save uploaded file temporarily
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Determine object name (automatically add data/ prefix)
        object_name = "data/" + file.filename
        
        # Upload to bucket
        upload_info = object_storage.upload_object(
            temp_path,
            object_name,
            content_type=content_type,
            timeout=timeout
        )
        
        return ImageUploadResponse(
            success=True,
            message="File uploaded successfully",
            object_name=file.filename,  # Return only filename without prefix
            bytes_uploaded=upload_info["bytes"],
            content_type=content_type or "image/tiff"
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error uploading file: {str(e)}"
        )
    finally:
        # Clean up temporary file
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


@router.post("/list", response_model=ImageListResponse)
async def list_images(request: ImageListRequest):
    """
    List GeoTIFF images in the object storage bucket.
    
    This endpoint lists all GeoTIFF images in the bucket.
    The "data/" prefix is handled automatically by the backend.
    
    Args:
        request: List request parameters (limit, timeout)
        
    Returns:
        List of images with metadata (filenames without prefix)
        
    Raises:
        HTTPException: If listing fails
    """
    try:
        # List objects from bucket (always use data/ prefix internally)
        object_names = object_storage.list_objects(
            prefix="data/",
            limit=request.limit,
            timeout=request.timeout
        )
        
        # Get detailed information for each object
        images = []
        for obj_name in object_names:
            # Only include GeoTIFF files
            if obj_name.lower().endswith(('.tif', '.tiff')):
                info = object_storage.get_object_info(obj_name)
                if info:
                    # Remove "data/" prefix from the name for frontend
                    display_name = obj_name.replace("data/", "", 1) if obj_name.startswith("data/") else obj_name
                    images.append(ImageInfo(
                        name=display_name,  # Return filename without prefix
                        size=info["size"],
                        last_modified=info["last_modified"],
                        content_type=info["content_type"],
                        etag=info["etag"]
                    ))
        
        return ImageListResponse(
            success=True,
            prefix="",  # Empty prefix for frontend
            count=len(images),
            images=images
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing images: {str(e)}"
        )


@router.get("/list", response_model=ImageListResponse)
async def list_images_get(
    limit: int = Query(default=1000, ge=1, le=10000, description="Maximum number of objects to return"),
    timeout: int = Query(default=30, ge=5, le=300, description="Request timeout in seconds")
):
    """
    List GeoTIFF images in the object storage bucket (GET version).
    
    This is a convenience GET endpoint for listing images with query parameters.
    The "data/" prefix is handled automatically by the backend.
    
    Args:
        limit: Maximum number of objects to return (default: 1000)
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        List of images with metadata (filenames without prefix)
        
    Raises:
        HTTPException: If listing fails
    """
    request = ImageListRequest(prefix="", limit=limit, timeout=timeout)
    return await list_images(request)


@router.get("/download/{object_name:path}")
async def download_image(
    object_name: str,
    timeout: int = Query(120, ge=30, le=600, description="Download timeout in seconds")
):
    """
    Download a GeoTIFF image from the object storage bucket.
    
    This endpoint downloads an image file and returns it directly in the HTTP response.
    The "data/" prefix is handled automatically by the backend.
    
    Args:
        object_name: Filename (without prefix)
        timeout: Download timeout in seconds (default: 120)
        
    Returns:
        File response with the image data
        
    Raises:
        HTTPException: If download fails or file not found
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Add data/ prefix internally
        full_object_name = f"data/{object_name}"
        
        # Download object
        download_info = object_storage.download_object(
            full_object_name,
            download_dir=temp_dir,
            timeout=timeout
        )
        
        file_path = download_info["saved_to"]
        
        # Return the file
        response = FileResponse(
            file_path,
            filename=os.path.basename(object_name),
            media_type="image/tiff"
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading image: {str(e)}"
        )
    finally:
        # Note: In production, consider using background tasks to clean up temp files
        pass


@router.get("/exists/{object_name:path}")
async def check_image_exists(object_name: str):
    """
    Check if a GeoTIFF image exists in the object storage bucket.
    
    Args:
        object_name: Filename (without prefix)
        
    Returns:
        Dictionary with existence status
        
    Raises:
        HTTPException: If check fails
    """
    try:
        # Add data/ prefix internally
        full_object_name = f"data/{object_name}"
        exists = object_storage.object_exists(full_object_name)
        
        return {
            "object_name": object_name,  # Return filename without prefix
            "exists": exists,
            "message": "Object found" if exists else "Object not found"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking image existence: {str(e)}"
        )


@router.get("/info/{object_name:path}")
async def get_image_info(object_name: str):
    """
    Get detailed information about a GeoTIFF image in the bucket.
    
    Args:
        object_name: Filename (without prefix)
        
    Returns:
        Image information or 404 if not found
        
    Raises:
        HTTPException: If info retrieval fails
    """
    try:
        # Add data/ prefix internally
        full_object_name = f"data/{object_name}"
        info = object_storage.get_object_info(full_object_name)
        
        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"Image '{object_name}' not found"
            )
        
        return ImageInfo(
            name=object_name,  # Return filename without prefix
            size=info["size"],
            last_modified=info["last_modified"],
            content_type=info["content_type"],
            etag=info["etag"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting image info: {str(e)}"
        )
