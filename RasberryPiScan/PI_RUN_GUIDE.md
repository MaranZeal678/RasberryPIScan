# Raspberry Pi Run Guide

This folder is ready to run directly on a Raspberry Pi 4 after you copy it over.

## 1. Wiring

- Camera: connect the 12 MP camera module ribbon cable and confirm it works with `libcamera-hello`.
- Servo pan signal: GPIO 17
- Servo tilt signal: GPIO 18
- Servo power: use a separate 5V supply with a shared ground to the Pi

## 2. Copy the folder to the Pi

Example from your Mac:

```bash
scp -r /Users/maran/Desktop/RasberryPiScan pi@<PI_IP>:~/
```

Then on the Pi:

```bash
cd ~/RasberryPiScan
chmod +x full_setup.sh setup_autostart.sh
./full_setup.sh
```

## 3. Test the camera

```bash
python3 test_cam.py
```

You should see a live preview window and terminal logs showing the active backend and frame rate.

## 4. Run the tracker

```bash
python3 tracker.py
```

What it does:

- shows the live camera feed
- prints a camera/runtime log in the terminal once per second
- detects the moving hand with OpenCV
- optionally detects an instrument if one of the ONNX models in this folder is available
- moves the adjacent servo to follow the hand position

Useful options:

```bash
python3 tracker.py --headless
python3 tracker.py --show-mask
python3 tracker.py --camera-index 0
```

## 5. Enable autostart

```bash
./setup_autostart.sh
```

Then follow the logs with:

```bash
sudo journalctl -u surgical_tracker.service -f
```

## 6. Troubleshooting

- `No camera backend could be opened`: run `libcamera-hello` and check the ribbon cable and camera enablement.
- Servo does not move: make sure `pigpiod` is running with `systemctl status pigpiod`.
- Preview window does not open: run with a desktop session, or use `python3 tracker.py --headless`.
- Tracking is noisy: use `python3 tracker.py --show-mask` and adjust lighting so the hand stands out from the background.
