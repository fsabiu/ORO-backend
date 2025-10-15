"""
Ruleset service for handling business logic and database operations.

This module contains the service layer for ruleset operations,
handling the conversion between database records and API models.
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..database import Database
from ..models import RulesetCreate, RulesetUpdate, RulesetResponse, GeometryBase, Condition


class RulesetService:
    """Service class for ruleset operations."""
    
    def __init__(self, db: Database):
        """
        Initialize the ruleset service.
        
        Args:
            db: Database connection instance
        """
        self.db = db
    
    def create_ruleset(self, ruleset_data: RulesetCreate) -> RulesetResponse:
        """
        Create a new ruleset.
        
        Args:
            ruleset_data: Ruleset creation data
            
        Returns:
            Created ruleset response
            
        Raises:
            Exception: If creation fails
        """
        # Convert geometry to Oracle SDO_GEOMETRY format
        sdo_geometry = self._geometry_to_sdo(ruleset_data.area_of_interest)
        
        # Convert JSON fields to strings for Oracle
        user_groups_json = json.dumps(ruleset_data.user_groups) if ruleset_data.user_groups else None
        conditions_json = json.dumps([condition.dict() for condition in ruleset_data.conditions]) if ruleset_data.conditions else None
        
        # Insert the ruleset
        query = """
            INSERT INTO RULESETS (name, description, user_groups, conditions, area_of_interest, author)
            VALUES (:name, :description, :user_groups, :conditions, SDO_GEOMETRY(:sdo_geometry), :author)
            RETURNING id INTO :ruleset_id
        """
        
        params = {
            'name': ruleset_data.name,
            'description': ruleset_data.description,
            'user_groups': user_groups_json,
            'conditions': conditions_json,
            'sdo_geometry': sdo_geometry,
            'author': ruleset_data.author,
            'ruleset_id': None
        }
        
        # Execute the insert
        cursor = self.db.connection.cursor()
        cursor.execute(query, params)
        ruleset_id = cursor.fetchone()[0]
        cursor.close()
        
        # Return the created ruleset
        return self.get_ruleset(ruleset_id)
    
    def get_ruleset(self, ruleset_id: int) -> RulesetResponse:
        """
        Get a ruleset by ID.
        
        Args:
            ruleset_id: Ruleset ID
            
        Returns:
            Ruleset response
            
        Raises:
            Exception: If ruleset not found
        """
        query = """
            SELECT id, name, description, user_groups, conditions, area_of_interest, author, created_at, updated_at
            FROM RULESETS
            WHERE id = :ruleset_id
        """
        
        result = self.db.execute_query(query, {'ruleset_id': ruleset_id})
        
        if not result:
            raise Exception(f"Ruleset with ID {ruleset_id} not found")
        
        ruleset = result[0]
        
        # Convert SDO_GEOMETRY to GeoJSON format
        area_of_interest = self._sdo_to_geometry(ruleset['AREA_OF_INTEREST'])
        
        # Parse JSON fields
        user_groups = json.loads(ruleset['USER_GROUPS']) if ruleset['USER_GROUPS'] else []
        conditions_data = json.loads(ruleset['CONDITIONS']) if ruleset['CONDITIONS'] else []
        conditions = [Condition(**condition) for condition in conditions_data]
        
        return RulesetResponse(
            id=ruleset['ID'],
            name=ruleset['NAME'],
            description=ruleset['DESCRIPTION'],
            user_groups=user_groups,
            conditions=conditions,
            area_of_interest=area_of_interest,
            author=ruleset['AUTHOR'],
            created_at=ruleset['CREATED_AT'],
            updated_at=ruleset['UPDATED_AT']
        )
    
    def get_rulesets(self, page: int = 1, per_page: int = 10, author: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a list of rulesets with pagination.
        
        Args:
            page: Page number (1-based)
            per_page: Number of items per page
            author: Filter by author name (optional)
            
        Returns:
            Dictionary containing rulesets list and pagination info
        """
        offset = (page - 1) * per_page
        
        # Build the WHERE clause
        where_clause = ""
        params = {'offset': offset, 'per_page': per_page}
        
        if author is not None:
            where_clause = "WHERE author = :author"
            params['author'] = author
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM RULESETS {where_clause}"
        count_result = self.db.execute_query(count_query, {k: v for k, v in params.items() if k != 'offset' and k != 'per_page'})
        total = count_result[0]['TOTAL'] if count_result else 0
        
        # Get rulesets
        query = f"""
            SELECT id, name, description, user_groups, conditions, area_of_interest, author, created_at, updated_at
            FROM RULESETS
            {where_clause}
            ORDER BY id
            OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
        """
        
        results = self.db.execute_query(query, params)
        
        rulesets = []
        for result in results:
            area_of_interest = self._sdo_to_geometry(result['AREA_OF_INTEREST'])
            
            # Parse JSON fields
            user_groups = json.loads(result['USER_GROUPS']) if result['USER_GROUPS'] else []
            conditions_data = json.loads(result['CONDITIONS']) if result['CONDITIONS'] else []
            conditions = [Condition(**condition) for condition in conditions_data]
            
            rulesets.append(RulesetResponse(
                id=result['ID'],
                name=result['NAME'],
                description=result['DESCRIPTION'],
                user_groups=user_groups,
                conditions=conditions,
                area_of_interest=area_of_interest,
                author=result['AUTHOR'],
                created_at=result['CREATED_AT'],
                updated_at=result['UPDATED_AT']
            ))
        
        return {
            'rulesets': rulesets,
            'total': total,
            'page': page,
            'per_page': per_page
        }
    
    def update_ruleset(self, ruleset_id: int, ruleset_data: RulesetUpdate) -> RulesetResponse:
        """
        Update an existing ruleset.
        
        Args:
            ruleset_id: Ruleset ID
            ruleset_data: Ruleset update data
            
        Returns:
            Updated ruleset response
            
        Raises:
            Exception: If ruleset not found or update fails
        """
        # Check if ruleset exists
        self.get_ruleset(ruleset_id)
        
        # Build update query dynamically
        update_fields = []
        params = {'ruleset_id': ruleset_id}
        
        if ruleset_data.name is not None:
            update_fields.append("name = :name")
            params['name'] = ruleset_data.name
        
        if ruleset_data.description is not None:
            update_fields.append("description = :description")
            params['description'] = ruleset_data.description
        
        if ruleset_data.user_groups is not None:
            user_groups_json = json.dumps(ruleset_data.user_groups)
            update_fields.append("user_groups = :user_groups")
            params['user_groups'] = user_groups_json
        
        if ruleset_data.conditions is not None:
            conditions_json = json.dumps([condition.dict() for condition in ruleset_data.conditions])
            update_fields.append("conditions = :conditions")
            params['conditions'] = conditions_json
        
        if ruleset_data.area_of_interest is not None:
            sdo_geometry = self._geometry_to_sdo(ruleset_data.area_of_interest)
            update_fields.append("area_of_interest = SDO_GEOMETRY(:sdo_geometry)")
            params['sdo_geometry'] = sdo_geometry
        
        if ruleset_data.author is not None:
            update_fields.append("author = :author")
            params['author'] = ruleset_data.author
        
        if not update_fields:
            return self.get_ruleset(ruleset_id)
        
        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"""
            UPDATE RULESETS
            SET {', '.join(update_fields)}
            WHERE id = :ruleset_id
        """
        
        self.db.execute_update(query, params)
        
        return self.get_ruleset(ruleset_id)
    
    def delete_ruleset(self, ruleset_id: int) -> bool:
        """
        Delete a ruleset.
        
        Args:
            ruleset_id: Ruleset ID
            
        Returns:
            True if deleted successfully
            
        Raises:
            Exception: If ruleset not found or deletion fails
        """
        # Check if ruleset exists
        self.get_ruleset(ruleset_id)
        
        query = "DELETE FROM RULESETS WHERE id = :ruleset_id"
        affected_rows = self.db.execute_update(query, {'ruleset_id': ruleset_id})
        
        return affected_rows > 0
    
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
