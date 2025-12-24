LHR Raspberry PI code for 
- Client 
- Serial with Raspberry PI Pico
- Kiosk Setup with touchscreen UI
- Camera Frame Streaming 
- Storing Protocols (gcode files etc)


⚠️ Important Note:
- We write pyserial in this file, even though we import it as import serial in Python.

- Do not install a package simply named "serial"; it is an unrelated library that will break your code. pyserial is the correct one for UART/USB communication. 

