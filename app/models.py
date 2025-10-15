"""
Pydantic models for API data validation and serialization.

This module defines the data models used for API requests and responses,
ensuring proper data validation and type safety.
"""

from typing import Optional, List, Dict, Any
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


class RulesetCreate(BaseModel):
    """Model for creating a new ruleset."""
    name: str = Field(..., min_length=1, max_length=255, description="Ruleset name")
    description: Optional[str] = Field(None, max_length=1024, description="Ruleset description")
    user_groups: Optional[Dict[str, Any]] = Field(None, description="User groups configuration")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Rule conditions")
    area_of_interest: GeometryBase = Field(..., description="Geographic area of interest")
    author: str = Field(..., min_length=1, max_length=255, description="Author name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Urban Area Monitoring",
                "description": "Monitor urban areas for vehicle detection",
                "user_groups": ["admin", "analyst"],
                "conditions": {
                    "min_confidence": 0.8,
                    "object_types": ["car", "truck", "bus"]
                },
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
                "author": "admin@example.com"
            }
        }


class RulesetUpdate(BaseModel):
    """Model for updating an existing ruleset."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Ruleset name")
    description: Optional[str] = Field(None, max_length=1024, description="Ruleset description")
    user_groups: Optional[Dict[str, Any]] = Field(None, description="User groups configuration")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Rule conditions")
    area_of_interest: Optional[GeometryBase] = Field(None, description="Geographic area of interest")
    author: Optional[str] = Field(None, min_length=1, max_length=255, description="Author name")


class RulesetResponse(BaseModel):
    """Model for ruleset API responses."""
    id: int = Field(..., description="Ruleset ID")
    name: str = Field(..., description="Ruleset name")
    description: Optional[str] = Field(None, description="Ruleset description")
    user_groups: Optional[Dict[str, Any]] = Field(None, description="User groups configuration")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Rule conditions")
    area_of_interest: GeometryBase = Field(..., description="Geographic area of interest")
    author: str = Field(..., description="Author name")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Urban Area Monitoring",
                "description": "Monitor urban areas for vehicle detection",
                "user_groups": ["admin", "analyst"],
                "conditions": {
                    "min_confidence": 0.8,
                    "object_types": ["car", "truck", "bus"]
                },
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
                "author": "admin@example.com",
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
                        "name": "Urban Area Monitoring",
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
                        "author_id": 1,
                        "created_at": "2024-01-15T10:30:00Z"
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
