"""
Report API routes.

This module defines the REST API endpoints for report operations,
including CRUD operations and status management.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from ..database import get_database
from ..models import (
    ReportCreate, 
    ReportUpdate, 
    ReportResponse, 
    ReportListResponse,
    ReportCreationResponse,
    ErrorResponse,
    SuccessResponse
)
from ..services.report_service import ReportService
from ..services.validation_service import ValidationService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_model=ReportListResponse)
async def get_reports(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(10, ge=1, le=100, description="Number of items per page"),
    author: Optional[str] = Query(None, description="Filter by author"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db=Depends(get_database)
):
    """
    Get a list of reports with pagination and optional filtering.
    
    Args:
        page: Page number (1-based)
        per_page: Number of items per page (1-100)
        author: Filter by author name (optional)
        status: Filter by status (optional)
        db: Database dependency
        
    Returns:
        List of reports with pagination info
        
    Raises:
        HTTPException: If there's an error retrieving reports
    """
    try:
        service = ReportService(db)
        result = service.get_reports(page=page, per_page=per_page, author=author, status=status)
        
        return ReportListResponse(
            reports=result['reports'],
            total=result['total'],
            page=result['page'],
            per_page=result['per_page']
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving reports: {str(e)}"
        )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db=Depends(get_database)
):
    """
    Get a specific report by ID.
    
    Args:
        report_id: Report ID
        db: Database dependency
        
    Returns:
        Report details
        
    Raises:
        HTTPException: If report not found or error occurs
    """
    try:
        service = ReportService(db)
        report = service.get_report(report_id)
        return report
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Report with ID {report_id} not found"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving report: {str(e)}"
        )


@router.post("/", response_model=ReportCreationResponse, status_code=202)
async def create_report(
    report_data: ReportCreate,
    db=Depends(get_database)
):
    """
    Create a new report and trigger background processing.
    
    This endpoint implements the CREATE REPORT specification:
    - Validates all required fields and dependencies
    - Creates the initial report record with 'pending' status
    - Triggers asynchronous background processing
    - Returns 202 Accepted with report_id for tracking
    
    Args:
        report_data: Report creation data with processing parameters
        db: Database dependency
        
    Returns:
        Dictionary with report_id and status information
        
    Raises:
        HTTPException: If validation fails or creation fails
    """
    try:
        service = ReportService(db)
        result = service.create_report_with_processing(report_data)
        return result
    except Exception as e:
        # Determine appropriate status code based on error type
        if "not found" in str(e).lower():
            status_code = 404
        elif "validation" in str(e).lower() or "invalid" in str(e).lower():
            status_code = 400
        else:
            status_code = 500
            
        raise HTTPException(
            status_code=status_code,
            detail=f"Error creating report: {str(e)}"
        )


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: int,
    report_data: ReportUpdate,
    db=Depends(get_database)
):
    """
    Update an existing report.
    
    Args:
        report_id: Report ID
        report_data: Report update data
        db: Database dependency
        
    Returns:
        Updated report details
        
    Raises:
        HTTPException: If report not found or update fails
    """
    try:
        service = ReportService(db)
        report = service.update_report(report_id, report_data)
        return report
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Report with ID {report_id} not found"
            )
        raise HTTPException(
            status_code=400,
            detail=f"Error updating report: {str(e)}"
        )


@router.delete("/{report_id}", response_model=SuccessResponse)
async def delete_report(
    report_id: int,
    db=Depends(get_database)
):
    """
    Delete a report.
    
    Args:
        report_id: Report ID
        db: Database dependency
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If report not found or deletion fails
    """
    try:
        service = ReportService(db)
        success = service.delete_report(report_id)
        
        if success:
            return SuccessResponse(
                message="Report deleted successfully",
                data={"id": report_id}
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete report"
            )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Report with ID {report_id} not found"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting report: {str(e)}"
        )


@router.patch("/{report_id}/status", response_model=ReportResponse)
async def update_report_status(
    report_id: int,
    status: str = Query(..., description="New status"),
    db=Depends(get_database)
):
    """
    Update the status of a report.
    
    Args:
        report_id: Report ID
        status: New status (pending, processing, completed, failed)
        db: Database dependency
        
    Returns:
        Updated report details
        
    Raises:
        HTTPException: If report not found or status update fails
    """
    try:
        service = ReportService(db)
        report_data = ReportUpdate(status=status)
        report = service.update_report(report_id, report_data)
        return report
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Report with ID {report_id} not found"
            )
        raise HTTPException(
            status_code=400,
            detail=f"Error updating report status: {str(e)}"
        )