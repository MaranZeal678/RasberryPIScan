#!/bin/bash
set -euo pipefail

echo "--- Raspberry Pi Tracker Setup ---"
echo "Installing Raspberry Pi OS packages required for camera, OpenCV, and servo control..."

sudo apt-get update
sudo apt-get install -y \
    libcamera-apps \
    pigpio \
    python3-gpiozero \
    python3-libcamera \
    python3-numpy \
    python3-opencv \
    python3-picamera2 \
    python3-pigpio

echo "Enabling pigpiod..."
sudo systemctl enable pigpiod
sudo systemctl restart pigpiod

echo ""
echo "Setup complete."
echo "1. Test the camera: python3 test_cam.py"
echo "2. Run the tracker: python3 tracker.py"
echo "3. For boot-time startup: ./setup_autostart.sh"
