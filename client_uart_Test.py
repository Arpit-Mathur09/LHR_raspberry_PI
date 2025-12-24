""" import requests
import serial
import time
import os
from datetime import datetime

# --- CONFIGURATION ---
SERVER_URL = "http://192.168.31.236:5000/" # <--- CHECK YOUR IP
LOCAL_DIR = "/home/lhr/recent_protocols"
LOG_DIR = "/home/lhr/logs"

for d in [LOCAL_DIR, LOG_DIR]: os.makedirs(d, exist_ok=True)

class RobotClient:
    def __init__(self):
        try:
            print("🔌 Connecting to Serial Port...")
            self.ser = serial.Serial('/dev/serial0', 115200, timeout=0.1)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            print("✅ Serial Connected.")
            
            # Flush "Ghost" data from Pico
            time.sleep(1)
            self.ser.write(b"\n\n")
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            
        except Exception as e:
            print(f"⚠️ Serial Port Failed: {e}")
            self.ser = None

        self.is_running = False
        self.is_paused = False
        self.current_filename = None
        self.current_session_log = None
        self.lines = []
        self.ptr = 0
        
        # --- FIX 1: INITIALIZE SEQUENCE COUNTER ---
        self.seq_num = 1 
        
        self.log_accumulator = []

    def start_new_log_session(self, filename):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_session_log = f"{filename}_{timestamp}.log"
        self.log(f"🚀 Started Protocol Session: {filename}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        print(entry)
        if self.current_session_log:
            try:
                with open(os.path.join(LOG_DIR, self.current_session_log), "a", encoding="utf-8") as f: 
                    f.write(entry + "\n")
            except: pass
        self.log_accumulator.append(entry)

    def sync_with_server(self):
        progress = 0
        current_line_txt = "Idle"
        if self.lines and self.ptr < len(self.lines):
            progress = int((self.ptr / len(self.lines)) * 100)
            current_line_txt = self.lines[self.ptr].strip()

        payload = {
            "file": self.current_filename,
            "line": current_line_txt,
            "progress": progress,
            "est": "N/A", 
            "logs": "\n".join(self.log_accumulator)
        }
        self.log_accumulator = []

        try:
            r = requests.post(f"{SERVER_URL}/pi/sync", json=payload, timeout=0.5)
            if r.status_code == 200:
                for cmd in r.json().get("commands", []):
                    self.handle_event(cmd)
        except: pass

    def handle_event(self, cmd):
        ev = cmd["event"]
        if ev == "PAUSE": self.is_paused = True; self.log("⏸ Paused")
        elif ev == "RESUME": self.is_paused = False; self.log("▶ Resumed")
        elif ev == "CLEAR": self.is_running = False; self.log("🧹 Cleared")
        elif ev == "NEW_FILE": self.download_file(cmd["filename"])
        elif ev == "SERIAL_SEND": 
            if self.ser: self.ser.write((cmd["data"] + "\n").encode())

    def download_file(self, filename):
        self.log(f"📥 Downloading {filename}...")
        try:
            r = requests.get(f"{SERVER_URL}/download/{filename}")
            local_path = os.path.join(LOCAL_DIR, filename)
            with open(local_path, "wb") as f: f.write(r.content)
            with open(local_path, "r", encoding="utf-8") as f: self.lines = f.readlines()
            
            self.current_filename = filename
            self.ptr = 0
            # --- FIX 2: RESET SEQUENCE ON NEW FILE ---
            self.seq_num = 1
            
            self.is_running = True
            self.is_paused = False
            self.start_new_log_session(filename)
            if self.ser: self.ser.reset_input_buffer()
                
        except Exception as e:
            self.log(f"❌ Error: {e}")

    def run(self):
        print("🚀 Pi Robot Client Online")
        while True:
            self.sync_with_server()

            if self.is_running and not self.is_paused and self.lines:
                if self.ptr >= len(self.lines):
                    self.log("✅ Protocol Finished"); self.is_running = False; continue

                raw_line = self.lines[self.ptr].strip()
                if not raw_line or raw_line.startswith(';'):
                    self.ptr += 1; continue

                # Prepare Packet
                packet = f"N{raw_line}*{self.seq_num}"
                self.log(f"➡️ TX: {packet}")
                
                if self.ser:
                    self.ser.reset_input_buffer() 
                    self.ser.write((packet + "\n").encode())

                    # --- WAIT LOOP ---
                    echo_matched = False
                    start_wait = time.time()
                    waiting = True
                    
                    while waiting:
                        if self.ser.in_waiting:
                            try:
                                resp = self.ser.readline().decode('utf-8', errors='ignore').strip()
                                if resp:
                                    if "RX from" not in resp: self.log(f"⬅️ RX: {resp}")

                                    # 1. Match Echo (Strict Sync)
                                    if "RX from" in resp and f"*{self.seq_num}" in resp:
                                        echo_matched = True
                                    
                                    # 2. Check Status
                                    if "PAUSE" in resp:
                                        self.log("⏸ Pico requested WAIT (Command Accepted)")
                                        self.is_paused = True
                                        
                                        # --- WAITE FIX: Mark as Done ---
                                        self.ptr += 1
                                        self.seq_num += 1
                                        waiting = False 
                                        
                                    elif "OK" in resp:
                                        if echo_matched:
                                            self.ptr += 1
                                            self.seq_num += 1
                                            waiting = False
                                            
                                    elif "ERR" in resp:
                                        self.log(f"❌ Hardware Error: {resp}")
                                        self.is_running = False
                                        waiting = False

                            except: pass

                        # Keep Sync Alive
                        if time.time() - start_wait > 0.5:
                            self.sync_with_server()
                            start_wait = time.time()
                            
                            # If USER Pause, stay on line. If User Stop, break.
                            if self.is_paused and waiting: break 
                            if not self.is_running: break
                            
                        time.sleep(0.005)
                else:
                    time.sleep(1); self.ptr += 1

            time.sleep(0.1)

if __name__ == "__main__":
    client = RobotClient()
    client.run() """
    
    
import requests
import serial
import time
import os
from datetime import datetime

# --- CONFIGURATION ---
SERVER_URL = "http://192.168.31.236:5000" 
LOCAL_DIR = "/home/lhr/recent_protocols"
LOG_DIR = "/home/lhr/logs"

for d in [LOCAL_DIR, LOG_DIR]: os.makedirs(d, exist_ok=True)

class RobotClient:
    def __init__(self):
        try:
            print("🔌 Connecting to Serial Port...")
            self.ser = serial.Serial('/dev/serial0', 115200, timeout=0.1)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            print("✅ Serial Connected.")
            
            # Flush "Ghost" data from Pico
            time.sleep(1)
            self.ser.write(b"\n\n")
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            
        except Exception as e:
            print(f"⚠️ Serial Port Failed: {e}")
            self.ser = None

        self.is_running = False
        self.is_paused = False
        self.current_filename = None
        self.current_session_log = None
        self.lines = []
        self.ptr = 0
        self.seq_num = 1 
        self.log_accumulator = []

    def start_new_log_session(self, filename):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_session_log = f"{filename}_{timestamp}.log"
        self.log(f"🚀 Started Protocol Session: {filename}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        print(entry)
        if self.current_session_log:
            try:
                with open(os.path.join(LOG_DIR, self.current_session_log), "a", encoding="utf-8") as f: 
                    f.write(entry + "\n")
            except: pass
        self.log_accumulator.append(entry)

    def sync_with_server(self):
        progress = 0
        current_line_txt = "Idle"
        if self.lines and self.ptr < len(self.lines):
            progress = int((self.ptr / len(self.lines)) * 100)
            current_line_txt = self.lines[self.ptr].strip()

        payload = {
            "file": self.current_filename,
            "line": current_line_txt,
            "progress": progress,
            "est": "N/A", 
            "logs": "\n".join(self.log_accumulator)
        }
        self.log_accumulator = []

        try:
            r = requests.post(f"{SERVER_URL}/pi/sync", json=payload, timeout=0.5)
            if r.status_code == 200:
                for cmd in r.json().get("commands", []):
                    self.handle_event(cmd)
        except: pass

    def handle_event(self, cmd):
        ev = cmd["event"]
        if ev == "PAUSE": self.is_paused = True; self.log("⏸ Paused (User)")
        elif ev == "RESUME": self.is_paused = False; self.log("▶ Resumed (User)")
        elif ev == "CLEAR": self.is_running = False; self.log("🧹 Cleared")
        elif ev == "NEW_FILE": self.download_file(cmd["filename"])
        
        # --- CALIBRATION & MANUAL MOVES ---
        elif ev == "SERIAL_SEND": 
            data = cmd["data"]
            self.log(f"🔧 Calibration/Manual: {data}")
            if self.ser: 
                self.ser.write((data + "\n").encode())

    def download_file(self, filename):
        self.log(f"📥 Downloading {filename}...")
        try:
            r = requests.get(f"{SERVER_URL}/download/{filename}")
            local_path = os.path.join(LOCAL_DIR, filename)
            with open(local_path, "wb") as f: f.write(r.content)
            with open(local_path, "r", encoding="utf-8") as f: self.lines = f.readlines()
            
            self.current_filename = filename
            self.ptr = 0
            self.seq_num = 1
            self.is_running = True
            self.is_paused = False
            self.start_new_log_session(filename)
            if self.ser: self.ser.reset_input_buffer()
                
        except Exception as e:
            self.log(f"❌ Error: {e}")

    def run(self):
        print("🚀 Pi Robot Client Online")
        while True:
            self.sync_with_server()

            # --- 1. IDLE/CALIBRATION LISTENER ---
            # Even if no file is running, we must read Serial to catch "OK" 
            # from manual calibration moves so the buffer stays clean.
            if not self.is_running and self.ser and self.ser.in_waiting:
                try:
                    resp = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if resp: self.log(f"⬅️ RX (Idle): {resp}")
                except: pass

            # --- 2. FILE EXECUTION LOOP ---
            if self.is_running and not self.is_paused and self.lines:
                if self.ptr >= len(self.lines):
                    self.log("✅ Protocol Finished"); self.is_running = False; continue

                raw_line = self.lines[self.ptr].strip()
                if not raw_line or raw_line.startswith(';'):
                    self.ptr += 1; continue

                # Prepare Packet
                packet = f"N{raw_line}*{self.seq_num}"
                self.log(f"➡️ TX: {packet}")
                
                if self.ser:
                    self.ser.reset_input_buffer() 
                    self.ser.write((packet + "\n").encode())

                    # --- WAIT LOOP ---
                    echo_matched = False
                    start_wait = time.time()
                    waiting = True
                    
                    while waiting:
                        if self.ser.in_waiting:
                            try:
                                resp = self.ser.readline().decode('utf-8', errors='ignore').strip()
                                if resp:
                                    # Log everything (Filtering echo to reduce noise)
                                    if "RX from" not in resp: self.log(f"⬅️ RX: {resp}")

                                    # Match Sequence Echo
                                    if "RX from" in resp and f"*{self.seq_num}" in resp:
                                        echo_matched = True
                                    
                                    # --- CHECK STATUS ---
                                    if "PAUSE" in resp:  # <--- UPDATED FROM WAITE
                                        self.log("⏸ Pico requested PAUSE (User Action Required)")
                                        self.is_paused = True
                                        
                                        # It is treated as DONE so resume moves to next line
                                        self.ptr += 1
                                        self.seq_num += 1
                                        waiting = False 
                                        
                                    elif "OK" in resp:
                                        if echo_matched:
                                            self.ptr += 1
                                            self.seq_num += 1
                                            waiting = False
                                            
                                    elif "ERR" in resp:
                                        self.log(f"❌ Hardware Error: {resp}")
                                        self.is_running = False
                                        waiting = False

                            except: pass

                        # Keep Sync Alive
                        if time.time() - start_wait > 0.5:
                            self.sync_with_server()
                            start_wait = time.time()
                            if self.is_paused and waiting: break 
                            if not self.is_running: break
                            
                        time.sleep(0.005)
                else:
                    time.sleep(1); self.ptr += 1

            time.sleep(0.1)

if __name__ == "__main__":
    client = RobotClient()
    client.run()