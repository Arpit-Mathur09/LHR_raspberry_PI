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

