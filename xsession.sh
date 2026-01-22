#!/bin/bash

# Start backend if not running
systemctl start mediamtx
systemctl start robot-flask
systemctl start cloudflared

# Activate venv and start UI
cd /home/lhr/Robot_Client
source env/bin/activate
python3 main_ui.py
