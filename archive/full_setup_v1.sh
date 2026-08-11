#!/bin/bash
# Master Setup Script for Surgical AI Tracker
# Use this to restore the project from scratch on a Raspberry Pi

echo "--- Starting Full System Setup ---"

# 1. Update and Install System Dependencies
echo "Updating system and installing hardware drivers..."
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    libcamera-v4l2 \
    gstreamer1.0-plugins-bad \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    pigpio \
    python3-pigpio

# 2. Enable and Start pigpiod (Hardware PWM for Servos)
echo "Setting up Servo Daemon (pigpiod)..."
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# 3. Create Virtual Environment
echo "Creating Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 4. Install Python Packages
echo "Installing AI and Robotics libraries (this can take several minutes)..."
source venv/bin/activate

# Ensure pip is up to date
pip install --upgrade pip setuptools wheel

# Install core requirements
pip install -r requirements.txt

# Explicitly ensure YOLO and Mediapipe are installed (redundant but safe)
pip install ultralytics mediapipe opencv-python

# 5. Set up Autostart Service
echo "Configuring automatic boot-up..."
chmod +x setup_autostart.sh
./setup_autostart.sh

echo ""
echo "--- ALL INSTALLATION COMMANDS COMPLETE ---"
echo "1. Restart your Pi: sudo reboot"
echo "2. After reboot, test your camera: python3 test_cam.py"
echo "3. Run the full app: python3 tracker.py"
echo ""
