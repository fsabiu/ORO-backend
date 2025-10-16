import sys
import torch

def verify_installations():
    """
    Checks if Ultralytics and MMRotate are installed and functional.
    """
    print("---" * 10)
    print("Starting installation verification...")
    print(f"Python Version: {sys.version}")
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"Current GPU: {torch.cuda.get_device_name(torch.cuda.current_device())}")
    print("---" * 10)

    # --- Verify Ultralytics ---
    try:
        print("\nVerifying Ultralytics (YOLO)...")
        from ultralytics import YOLO

        # This command will download the model if it's not cached
        model = YOLO('yolov8n.pt')
        model.info()
        print("\n✅ Ultralytics installation is OK.")

    except ImportError:
        print("\n❌ FAILED: Ultralytics is not installed.")
    except Exception as e:
        print(f"\n❌ FAILED: An error occurred while verifying Ultralytics: {e}")


    # --- Verify MMRotate ---
    try:
        print("\nVerifying MMRotate...")
        import mmrotate

        # Printing the version is a standard and reliable check
        print(f"MMRotate Version: {mmrotate.__version__}")
        print("\n✅ MMRotate installation is OK.")

    except ImportError:
        print("\n❌ FAILED: MMRotate is not installed.")
    except Exception as e:
        print(f"\n❌ FAILED: An error occurred while verifying MMRotate: {e}")

    print("\n" + "---" * 10)
    print("Verification complete.")
    print("---" * 10)


if __name__ == "__main__":
    verify_installations()