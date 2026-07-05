Description : These are the Files saved on Pi 4 B Pi
 `main_ui.py , backend.py , network.py ,hardware.py` and using @AP render remote server now  
(old -mockserver - server.py) 

# LHR Raspberry PI code for 
- Client 
- Serial with Raspberry PI Pico
- Kiosk Setup with touchscreen UI
- Camera Frame Streaming 
- Storing Protocols (gcode files etc)

# KIOSK SETUP 
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
- Before starting the client, install the websocket deps in the venv:
    ./env/bin/python -m pip install python-socketio==5.3.0 websocket-client==1.9.0
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


# Module Installation Command for @AP remote Machine connection

 ./env/bin/python -m pip install python-socketio==5.3.0 websocket-client==1.9.0

---

# Splash screen Setup 

Since your old SD card already has the X11 launch sequence working perfectly, we can skip all the risky .bash_profile and .xinitrc troubleshooting. We just need to silence the hardware and install the final, bulletproof version of the custom Plymouth theme we just built.

Here is the complete, streamlined installation from scratch.

## Phase 1: Silence the Hardware and Kernel
First, we need to kill the rainbow square and the wall of kernel text.

>Disable the Rainbow Screen:

Bash
``sudo nano /boot/firmware/config.txt``
Add this exact line to the very bottom, then save and exit (Ctrl+O, Enter, Ctrl+X):

Plaintext
disable_splash=1
Silence the Kernel Wall of Text:

Bash
``sudo nano /boot/firmware/cmdline.txt``
Crucial Rule: This file must remain a single line. Do not press Enter.

Look for `console=tty1` and change it to `console=tty3` if not present add this as well

Add this exactly to the very end of the line:

``quiet splash loglevel=0 logo.nologo vt.global_cursor_default=0 plymouth.ignore-serial-consoles``
Save and exit (Ctrl+O, Enter, Ctrl+X).

## Phase 2: Install Plymouth & Create the Theme
Copy and paste this entire block into your SSH terminal. It will install Plymouth, create your custom folder, and write the configuration file automatically.

Bash
1. #Install Plymouth
``sudo apt update && sudo apt install -y plymouth plymouth-themes``

2. #Create the theme directory
``sudo mkdir -p /usr/share/plymouth/themes/custom-splash``

3. #Create the theme configuration file copy & paste

```
cat << 'EOF' | sudo tee /usr/share/plymouth/themes/custom-splash/custom-splash.plymouth

[Plymouth Theme]
Name=Custom Splash
Description=Professional Boot Logo
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/custom-splash
ScriptFile=/usr/share/plymouth/themes/custom-splash/custom-splash.script
EOF
```

## Phase 3: The Final Plymouth Script
This is the final, perfected version of the script we built. It dynamically calculates the screen resolution to prevent layout breaking, anchors the text to the absolute bottom, and handles both boot and shutdown modes.

>Copy and paste this entire block:


```
cat << 'EOF' | sudo tee /usr/share/plymouth/themes/custom-splash/custom-splash.script
# Get System Mode
system_mode = Plymouth.GetMode();

# Setup Base Images and Sprites
logo_image = Image("logo.png");
logo_sprite = Sprite(logo_image);

spinner_image = Image("spinner.png");
spinner_sprite = Sprite();

text_sprite = Sprite();
loading_image = Image.Text(" ", 1, 1, 1);

# Animation Variables
angle = 0;
time_tick = 0;

# The Refresh Function (Runs continuously)
fun refresh_callback () {
    screen_width = Window.GetWidth();
    screen_height = Window.GetHeight();

    # Update Logo Position
    logo_sprite.SetX(screen_width / 2 - logo_image.GetWidth() / 2);
    logo_sprite.SetY(screen_height / 2 - logo_image.GetHeight() / 2 - 20);

    # Rotate the spinner
    angle = angle + 0.05;
    rotated_spinner = spinner_image.Rotate(angle);
    spinner_sprite.SetImage(rotated_spinner);
    spinner_sprite.SetX(screen_width / 2 - rotated_spinner.GetWidth() / 2);
    spinner_sprite.SetY(screen_height / 2 + logo_image.GetHeight() / 2 + 20);

    # Advance time
    time_tick++;
    
    # Text Sequence (Boot vs Shutdown)
    if (system_mode == "shutdown" || system_mode == "reboot") {
        if (time_tick == 1) loading_image = Image.Text("Deinitializing Core Systems...", 1, 1, 1);
        if (time_tick == 100) loading_image = Image.Text("Terminating Hardware Services...", 1, 1, 1);
        if (time_tick == 250) loading_image = Image.Text("Powering Down...", 1, 1, 1);
    } else {
        if (time_tick == 1) loading_image = Image.Text("Initializing Core Systems...", 1, 1, 1);
        if (time_tick == 100) loading_image = Image.Text("Initializing WiFi Module...", 1, 1, 1);
        if (time_tick == 250) loading_image = Image.Text("Starting User Interface...", 1, 1, 1);
    }

    # Update text position dynamically (Bottom Anchor)
    text_sprite.SetImage(loading_image);
    text_sprite.SetX(screen_width / 2 - loading_image.GetWidth() / 2);
    text_sprite.SetY(screen_height - loading_image.GetHeight() - 50);
}

Plymouth.SetRefreshFunction(refresh_callback);
EOF

```

## Phase 4: Add Images, Hide Login Text, and Compile
Ensure your logo.png and spinner.png (50x50 size) are sitting in your home directory (/home/lhr/). Then run this final block to move the images, safely hide the standard Debian login text, and compile the boot sector.

```
# 1. Copy your custom images into the theme folder
sudo cp ~/logo.png ~/spinner.png /usr/share/plymouth/themes/custom-splash/

# 2. Hide the OS Banner and "Message of the Day"
sudo cp /dev/null /etc/issue
touch ~/.hushlogin

# 3. Rebuild the Boot Sector (This takes ~30 seconds)
sudo plymouth-set-default-theme -R custom-splash
```

## Phase 5: Xint prints redirect
Instead, we are going to use native, 100% safe Linux file tricks. We are going to let the system boot normally, but we will "gag" the text so it prints blank spaces or routes to hidden files instead of drawing on your monitor.

This will not crash X11, and it will not trap your display.

Copy and paste this entire block into your SSH terminal and press Enter:

```
# 1. Kill the "Debian GNU/Linux" OS banner that prints before login
sudo cp /dev/null /etc/issue

# 2. Kill the "Last login" and MOTD (Message of the Day) text
touch ~/.hushlogin

# 3. Safely update the auto-start to clear the screen and hide X11 text
cat << 'EOF' > /home/lhr/.bash_profile
# Load standard bash configurations
if [ -n "$BASH_VERSION" ] && [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi

# Auto-start X11 if logged in on the physical screen
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    clear
    startx -- -keeptty -nocursor > /home/lhr/startx_hidden.log 2>&1
fi
EOF
```
## Phase 6: Silence the Login Text
Here is exactly what is happening: Even though we deleted the welcome text files, the system program responsible for logging you in (called agetty) is hardcoded to print your username (lhr login:) for a split second before your .bash_profile has a chance to execute the clear command. That delay is what causes the unprofessional 1-second flash of the terminal.

To fix it, we are going to keep your auto-login exactly as it is, but we will pass a few "silencer" flags to the agetty program so it keeps its mouth shut while it logs you in.

Copy and paste this entire block into your SSH terminal and press Enter:

```
# 1. Ensure the override folder exists
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d

# 2. Update the auto-login rule with "silencer" flags (--skip-login and --noissue)
cat << 'EOF' | sudo tee /etc/systemd/system/getty@tty1.service.d/override.conf
[Service]
ExecStart=
ExecStart=-/sbin/agetty --skip-login --noissue --autologin lhr --noclear %I $TERM
EOF

# 3. Reload the system to apply the silenced login
sudo systemctl daemon-reload
```
Once that last command finishes running, you are fully set up. Run sudo reboot and you should have your perfectly smooth, silent boot sequence right back!
