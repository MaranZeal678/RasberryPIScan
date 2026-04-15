from ultralytics import YOLO
import os

def main():
    print("Starting YOLOv8 training process...")
    
    # Check if the dataset config exists
    data_path = "instruments.v2i.yolov8/data.yaml"
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        return

    # Load a pre-trained Nano model (lightest model, ideal for Raspberry Pi)
    model = YOLO("yolov8n.pt")

    # Train the model using the provided dataset
    # macOS with M1/M2/M3 chips will automatically use 'mps' hardware acceleration.
    print(f"Training on dataset: {data_path}")
    model.train(
        data=data_path,
        epochs=30,          # Reduced strictly for faster initial demonstration (you can scale this up)
        imgsz=640,          # Matches the Roboflow image resize parameter
        batch=16,
        name="surgical_instrument_model"
    )

    # Export the model to ONNX format (highly supported and fast on Raspberry Pi CPU)
    print("Exporting model for the Raspberry Pi...")
    export_path = model.export(format="onnx")
    
    print(f"\nTraining totally complete! ONNX model exported to: {export_path}")
    print("The standard Pytorch final weights are located at runs/detect/surgical_instrument_model/weights/best.pt")

if __name__ == "__main__":
    main()
