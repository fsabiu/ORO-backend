"""
Ruleset API routes.

This module defines the FastAPI routes for ruleset operations,
handling HTTP requests and responses.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import JSONResponse

from ..database import Database
from ..services.ruleset_service import RulesetService
from ..models import (
    RulesetCreate, 
    RulesetUpdate, 
    RulesetResponse, 
    RulesetListResponse,
    ErrorResponse,
    SuccessResponse
)


def get_database() -> Database:
    """Dependency to get database connection."""
    db = Database()
    db.connect()
    return db


def get_ruleset_service(db: Database = Depends(get_database)) -> RulesetService:
    """Dependency to get ruleset service."""
    return RulesetService(db)


router = APIRouter(prefix="/rulesets", tags=["rulesets"])


@router.post(
    "/",
    response_model=RulesetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ruleset",
    description="Create a new ruleset with the specified name and area of interest."
)
async def create_ruleset(
    ruleset_data: RulesetCreate,
    service: RulesetService = Depends(get_ruleset_service)
):
    """
    Create a new ruleset.
    
    - **name**: Name of the ruleset (required)
    - **description**: Description of the ruleset (optional)
    - **user_groups**: User groups configuration as JSON (optional)
    - **conditions**: Rule conditions as JSON (optional)
    - **area_of_interest**: Geographic area of interest as GeoJSON geometry (required)
    - **author**: Author name (required)
    """
    try:
        with service.db:
            return service.create_ruleset(ruleset_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create ruleset: {str(e)}"
        )


@router.get(
    "/",
    response_model=RulesetListResponse,
    summary="Get all rulesets",
    description="Get a paginated list of all rulesets with optional filtering by author."
)
async def get_rulesets(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(10, ge=1, le=100, description="Number of items per page"),
    author: Optional[str] = Query(None, description="Filter by author name"),
    service: RulesetService = Depends(get_ruleset_service)
):
    """
    Get a paginated list of rulesets.
    
    - **page**: Page number (default: 1)
    - **per_page**: Number of items per page (default: 10, max: 100)
    - **author**: Filter by author name (optional)
    """
    try:
        with service.db:
            result = service.get_rulesets(page=page, per_page=per_page, author=author)
            return RulesetListResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve rulesets: {str(e)}"
        )


@router.get(
    "/{ruleset_id}",
    response_model=RulesetResponse,
    summary="Get a ruleset by ID",
    description="Get a specific ruleset by its ID."
)
async def get_ruleset(
    ruleset_id: int,
    service: RulesetService = Depends(get_ruleset_service)
):
    """
    Get a ruleset by ID.
    
    - **ruleset_id**: ID of the ruleset to retrieve
    """
    try:
        with service.db:
            return service.get_ruleset(ruleset_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ruleset with ID {ruleset_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ruleset: {str(e)}"
        )


@router.put(
    "/{ruleset_id}",
    response_model=RulesetResponse,
    summary="Update a ruleset",
    description="Update an existing ruleset with new data."
)
async def update_ruleset(
    ruleset_id: int,
    ruleset_data: RulesetUpdate,
    service: RulesetService = Depends(get_ruleset_service)
):
    """
    Update a ruleset.
    
    - **ruleset_id**: ID of the ruleset to update
    - **name**: New name for the ruleset (optional)
    - **description**: New description for the ruleset (optional)
    - **user_groups**: New user groups configuration (optional)
    - **conditions**: New rule conditions (optional)
    - **area_of_interest**: New area of interest (optional)
    - **author**: New author name (optional)
    """
    try:
        with service.db:
            return service.update_ruleset(ruleset_id, ruleset_data)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ruleset with ID {ruleset_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update ruleset: {str(e)}"
        )


@router.delete(
    "/{ruleset_id}",
    response_model=SuccessResponse,
    summary="Delete a ruleset",
    description="Delete a ruleset by its ID."
)
async def delete_ruleset(
    ruleset_id: int,
    service: RulesetService = Depends(get_ruleset_service)
):
    """
    Delete a ruleset.
    
    - **ruleset_id**: ID of the ruleset to delete
    """
    try:
        with service.db:
            success = service.delete_ruleset(ruleset_id)
            if success:
                return SuccessResponse(
                    message="Ruleset deleted successfully",
                    data={"id": ruleset_id}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete ruleset"
                )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ruleset with ID {ruleset_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete ruleset: {str(e)}"
        )
