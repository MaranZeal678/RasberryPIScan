import argparse
import math
import time

import cv2

from servo_controller import PanTiltServoController
from vision_runtime import CameraStream, HandTracker, InstrumentDetector


def parse_args():
    parser = argparse.ArgumentParser(
        description="Track a hand with an adjacent servo on Raspberry Pi."
    )
    parser.add_argument("--width", type=int, default=640, help="Camera width.")
    parser.add_argument("--height", type=int, default=480, help="Camera height.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Disable the preview window and run from the terminal only.",
    )
    parser.add_argument(
        "--show-mask",
        action="store_true",
        help="Display the hand mask for tuning and debugging.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Fallback OpenCV camera index.",
    )
    parser.add_argument(
        "--model-path",
        default="",
        help="Optional ONNX model path for instrument detection.",
    )
    return parser.parse_args()


def draw_crosshair(frame):
    height, width = frame.shape[:2]
    center = (width // 2, height // 2)
    cv2.drawMarker(
        frame,
        center,
        (255, 255, 255),
        markerType=cv2.MARKER_CROSS,
        markerSize=24,
        thickness=1,
    )


def choose_target(hand_detection, instrument_detection):
    if hand_detection:
        return hand_detection.center
    if instrument_detection:
        return instrument_detection.center
    return None


def classify_scene(hand_detection, instrument_detection):
    if hand_detection and instrument_detection:
        hand_x, hand_y = hand_detection.center
        tool_x, tool_y = instrument_detection.center
        distance = math.hypot(tool_x - hand_x, tool_y - hand_y)
        if distance < 170:
            return "HAND + INSTRUMENT"
        return "HAND DETECTED | TOOL SEPARATE"
    if hand_detection:
        return "HAND DETECTED"
    if instrument_detection:
        return "INSTRUMENT DETECTED"
    return "NO TARGET"


def render_overlay(frame, hand_detection, instrument_detection, status_text, servo, fps, camera):
    draw_crosshair(frame)

    if hand_detection:
        x, y, w, h = hand_detection.bbox
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 180, 255), 2)
        cv2.circle(frame, hand_detection.center, 10, (0, 180, 255), -1)
        cv2.putText(
            frame,
            "Hand",
            (x, max(18, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 180, 255),
            2,
        )

    if instrument_detection:
        x, y, w, h = instrument_detection.bbox
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.circle(frame, instrument_detection.center, 8, (0, 255, 0), -1)
        cv2.putText(
            frame,
            f"Instrument {instrument_detection.score:.2f}",
            (x, max(18, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

    lines = [
        status_text,
        f"Camera: {camera.backend_name} @ {camera.width}x{camera.height} | FPS: {fps:.1f}",
        f"Servo PAN {servo.current_pan_angle:5.1f} deg | TILT {servo.current_tilt_angle:5.1f} deg",
    ]

    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (10, 28 + (index * 24)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )


def log_state(camera, hand_detection, instrument_detection, servo, fps):
    hand_text = "yes" if hand_detection else "no"
    instrument_text = "yes" if instrument_detection else "no"
    print(
        "[tracker] "
        f"camera={camera.backend_name} "
        f"frame={camera.width}x{camera.height} "
        f"fps={fps:.1f} "
        f"hand={hand_text} "
        f"instrument={instrument_text} "
        f"pan={servo.current_pan_angle:.1f} "
        f"tilt={servo.current_tilt_angle:.1f}"
    )


def main():
    args = parse_args()

    camera = CameraStream(width=args.width, height=args.height, camera_index=args.camera_index)
    hand_tracker = HandTracker()
    instrument_detector = InstrumentDetector(model_path=args.model_path)
    servo = PanTiltServoController(pan_pin=17, tilt_pin=18)

    try:
        camera.open()
        print("[tracker] Camera ready.")
        print(f"[tracker] Backend: {camera.backend_name}")
        if instrument_detector.loaded:
            print(f"[tracker] Instrument model: {instrument_detector.model_name}")
        else:
            print("[tracker] Instrument model disabled. Hand tracking remains active.")
        print("[tracker] Press q in the preview window to stop.")

        previous_time = time.time()
        last_log_time = 0.0

        while True:
            frame = camera.read()
            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (args.width, args.height))

            hand_detection, hand_mask = hand_tracker.detect(frame)
            instrument_detection = instrument_detector.detect(frame)
            target = choose_target(hand_detection, instrument_detection)

            current_time = time.time()
            elapsed = max(current_time - previous_time, 1e-6)
            fps = 1.0 / elapsed
            previous_time = current_time

            if target:
                target_x = target[0] / float(args.width)
                target_y = target[1] / float(args.height)
                servo.track_target(target_x, target_y)
                cv2.line(frame, (args.width // 2, args.height), target, (0, 0, 255), 2)
                cv2.circle(frame, target, 14, (0, 255, 255), 2)

            status_text = classify_scene(hand_detection, instrument_detection)
            render_overlay(
                frame,
                hand_detection,
                instrument_detection,
                status_text,
                servo,
                fps,
                camera,
            )

            if current_time - last_log_time >= 1.0:
                log_state(camera, hand_detection, instrument_detection, servo, fps)
                last_log_time = current_time

            if not args.headless:
                cv2.imshow("Pi Hand Tracker", frame)
                if args.show_mask:
                    cv2.imshow("Hand Mask", hand_mask)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        print("\n[tracker] Stopped by user.")
    except Exception as exc:
        print(f"[tracker] Fatal error: {exc}")
        raise
    finally:
        camera.close()
        servo.cleanup()
        cv2.destroyAllWindows()
        print("[tracker] Shutdown complete.")


if __name__ == "__main__":
    main()
