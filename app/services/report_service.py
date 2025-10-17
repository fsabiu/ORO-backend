"""
Report service for handling business logic and database operations.

This module contains the service layer for report operations,
handling the conversion between database records and API models.
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..database import Database
from ..models import ReportCreate, ReportUpdate, ReportResponse, GeometryBase
from .validation_service import ValidationService


class ReportService:
    """Service class for report operations."""
    
    def __init__(self, db: Database):
        """
        Initialize the report service.
        
        Args:
            db: Database connection instance
        """
        self.db = db
    
    def create_report(self, report_data: ReportCreate) -> ReportResponse:
        """
        Create a new report.
        
        Args:
            report_data: Report creation data
            
        Returns:
            Created report response
            
        Raises:
            Exception: If creation fails
        """
        # Build the query with or without geometry
        if report_data.area_of_interest:
            sdo_geometry_sql = self._geometry_to_sdo(report_data.area_of_interest)
            query = f"""
                INSERT INTO REPORTS (name, bucket_img_path, area_of_interest, author)
                VALUES (:name, :bucket_img_path, {sdo_geometry_sql}, :author)
            """
        else:
            query = """
                INSERT INTO REPORTS (name, bucket_img_path, area_of_interest, author)
                VALUES (:name, :bucket_img_path, NULL, :author)
            """
        
        params = {
            'name': report_data.name,
            'bucket_img_path': report_data.bucket_img_path,
            'author': report_data.author
        }
        
        # Execute the insert
        cursor = self.db.connection.cursor()
        cursor.execute(query, params)
        self.db.connection.commit()  # CRITICAL: Commit the transaction
        cursor.close()
        
        # Get the generated ID by querying the last inserted record
        id_query = """
            SELECT id FROM REPORTS 
            WHERE name = :name AND author = :author 
            ORDER BY created_at DESC 
            FETCH FIRST 1 ROWS ONLY
        """
        
        id_params = {
            'name': report_data.name,
            'author': report_data.author
        }
        
        cursor = self.db.connection.cursor()
        cursor.execute(id_query, id_params)
        result = cursor.fetchone()
        report_id = result[0] if result else None
        cursor.close()
        
        if report_id is None:
            raise Exception("Failed to get generated report ID")
        
        # Return the created report
        return self.get_report(report_id)
    
    def get_report(self, report_id: int) -> ReportResponse:
        """
        Get a report by ID.
        
        Args:
            report_id: Report ID
            
        Returns:
            Report response
            
        Raises:
            Exception: If report not found
        """
        query = """
            SELECT id, name, status, timestamp, bucket_img_path, image_footprint, area_of_interest, author, created_at, updated_at
            FROM REPORTS
            WHERE id = :report_id
        """
        
        result = self.db.execute_query(query, {'report_id': report_id})
        
        if not result:
            raise Exception(f"Report with ID {report_id} not found")
        
        report = result[0]
        
        # Convert SDO_GEOMETRY to GeoJSON format if present
        image_footprint = None
        if report['IMAGE_FOOTPRINT']:
            image_footprint = self._sdo_to_geometry(report['IMAGE_FOOTPRINT'])
        
        area_of_interest = None
        if report['AREA_OF_INTEREST']:
            area_of_interest = self._sdo_to_geometry(report['AREA_OF_INTEREST'])
        
        return ReportResponse(
            id=report['ID'],
            name=report['NAME'],
            status=report['STATUS'],
            timestamp=report['TIMESTAMP'],
            bucket_img_path=report['BUCKET_IMG_PATH'],
            image_footprint=image_footprint,
            area_of_interest=area_of_interest,
            author=report['AUTHOR'],
            created_at=report['CREATED_AT'],
            updated_at=report['UPDATED_AT']
        )
    
    def get_reports(self, page: int = 1, per_page: int = 10, author: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a list of reports with pagination.
        
        Args:
            page: Page number (1-based)
            per_page: Number of items per page
            author: Filter by author name (optional)
            status: Filter by status (optional)
            
        Returns:
            Dictionary containing reports list and pagination info
        """
        offset = (page - 1) * per_page
        
        # Build the WHERE clause
        where_conditions = []
        params = {'offset': offset, 'per_page': per_page}
        
        if author is not None:
            where_conditions.append("author = :author")
            params['author'] = author
        
        if status is not None:
            where_conditions.append("status = :status")
            params['status'] = status
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM REPORTS {where_clause}"
        count_result = self.db.execute_query(count_query, {k: v for k, v in params.items() if k != 'offset' and k != 'per_page'})
        total = count_result[0]['TOTAL'] if count_result else 0
        
        # Get reports
        query = f"""
            SELECT id, name, status, timestamp, bucket_img_path, image_footprint, area_of_interest, author, created_at, updated_at
            FROM REPORTS
            {where_clause}
            ORDER BY created_at DESC
            OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
        """
        
        results = self.db.execute_query(query, params)
        
        reports = []
        for result in results:
            # Convert SDO_GEOMETRY to GeoJSON format if present
            image_footprint = None
            if result['IMAGE_FOOTPRINT']:
                image_footprint = self._sdo_to_geometry(result['IMAGE_FOOTPRINT'])
            
            area_of_interest = None
            if result['AREA_OF_INTEREST']:
                area_of_interest = self._sdo_to_geometry(result['AREA_OF_INTEREST'])
            
            reports.append(ReportResponse(
                id=result['ID'],
                name=result['NAME'],
                status=result['STATUS'],
                timestamp=result['TIMESTAMP'],
                bucket_img_path=result['BUCKET_IMG_PATH'],
                image_footprint=image_footprint,
                area_of_interest=area_of_interest,
                author=result['AUTHOR'],
                created_at=result['CREATED_AT'],
                updated_at=result['UPDATED_AT']
            ))
        
        return {
            'reports': reports,
            'total': total,
            'page': page,
            'per_page': per_page
        }
    
    def update_report(self, report_id: int, report_data: ReportUpdate) -> ReportResponse:
        """
        Update an existing report.
        
        Args:
            report_id: Report ID
            report_data: Report update data
            
        Returns:
            Updated report response
            
        Raises:
            Exception: If report not found or update fails
        """
        # Check if report exists
        self.get_report(report_id)
        
        # Build update query dynamically
        update_fields = []
        params = {'report_id': report_id}
        
        if report_data.name is not None:
            update_fields.append("name = :name")
            params['name'] = report_data.name
        
        if report_data.status is not None:
            update_fields.append("status = :status")
            params['status'] = report_data.status
        
        if report_data.bucket_img_path is not None:
            update_fields.append("bucket_img_path = :bucket_img_path")
            params['bucket_img_path'] = report_data.bucket_img_path
        
        # Note: Geometry updates need to be handled separately due to SQL construction
        # For now, we'll skip geometry updates in this method
        # TODO: Implement proper geometry update handling
        if report_data.image_footprint is not None:
            raise ValueError("Updating image_footprint is not yet supported. Please use a dedicated endpoint.")
        
        if report_data.area_of_interest is not None:
            raise ValueError("Updating area_of_interest is not yet supported. Please use a dedicated endpoint.")
        
        if report_data.author is not None:
            update_fields.append("author = :author")
            params['author'] = report_data.author
        
        if not update_fields:
            return self.get_report(report_id)
        
        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"""
            UPDATE REPORTS
            SET {', '.join(update_fields)}
            WHERE id = :report_id
        """
        
        self.db.execute_update(query, params)
        
        return self.get_report(report_id)
    
    def delete_report(self, report_id: int) -> bool:
        """
        Delete a report.
        
        Args:
            report_id: Report ID
            
        Returns:
            True if deleted successfully
            
        Raises:
            Exception: If report not found or deletion fails
        """
        # Check if report exists
        self.get_report(report_id)
        
        query = "DELETE FROM REPORTS WHERE id = :report_id"
        affected_rows = self.db.execute_update(query, {'report_id': report_id})
        
        return affected_rows > 0
    
    def create_report_with_processing(self, report_data: ReportCreate) -> Dict[str, Any]:
        """
        Create a new report and trigger background processing.
        
        This method implements the CREATE REPORT specification:
        - Validates all required fields and dependencies
        - Creates the initial report record
        - Triggers background processing task
        - Returns 202 Accepted response
        
        Args:
            report_data: Report creation data with new specifications
            
        Returns:
            Dictionary containing report_id and status
            
        Raises:
            Exception: If validation fails or creation fails
        """
        # Initialize validation service
        validation_service = ValidationService(self.db)
        
        # Step 1: Validation
        self._validate_report_creation(report_data, validation_service)
        
        # Step 2: Create report record
        report_id = self._create_report_record(report_data)
        
        # Step 3: Trigger background processing
        self._trigger_background_processing(report_id, report_data)
        
        return {
            "report_id": report_id,
            "status": "accepted",
            "message": "Report creation initiated. Processing will begin shortly."
        }
    
    def _validate_report_creation(self, report_data: ReportCreate, validation_service: ValidationService):
        """
        Validate all requirements for report creation.
        
        Args:
            report_data: Report creation data
            validation_service: Validation service instance
            
        Raises:
            Exception: If any validation fails
        """
        # Validate image exists in object storage
        if not validation_service.validate_image_exists(report_data.image_name):
            raise Exception(f"Image '{report_data.image_name}' not found in object storage")
        
        # Validate all rulesets exist
        ruleset_validation = validation_service.validate_rulesets_exist(report_data.ruleset_ids)
        if not ruleset_validation["valid"]:
            missing = ruleset_validation["missing_rulesets"]
            raise Exception(f"Rulesets not found: {missing}")
        
        # Validate model exists
        if not validation_service.validate_model_exists(report_data.model_id):
            raise Exception(f"Model '{report_data.model_id}' not found or not available")
        
        # Validate author exists
        if not validation_service.validate_author_exists(report_data.author_id):
            raise Exception(f"Author '{report_data.author_id}' not found")
        
        # Validate area of interest if provided
        if report_data.area_of_interest:
            if not validation_service.validate_geometry(report_data.area_of_interest.dict()):
                raise Exception("Invalid area of interest geometry")
    
    def _create_report_record(self, report_data: ReportCreate) -> int:
        """
        Create the initial report record in the database.
        
        Args:
            report_data: Report creation data
            
        Returns:
            ID of the created report
        """
        # Build the query with or without geometry
        if report_data.area_of_interest:
            sdo_geometry_sql = self._geometry_to_sdo(report_data.area_of_interest)
            query = f"""
                INSERT INTO REPORTS (name, status, bucket_img_path, area_of_interest, author)
                VALUES (:name, 'initiating', :bucket_img_path, {sdo_geometry_sql}, :author)
            """
        else:
            query = """
                INSERT INTO REPORTS (name, status, bucket_img_path, area_of_interest, author)
                VALUES (:name, 'initiating', :bucket_img_path, NULL, :author)
            """
        
        params = {
            'name': report_data.report_name,
            'bucket_img_path': report_data.image_name,
            'author': report_data.author_id
        }
        
        # Execute the insert
        cursor = self.db.connection.cursor()
        cursor.execute(query, params)
        self.db.connection.commit()  # CRITICAL: Commit the transaction
        cursor.close()
        
        # Get the generated ID by querying the last inserted record
        id_query = """
            SELECT id FROM REPORTS 
            WHERE name = :name AND author = :author 
            ORDER BY created_at DESC 
            FETCH FIRST 1 ROWS ONLY
        """
        
        id_params = {
            'name': report_data.report_name,
            'author': report_data.author_id
        }
        
        cursor = self.db.connection.cursor()
        cursor.execute(id_query, id_params)
        result = cursor.fetchone()
        report_id = result[0] if result else None
        cursor.close()
        
        if report_id is None:
            raise Exception("Failed to get generated report ID")
        
        return report_id
    
    def _trigger_background_processing(self, report_id: int, report_data: ReportCreate):
        """
        Trigger the background processing task.
        
        Args:
            report_id: ID of the created report
            report_data: Original report creation data
            
        TODO: Implement actual background task triggering
        - Use Celery or similar task queue
        - Pass all necessary parameters
        - Handle task queuing errors
        """
        # TODO: Implement background task triggering
        # This is a placeholder implementation
        # In production, you would:
        # 1. Import the Celery task
        # 2. Queue the task with all parameters
        # 3. Handle any queuing errors
        # 4. Log the task submission
        
        # from ..tasks.report_processing import process_report_task
        # 
        # try:
        #     task = process_report_task.delay(
        #         report_id=report_id,
        #         model_id=report_data.model_id,
        #         confidence_threshold=report_data.confidence_threshold,
        #         ruleset_ids=report_data.ruleset_ids,
        #         area_of_interest=report_data.area_of_interest.dict() if report_data.area_of_interest else None
        #     )
        #     logger.info(f"Background task queued for report_id: {report_id}, task_id: {task.id}")
        # except Exception as e:
        #     logger.error(f"Failed to queue background task for report_id: {report_id}, error: {str(e)}")
        #     raise Exception(f"Failed to start background processing: {str(e)}")
        
        # For now, just log the action
        print(f"TODO: Trigger background processing for report_id: {report_id}")
        print(f"Parameters: model_id={report_data.model_id}, confidence={report_data.confidence_threshold}")
        print(f"Rulesets: {report_data.ruleset_ids}")
    
    def _geometry_to_sdo(self, geometry: GeometryBase) -> str:
        """
        Convert GeoJSON geometry to Oracle SDO_GEOMETRY format.
        
        Args:
            geometry: GeoJSON geometry
            
        Returns:
            SDO_GEOMETRY string
        """
        # This is a simplified conversion - in production, you'd want a more robust solution
        coords = geometry.coordinates
        
        if geometry.type == 'Polygon':
            # Convert to SDO_GEOMETRY format
            # For now, we'll store as a simple polygon
            return f"SDO_GEOMETRY(2003, 4326, NULL, SDO_ELEM_INFO_ARRAY(1, 1003, 1), SDO_ORDINATE_ARRAY({self._coords_to_string(coords[0])}))"
        else:
            # For other geometry types, you'd implement similar conversions
            raise ValueError(f"Unsupported geometry type: {geometry.type}")
    
    def _sdo_to_geometry(self, sdo_geometry) -> GeometryBase:
        """
        Convert Oracle SDO_GEOMETRY to GeoJSON geometry format.
        
        Args:
            sdo_geometry: Oracle SDO_GEOMETRY object
            
        Returns:
            GeoJSON geometry
        """
        # This is a simplified conversion - in production, you'd want a more robust solution
        # For now, we'll return a basic polygon structure
        # In a real implementation, you'd parse the SDO_GEOMETRY object
        
        # Placeholder - you'd implement proper SDO_GEOMETRY to GeoJSON conversion here
        return GeometryBase(
            type="Polygon",
            coordinates=[[[-74.0059, 40.7128], [-73.9352, 40.7128], [-73.9352, 40.7589], [-74.0059, 40.7589], [-74.0059, 40.7128]]]
        )
    
    def _coords_to_string(self, coords: List[List[float]]) -> str:
        """
        Convert coordinate array to string format for SDO_GEOMETRY.
        
        Args:
            coords: List of coordinate pairs
            
        Returns:
            Coordinate string
        """
        return ', '.join([f"{coord[0]}, {coord[1]}" for coord in coords])
