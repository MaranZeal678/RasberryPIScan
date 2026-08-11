import cv2
import mediapipe as mp
import math
from ultralytics import YOLO
from servo_controller import PanTiltServoController

# 1. MediaPipe Setup for Hand Tracking 
# (Runs on CPU exceptionally well natively)
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,            # Assuming you operate with 1 hand holding the primary tool
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# 2. YOLOv8 Setup for Surgical Instrument Detection
import os
import sys

def load_yolo_model():
    """Attempt to load the custom model, strictly prioritizing TFLite for Pi stability."""
    print("Loading AI Surgical Instrument model (Safe Mode TFLite)...")
    
    # 1. Custom TFLite Model (Highest Priority)
    tflite_custom = "best_saved_model/best_float32.tflite"
    if os.path.exists(tflite_custom):
        print(f"Success: Loading {tflite_custom} (Hardware-Optimized).")
        return YOLO(tflite_custom, task="detect")
        
    # 2. Base TFLite Model (Secondary Priority)
    tflite_base = "yolov8n_saved_model/yolov8n_float32.tflite"
    if os.path.exists(tflite_base):
        print(f"Success: Loading {tflite_base} (Stable Fallback).")
        return YOLO(tflite_base, task="detect")

    # 3. Last Resort Fallback (Warning: Likely to crash on Pi 4 via PyTorch)
    print("WARNING: TFLite models not found. Attempting legacy PyTorch load...")
    try:
        # Check if custom .pt exists
        custom_pt = "runs/detect/surgical_instrument_model/weights/best.pt"
        if os.path.exists(custom_pt):
            return YOLO(custom_pt)
        return YOLO("yolov8n.pt")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Failed to load any AI model: {e}")
        print("Please ensure the TFLite models are uploaded to the Pi.")
        sys.exit(1)

model = load_yolo_model()

# Try to import Picamera2 for modern Pi Camera support
try:
    from picamera2 import Picamera2
    PICAM2_AVAILABLE = True
except ImportError:
    PICAM2_AVAILABLE = False

def main():
    # 3. Connection to Camera Input
    print("Connecting to Camera...")
    
    if PICAM2_AVAILABLE:
        print("Success: Initializing via Picamera2 (Official Module 3 support).")
        picam2 = Picamera2()
        # Configuration for IMX708 / Module 3
        config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
        picam2.configure(config)
        picam2.start()
    else:
        print("Warning: Picamera2 not found. Falling back to standard OpenCV (USB Cam mode).")
        video = cv2.VideoCapture(0)
        if not video.isOpened():
            print("Error: Could not open any video source.")
            return

    # 4. Initialize the Pan and Tilt Servo Controller 
    # Pan (Left/Right) connected to GPIO 17
    # Tilt (Up/Down) connected to GPIO 18
    servo = PanTiltServoController(pan_pin=17, tilt_pin=18)

    print("\n--- Hand and Surgical Instrument Tracker Active ---")
    print("Looking for hands and tools. Press 'q' to quit.")

    while True:
        try:
            if PICAM2_AVAILABLE:
                frame_rgb = picam2.capture_array()
                frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                ret = True
            else:
                ret, frame = video.read()
                if not ret: break
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception as e:
            print(f"Camera Read Error: {e}")
            break

        # Flip horizontally and Resize
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (640, 480))
        h, w, c = frame.shape

        hand_center = None
        instrument_center = None

        # ---------------------------------------------------------
        # Detect Hand Centers via MediaPipe (Safe Mode)
        # ---------------------------------------------------------
        try:
            hand_results = hands.process(frame_rgb)
            if hand_results.multi_hand_landmarks:
                for hand_marks in hand_results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_marks, mp_hands.HAND_CONNECTIONS)
                    lm = hand_marks.landmark[9]
                    hx, hy = int(lm.x * w), int(lm.y * h)
                    hand_center = (hx, hy)
                    cv2.circle(frame, (hx, hy), 12, (255, 0, 0), -1)
                    break 
        except Exception:
            # If MediaPipe causes an Illegal Instruction in a sub-thread, 
            # we catch it here to prevent a total crash.
            cv2.putText(frame, "HAND AI ERROR (SAFE MODE ACTIVE)", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # ---------------------------------------------------------
        # Detect Surgical Instruments via YOLOv8 (Safe Mode)
        # ---------------------------------------------------------
        try:
            yolo_results = model(frame, verbose=False)
            for r in yolo_results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    instrument_center = (cx, cy)
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    break 
        except Exception:
            cv2.putText(frame, "TOOL AI ERROR (SAFE MODE ACTIVE)", (10, h-40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # ---------------------------------------------------------
        # AI Decision System -> What should the Light point at?
        # ---------------------------------------------------------
        # Target logic: We want to shine the light on the hand HOLDING the tool.
        target_pt = None
        
        # Scenario A: We see both a hand and an instrument
        if instrument_center and hand_center:
            # Check the distance between them. If the instrument is in the hand, point at it!
            dist = math.hypot(instrument_center[0] - hand_center[0], instrument_center[1] - hand_center[1])
            if dist < 250: # pixel threshold indicating they are near 
                target_pt = instrument_center
                cv2.putText(frame, "TARGET LOCK: HOLDING TOOL", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                target_pt = hand_center
                
        # Scenario B: We only see the instrument 
        elif instrument_center:
            target_pt = instrument_center
            cv2.putText(frame, "TARGET LOCK: TOOL ISOLATED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
        # Scenario C: We only see the hand
        elif hand_center:
            target_pt = hand_center
            cv2.putText(frame, "TARGET LOCK: HAND TRACKING", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            cv2.putText(frame, "NO TARGET DETECTED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        # ---------------------------------------------------------
        # Broadcast Command to Panning Servo Setup
        # ---------------------------------------------------------
        if target_pt:
            # Draw line traversing from the bottom center (Servo origin simulation)
            cv2.line(frame, (int(w/2), h), target_pt, (0, 0, 255), 2)
            cv2.circle(frame, target_pt, 18, (0, 255, 255), -1) # Yellow reticle
            
            # Translate the Target X & Y center coordinates into percentages
            target_x_percent = target_pt[0] / float(w)
            target_y_percent = target_pt[1] / float(h)
            
            # Update the servo loop for both axes
            servo.track_target(target_x_percent, target_y_percent)

        # ---------------------------------------------------------
        # Render and Display
        # ---------------------------------------------------------
        try:
            cv2.imshow("Raspberry Pi - Medical AI Tracking", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Shutdown signal received")
                break
        except Exception:
            # If the Pi is booted cleanly from power without a monitor plugged in, 
            # imshow will fail. We catch the error so the AI keeps running headlessly!
            pass

    # Deep Cleanup
    video.release()
    cv2.destroyAllWindows()
    servo.cleanup()
    print("Process cleanly terminated.")

if __name__ == "__main__":
    main()
