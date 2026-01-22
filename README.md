Description : These are the Files saved on Pi 4
Pi- main_ui.py , backend.py
mockserver - server.py

LHR Raspberry PI code for 
- Client 
- Serial with Raspberry PI Pico
- Kiosk Setup with touchscreen UI
- Camera Frame Streaming 
- Storing Protocols (gcode files etc)

KIOSK SETUP 
- Install Raspberry PI OS (64 bit) CLI on your Raspberry PI
-apt update && apt upgrade -y
- Install required packages should be install in root
    sudo apt install --no-install-recommends xserver-xorg x11-xserver-utils xinit openbox chromium unclutter
    -- sudo apt-get update && sudo apt-get install -y libatlas-base-dev libopenjp2-7 libtiff5 libgl1-mesa-glx
    --further more in clickup task

- Installation of fonts: sudo apt install fonts-unifont fonts-symbola

cloudflare 
 -cloudflared tunnel create pi-tunnel 
    Tunnel credentials written to /home/lhr/.cloudflared/861a0c8c-8b8a-483f-976d-63bccca24461.json. cloudflared chose this file based on where your origin certificate was found. Keep this file secret. To revoke these credentials, delete the tunnel.
    Created tunnel pi-tunnel with id 861a0c8c-8b8a-483f-976d-63bccca24461
-Kimoteh377@noihse.com cloufare temp account 

▶️TO run (assuming working directory is /home/lhr/Robot_Client)
- sudo startx /home/lhr/Robot_Client/env/bin/python3 /home/lhr/Robot_Client/main_ui.py
- cd /opt/mediamtx && ./mediamtx
- source /home/lhr/Robot_Client/env/bin/activate &&python3 /home/lhr/Robot_Client/server.py 

**Automatic Startup (Recommended)**
- All services auto-start on boot (mediamtx, robot-flask, cloudflared, main_ui)
- Just reboot: `sudo reboot`


**Status Check**
```bash
sudo systemctl status mediamtx
sudo systemctl status robot-flask
sudo systemctl status cloudflared
```

**Access Dashboard**
- Local: http://192.168.31.83:5000 (user: admin, pass: strongpassword)
- Remote: Via cloudflare tunnel ([LINK](https://app.lhrpi.dpdns.org/))
(Remote works only pi is working and connected to internet)

*NOTE For graceful shutdown for pi for future
-GPIO 16
    sudo nano /boot/firmware/config.txt
    add this- dtoverlay=gpio-shutdown,gpio_pin=16,gpio_pull=up

⚠️ Important Note:
- We write pyserial in this file, even though we import it as import serial in Python.

- Do not install a package simply named "serial"; it is an unrelated library that will break your code. pyserial is the correct one for UART/USB communication. 

🎯V1.4 Pi+Pico and Mockeserver 
-PI 
    - Interfaced 5 Inch touch screen display 
    - ADT75 and BME 280 
    - 1 Fan and 1 heater (creality heat bed)
    - UI (see UIandServerChecklist.txt)

⏭️Next Step 
    - 2 DS18b20 on PI for the heat bed temperature 
    - ADT75 for cicuit temperature
    - Colling Fan (Overall PID)
    - UI & Servere Add Pippette and Pump UI
    PICO 
    - See Pico subtasks in Clickup

    

