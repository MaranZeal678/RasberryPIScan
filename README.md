# RasberryPIScan — Instrument-Following Surgical Headlamp

A Raspberry Pi 4 prototype for a **helmet-mounted surgical light that aims itself.**
A camera watches the surgical field, a vision pipeline locates the surgeon's hand and
the instrument they are holding, and a pan/tilt servo rig keeps the light pointed at
the active working area — so the surgeon never stops to reposition a lamp.

> **Prototype / research only.** This is not a certified medical device and must not be
> used in live surgical care without validation, safety review, and regulatory approval.
> See [Scope & disclaimer](#scope--disclaimer).

---

## How it works

```
Pi Camera ──▶ CameraStream ──┬──▶ HandTracker         (OpenCV motion + skin segmentation)
 (Picamera2 /                │                              │
  OpenCV fallback)           └──▶ InstrumentDetector   (YOLOv8n, ONNX / TFLite)
                                                             │
                                        choose_target() ─────┤
                                        classify_scene()     │
                                                             ▼
                                          PanTiltServoController (GPIO 17 / 18)
                                                   pan + tilt, smoothed
```

The tracker prefers the **hand** as the aim point and falls back to the **instrument**
when no hand is visible. When both are present and within ~170 px it reports a combined
`HAND + INSTRUMENT` state — the signal that the surgeon is actively working on tissue.

Servo motion is deliberately damped (deadband, proportional gain, capped step size) so the
light glides instead of jittering with every frame of detection noise.

Full render of the pipeline: [`docs/architecture-flowchart.html`](docs/architecture-flowchart.html)

## Trained model

Custom YOLOv8n fine-tuned on a 26-class surgical instrument dataset
([Roboflow: instruments-avfab v2](https://universe.roboflow.com/detection-0eju3/instruments-avfab/dataset/2)).

| Metric | Value |
| --- | --- |
| Epochs | 30 |
| Precision | 0.468 |
| Recall | 0.739 |
| mAP@50 | 0.646 |
| mAP@50-95 | 0.546 |
| Classes | 26 |

Training curves, confusion matrices, and validation batch predictions are in
[`results/`](results/). Raw per-epoch numbers: [`results/results.csv`](results/results.csv).

Recall is meaningfully higher than precision — an intentional trade for this use case.
Missing the instrument means the light goes dark on the surgeon; a spurious extra box
just nudges the aim point slightly.

The model is exported to ONNX and float32/float16 TFLite so it runs on the Pi's CPU
without a Coral or GPU. The runtime loads TFLite first for stability on-device.

## Repository layout

| Path | Contents |
| --- | --- |
| [`tracker.py`](tracker.py) | Main runtime loop — detection, target choice, servo command, overlay |
| [`vision_runtime.py`](vision_runtime.py) | `CameraStream`, `HandTracker`, `InstrumentDetector` |
| [`servo_controller.py`](servo_controller.py) | `PanTiltServoController` — GPIO pan/tilt with smoothing |
| [`train_yolo.py`](train_yolo.py) | Fine-tunes YOLOv8n on the instrument dataset |
| [`test_cam.py`](test_cam.py) | Camera bring-up check (backend + FPS) |
| [`scripts/`](scripts/) | `full_setup.sh` (Pi deps), `setup_autostart.sh` (systemd unit) |
| [`docs/`](docs/) | Pi run guide, architecture flowchart, working notes |
| [`models/`](models/) | Exported weights — `.pt`, `.onnx`, TFLite, calibration data |
| [`data/`](data/) | The 26-class instrument dataset (train/valid/test) |
| [`results/`](results/) | Training metrics, curves, confusion matrices, checkpoints |
| [`archive/`](archive/) | Superseded first iteration, kept for reference |

## Quickstart on a Raspberry Pi 4

```bash
git clone https://github.com/MaranZeal678/RasberryPIScan.git
cd RasberryPIScan
chmod +x scripts/*.sh
./scripts/full_setup.sh
```

Verify the camera, then run the tracker:

```bash
python3 test_cam.py
python3 tracker.py
```

Useful flags:

```bash
python3 tracker.py --headless        # no preview window, terminal logs only
python3 tracker.py --show-mask       # visualize the hand mask while tuning
python3 tracker.py --camera-index 0  # pick the OpenCV fallback camera
```

Run it on boot as a systemd service:

```bash
./scripts/setup_autostart.sh
sudo journalctl -u surgical_tracker.service -f
```

Wiring, troubleshooting, and the full walkthrough: [`docs/PI_RUN_GUIDE.md`](docs/PI_RUN_GUIDE.md)

## Hardware

- Raspberry Pi 4
- 12 MP Pi camera module (via `libcamera` / Picamera2)
- 2× hobby servos for pan and tilt — signal on **GPIO 17** (pan) and **GPIO 18** (tilt)
- Separate 5 V supply for the servos, with ground shared to the Pi

`servo_controller.py` mocks the GPIO layer when `gpiozero`/`pigpio` are absent, so the
full pipeline can be developed and run on a Mac or PC without any hardware attached.

## Scope & disclaimer

This project was built as an exploration of computer-vision-assisted surgical tooling.
It is a research prototype and a demonstration only. It is **not** a certified medical
device, has not been clinically validated, and carries no institutional endorsement — do
not represent it as an official product of any medical institution.
