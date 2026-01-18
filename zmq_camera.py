import sys
import subprocess
import imagezmq
import time

# --- CONFIGURATION ---
SERVER_IP = "192.168.31.236"
PORT = 5555
CAM_ID = "RobotCam1"

# --- OPTIMIZED COMMAND ---
CMD = [
    "rpicam-vid", 
    "-t", "0", 
    "--inline",
    
    # 1. SPEED SETTINGS
    "--width", "480",       
    "--height", "360",      
    "--framerate", "15",    
    # ... inside your CMD list ...

    "--codec", "mjpeg", 
    "--quality", "20",
    
    # --- COLOR CORRECTION FIX ---
    # 1. Use 'tungsten' preset. 
    # This tells the camera "The light is very orange", so it aggressively cuts Red/Pink.
    "--awb", "tungsten",   
    
    # 2. REMOVE the manual gains line. 
    # It does not work because 'awb off' crashes your Pi.
    # "--awbgains", "1.0,2.0",  <-- DELETE THIS LINE
    
    # 3. Reduce Saturation. 
    # Turning this down makes the purple look more like grey/black.
    # Try 0.0 for Black & White (Clearest), or 0.5 for muted Color.
    "--saturation", "0.0",
    
    "--metering", "matrix", 
    "--brightness", "0.0", 
    
    # ... rest of settings ...
    # 3. LATENCY OPTIMIZATION
    "--nopreview",          
    "--denoise", "cdn_off", 
    "-o", "-"
]

def find_jpeg_end(buffer, start_index):
    index = buffer.find(b'\xff\xd9', start_index)
    if index != -1: return index + 2
    return -1

def stream():
    print(f"📡 Connecting to Server at {SERVER_IP}:{PORT}...")
    sender = imagezmq.ImageSender(connect_to=f"tcp://{SERVER_IP}:{PORT}")
    print(f"📷 Starting Stream with Manual Color Fix: {' '.join(CMD)}")

    try:
        process = subprocess.Popen(CMD, stdout=subprocess.PIPE, stderr=sys.stderr, bufsize=0)
    except FileNotFoundError:
        CMD[0] = "libcamera-vid"
        process = subprocess.Popen(CMD, stdout=subprocess.PIPE, stderr=sys.stderr, bufsize=0)

    buffer = b''
    
    try:
        while True:
            chunk = process.stdout.read(2048)
            if not chunk: break
            
            buffer += chunk
            start = buffer.find(b'\xff\xd8')
            
            if start != -1:
                end = find_jpeg_end(buffer, start)
                if end != -1:
                    jpg_data = buffer[start:end]
                    try:
                        sender.send_jpg(CAM_ID, jpg_data)
                    except:
                        pass 
                    buffer = buffer[end:]
                    
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        process.terminate()

if __name__ == "__main__":
    stream()