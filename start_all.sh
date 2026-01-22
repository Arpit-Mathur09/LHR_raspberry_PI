#!/bin/bash

# Make sure services are running
sudo systemctl start mediamtx
sudo systemctl start robot-flask
sudo systemctl start cloudflared

# Start X session with xinit
exec xinit /home/lhr/Robot_Client/xsession.sh -- :0 -nolisten tcp
