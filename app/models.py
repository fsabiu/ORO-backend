"""
Pydantic models for API data validation and serialization.

This module defines the data models used for API requests and responses,
ensuring proper data validation and type safety.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
import json


class GeometryBase(BaseModel):
    """Base model for geometry data."""
    type: str = Field(..., description="Geometry type (e.g., 'Polygon', 'Point')")
    coordinates: List[Any] = Field(..., description="Geometry coordinates")
    
    @validator('type')
    def validate_geometry_type(cls, v):
        allowed_types = ['Polygon', 'Point', 'LineString', 'MultiPolygon', 'MultiPoint', 'MultiLineString']
        if v not in allowed_types:
            raise ValueError(f'Geometry type must be one of: {", ".join(allowed_types)}')
        return v


class Condition(BaseModel):
    """Model for individual rule conditions."""
    object_id: Optional[int] = Field(None, description="Object ID (optional)")
    object_name: str = Field(..., description="Name of the object to detect")
    condition: str = Field(..., description="Condition type (e.g., 'more than', 'less than')")
    count: int = Field(..., ge=0, description="Count threshold for the condition")
    logical_operator: Optional[str] = Field(None, description="Logical operator for combining conditions ('AND', 'OR')")
    
    @validator('condition')
    def validate_condition(cls, v):
        allowed_conditions = ['more than', 'less than', 'equals', 'not equals']
        if v not in allowed_conditions:
            raise ValueError(f'Condition must be one of: {", ".join(allowed_conditions)}')
        return v
    
    @validator('logical_operator')
    def validate_logical_operator(cls, v):
        if v is not None:
            allowed_operators = ['AND', 'OR']
            if v not in allowed_operators:
                raise ValueError(f'Logical operator must be one of: {", ".join(allowed_operators)}')
        return v


class RulesetCreate(BaseModel):
    """Model for creating a new ruleset."""
    name: str = Field(..., min_length=1, max_length=255, description="Ruleset name")
    description: Optional[str] = Field(None, max_length=1024, description="Ruleset description")
    user_groups: List[str] = Field(..., description="List of user group email addresses")
    conditions: List[Condition] = Field(..., description="List of rule conditions")
    author: str = Field(..., min_length=1, max_length=255, description="Author name")
    
    @validator('user_groups')
    def validate_user_groups(cls, v):
        if not v:
            raise ValueError('At least one user group must be specified')
        return v
    
    @validator('conditions')
    def validate_conditions(cls, v):
        if not v:
            raise ValueError('At least one condition must be specified')
        # First condition should not have logical_operator
        if v and v[0].logical_operator is not None:
            raise ValueError('First condition cannot have a logical operator')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "City Reconnaissance",
                "description": "Policy for civilian city reconnaissance and adjacent missions",
                "user_groups": ["francesco@company.com", "claudia@company.com"],
                "conditions": [
                    {
                        "object_name": "Large Vehicles",
                        "condition": "more than",
                        "count": 20
                    },
                    {
                        "object_id": 2,
                        "object_name": "Civilian cars",
                        "condition": "less than",
                        "count": 5,
                        "logical_operator": "AND"
                    },
                    {
                        "object_id": 3,
                        "object_name": "Aircrafts",
                        "condition": "more than",
                        "count": 3,
                        "logical_operator": "OR"
                    }
                ],
                "author": "Wilhelm Matuszewski"
            }
        }


class RulesetUpdate(BaseModel):
    """Model for updating an existing ruleset."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Ruleset name")
    description: Optional[str] = Field(None, max_length=1024, description="Ruleset description")
    user_groups: Optional[List[str]] = Field(None, description="List of user group email addresses")
    conditions: Optional[List[Condition]] = Field(None, description="List of rule conditions")
    author: Optional[str] = Field(None, min_length=1, max_length=255, description="Author name")
    
    @validator('user_groups')
    def validate_user_groups(cls, v):
        if v is not None and not v:
            raise ValueError('User groups list cannot be empty')
        return v
    
    @validator('conditions')
    def validate_conditions(cls, v):
        if v is not None:
            if not v:
                raise ValueError('Conditions list cannot be empty')
            # First condition should not have logical_operator
            if v and v[0].logical_operator is not None:
                raise ValueError('First condition cannot have a logical operator')
        return v


class RulesetResponse(BaseModel):
    """Model for ruleset API responses."""
    id: int = Field(..., description="Ruleset ID")
    name: str = Field(..., description="Ruleset name")
    description: Optional[str] = Field(None, description="Ruleset description")
    user_groups: List[str] = Field(..., description="List of user group email addresses")
    conditions: List[Condition] = Field(..., description="List of rule conditions")
    author: str = Field(..., description="Author name")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "City Reconnaissance",
                "description": "Policy for civilian city reconnaissance and adjacent missions",
                "user_groups": ["francesco@company.com", "claudia@company.com"],
                "conditions": [
                    {
                        "object_name": "Large Vehicles",
                        "condition": "more than",
                        "count": 20
                    },
                    {
                        "object_id": 2,
                        "object_name": "Civilian cars",
                        "condition": "less than",
                        "count": 5,
                        "logical_operator": "AND"
                    },
                    {
                        "object_id": 3,
                        "object_name": "Aircrafts",
                        "condition": "more than",
                        "count": 3,
                        "logical_operator": "OR"
                    }
                ],
                "author": "Wilhelm Matuszewski",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class RulesetListResponse(BaseModel):
    """Model for ruleset list API responses."""
    rulesets: List[RulesetResponse] = Field(..., description="List of rulesets")
    total: int = Field(..., description="Total number of rulesets")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of items per page")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rulesets": [
                    {
                        "id": 1,
                        "name": "City Reconnaissance",
                        "description": "Policy for civilian city reconnaissance and adjacent missions",
                        "user_groups": ["francesco@company.com", "claudia@company.com"],
                        "conditions": [
                            {
                                "object_name": "Large Vehicles",
                                "condition": "more than",
                                "count": 20
                            }
                        ],
                        "author": "Wilhelm Matuszewski",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "per_page": 10
            }
        }


class ErrorResponse(BaseModel):
    """Model for error responses."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Not Found",
                "detail": "Ruleset with ID 123 not found",
                "status_code": 404
            }
        }


class SuccessResponse(BaseModel):
    """Model for success responses."""
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Ruleset deleted successfully",
                "data": {"id": 123}
            }
        }


# =============================================================================
# REPORT MODELS
# =============================================================================

class ReportCreate(BaseModel):
    """Model for creating a new report."""
    image_name: str = Field(..., min_length=1, max_length=255, description="Filename of the GeoTIFF in object storage")
    report_name: str = Field(..., min_length=1, max_length=255, description="User-friendly name for the analysis report")
    model_id: str = Field(..., min_length=1, max_length=255, description="Identifier for the ML model to be used")
    confidence_threshold: float = Field(..., ge=0.0, le=1.0, description="Minimum confidence score for detections (0.0 to 1.0)")
    author_id: str = Field(..., min_length=1, max_length=255, description="ID of the user initiating the request")
    ruleset_ids: List[int] = Field(..., description="Array of ruleset IDs to check against")
    area_of_interest: Optional[GeometryBase] = Field(None, description="Geographic area of interest")
    
    @validator('ruleset_ids')
    def validate_ruleset_ids(cls, v):
        if not v:
            raise ValueError('At least one ruleset ID must be provided')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "image_name": "urban_analysis_2024_01_15.tif",
                "report_name": "Urban Analysis - Downtown District",
                "model_id": "yolo_v8_urban_detection",
                "confidence_threshold": 0.7,
                "author_id": "user_123",
                "ruleset_ids": [1, 2, 3],
                "area_of_interest": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-74.0059, 40.7128],
                        [-73.9352, 40.7128],
                        [-73.9352, 40.7589],
                        [-74.0059, 40.7589],
                        [-74.0059, 40.7128]
                    ]]
                }
            }
        }


class ReportUpdate(BaseModel):
    """Model for updating an existing report."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Report name")
    status: Optional[str] = Field(None, description="Processing status")
    bucket_img_path: Optional[str] = Field(None, min_length=1, max_length=512, description="Path to the image in the bucket")
    area_of_interest: Optional[GeometryBase] = Field(None, description="Geographic area of interest")
    author: Optional[str] = Field(None, min_length=1, max_length=255, description="Author name")
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['pending', 'processing', 'completed', 'failed']
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v


class ReportResponse(BaseModel):
    """Model for report API responses."""
    id: int = Field(..., description="Report ID")
    name: str = Field(..., description="Report name")
    status: str = Field(..., description="Processing status")
    timestamp: Optional[datetime] = Field(None, description="Processing timestamp")
    bucket_img_path: str = Field(..., description="Path to the image in the bucket")
    area_of_interest: Optional[GeometryBase] = Field(None, description="Geographic area of interest")
    author: str = Field(..., description="Author name")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Urban Analysis - Downtown District",
                "status": "completed",
                "timestamp": "2024-01-15T10:30:00Z",
                "bucket_img_path": "images/urban_analysis_2024_01_15.tif",
                "area_of_interest": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-74.0059, 40.7128],
                        [-73.9352, 40.7128],
                        [-73.9352, 40.7589],
                        [-74.0059, 40.7589],
                        [-74.0059, 40.7128]
                    ]]
                },
                "author": "analyst@company.com",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class ReportListResponse(BaseModel):
    """Model for report list API responses."""
    reports: List[ReportResponse] = Field(..., description="List of reports")
    total: int = Field(..., description="Total number of reports")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of items per page")


class ReportCreationResponse(BaseModel):
    """Model for report creation response (202 Accepted)."""
    report_id: int = Field(..., description="ID of the created report")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_id": 123,
                "status": "accepted",
                "message": "Report creation initiated. Processing will begin shortly."
            }
        }


# =============================================================================
# IMAGE MODELS
# =============================================================================

class ImageUploadResponse(BaseModel):
    """Model for image upload response."""
    success: bool = Field(..., description="Upload success status")
    message: str = Field(..., description="Status message")
    object_name: str = Field(..., description="Object name in bucket")
    bytes_uploaded: int = Field(..., description="Number of bytes uploaded")
    content_type: str = Field(..., description="Content type of uploaded file")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "File uploaded successfully",
                "object_name": "urban_analysis_2024_01_15.tif",
                "bytes_uploaded": 15728640,
                "content_type": "image/tiff"
            }
        }


class ImageInfo(BaseModel):
    """Model for image information."""
    name: str = Field(..., description="Object name in bucket")
    size: int = Field(..., description="File size in bytes")
    last_modified: Optional[str] = Field(None, description="Last modified timestamp")
    content_type: Optional[str] = Field(None, description="Content type")
    etag: Optional[str] = Field(None, description="ETag for the object")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "urban_analysis_2024_01_15.tif",
                "size": 15728640,
                "last_modified": "Mon, 15 Jan 2024 10:30:00 GMT",
                "content_type": "image/tiff",
                "etag": "\"d41d8cd98f00b204e9800998ecf8427e\""
            }
        }


class ImageListResponse(BaseModel):
    """Model for image list response."""
    success: bool = Field(..., description="Operation success status")
    prefix: str = Field(..., description="Prefix used for listing (empty for frontend)")
    count: int = Field(..., description="Number of images found")
    images: List[ImageInfo] = Field(..., description="List of image information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "prefix": "",
                "count": 3,
                "images": [
                    {
                        "name": "urban_analysis_2024_01_15.tif",
                        "size": 15728640,
                        "last_modified": "Mon, 15 Jan 2024 10:30:00 GMT",
                        "content_type": "image/tiff",
                        "etag": "\"d41d8cd98f00b204e9800998ecf8427e\""
                    },
                    {
                        "name": "port_activity_2024_01_14.tif",
                        "size": 20971520,
                        "last_modified": "Sun, 14 Jan 2024 15:45:00 GMT",
                        "content_type": "image/tiff",
                        "etag": "\"e41d8cd98f00b204e9800998ecf8427f\""
                    }
                ]
            }
        }


class ImageListRequest(BaseModel):
    """Model for image list request parameters."""
    limit: int = Field(default=1000, ge=1, le=10000, description="Maximum number of objects to return")
    timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "limit": 100,
                "timeout": 30
            }
        }
