# Project Environment Setup Guide

This guide outlines the steps to create a consistent and reproducible Conda environment for this project, which includes Ultralytics, MMRotate, and other dependencies.

## Prerequisites

- Conda (Miniforge or Anaconda) must be installed.
- You must have the `requirements.txt` and `verify_install.py` files in your project directory.

## 1. Installation

Follow these steps in your terminal to create and configure the project environment.

### A. Create and Activate the Conda Environment:

```bash
conda create -n ORO-ml python=3.8 -y
conda activate ORO-ml
```

### B. Install Standard Packages:

Install all dependencies from the requirements.txt file. This includes PyTorch, Ultralytics, FastAPI, and the openmim tool.

```bash
pip install -r requirements.txt
```

### C. Install MMLab Packages:

Use the `mim` tool (installed in the previous step) to install the special pre-compiled MMLab libraries. This step is crucial and must be done separately.

```bash
mim install mmcv-full==1.7.2
mim install mmdet==2.28.2
mim install mmrotate==0.3.4
```


## 2. Setup Model Configurations

MMRotate models require configuration files and base configs to work properly.

### A. Setup Models and Configs:

```bash
# Download models and automatically setup MMRotate configs
cd models
python setup_models.py --filter mm

# This will:
# - Download MMRotate model checkpoints
# - Download and copy config files for each model
# - Copy base config files (_base_/) needed by MMRotate
```

### B. Manual Setup (if needed):

If you need to manually copy base configs:

```bash
cd models
git clone --depth 1 https://github.com/open-mmlab/mmrotate.git /tmp/mmrotate_temp
cp -r /tmp/mmrotate_temp/configs/_base_ .
rm -rf /tmp/mmrotate_temp
```

After setup, your models directory should have:
- Model folders (e.g., `mm-oriented-rcnn-r50/`) with `file.pt`, `metadata.json`, and `config.py`
- `_base_/` folder with base config files

## 3. Verification

After completing the installation, run the verification script to ensure both Ultralytics and MMRotate are functioning correctly.

### A. Run the Verification Script:

```bash
python tests/verify_install.py
```

### B. Run Inference Test:

Test that all model types work correctly:

```bash
# Add a test image at tests/images/test.png or test.jpg
python tests/test_inference.py
```

This will test YOLO, YOLO OBB, and MMRotate models, generating:
- Detection results in `tests/output/inference_results.json`
- Annotated images in `tests/output/*.jpg`

### C. Check the Output:

A successful verification will display:

```bash
✅ Ultralytics installation is OK.
✅ MMRotate installation is OK.
Verification complete.
```