"""
Model Inference Service

This module provides a unified interface for running inference across different
model types (YOLO, MMRotate) with consistent output format.
"""

import os
import json
import math
import numpy as np
import torch
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from PIL import Image
import cv2


class ModelInferenceService:
    """
    Unified interface for model inference across different model types.
    
    Supports:
    - YOLO models (YOLOv8, YOLOv11, including OBB variants)
    - MMRotate models (Oriented R-CNN, Rotated RetinaNet, etc.)
    """
    
    def __init__(self):
        """Initialize the model inference service."""
        self.models_dir = Path(__file__).parent.parent.parent / "models"
        self.loaded_models = {}  # Cache for loaded models
        
    def _get_model_metadata(self, model_id: int) -> Optional[Dict[str, Any]]:
        """
        Get model metadata by ID.
        
        Args:
            model_id: Model ID to look up
            
        Returns:
            Dictionary with model metadata or None if not found
        """
        if not self.models_dir.exists():
            return None
            
        for model_folder in self.models_dir.iterdir():
            if model_folder.is_dir():
                metadata_file = model_folder / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            if metadata.get('id') == model_id:
                                metadata['folder'] = model_folder.name
                                metadata['folder_path'] = str(model_folder)
                                metadata['checkpoint_path'] = str(model_folder / "file.pt")
                                return metadata
                    except (json.JSONDecodeError, IOError):
                        continue
        
        return None
    
    def _determine_model_type(self, folder_name: str) -> str:
        """
        Determine model type from folder name.
        
        Args:
            folder_name: Name of the model folder
            
        Returns:
            Model type: 'yolo', 'yolo-obb', or 'mmrotate'
        """
        folder_lower = folder_name.lower()
        
        if 'yolo' in folder_lower:
            if 'obb' in folder_lower:
                return 'yolo-obb'
            return 'yolo'
        elif folder_lower.startswith('mm-'):
            return 'mmrotate'
        
        return 'unknown'
    
    def _load_yolo_model(self, checkpoint_path: str):
        """
        Load a YOLO model.
        
        Args:
            checkpoint_path: Path to the YOLO checkpoint file
            
        Returns:
            Loaded YOLO model
        """
        from ultralytics import YOLO
        return YOLO(checkpoint_path)
    
    def _load_mmrotate_model(self, checkpoint_path: str, folder_name: str):
        """
        Load an MMRotate model.
        
        Args:
            checkpoint_path: Path to the MMRotate checkpoint file
            folder_name: Name of the model folder
            
        Returns:
            Loaded MMRotate model (config and checkpoint)
        """
        try:
            # Import mmrotate to register custom models
            import mmrotate  # noqa
            from mmdet.apis import init_detector
        except ImportError as e:
            raise ImportError(
                f"MMRotate/MMDet import failed: {str(e)}\n"
                f"Install with: mim install mmrotate mmdet"
            )
        
        # Get config path
        model_folder = Path(checkpoint_path).parent
        config_path = model_folder / "config.py"
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Run: python models/setup_models.py --filter mm\n"
                f"to download config files for MMRotate models."
            )
        
        # Initialize model
        device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
        model = init_detector(str(config_path), checkpoint_path, device=device)
        
        return model
    
    def load_model(self, model_id: int) -> bool:
        """
        Load a model into memory by ID.
        
        Args:
            model_id: ID of the model to load
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        # Check if already loaded
        if model_id in self.loaded_models:
            return True
        
        # Get model metadata
        metadata = self._get_model_metadata(model_id)
        if not metadata:
            return False
        
        # Check if checkpoint exists
        checkpoint_path = metadata['checkpoint_path']
        if not os.path.exists(checkpoint_path):
            return False
        
        # Determine model type
        model_type = self._determine_model_type(metadata['folder'])
        
        try:
            # Load model based on type
            if model_type in ['yolo', 'yolo-obb']:
                model = self._load_yolo_model(checkpoint_path)
                self.loaded_models[model_id] = {
                    'model': model,
                    'type': model_type,
                    'metadata': metadata
                }
                return True
            elif model_type == 'mmrotate':
                model = self._load_mmrotate_model(checkpoint_path, metadata['folder'])
                self.loaded_models[model_id] = {
                    'model': model,
                    'type': model_type,
                    'metadata': metadata
                }
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error loading model {model_id}: {str(e)}")
            return False
    
    def _yolo_inference(self, model, image_path: str, confidence: float) -> List[Dict[str, Any]]:
        """
        Run inference with a YOLO model.
        
        Args:
            model: Loaded YOLO model
            image_path: Path to the image
            confidence: Confidence threshold
            
        Returns:
            List of detections in unified format
        """
        results = model.predict(image_path, conf=confidence, verbose=False)
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            
            for idx in range(len(boxes)):
                box = boxes[idx]
                
                # Get box coordinates
                if hasattr(box, 'xyxy'):
                    # Standard bounding box
                    coords = box.xyxy[0].cpu().numpy().tolist()
                    bbox_type = 'xyxy'
                elif hasattr(box, 'xywh'):
                    # Center format
                    coords = box.xywh[0].cpu().numpy().tolist()
                    bbox_type = 'xywh'
                else:
                    continue
                
                # Check for OBB (oriented bounding box)
                obb_coords = None
                if hasattr(result, 'obb') and result.obb is not None:
                    obb = result.obb[idx]
                    if hasattr(obb, 'xyxyxyxy'):
                        obb_coords = obb.xyxyxyxy[0].cpu().numpy().tolist()
                
                detection = {
                    'class_id': int(box.cls[0].cpu().numpy()),
                    'class_name': result.names[int(box.cls[0])],
                    'confidence': float(box.conf[0].cpu().numpy()),
                    'bbox': coords,
                    'bbox_type': bbox_type,
                }
                
                # Add OBB if available
                if obb_coords:
                    detection['obb'] = obb_coords
                    detection['bbox_type'] = 'obb'
                
                detections.append(detection)
        
        return detections
    
    def _mmrotate_inference(self, model, image_path: str, confidence: float) -> List[Dict[str, Any]]:
        """
        Run inference with an MMRotate model.
        
        Args:
            model: Loaded MMRotate model
            image_path: Path to the image
            confidence: Confidence threshold
            
        Returns:
            List of detections in unified format
        """
        try:
            from mmdet.apis import inference_detector
        except ImportError:
            raise ImportError(
                "MMDet not installed. Install with: mim install mmdet"
            )
        
        # Run inference
        result = inference_detector(model, image_path)
        
        # Parse results
        detections = []
        
        # MMRotate returns results as tuple or list of arrays
        # Each array contains detections for one class
        if isinstance(result, tuple):
            bbox_result = result[0]
        else:
            bbox_result = result
        
        # Process each class
        for class_id, class_detections in enumerate(bbox_result):
            # MMRotate detections format: [cx, cy, w, h, angle, score] for rotated boxes
            # or [x1, y1, x2, y2, score] for regular boxes
            for detection in class_detections:
                if len(detection) < 5:
                    continue
                
                # Extract detection info
                if len(detection) == 6:  # [cx, cy, w, h, angle, score] - rotated box
                    cx, cy, w, h, angle, score = detection
                    # cx, cy are center coordinates
                    x = float(cx - w/2)  # Convert center to top-left
                    y = float(cy - h/2)
                    w = float(w)
                    h = float(h)
                    angle = float(angle)
                    has_angle = True
                elif len(detection) == 5:  # [x1, y1, x2, y2, score] - regular box
                    x1, y1, x2, y2, score = detection
                    # Convert to xywh format
                    x = float(x1)
                    y = float(y1)
                    w = float(x2 - x1)
                    h = float(y2 - y1)
                    angle = 0.0
                    has_angle = False
                else:
                    continue
                
                # Filter by confidence
                if float(score) < confidence:
                    continue
                
                # Create detection dict
                det = {
                    'class_id': int(class_id),
                    'class_name': model.CLASSES[class_id] if hasattr(model, 'CLASSES') else str(class_id),
                    'confidence': float(score),
                    'bbox': [float(x), float(y), float(w), float(h)],
                    'bbox_type': 'xywha' if has_angle else 'xywh'
                }
                
                # Add angle if available
                if has_angle:
                    det['angle'] = float(angle)
                    
                    # Calculate 4 corners from center, width, height, angle
                    cx, cy = x + w/2, y + h/2
                    angle_rad = math.radians(angle)
                    
                    # Calculate corners
                    cos_a = math.cos(angle_rad)
                    sin_a = math.sin(angle_rad)
                    
                    dx = w / 2
                    dy = h / 2
                    
                    corners = []
                    for dx_sign, dy_sign in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
                        px = cx + dx_sign * dx * cos_a - dy_sign * dy * sin_a
                        py = cy + dx_sign * dx * sin_a + dy_sign * dy * cos_a
                        corners.extend([float(px), float(py)])
                    
                    det['obb'] = corners  # 8 values: [x1,y1, x2,y2, x3,y3, x4,y4]
                
                detections.append(det)
        
        return detections
    
    def predict(
        self,
        model_id: int,
        image_path: str,
        confidence: float = 0.25,
        auto_load: bool = True
    ) -> Dict[str, Any]:
        """
        Run inference on an image using the specified model.
        
        Args:
            model_id: ID of the model to use
            image_path: Path to the input image
            confidence: Confidence threshold (default: 0.25)
            auto_load: Automatically load model if not loaded (default: True)
            
        Returns:
            Dictionary with:
            - success: Boolean indicating success
            - model_id: ID of the model used
            - model_name: Name of the model
            - model_type: Type of model (yolo, yolo-obb, mmrotate)
            - image_path: Path to the input image
            - image_size: [width, height] of the image
            - detections: List of detections
            - detection_count: Number of detections
            - error: Error message if failed
        """
        # Load model if needed
        if model_id not in self.loaded_models:
            if auto_load:
                if not self.load_model(model_id):
                    return {
                        'success': False,
                        'error': f'Failed to load model with ID {model_id}'
                    }
            else:
                return {
                    'success': False,
                    'error': f'Model {model_id} not loaded. Call load_model() first.'
                }
        
        # Check if image exists
        if not os.path.exists(image_path):
            return {
                'success': False,
                'error': f'Image not found: {image_path}'
            }
        
        # Get image size
        try:
            img = Image.open(image_path)
            image_size = list(img.size)  # [width, height]
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to read image: {str(e)}'
            }
        
        # Get model info
        model_info = self.loaded_models[model_id]
        model = model_info['model']
        model_type = model_info['type']
        metadata = model_info['metadata']
        
        # Run inference based on model type
        try:
            if model_type in ['yolo', 'yolo-obb']:
                detections = self._yolo_inference(model, image_path, confidence)
            elif model_type == 'mmrotate':
                detections = self._mmrotate_inference(model, image_path, confidence)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported model type: {model_type}'
                }
            
            return {
                'success': True,
                'model_id': model_id,
                'model_name': metadata['name'],
                'model_type': model_type,
                'image_path': image_path,
                'image_size': image_size,
                'detections': detections,
                'detection_count': len(detections),
                'confidence_threshold': confidence
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Inference failed: {str(e)}'
            }
    
    def unload_model(self, model_id: int) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_id: ID of the model to unload
            
        Returns:
            True if unloaded successfully, False if not loaded
        """
        if model_id in self.loaded_models:
            del self.loaded_models[model_id]
            return True
        return False
    
    def unload_all_models(self):
        """Unload all models from memory."""
        self.loaded_models.clear()
    
    def get_loaded_models(self) -> List[int]:
        """
        Get list of currently loaded model IDs.
        
        Returns:
            List of model IDs
        """
        return list(self.loaded_models.keys())

