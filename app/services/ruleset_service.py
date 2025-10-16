"""
Ruleset service for handling business logic and database operations.

This module contains the service layer for ruleset operations,
handling the conversion between database records and API models.
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..database import Database
from ..models import RulesetCreate, RulesetUpdate, RulesetResponse, Condition


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
        # Convert JSON fields to strings for Oracle
        user_groups_json = json.dumps(ruleset_data.user_groups) if ruleset_data.user_groups else None
        conditions_json = json.dumps([condition.dict() for condition in ruleset_data.conditions]) if ruleset_data.conditions else None
        
        # Insert the ruleset
        query = """
            INSERT INTO RULESETS (name, description, user_groups, conditions, author)
            VALUES (:name, :description, :user_groups, :conditions, :author)
            RETURNING id INTO :ruleset_id
        """
        
        params = {
            'name': ruleset_data.name,
            'description': ruleset_data.description,
            'user_groups': user_groups_json,
            'conditions': conditions_json,
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
            SELECT id, name, description, user_groups, conditions, author, created_at, updated_at
            FROM RULESETS
            WHERE id = :ruleset_id
        """
        
        result = self.db.execute_query(query, {'ruleset_id': ruleset_id})
        
        if not result:
            raise Exception(f"Ruleset with ID {ruleset_id} not found")
        
        ruleset = result[0]
        
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
            SELECT id, name, description, user_groups, conditions, author, created_at, updated_at
            FROM RULESETS
            {where_clause}
            ORDER BY id
            OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
        """
        
        results = self.db.execute_query(query, params)
        
        rulesets = []
        for result in results:
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
    
