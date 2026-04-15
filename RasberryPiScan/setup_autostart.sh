#!/bin/bash
set -euo pipefail

echo "Stopping any existing tracker service..."
sudo systemctl stop surgical_tracker.service || true

echo "Ensuring pigpiod is running..."
sudo systemctl enable pigpiod
sudo systemctl restart pigpiod

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "Creating systemd service..."
cat <<EOT | sudo tee /etc/systemd/system/surgical_tracker.service >/dev/null
[Unit]
Description=Raspberry Pi Hand Tracker
After=multi-user.target pigpiod.service
Requires=pigpiod.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$DIR
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONNOUSERSITE=1
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/python3 -s $DIR/tracker.py --headless
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOT

sudo systemctl daemon-reload
sudo systemctl enable surgical_tracker.service
sudo systemctl restart surgical_tracker.service

echo ""
echo "Autostart enabled."
echo "Logs: sudo journalctl -u surgical_tracker.service -f"
