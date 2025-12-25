#!/bin/bash
# Set Screen Saver to 600 seconds (10 minutes)
xset s 600 600
xset +dpms
xset dpms 600 600 600

# Run your UI
exec /home/lhr/Robot_Client/env/bin/python3 /home/lhr/Robot_Client/main_ui.py