"""
Model API routes.

This module defines the REST API endpoints for model operations,
including listing available models and their metadata.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends

from ..database import get_database
from ..services.validation_service import ValidationService

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/")
async def get_available_models(
    model_id: Optional[int] = Query(None, description="Filter by model ID"),
    name: Optional[str] = Query(None, description="Filter by model name (case-insensitive, partial match)"),
    class_name: Optional[str] = Query(None, description="Filter models that can detect this class"),
    type: Optional[str] = Query(None, description="Filter by model type (yolo, mm)"),
    dataset: Optional[str] = Query(None, description="Filter by dataset (coco, dota)"),
    db=Depends(get_database)
):
    """
    Get list of available ML models with optional filtering.
    
    Args:
        model_id: Filter by specific model ID
        name: Filter by model name (case-insensitive, partial match)
        class_name: Filter models that can detect this class
        type: Filter by model type (yolo, mm)
        dataset: Filter by dataset (coco, dota)
        db: Database dependency
        
    Returns:
        Dictionary with:
        - models: List of model metadata objects sorted by ID
        - total: Total count of models
        
    Each model contains:
        - id: Sequential model ID
        - name: Model name (e.g., "YOLOv11x-COCO")
        - classes: List of detectable classes
        
    Example queries:
        /models?model_id=1
        /models?name=yolo
        /models?class_name=person
        /models?type=yolo
        /models?dataset=coco
        /models?type=yolo&class_name=car
    """
    try:
        validation_service = ValidationService(db)
        models = validation_service.get_available_models()
        
        # Filter models based on query parameters
        filtered_models = []
        for model in models:
            # Skip if doesn't match model_id filter
            if model_id is not None:
                try:
                    if int(model['id']) != int(model_id):
                        continue
                except (ValueError, TypeError):
                    continue
                
            # Skip if doesn't match name filter
            if name is not None and name.lower() not in model['name'].lower():
                continue
                
            # Skip if doesn't match class filter
            if class_name is not None and class_name.lower() not in [c.lower() for c in model['classes']]:
                continue
                
            # Skip if doesn't match type filter
            if type is not None:
                if type.lower() == 'yolo' and 'yolo' not in model['name'].lower():
                    continue
                if type.lower() == 'mm' and not model.get('folder', '').startswith('mm-'):
                    continue
                    
            # Skip if doesn't match dataset filter
            if dataset is not None:
                if dataset.lower() == 'coco' and 'coco' not in model['name'].lower():
                    continue
                if dataset.lower() == 'dota' and 'dota' not in model['name'].lower():
                    continue
            
            # Remove internal fields from response
            filtered_model = {
                'id': model['id'],
                'name': model['name'],
                'classes': model['classes']
            }
            filtered_models.append(filtered_model)
        
        return {
            "models": filtered_models,
            "total": len(filtered_models)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving available models: {str(e)}"
        )
