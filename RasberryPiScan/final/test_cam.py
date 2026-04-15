import cv2
import time
import os
import subprocess

# Try to import Picamera2 for official driver support
try:
    from picamera2 import Picamera2
    PICAM2_AVAILABLE = True
except ImportError:
    PICAM2_AVAILABLE = False

def check_hardware_camera():
    """Uses rpicam-hello to verify if the hardware actually sees a camera."""
    print("[HARDWARE CHECK] Pinging camera hardware via rpicam-apps...")
    try:
        # Run rpicam-hello --list-cameras to see what the OS detects
        result = subprocess.run(['rpicam-hello', '--list-cameras'], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"OS Reports: {result.stdout.strip()}")
            if "imx708" in result.stdout.lower():
                return "imx708"
            return "found"
        else:
            print("OS Reports: No camera detected at hardware level.")
            return "missing"
    except Exception:
        print("Hardware Ping: rpicam-apps not installed or failed.")
        return "unknown"

def get_gstreamer_pipeline(sensor="imx708"):
    """Generates a specialized GStreamer pipeline for Arducam Module 3."""
    # Optimization for Module 3 (IMX708)
    return (
        "libcamerasrc ! "
        "video/x-raw, width=640, height=480, format=RGB ! "
        "videoconvert ! "
        "appsink"
    )

def test_camera():
    print("\n--- Advanced Camera Diagnostic Tool v2.0 ---")
    
    # 0. Hardware Layer Check
    hw_status = check_hardware_camera()
    if hw_status == "missing":
        print("\n[!] HARDWARE ALERT: Your ribbon cable may be loose or the camera is disabled.")
        print("FIX: Run 'sudo raspi-config', go to Interface Options, and enable Camera.")
        print("FIX: Ensure 'dtoverlay=imx708' is in /boot/firmware/config.txt")
    
    # 1. Primary Attempt: Picamera2 (Official)
    if PICAM2_AVAILABLE:
        try:
            print("\n[MODE 1] Using Picamera2 (Official Wrapper)...")
            picam2 = Picamera2()
            config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
            picam2.configure(config)
            picam2.start()
            
            print(">>> SUCCESS: Picamera2 active.")
            while True:
                frame_rgb = picam2.capture_array()
                frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                cv2.imshow("TEST: Picamera2 Mode", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            picam2.stop()
            cv2.destroyAllWindows()
            return
        except Exception as e:
            print(f"[!] Picamera2 failed to open stream: {e}")

    # 2. Secondary Attempt: GStreamer libcamerasrc (The 'rpicam' bridge)
    print("\n[MODE 2] Testing Industrial GStreamer (rpicam-vid backend)...")
    pipeline = get_gstreamer_pipeline()
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    
    if cap.isOpened():
        print(">>> SUCCESS: GStreamer Safe Mode active.")
        while True:
            ret, frame = cap.read()
            if not ret: break
            cv2.imshow("TEST: GStreamer Safe Mode", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
        return
    else:
        print("[!] GStreamer Safe Mode failed.")

    # 3. Final Fallback: Standard V4L2 Device
    print("\n[MODE 3] Testing Standard V4L2 (Generic USB/Direct)...")
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print(">>> SUCCESS: Default V4L2 active.")
        while True:
            ret, frame = cap.read()
            if not ret: break
            cv2.imshow("TEST: Standard V4L2 Mode", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
        return
    
    print("\n[CRITICAL ERROR] No camera signal detected.")
    print("-" * 40)
    print("FINAL PI 4 CHECKLIST:")
    print("1. Check ribbon cable (Blue tab faces USB/Ethernet ports).")
    print("2. Run: sudo apt-get update && sudo apt-get install -y rpicam-apps")
    print("3. Add line 'dtoverlay=imx708' to /boot/firmware/config.txt and Reboot.")
    print("-" * 40)

if __name__ == "__main__":
    test_camera()
