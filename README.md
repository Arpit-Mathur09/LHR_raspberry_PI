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

- Installation of fonts: sudo apt install fonts-unifont fonts-symbola


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

    

