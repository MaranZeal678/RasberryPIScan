from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

try:
    from picamera2 import Picamera2

    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False


@dataclass
class Detection:
    label: str
    score: float
    bbox: tuple

    @property
    def center(self):
        x, y, width, height = self.bbox
        return (x + (width // 2), y + (height // 2))


class CameraStream:
    def __init__(self, width=640, height=480, camera_index=0):
        self.width = width
        self.height = height
        self.camera_index = camera_index
        self.backend_name = "uninitialized"
        self.picam2 = None
        self.capture = None

    def open(self):
        if PICAMERA2_AVAILABLE:
            try:
                self.picam2 = Picamera2()
                config = self.picam2.create_video_configuration(
                    main={"size": (self.width, self.height), "format": "RGB888"}
                )
                self.picam2.configure(config)
                self.picam2.start()
                self.backend_name = "Picamera2"
                return
            except Exception as exc:
                print(f"[camera] Picamera2 failed: {exc}")
                self.picam2 = None

        self.capture = cv2.VideoCapture(self.camera_index)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        if not self.capture.isOpened():
            raise RuntimeError("No camera backend could be opened.")

        self.backend_name = f"OpenCV({self.camera_index})"

    def read(self):
        if self.picam2:
            frame_rgb = self.picam2.capture_array()
            return cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

        if not self.capture:
            raise RuntimeError("Camera has not been opened.")

        ok, frame = self.capture.read()
        if not ok or frame is None:
            raise RuntimeError("Camera frame read failed.")
        return frame

    def close(self):
        if self.picam2:
            self.picam2.stop()
            self.picam2 = None
        if self.capture:
            self.capture.release()
            self.capture = None


class HandTracker:
    def __init__(self):
        self.background = cv2.createBackgroundSubtractorMOG2(
            history=120, varThreshold=32, detectShadows=False
        )
        self.previous_center = None

    def _clean_mask(self, mask):
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.medianBlur(mask, 5)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        return cv2.dilate(mask, kernel, iterations=1)

    def _skin_mask(self, frame):
        blurred = cv2.GaussianBlur(frame, (7, 7), 0)

        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        hsv_low = cv2.inRange(hsv, (0, 20, 40), (25, 255, 255))
        hsv_high = cv2.inRange(hsv, (160, 20, 40), (179, 255, 255))
        hsv_mask = cv2.bitwise_or(hsv_low, hsv_high)

        ycrcb = cv2.cvtColor(blurred, cv2.COLOR_BGR2YCrCb)
        ycrcb_mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 180, 135))

        skin_mask = cv2.bitwise_and(hsv_mask, ycrcb_mask)
        return self._clean_mask(skin_mask)

    def _motion_mask(self, frame):
        foreground = self.background.apply(frame)
        _, foreground = cv2.threshold(foreground, 200, 255, cv2.THRESH_BINARY)
        return self._clean_mask(foreground)

    def _pick_contour(self, contours, frame_area):
        best_contour = None
        best_score = -1.0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1800:
                continue
            if area > frame_area * 0.55:
                continue

            x, y, width, height = cv2.boundingRect(contour)
            if width < 30 or height < 30:
                continue

            center_x = x + (width // 2)
            center_y = y + (height // 2)
            score = area

            if self.previous_center:
                distance = np.hypot(
                    center_x - self.previous_center[0],
                    center_y - self.previous_center[1],
                )
                score -= distance * 3.0

            if score > best_score:
                best_score = score
                best_contour = contour

        return best_contour

    def detect(self, frame):
        frame_area = frame.shape[0] * frame.shape[1]
        skin_mask = self._skin_mask(frame)
        motion_mask = self._motion_mask(frame)
        combined_mask = cv2.bitwise_and(skin_mask, motion_mask)

        contours, _ = cv2.findContours(
            combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        contour = self._pick_contour(contours, frame_area)

        if contour is None:
            contours, _ = cv2.findContours(
                motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            contour = self._pick_contour(contours, frame_area)
            display_mask = motion_mask
        else:
            display_mask = combined_mask

        if contour is None:
            self.previous_center = None
            return None, display_mask

        x, y, width, height = cv2.boundingRect(contour)
        center = (x + (width // 2), y + (height // 2))

        if self.previous_center:
            alpha = 0.45
            center = (
                int((alpha * center[0]) + ((1.0 - alpha) * self.previous_center[0])),
                int((alpha * center[1]) + ((1.0 - alpha) * self.previous_center[1])),
            )
            x = max(center[0] - (width // 2), 0)
            y = max(center[1] - (height // 2), 0)

        self.previous_center = center
        return Detection("hand", 1.0, (x, y, width, height)), display_mask


class InstrumentDetector:
    def __init__(self, model_path=""):
        self.net = None
        self.loaded = False
        self.model_name = "disabled"
        self.input_size = 640
        self.confidence_threshold = 0.45
        self.nms_threshold = 0.35
        self.allowed_labels = {"scissors", "knife", "fork", "spoon"}
        self.label_names = {}
        self.custom_model = False

        candidate_paths = []
        if model_path:
            candidate_paths.append(Path(model_path))

        root = Path(__file__).resolve().parent
        candidate_paths.extend(
            [
                root / "final" / "runs" / "detect" / "surgical_instrument_model" / "weights" / "best.onnx",
                root / "final" / "runs" / "detect" / "surgical_instrument_model2" / "weights" / "best.onnx",
                root / "yolov8n.onnx",
            ]
        )

        for candidate in candidate_paths:
            if not candidate.exists():
                continue
            try:
                self.net = cv2.dnn.readNetFromONNX(str(candidate))
                self.loaded = True
                self.model_name = str(candidate.relative_to(root))
                self.custom_model = "best.onnx" in candidate.name
                self.label_names = self._load_labels(candidate)
                break
            except Exception as exc:
                print(f"[detector] Failed to load {candidate}: {exc}")

    def _load_labels(self, model_path):
        root = Path(__file__).resolve().parent
        if "surgical_instrument_model" in str(model_path):
            return {index: "instrument" for index in range(26)}
        if "yolov8n.onnx" in model_path.name:
            return {
                42: "fork",
                43: "knife",
                44: "spoon",
                76: "scissors",
            }
        metadata_path = root / "yolov8n_saved_model" / "metadata.yaml"
        if metadata_path.exists():
            return {42: "fork", 43: "knife", 44: "spoon", 76: "scissors"}
        return {}

    def _parse_output(self, output, frame_shape):
        rows = output[0]
        rows = rows.transpose()

        frame_height, frame_width = frame_shape[:2]
        x_factor = frame_width / float(self.input_size)
        y_factor = frame_height / float(self.input_size)

        boxes = []
        scores = []
        labels = []

        for row in rows:
            classes = row[4:]
            class_id = int(np.argmax(classes))
            score = float(classes[class_id])

            if score < self.confidence_threshold:
                continue

            label = self.label_names.get(class_id, "instrument")
            if not self.custom_model and label not in self.allowed_labels:
                continue

            center_x, center_y, width, height = row[:4]
            left = int((center_x - (width / 2.0)) * x_factor)
            top = int((center_y - (height / 2.0)) * y_factor)
            box_width = int(width * x_factor)
            box_height = int(height * y_factor)

            left = max(left, 0)
            top = max(top, 0)
            box_width = max(box_width, 1)
            box_height = max(box_height, 1)

            boxes.append([left, top, box_width, box_height])
            scores.append(score)
            labels.append(label)

        return boxes, scores, labels

    def detect(self, frame):
        if not self.loaded:
            return None

        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1.0 / 255.0,
            size=(self.input_size, self.input_size),
            swapRB=True,
            crop=False,
        )
        self.net.setInput(blob)
        output = self.net.forward()

        boxes, scores, labels = self._parse_output(output, frame.shape)
        if not boxes:
            return None

        indices = cv2.dnn.NMSBoxes(
            boxes, scores, self.confidence_threshold, self.nms_threshold
        )
        if len(indices) == 0:
            return None

        if hasattr(indices, "flatten"):
            best_index = int(indices.flatten()[0])
        else:
            best_index = int(indices[0])

        bbox = tuple(boxes[best_index])
        return Detection(labels[best_index], scores[best_index], bbox)
