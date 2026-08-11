from ultralytics import YOLO
import sys
import os

def export_to_tflite():
    print("\n--- Model Export System (TFLite Converter) ---")
    
    # 1. Check for the custom model first
    custom_model_path = "runs/detect/surgical_instrument_model/weights/best.pt"
    
    if os.path.exists(custom_model_path):
        print(f"Loading custom model from: {custom_model_path}")
        model_to_convert = custom_model_path
    else:
        print("Custom model not found. Using default yolov8n.pt for conversion.")
        model_to_convert = "yolov8n.pt"

    print(f"Exporting {model_to_convert} to TFLite format (this will take a moment)...")
    
    try:
        # Load model and export to TFLite
        model = YOLO(model_to_convert)
        # int8 quantization is faster but float32 is most stable first
        model.export(format="tflite", imgsz=640)
        
        print("\n>>> [SUCCESS] Model exported successfully!")
        print("New Model Location: 'best_saved_model/best_float32.tflite' (or similar)")
        print("Use 'python3 tracker.py' to try the stable version now.")
    except Exception as e:
        print(f"\n>>> [FAIL] Export failed: {e}")
        print("Note: Ensure you have 'pip install onnx onnxslim onnx2tf tflite-runtime' if this fails.")

if __name__ == "__main__":
    export_to_tflite()
