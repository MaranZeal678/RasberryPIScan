import time

import cv2

from vision_runtime import CameraStream


def main():
    camera = CameraStream()
    previous_time = time.time()
    last_log_time = 0.0

    try:
        camera.open()
        print(f"[camera-test] Backend: {camera.backend_name}")
        print("[camera-test] Press q to quit.")

        while True:
            frame = camera.read()
            frame = cv2.flip(frame, 1)

            current_time = time.time()
            elapsed = max(current_time - previous_time, 1e-6)
            fps = 1.0 / elapsed
            previous_time = current_time

            cv2.putText(
                frame,
                f"{camera.backend_name} | {camera.width}x{camera.height} | FPS {fps:.1f}",
                (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

            if current_time - last_log_time >= 1.0:
                print(
                    "[camera-test] "
                    f"camera={camera.backend_name} "
                    f"frame={camera.width}x{camera.height} "
                    f"fps={fps:.1f}"
                )
                last_log_time = current_time

            cv2.imshow("Pi Camera Test", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
