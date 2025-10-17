#!/usr/bin/env python3
"""
Simple Model Inference Test Script

Tests both YOLO and MMRotate models, saves results as JSON and annotated images.
"""

import os
import sys
import json
import cv2
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.model_inference_service import ModelInferenceService


# Configuration
TEST_IMAGE = Path(__file__).parent / "images" / "test.png"
OUTPUT_DIR = Path(__file__).parent / "output"


def draw_detections(image_path, detections, model_name, output_path):
    """
    Draw detections on image and save.
    
    Args:
        image_path: Path to input image
        detections: List of detection dictionaries
        model_name: Name of the model (for title)
        output_path: Path to save annotated image
    """
    # Read image
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"  ✗ Failed to read image: {image_path}")
        return False
    
    # Colors for different classes (random but consistent)
    np.random.seed(42)
    colors = {}
    
    for det in detections:
        class_id = det['class_id']
        class_name = det['class_name']
        confidence = det['confidence']
        
        # Get or generate color for this class
        if class_id not in colors:
            colors[class_id] = tuple(np.random.randint(0, 255, 3).tolist())
        color = colors[class_id]
        
        # Draw based on bbox type
        if 'obb' in det and len(det['obb']) == 8:
            # Draw oriented bounding box (4 corners)
            points = np.array(det['obb']).reshape(4, 2).astype(np.int32)
            cv2.polylines(img, [points], True, color, 2)
            
            # Draw label at first corner
            label = f"{class_name}: {confidence:.2f}"
            if 'angle' in det:
                label += f" ({det['angle']:.1f}°)"
            
            cv2.putText(img, label, (int(points[0][0]), int(points[0][1]) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
        else:
            # Draw regular bounding box
            bbox = det['bbox']
            
            if det['bbox_type'] == 'xyxy':
                x1, y1, x2, y2 = map(int, bbox)
            elif det['bbox_type'] in ['xywh', 'xywha']:
                x, y, w, h = bbox
                x1, y1 = int(x), int(y)
                x2, y2 = int(x + w), int(y + h)
            else:
                continue
            
            # Draw rectangle
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(img, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # Add model name at top
    cv2.putText(img, f"Model: {model_name} | Detections: {len(detections)}", 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Save image
    cv2.imwrite(str(output_path), img)
    return True


def test_model(service, model_id, image_path, model_type_name):
    """
    Test a single model and return results.
    
    Args:
        service: ModelInferenceService instance
        model_id: Model ID to test
        image_path: Path to test image
        model_type_name: Description of model type (for output)
        
    Returns:
        Dictionary with test results or None if failed
    """
    print(f"\n{'='*70}")
    print(f"Testing Model ID: {model_id} ({model_type_name})")
    print(f"{'='*70}")
    
    # Get model metadata
    metadata = service._get_model_metadata(model_id)
    if not metadata:
        print(f"  ✗ Model {model_id} not found")
        return None
    
    print(f"  Model Name: {metadata['name']}")
    print(f"  Model Folder: {metadata['folder']}")
    
    # Check checkpoint exists
    if not os.path.exists(metadata['checkpoint_path']):
        print(f"  ✗ Checkpoint not found: {metadata['checkpoint_path']}")
        return None
    
    # Run inference
    print(f"  Running inference...")
    result = service.predict(
        model_id=model_id,
        image_path=str(image_path),
        confidence=0.25,
        auto_load=True
    )
    
    if not result['success']:
        print(f"  ✗ Inference failed: {result.get('error', 'Unknown error')}")
        return None
    
    print(f"  ✓ Inference successful")
    print(f"  ✓ Detections: {result['detection_count']}")
    print(f"  ✓ Model Type: {result['model_type']}")
    print(f"  ✓ Image Size: {result['image_size']}")
    
    # Show some detections
    if result['detection_count'] > 0:
        print(f"\n  Top 5 Detections:")
        for i, det in enumerate(result['detections'][:5], 1):
            label = f"    {i}. {det['class_name']}: {det['confidence']:.2%}"
            if 'angle' in det:
                label += f" (angle: {det['angle']:.1f}°)"
            print(label)
    
    return result


def find_model_by_folder_pattern(service, pattern):
    """
    Find first model matching a folder name pattern.
    
    Args:
        service: ModelInferenceService instance
        pattern: String pattern to match in folder name
        
    Returns:
        Model ID or None if not found
    """
    models_dir = service.models_dir
    if not models_dir.exists():
        return None
    
    for model_folder in sorted(models_dir.iterdir()):
        if model_folder.is_dir() and pattern in model_folder.name.lower():
            metadata_file = model_folder / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        return metadata.get('id')
                except:
                    continue
    return None


def main():
    """Main test function."""
    print("\n" + "="*70)
    print("MODEL INFERENCE TEST")
    print("="*70)
    
    # Check test image exists
    if not TEST_IMAGE.exists():
        print(f"\n✗ Test image not found: {TEST_IMAGE}")
        print(f"  Please add a test image at: {TEST_IMAGE}")
        return
    
    print(f"\nTest Image: {TEST_IMAGE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize service
    print("\nInitializing Model Inference Service...")
    service = ModelInferenceService()
    print("✓ Service initialized")
    
    # Find models by folder pattern
    print("\nScanning for available models...")
    yolo_model_id = find_model_by_folder_pattern(service, "yolov11n-coco")
    yolo_obb_model_id = find_model_by_folder_pattern(service, "yolov11n-obb")
    mm_model_id = find_model_by_folder_pattern(service, "mm-oriented-rcnn")
    
    print(f"  YOLO COCO model: {'Found (ID: ' + str(yolo_model_id) + ')' if yolo_model_id else 'Not found'}")
    print(f"  YOLO OBB model: {'Found (ID: ' + str(yolo_obb_model_id) + ')' if yolo_obb_model_id else 'Not found'}")
    print(f"  MMRotate model: {'Found (ID: ' + str(mm_model_id) + ')' if mm_model_id else 'Not found'}")
    
    # Store all results
    all_results = {
        'test_image': str(TEST_IMAGE),
        'yolo_model': None,
        'yolo_obb_model': None,
        'mmrotate_model': None
    }
    
    # Test YOLO model
    if yolo_model_id:
        print("\n" + "="*70)
        print("TESTING YOLO MODEL (COCO)")
        print("="*70)
        
        result = test_model(service, yolo_model_id, TEST_IMAGE, "YOLO COCO")
        if result:
            all_results['yolo_model'] = result
            
            # Save annotated image
            output_img = OUTPUT_DIR / f"yolo_coco_detections.jpg"
            if draw_detections(TEST_IMAGE, result['detections'], 
                             result['model_name'], output_img):
                print(f"  ✓ Saved annotated image: {output_img}")
                result['annotated_image'] = str(output_img)
            
            # Unload model to free memory
            service.unload_model(yolo_model_id)
    
    # Test YOLO OBB model
    if yolo_obb_model_id:
        print("\n" + "="*70)
        print("TESTING YOLO OBB MODEL (DOTA)")
        print("="*70)
        
        result = test_model(service, yolo_obb_model_id, TEST_IMAGE, "YOLO OBB DOTA")
        if result:
            all_results['yolo_obb_model'] = result
            
            # Save annotated image
            output_img = OUTPUT_DIR / f"yolo_obb_detections.jpg"
            if draw_detections(TEST_IMAGE, result['detections'], 
                             result['model_name'], output_img):
                print(f"  ✓ Saved annotated image: {output_img}")
                result['annotated_image'] = str(output_img)
            
            # Unload model to free memory
            service.unload_model(yolo_obb_model_id)
    
    # Test MMRotate model
    if mm_model_id:
        print("\n" + "="*70)
        print("TESTING MMROTATE MODEL (DOTA)")
        print("="*70)
        
        result = test_model(service, mm_model_id, TEST_IMAGE, "MMRotate DOTA")
        if result:
            all_results['mmrotate_model'] = result
            
            # Save annotated image
            output_img = OUTPUT_DIR / f"mmrotate_detections.jpg"
            if draw_detections(TEST_IMAGE, result['detections'], 
                             result['model_name'], output_img):
                print(f"  ✓ Saved annotated image: {output_img}")
                result['annotated_image'] = str(output_img)
            
            # Unload model to free memory
            service.unload_model(mm_model_id)
    
    # Save all results as JSON
    output_json = OUTPUT_DIR / "inference_results.json"
    with open(output_json, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"YOLO Model: {'✓ Tested' if all_results['yolo_model'] else '✗ Not tested'}")
    print(f"YOLO OBB Model: {'✓ Tested' if all_results['yolo_obb_model'] else '✗ Not tested'}")
    print(f"MMRotate Model: {'✓ Tested' if all_results['mmrotate_model'] else '✗ Not tested'}")
    print(f"\n✓ Results saved to: {output_json}")
    print(f"✓ Annotated images saved to: {OUTPUT_DIR}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

