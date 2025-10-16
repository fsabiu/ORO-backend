# Models Setup - Usage Examples

This document provides practical examples of how to use the unified model setup script.

## Quick Start

### 1. View Available Models

```bash
# List all models from configuration
python setup_models.py --list

# This will show:
# - Total number of models
# - Models grouped by type (YOLO, MMRotate)
# - Name and folder for each model
```

### 2. Download All Models

```bash
# Download and setup all models
python setup_models.py

# The script will:
# - Read configuration from models_config.yaml
# - Create folders like: models/yolov11n-coco/, models/mm-oriented-rcnn-r50/
# - Download checkpoints and save as file.pt
# - Create metadata.json with ID, name, and classes
# - Skip existing models automatically
```

### 3. Download Specific Model Types

```bash
# Download only YOLO models
python setup_models.py --filter yolo

# Download only MMRotate models
python setup_models.py --filter mm

# Download only COCO-based models
python setup_models.py --filter coco

# Download only DOTA-based models
python setup_models.py --filter dota
```

## Customization Examples

### Add a Custom Model

Edit `models_config.yaml` and add your model to the `models` list:

```yaml
models:
  # ... existing models ...
  
  - name: My Custom Detector
    folder_name: my-custom-detector
    checkpoint_url: https://example.com/path/to/checkpoint.pt
    classes:
      - person
      - vehicle
      - building
```

Then run:
```bash
python setup_models.py
```

### Add a Model with Shared Classes

Use YAML anchors to reference existing class lists:

```yaml
models:
  # ... existing models ...
  
  - name: YOLOv8x-Custom-COCO
    folder_name: yolov8x-custom-coco
    checkpoint_url: https://example.com/custom-yolov8x.pt
    classes: *coco_classes  # References the coco_classes anchor
```

### Define Custom Class Lists

Add custom class lists at the top of `models_config.yaml`:

```yaml
# Custom class definitions
custom_aerial_classes: &custom_aerial_classes
  - drone
  - bird
  - airplane
  - helicopter
  - balloon

# ... existing class lists ...

models:
  # ... existing models ...
  
  - name: Aerial Object Detector
    folder_name: aerial-detector
    checkpoint_url: https://example.com/aerial-detector.pt
    classes: *custom_aerial_classes
```

## Understanding Model IDs

Model IDs are **sequential** and **global** across the entire models directory:

```
models/
├── mm-orncnn/              # ID: 1
│   ├── file.pt
│   └── metadata.json
├── yolov11-DOTA/           # ID: 2
│   ├── file.pt
│   └── metadata.json
├── mm-oriented-rcnn-r50/   # ID: 3 (if you run setup_mmrotate_models.py)
│   ├── file.pt
│   └── metadata.json
└── yolov11n/               # ID: 9 (if you run setup_yolo_models.py after mmrotate)
    ├── file.pt
    └── metadata.json
```

The scripts automatically:
1. Scan all existing models
2. Find the highest ID
3. Continue numbering from there

## Iterating Over Models in Code

Here's a Python example to iterate over all available models:

```python
import json
from pathlib import Path

MODELS_DIR = Path("models")

def load_all_models():
    """Load all models and their metadata."""
    models = []
    
    for model_dir in MODELS_DIR.iterdir():
        if model_dir.is_dir():
            metadata_file = model_dir / "metadata.json"
            checkpoint_file = model_dir / "file.pt"
            
            if metadata_file.exists() and checkpoint_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    metadata['checkpoint_path'] = str(checkpoint_file)
                    models.append(metadata)
    
    # Sort by ID
    models.sort(key=lambda x: x['id'])
    return models

# Usage
models = load_all_models()
for model in models:
    print(f"Model {model['id']}: {model['name']}")
    print(f"  Classes: {', '.join(model['classes'][:5])}...")
    print(f"  Checkpoint: {model['checkpoint_path']}")
```

## Example: Loading a Model for Inference

### For MMRotate Models

```python
from mmrotate.apis import init_detector, inference_detector
import json

# Load model metadata
with open('models/mm-oriented-rcnn-r50/metadata.json', 'r') as f:
    metadata = json.load(f)

# Initialize model
config_file = 'path/to/config.py'  # You'll need the config file
checkpoint = 'models/mm-oriented-rcnn-r50/file.pt'
model = init_detector(config_file, checkpoint, device='cuda:0')

# Get class names
class_names = metadata['classes']

# Run inference
img = 'path/to/image.jpg'
result = inference_detector(model, img)
```

### For YOLO Models

```python
from ultralytics import YOLO
import json

# Load model metadata
with open('models/yolov11n/metadata.json', 'r') as f:
    metadata = json.load(f)

# Initialize model
model = YOLO('models/yolov11n/file.pt')

# Get class names
class_names = metadata['classes']

# Run inference
results = model('path/to/image.jpg')

# Process results
for result in results:
    boxes = result.boxes
    for box in boxes:
        class_id = int(box.cls[0])
        class_name = class_names[class_id]
        confidence = float(box.conf[0])
        print(f"Detected: {class_name} ({confidence:.2f})")
```

## Tips

1. **Storage Space**: Each model can be 10-200 MB. Make sure you have enough disk space before downloading all models.

2. **Network**: Downloads may take time depending on your internet connection. The scripts show progress bars.

3. **Selective Download**: You can comment out models you don't need in the setup scripts before running them.

4. **Model Updates**: To update a model, simply delete its folder and run the setup script again.

5. **Backup**: Consider backing up your models directory if you've customized configurations or downloaded many models.

## Troubleshooting

### Download Failed
- Check your internet connection
- Verify the checkpoint URL is still valid
- Check if you have write permissions in the models directory

### Model ID Conflicts
- Don't manually edit IDs in metadata.json
- Let the scripts handle ID assignment automatically
- If you need to reset IDs, you'll need to manually update all metadata.json files

### Missing Checkpoint
- Re-run the setup script
- Check the checkpoint URL in the script
- Manually download and place as `file.pt` in the model folder

