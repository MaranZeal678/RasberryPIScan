import cv2
import numpy as np
import time

# ---------------------------------------------------------
# Step 1: Test OpenCV (Math/Flip)
# ---------------------------------------------------------
print("\n[STEP 1] Testing OpenCV Math & SIMD...")
try:
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_frame = cv2.flip(dummy_frame, 1)
    dummy_frame = cv2.resize(dummy_frame, (320, 240))
    print(">>> [SUCCESS] OpenCV Math is stable.")
except Exception as e:
    print(f">>> [FAIL] OpenCV crashed: {e}")

# ---------------------------------------------------------
# Step 2: Test MediaPipe (Inference)
# ---------------------------------------------------------
print("\n[STEP 2] Testing MediaPipe Hand Detection...")
try:
    import mediapipe as mp
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=True, max_num_hands=1)
    
    # Create a dummy RGB frame for the AI
    test_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    # The moment of truth: process the frame
    results = hands.process(test_rgb)
    print(">>> [SUCCESS] MediaPipe Inference is stable.")
except Exception as e:
    print(f">>> [FAIL] MediaPipe crashed or Illegal Instruction: {e}")

# ---------------------------------------------------------
# Step 3: Test YOLO/Torch (Inference)
# ---------------------------------------------------------
print("\n[STEP 3] Testing YOLOv8/Torch Detection...")
try:
    from ultralytics import YOLO
    # Load the basic model
    model = YOLO("yolov8n.pt")
    # Create a dummy frame
    test_frame = np.zeros((640, 640, 3), dtype=np.uint8)
    # Perform prediction
    results = model(test_frame, verbose=False)
    print(">>> [SUCCESS] YOLO/Torch Inference is stable.")
except Exception as e:
    print(f">>> [FAIL] YOLO/Torch crashed: {e}")

print("\n--- Diagnostic Test Complete ---")
