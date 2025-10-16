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


## 2. Verification

After completing the installation, run the verification script to ensure both Ultralytics and MMRotate are functioning correctly.

### A. Run the Verification Script:

```bash
python tests/verify_install.py
```

### B. Check the Output:

A successful run will display your system's PyTorch/CUDA details and end with messages confirming that both installations are OK:

```bash
...
✅ Ultralytics installation is OK.
...
✅ MMRotate installation is OK.
...
Verification complete.
```