# Model Inference Service Guide

## Overview

The Model Inference Service provides a unified interface for running inference across different model types (YOLO, MMRotate) with consistent output format.

## Features

- **Unified API**: Single interface for all model types
- **Automatic Model Loading**: Models are loaded on-demand
- **Consistent Output Format**: All models return the same structured output
- **Model Caching**: Loaded models are cached in memory for performance
- **Support for Multiple Model Types**:
  - YOLO models (YOLOv8, YOLOv11)
  - YOLO OBB models (oriented bounding boxes)
  - MMRotate models (oriented object detection)

## Usage

### Basic Example

```python
from app.services.model_inference_service import ModelInferenceService

# Initialize the service
service = ModelInferenceService()

# Run inference (auto-loads the model)
result = service.predict(
    model_id=28,  # YOLOv8n-COCO
    image_path="/path/to/image.jpg",
    confidence=0.25
)

if result['success']:
    print(f"Found {result['detection_count']} objects")
    for detection in result['detections']:
        print(f"- {detection['class_name']}: {detection['confidence']:.2f}")
```

### Manual Model Loading

For better performance when running multiple predictions:

```python
# Load model once
service.load_model(28)

# Run multiple predictions
for image_path in image_paths:
    result = service.predict(
        model_id=28,
        image_path=image_path,
        auto_load=False  # Don't reload
    )
    # Process results...

# Unload when done
service.unload_model(28)
```

### Managing Loaded Models

```python
# Check which models are loaded
loaded = service.get_loaded_models()
print(f"Loaded models: {loaded}")

# Unload specific model
service.unload_model(28)

# Unload all models
service.unload_all_models()
```

## API Reference

### `predict(model_id, image_path, confidence=0.25, auto_load=True)`

Run inference on an image.

**Parameters:**
- `model_id` (int): ID of the model to use
- `image_path` (str): Path to the input image
- `confidence` (float): Confidence threshold (default: 0.25)
- `auto_load` (bool): Automatically load model if not loaded (default: True)

**Returns:**
Dictionary with the following structure:

```python
{
    'success': True,
    'model_id': 28,
    'model_name': 'YOLOv8n-COCO',
    'model_type': 'yolo',  # or 'yolo-obb', 'mmrotate'
    'image_path': '/path/to/image.jpg',
    'image_size': [1920, 1080],  # [width, height]
    'detections': [
        {
            'class_id': 0,
            'class_name': 'person',
            'confidence': 0.85,
            'bbox': [100, 200, 300, 400],  # coordinates
            'bbox_type': 'xyxy'  # or 'xywh', 'obb'
        },
        # More detections...
    ],
    'detection_count': 5,
    'confidence_threshold': 0.25
}
```

**Error Response:**
```python
{
    'success': False,
    'error': 'Error message'
}
```

### Detection Format

Each detection contains:

- `class_id` (int): Numeric class ID
- `class_name` (str): Human-readable class name
- `confidence` (float): Detection confidence (0.0 - 1.0)
- `bbox` (list): Bounding box coordinates
- `bbox_type` (str): Type of bounding box
  - `'xyxy'`: [x1, y1, x2, y2] - top-left and bottom-right corners
  - `'xywh'`: [x_center, y_center, width, height] - center and dimensions
  - `'obb'`: Oriented bounding box (8 values for 4 corners)
- `obb` (list, optional): For OBB models, 8 coordinates [x1, y1, x2, y2, x3, y3, x4, y4]

### `load_model(model_id)`

Load a model into memory.

**Parameters:**
- `model_id` (int): ID of the model to load

**Returns:**
- `bool`: True if successful, False otherwise

### `unload_model(model_id)`

Unload a model from memory.

**Parameters:**
- `model_id` (int): ID of the model to unload

**Returns:**
- `bool`: True if unloaded, False if not loaded

### `unload_all_models()`

Unload all models from memory.

### `get_loaded_models()`

Get list of currently loaded model IDs.

**Returns:**
- `list[int]`: List of loaded model IDs

## Model Types

### YOLO Models

Standard YOLO models for object detection with axis-aligned bounding boxes.

**Model IDs:** 28-32 (YOLOv8), 33-37 (YOLOv11)

**Output:**
- `bbox_type`: `'xyxy'` or `'xywh'`
- Standard rectangular bounding boxes

### YOLO OBB Models

YOLO models trained for oriented object detection (e.g., DOTA dataset).

**Model IDs:** 38-42 (YOLOv11 OBB)

**Output:**
- `bbox_type`: `'obb'`
- `obb` field with 8 coordinates for rotated boxes
- Best for aerial imagery and rotated objects

### MMRotate Models

MMRotate models for oriented object detection.

**Model IDs:** 22-27

**Output:**
- Similar to YOLO OBB
- Requires proper MMRotate configuration

## Testing

Run the test suite:

```bash
# Place a test image at tests/images/test.jpg
cd /home/ubuntu/ORO-backend
pytest tests/test_model_inference.py -v
```

### Test Image Requirements

Place a test image at `tests/images/test.jpg`. The image should:
- Be a valid JPEG/PNG image
- Contain common objects (for COCO models: person, car, etc.)
- Be at least 640x640 pixels for best results
- Preferably contain aerial/rotated objects for OBB model testing

## Performance Tips

1. **Reuse Loaded Models**: Load once, predict many times
2. **Unload When Done**: Free memory when models are no longer needed
3. **Batch Processing**: Use the same model for multiple images
4. **Confidence Threshold**: Higher thresholds = fewer detections = faster processing

## Error Handling

The service handles various error conditions:

- **Model Not Found**: Returns error if model ID doesn't exist
- **Image Not Found**: Returns error if image path is invalid
- **Loading Failures**: Returns error if model fails to load
- **Inference Failures**: Returns error if prediction fails

Always check the `success` field before processing results:

```python
result = service.predict(model_id=28, image_path=image_path)

if result['success']:
    # Process detections
    pass
else:
    print(f"Error: {result['error']}")
```

## Integration Example

### With FastAPI Endpoint

```python
from fastapi import APIRouter, HTTPException
from app.services.model_inference_service import ModelInferenceService

router = APIRouter()
inference_service = ModelInferenceService()

@router.post("/detect")
async def detect_objects(model_id: int, image_path: str):
    result = inference_service.predict(
        model_id=model_id,
        image_path=image_path
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result
```

### With Async Processing

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_images_async(image_paths, model_id=28):
    service = ModelInferenceService()
    service.load_model(model_id)
    
    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                service.predict,
                model_id,
                image_path,
                0.25,
                False
            )
            for image_path in image_paths
        ]
        results = await asyncio.gather(*tasks)
    
    service.unload_model(model_id)
    return results
```

## Troubleshooting

### Model Won't Load

1. Check if model file exists: `models/{model_folder}/file.pt`
2. Check if metadata exists: `models/{model_folder}/metadata.json`
3. Verify model ID matches metadata
4. Check CUDA availability for GPU inference

### No Detections

1. Lower confidence threshold (try 0.1)
2. Check if image contains objects the model was trained on
3. Verify image is not corrupted
4. Check image size (minimum 640x640 recommended)

### MMRotate Models Not Working

MMRotate models require additional configuration files. This is a placeholder implementation. To enable MMRotate:

1. Install MMRotate properly
2. Add config files to model directories
3. Update `_load_mmrotate_model()` and `_mmrotate_inference()` methods

## Future Enhancements

- [ ] GPU device selection
- [ ] Batch inference support
- [ ] Image preprocessing options
- [ ] Results visualization
- [ ] Model performance metrics
- [ ] Support for additional model types
- [ ] Async inference support

