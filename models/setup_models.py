#!/usr/bin/env python3
"""
Unified Model Setup Script

This script downloads and organizes ML models (YOLO, MMRotate, etc.) based on
configuration from models_config.yaml. Each model gets its own folder with:
- file.pt: The model checkpoint
- metadata.json: Model metadata (id, name, classes)

Usage:
    python setup_models.py                  # Setup all models
    python setup_models.py --filter yolo    # Setup only YOLO models
    python setup_models.py --filter mm      # Setup only MMRotate models
    python setup_models.py --list           # List available models from config
"""

import os
import sys
import json
import yaml
import urllib.request
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Define the models directory
MODELS_DIR = Path(__file__).parent
CONFIG_FILE = MODELS_DIR / "models_config.yaml"


def load_config() -> Dict[str, Any]:
    """
    Load model configuration from YAML file.
    
    Returns:
        Dictionary containing model configurations
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid
    """
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")
    
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def get_next_model_id() -> int:
    """
    Get the next sequential model ID by checking existing metadata.json files.
    
    Returns:
        Next available model ID
    """
    max_id = 0
    
    if not MODELS_DIR.exists():
        return 1
    
    for model_dir in MODELS_DIR.iterdir():
        if model_dir.is_dir():
            metadata_file = model_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        model_id = metadata.get('id', 0)
                        max_id = max(max_id, model_id)
                except (json.JSONDecodeError, IOError):
                    continue
    
    return max_id + 1


def download_file(url: str, destination: Path, model_name: str) -> bool:
    """
    Download a file from URL to destination with progress indication.
    
    Args:
        url: URL to download from
        destination: Local path to save file
        model_name: Name of model (for display)
        
    Returns:
        True if download successful, False otherwise
    """
    print(f"Downloading {model_name}...")
    print(f"  URL: {url}")
    print(f"  Destination: {destination}")
    
    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(downloaded * 100 / total_size, 100)
            mb_downloaded = downloaded / 1024 / 1024
            mb_total = total_size / 1024 / 1024
            print(f"\r  Progress: {percent:.1f}% ({mb_downloaded:.1f} MB / {mb_total:.1f} MB)", end='')
    
    try:
        urllib.request.urlretrieve(url, destination, reporthook=progress_hook)
        print("\n  ✓ Download complete")
        return True
    except Exception as e:
        print(f"\n  ✗ Download failed: {e}")
        return False


def create_model_folder(model_info: Dict[str, Any], model_id: int) -> bool:
    """
    Create a model folder with checkpoint and metadata.
    
    Args:
        model_info: Dictionary with model configuration
        model_id: Sequential ID for the model
        
    Returns:
        True if setup successful, False otherwise
    """
    folder_name = model_info["folder_name"]
    model_folder = MODELS_DIR / folder_name
    
    # Create folder if it doesn't exist
    model_folder.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Setting up: {model_info['name']}")
    print(f"Folder: {folder_name}")
    print(f"Model ID: {model_id}")
    print(f"{'='*60}")
    
    # Download checkpoint
    checkpoint_file = model_folder / "file.pt"
    
    # Check if checkpoint already exists
    if checkpoint_file.exists():
        print(f"  ℹ Checkpoint already exists, skipping download")
    else:
        success = download_file(
            model_info["checkpoint_url"],
            checkpoint_file,
            model_info["name"]
        )
        if not success:
            print(f"  ✗ Failed to download checkpoint for {model_info['name']}")
            return False
    
    # Create metadata.json
    metadata = {
        "id": model_id,
        "name": model_info["name"],
        "classes": model_info["classes"]
    }
    
    metadata_file = model_folder / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=4)
    
    print(f"  ✓ Created metadata.json")
    print(f"  ✓ Model setup complete")
    
    return True


def filter_models(models: List[Dict[str, Any]], filter_str: str) -> List[Dict[str, Any]]:
    """
    Filter models based on a filter string.
    
    Args:
        models: List of model configurations
        filter_str: Filter string (e.g., 'yolo', 'mm', 'coco', 'dota')
        
    Returns:
        Filtered list of models
    """
    if not filter_str:
        return models
    
    filter_lower = filter_str.lower()
    filtered = []
    
    for model in models:
        name_lower = model['name'].lower()
        folder_lower = model['folder_name'].lower()
        
        if filter_lower in name_lower or filter_lower in folder_lower:
            filtered.append(model)
    
    return filtered


def list_models(config: Dict[str, Any]):
    """
    List all available models from configuration.
    
    Args:
        config: Configuration dictionary
    """
    models = config.get('models', [])
    
    print("="*80)
    print("Available Models in Configuration")
    print("="*80)
    print(f"Total models: {len(models)}\n")
    
    # Group models by type
    yolo_models = [m for m in models if 'yolo' in m['name'].lower()]
    mm_models = [m for m in models if 'mm-' in m['folder_name'].lower()]
    
    print(f"YOLO Models: {len(yolo_models)}")
    print(f"MMRotate Models: {len(mm_models)}")
    print("\n" + "="*80)
    print(f"{'#':<4} {'Name':<40} {'Folder':<30}")
    print("="*80)
    
    for idx, model in enumerate(models, 1):
        name = model['name'][:38] + '..' if len(model['name']) > 40 else model['name']
        folder = model['folder_name'][:28] + '..' if len(model['folder_name']) > 30 else model['folder_name']
        print(f"{idx:<4} {name:<40} {folder:<30}")
    
    print("="*80)


def main():
    """
    Main function to set up models based on configuration.
    """
    parser = argparse.ArgumentParser(
        description='Setup ML models for ORO-backend',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_models.py                  # Setup all models
  python setup_models.py --filter yolo    # Setup only YOLO models
  python setup_models.py --filter mm      # Setup only MMRotate models
  python setup_models.py --filter coco    # Setup only COCO models
  python setup_models.py --list           # List available models
        """
    )
    parser.add_argument(
        '--filter',
        type=str,
        help='Filter models by name/folder (e.g., yolo, mm, coco, dota)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available models from configuration'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = load_config()
        models = config.get('models', [])
        
        if not models:
            print("No models found in configuration file")
            return
        
        # List models if requested
        if args.list:
            list_models(config)
            return
        
        # Filter models if requested
        if args.filter:
            models = filter_models(models, args.filter)
            if not models:
                print(f"No models found matching filter: {args.filter}")
                return
        
        # Display setup information
        print("="*60)
        print("Model Setup Script")
        print("="*60)
        print(f"Configuration file: {CONFIG_FILE}")
        print(f"Models directory: {MODELS_DIR}")
        print(f"Number of models to setup: {len(models)}")
        if args.filter:
            print(f"Filter applied: {args.filter}")
        print()
        
        # Create models directory if it doesn't exist
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Get starting model ID
        starting_id = get_next_model_id()
        print(f"Starting model ID: {starting_id}")
        
        # Process each model
        successful = 0
        failed = 0
        
        for idx, model_info in enumerate(models):
            model_id = starting_id + idx
            
            try:
                if create_model_folder(model_info, model_id):
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"  ✗ Error setting up {model_info['name']}: {e}")
                failed += 1
        
        # Summary
        print("\n" + "="*60)
        print("Setup Summary")
        print("="*60)
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total: {len(models)}")
        print("="*60)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

