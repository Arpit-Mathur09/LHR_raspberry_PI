#!/bin/bash

# 1. Screen Settings (No Sleep)
xset -dpms
xset s off
xset s noblank

# 2. Start the Window Manager (in the background)
# This keeps the X server happy and manages your window size
matchbox-window-manager -use_titlebar no &

# 3. Allow Root (Sudo) to draw on the screen
# We wait a moment to ensure Matchbox is ready
sleep 1
xhost +si:localuser:root

# 4. Restart Background Services (As you requested)
sudo systemctl restart mediamtx
sudo systemctl restart robot-flask
sudo systemctl restart cloudflared


# 5. The Application Loop (Kiosk Mode)
while true; do
    # Run Python with sudo (for Hardware), utilizing the Virtual Env
    # -E preserves the environment variables so it finds the Display
    sudo -E /home/lhr/Robot_Client/env/bin/python3 /home/lhr/Robot_Client/main_ui.py 
    # If the app crashes, wait 2 seconds and restart it
    sleep 2
done