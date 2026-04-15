#!/bin/bash
# Run this on the Raspberry Pi to set up automatic boot
# NOTE: For Arducam Module 3, ensure you have run:
# sudo apt-get update && sudo apt-get install -y gstreamer1.0-plugins-bad libcamera-v4l2

echo "Stopping any existing version of the service..."
sudo systemctl stop surgical_tracker.service || true

echo "Creating the systemd service for Surgical AI Tracker..."

# 1. Enable pigpiod to start on boot
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# 2. Get the current directory (assuming this script is inside RasberryPiScan)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 3. Create the service file
cat <<EOT | sudo tee /etc/systemd/system/surgical_tracker.service
[Unit]
Description=Surgical AI Auto-Tracker
After=network.target pigpiod.service
Requires=pigpiod.service

[Service]
Type=simple
User=$USER
Environment=DISPLAY=:0
WorkingDirectory=$DIR
# If using a virtual environment, update 'python3' to '$DIR/venv/bin/python'
ExecStart=/usr/bin/python3 $DIR/tracker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOT

# 4. Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable surgical_tracker.service
sudo systemctl start surgical_tracker.service

echo ""
echo "=== Install Complete ==="
echo "The AI will now boot up automatically whenever the Raspberry Pi receives power."
echo "If you ever need to stop it manually, run: sudo systemctl stop surgical_tracker.service"
