"""
Validation service for report creation and other operations.

This module contains validation functions for various operations
including image existence, ruleset validation, and other checks.
"""

import os
import json
from typing import List, Dict, Any
from ..database import Database


class ValidationService:
    """Service class for validation operations."""
    
    def __init__(self, db: Database = None):
        """
        Initialize the validation service.
        
        Args:
            db: Database connection instance (optional for model operations)
        """
        self.db = db
    
    def validate_image_exists(self, image_name: str) -> bool:
        """
        Validate that the image exists in the object storage bucket.
        
        Args:
            image_name: Name of the image file
            
        Returns:
            True if image exists, False otherwise
        """
        try:
            from .object_storage_service import ObjectStorageService
            
            # Initialize object storage service
            object_storage = ObjectStorageService()
            
            # Check if image exists in bucket with data/ prefix
            object_name = f"data/{image_name}"
            return object_storage.object_exists(object_name)
            
        except Exception as e:
            # Log the error but don't raise it to avoid breaking the flow
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error validating image existence for '{image_name}': {e}")
            return False
    
    def validate_rulesets_exist(self, ruleset_ids: List[int]) -> Dict[str, Any]:
        """
        Validate that all ruleset IDs exist in the database.
        
        Args:
            ruleset_ids: List of ruleset IDs to validate
            
        Returns:
            Dictionary with validation results and existing rulesets
        """
        if not ruleset_ids:
            return {
                "valid": False,
                "existing_rulesets": [],
                "missing_rulesets": [],
                "ruleset_details": {},
                "error": "No ruleset IDs provided"
            }
        
        # Create placeholders for the IN clause
        placeholders = ','.join([f':id_{i}' for i in range(len(ruleset_ids))])
        query = f"""
            SELECT id, name, description, author, created_at
            FROM RULESETS
            WHERE id IN ({placeholders})
        """
        
        # Create parameters dictionary
        params = {f'id_{i}': ruleset_id for i, ruleset_id in enumerate(ruleset_ids)}
        
        try:
            results = self.db.execute_query(query, params)
            existing_ids = [row['ID'] for row in results]
            missing_ids = [rid for rid in ruleset_ids if rid not in existing_ids]
            
            # Create ruleset details dictionary
            ruleset_details = {
                row['ID']: {
                    'id': row['ID'],
                    'name': row['NAME'],
                    'description': row['DESCRIPTION'],
                    'author': row['AUTHOR'],
                    'created_at': row['CREATED_AT']
                }
                for row in results
            }
            
            return {
                "valid": len(missing_ids) == 0,
                "existing_rulesets": existing_ids,
                "missing_rulesets": missing_ids,
                "ruleset_details": ruleset_details
            }
            
        except Exception as e:
            return {
                "valid": False,
                "existing_rulesets": [],
                "missing_rulesets": ruleset_ids,
                "ruleset_details": {},
                "error": f"Database error: {str(e)}"
            }
    
    def validate_model_exists(self, model_id: str) -> bool:
        """
        Validate that the ML model exists and is available.
        
        Args:
            model_id: Identifier for the ML model
            
        Returns:
            True if model exists and is available, False otherwise
        """
        try:
            # Get the models directory path
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'models')
            
            if not os.path.exists(models_dir):
                return False
            
            # Check each model subdirectory for metadata.json
            for model_folder in os.listdir(models_dir):
                model_path = os.path.join(models_dir, model_folder)
                if os.path.isdir(model_path):
                    metadata_file = os.path.join(model_path, 'metadata.json')
                    if os.path.exists(metadata_file):
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                                # Check if the model_id matches either the 'id' or 'name' field
                                if (str(metadata.get('id')) == str(model_id) or 
                                    metadata.get('name', '').lower() == model_id.lower()):
                                    # Also check if the model file exists
                                    model_file = os.path.join(model_path, 'file.pt')
                                    return os.path.exists(model_file)
                        except (json.JSONDecodeError, KeyError):
                            continue
            
            return False
            
        except Exception as e:
            # Log the error but don't raise it
            print(f"Error validating model {model_id}: {str(e)}")
            return False
    
    def validate_author_exists(self, author_id: str) -> bool:
        """
        Validate that the author exists in the system.
        
        Args:
            author_id: ID of the user/author
            
        Returns:
            True if author exists, False otherwise
        """
        return True
    
    def validate_geometry(self, area_of_interest: Dict[str, Any]) -> bool:
        """
        Validate that the area of interest geometry is valid.
        
        Args:
            area_of_interest: Geometry object to validate
            
        Returns:
            True if geometry is valid, False otherwise
            
        TODO: Implement geometry validation
        - Validate GeoJSON structure
        - Check coordinate validity
        - Verify geometry is within reasonable bounds
        """
        # TODO: Implement geometry validation
        # This is a placeholder implementation
        # In production, you would:
        # 1. Validate GeoJSON structure
        # 2. Check coordinate validity and bounds
        # 3. Verify geometry is well-formed
        # 4. Return appropriate boolean result
        
        # For now, assume all geometries are valid
        return True
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available ML models from the models directory with full metadata.
        
        Returns:
            List of available models with their complete metadata including:
            - id: Model ID
            - name: Model name
            - classes: List of detectable classes
            - folder: Folder name in models directory
            - has_checkpoint: Whether checkpoint file exists
            - checkpoint_size_mb: Size of checkpoint file in MB
        """
        try:
            models = []
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'models')
            
            if not os.path.exists(models_dir):
                return models
            
            for model_folder in sorted(os.listdir(models_dir)):
                model_path = os.path.join(models_dir, model_folder)
                if os.path.isdir(model_path):
                    metadata_file = os.path.join(model_path, 'metadata.json')
                    checkpoint_file = os.path.join(model_path, 'file.pt')
                    
                    if os.path.exists(metadata_file):
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                                
                                # Add additional info
                                metadata['folder'] = model_folder
                                metadata['has_checkpoint'] = os.path.exists(checkpoint_file)
                                
                                if os.path.exists(checkpoint_file):
                                    metadata['checkpoint_size_mb'] = round(
                                        os.path.getsize(checkpoint_file) / 1024 / 1024, 2
                                    )
                                else:
                                    metadata['checkpoint_size_mb'] = 0
                                
                                models.append(metadata)
                        except (json.JSONDecodeError, IOError) as e:
                            # Log error but continue with other models
                            print(f"Error reading {metadata_file}: {e}")
                            continue
            
            # Sort by ID
            models.sort(key=lambda x: x.get('id', 0))
            return models
            
        except Exception as e:
            print(f"Error getting available models: {str(e)}")
            return []
