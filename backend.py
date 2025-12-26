""" import requests
import serial
import time
import os
import threading
import queue
from datetime import datetime

# --- CONFIGURATION ---
SERVER_URL = "http://192.168.31.236:5000" 
LOCAL_DIR = "/home/lhr/Robot_Client/recent_protocols"
LOG_DIR = "/home/lhr/Robot_Client/logs"

for d in [LOCAL_DIR, LOG_DIR]: os.makedirs(d, exist_ok=True)

class RobotClient:
    def __init__(self):
        # --- 1. SHARED STATE FOR UI (Read-Only for UI) ---
        self.state = {
            "status": "Idle",       
            "filename": "None",
            "progress": 0,
            "current_line": "Ready",
            "logs": [],             
            "connection": "Offline"
        }

        # --- 2. COMMAND QUEUE (UI sends commands here) ---
        self.command_queue = queue.Queue()

        # --- 3. HARDWARE SETUP (Your Real Logic) ---
        try:
            print("🔌 Connecting to Serial Port...")
            self.ser = serial.Serial('/dev/serial0', 115200, timeout=0.1)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.state["connection"] = "Connected"
            print("✅ Serial Connected.")
            
            # Flush "Ghost" data from Pico
            time.sleep(1)
            self.ser.write(b"\n\n")
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            
        except Exception as e:
            print(f"⚠️ Serial Port Failed: {e}")
            self.state["connection"] = "Error"
            self.ser = None

        # --- Internal Variables ---
        self.is_running = False
        self.is_paused = False
        self.current_filename = None
        self.current_session_log = None
        self.lines = []
        self.ptr = 0
        self.seq_num = 1 
        self.log_accumulator = []

    # --- UI INTERFACE METHODS (Called by Main Thread) ---
    def ui_send_gcode(self, gcode):
        self.command_queue.put(("MANUAL", gcode))

    def ui_load_and_run(self, filename):
        self.command_queue.put(("LOAD", filename))

    def ui_pause_resume(self):
        self.command_queue.put(("TOGGLE_PAUSE", None))

    def ui_stop(self):
        self.command_queue.put(("STOP", None))

    def start(self):
       
        t = threading.Thread(target=self._run_loop, daemon=True)
        t.start()

    # --- INTERNAL LOGIC ---
    def start_new_log_session(self, filename):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_session_log = f"{filename}_{timestamp}.log"
        self.log(f"🚀 Started Protocol Session: {filename}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        print(entry)
        
        # Update UI Shared State
        self.state["logs"].append(entry)
        if len(self.state["logs"]) > 5: self.state["logs"].pop(0)
        self.state["current_line"] = msg 

        # Write to File
        if self.current_session_log:
            try:
                with open(os.path.join(LOG_DIR, self.current_session_log), "a", encoding="utf-8") as f: 
                    f.write(entry + "\n")
            except: pass
        self.log_accumulator.append(entry)

    def sync_with_server(self):
        # Calculate Progress
        progress = 0
        current_line_txt = "Idle"
        if self.lines and self.ptr < len(self.lines):
            progress = int((self.ptr / len(self.lines)) * 100)
            current_line_txt = self.lines[self.ptr].strip()
            self.state["progress"] = progress # Update UI

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
                    self.handle_server_event(cmd)
        except: pass

    def handle_server_event(self, cmd):
        ev = cmd["event"]
        if ev == "PAUSE": 
            self.is_paused = True; 
            self.state["status"] = "Paused"
            self.log("⏸ Paused (Remote)")
        elif ev == "RESUME": 
            self.is_paused = False; 
            self.state["status"] = "Running"
            self.log("▶ Resumed (Remote)")
        elif ev == "CLEAR": 
            self.is_running = False; 
            self.state["status"] = "Idle"
            self.log("🧹 Cleared (Remote)")
        elif ev == "NEW_FILE": 
            self.download_file(cmd["filename"])
        elif ev == "SERIAL_SEND": 
            data = cmd["data"]
            self.log(f"🔧 Remote Manual: {data}")
            if self.ser: self.ser.write((data + "\n").encode())

    def download_file(self, filename):
        self.log(f"📥 Downloading {filename}...")
        try:
            r = requests.get(f"{SERVER_URL}/download/{filename}")
            local_path = os.path.join(LOCAL_DIR, filename)
            with open(local_path, "wb") as f: f.write(r.content)
            with open(local_path, "r", encoding="utf-8") as f: self.lines = f.readlines()
            
            self.current_filename = filename
            self.state["filename"] = filename
            self.ptr = 0
            self.seq_num = 1
            self.is_running = True
            self.is_paused = False
            self.state["status"] = "Running"
            self.start_new_log_session(filename)
            if self.ser: self.ser.reset_input_buffer()
                
        except Exception as e:
            self.log(f"❌ Download Error: {e}")

    # --- MAIN LOOP (Runs in Background Thread) ---
    def _run_loop(self):
        print("🚀 Backend Thread Active")
        while True:
            # 1. PROCESS UI QUEUE (Non-blocking)
            try:
                while not self.command_queue.empty():
                    cmd_type, data = self.command_queue.get_nowait()
                    
                    if cmd_type == "MANUAL":
                        if self.ser:
                            self.log(f"🔧 UI Manual: {data}")
                            self.ser.write((data + "\n").encode())
                    
                    elif cmd_type == "LOAD":
                        self.download_file(data)

                    elif cmd_type == "TOGGLE_PAUSE":
                        self.is_paused = not self.is_paused
                        status = "Paused" if self.is_paused else "Running"
                        self.state["status"] = status
                        self.log(f"⏯ {status} (UI)")

                    elif cmd_type == "STOP":
                        self.is_running = False
                        self.state["status"] = "Idle"
                        self.log("🛑 Stopped (UI)")
            except: pass

            # 2. SYNC SERVER
            self.sync_with_server()

            # 3. IDLE LISTENER (For Calibration/Manual Moves)
            if not self.is_running and self.ser and self.ser.in_waiting:
                try:
                    resp = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if resp: self.log(f"⬅️ RX (Idle): {resp}")
                except: pass

            # 4. FILE EXECUTION (Your Original Logic)
            if self.is_running and not self.is_paused and self.lines:
                if self.ptr >= len(self.lines):
                    self.log("✅ Protocol Finished")
                    self.is_running = False
                    self.state["status"] = "Done"
                    continue

                raw_line = self.lines[self.ptr].strip()
                if not raw_line or raw_line.startswith(';'):
                    self.ptr += 1
                    continue

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
                        # A. Check UI Queue Interrupts (Allow STOP during move)
                        if not self.command_queue.empty():
                            try:
                                cmd, _ = self.command_queue.get_nowait()
                                if cmd == "STOP":
                                    self.is_running = False; waiting = False; self.log("🛑 STOP Interrupted Move")
                                elif cmd == "TOGGLE_PAUSE":
                                    self.is_paused = True; self.log("⏸ Paused during move")
                            except: pass

                        if not waiting: break 

                        # B. Check Serial (Your Exact Logic)
                        if self.ser.in_waiting:
                            try:
                                resp = self.ser.readline().decode('utf-8', errors='ignore').strip()
                                if resp:
                                    if "RX from" not in resp: self.log(f"⬅️ RX: {resp}")
                                    if "RX from" in resp and f"*{self.seq_num}" in resp: echo_matched = True
                                    
                                    if "PAUSE" in resp:
                                        self.log("⏸ Pico requested PAUSE")
                                        self.is_paused = True
                                        self.ptr += 1; self.seq_num += 1; waiting = False 
                                        
                                    elif "OK" in resp:
                                        if echo_matched:
                                            self.ptr += 1; self.seq_num += 1; waiting = False
                                            
                                    elif "ERR" in resp:
                                        self.log(f"❌ Hardware Error: {resp}")
                                        self.is_running = False; waiting = False
                            except: pass

                        # C. Keep Sync Alive
                        if time.time() - start_wait > 0.5:
                            self.sync_with_server()
                            start_wait = time.time()
                            if self.is_paused and waiting: break 
                            if not self.is_running: break
                            
                        time.sleep(0.005)
                else:
                    # Fallback if Serial Failed
                    time.sleep(1); self.ptr += 1

            time.sleep(0.1) """

""" import requests
import serial
import time
import os
import threading
import queue
from datetime import datetime
import RPi.GPIO as GPIO  # Make sure to install: pip install RPi.GPIO
# --- CONFIGURATION ---
SERVER_URL = "http://192.168.31.236:5000" 
BASE_DIR = "/home/lhr/Robot_Client"
LOCAL_DIR = os.path.join(BASE_DIR, "recent_protocols")
LOG_DIR = os.path.join(BASE_DIR, "logs")

for d in [LOCAL_DIR, LOG_DIR]: os.makedirs(d, exist_ok=True)

class RobotClient:
    def __init__(self):
        # SHARED STATE
        self.state = {
            "status": "Idle",       
            "filename": "None",
            "progress": 0,
            "current_line": "Ready",
            "current_desc": "",       
            "logs": [],             
            "est": "--:--:--:--",
            "connection": "Offline"
        }

        self.command_queue = queue.Queue()
        
        # TIME TRACKING
        self.start_time = None
        self.smoothed_seconds = 0

        time.sleep(1)  # Initial Delay
 
        # --- 1. SETUP HARDWARE RESET PIN ---
        self.RESET_PIN = 17  
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.RESET_PIN, GPIO.OUT)
        
        # --- 2. PERFORM HARD RESET ---
        print("⚡ Hard Resetting Pico...")
        GPIO.output(self.RESET_PIN, 0)  # Pull RUN Low (OFF)
        time.sleep(0.2)                 # Wait
        GPIO.output(self.RESET_PIN, 1)  # Pull RUN High (ON)
        time.sleep(1)                 # Wait for Pico to boot fully
        
        # --- 3. CONNECT SERIAL ---
        try:
            # Use serial0 for GPIO UART
            self.ser = serial.Serial('/dev/serial0', 115200, timeout=0.1)
            time.sleep(0)
            # Flush any boot garbage
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            # Handshake
            self.state["connection"] = "Connected"
            self.ser.write(b"\n\n") 
            time.sleep(2)
            print("✅ Serial Connected (GPIO).")
            
        except Exception as e:
            print(f"⚠️ Serial Error: {e}")
            self.state["connection"] = "Error"

        self.is_running = False
        self.is_paused = False
        self.protocol_steps = []  
        self.ptr = 0
        self.seq_num = 1 
        self.log_accumulator = []
        self.current_filename = None
        self.current_session_log = None

    def format_time_dhms(self, seconds):
        if seconds <= 0: return "00:00:00:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        return f"{d:02}:{h:02}:{m:02}:{s:02}"

    def calculate_estimate(self):
        if not self.is_running or self.is_paused or not self.start_time:
            return

        total = len(self.protocol_steps)
        if total == 0: return
        
        progress_pct = (self.ptr / total) * 100
        self.state["progress"] = int(progress_pct)

        if progress_pct > 1:
            elapsed = time.time() - self.start_time
            raw_remaining = (elapsed / progress_pct) * (100 - progress_pct)
            
            if self.smoothed_seconds == 0: self.smoothed_seconds = raw_remaining
            else: self.smoothed_seconds = (0.99 * self.smoothed_seconds) + (0.01 * raw_remaining)
            
            self.state["est"] = self.format_time_dhms(self.smoothed_seconds)
        else:
            self.state["est"] = "Calculating..."

    def start_new_log_session(self, filename):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_session_log = f"{filename}_{timestamp}.log"
        self.log(f"🚀 Started Protocol: {filename}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        print(entry)
        
        # UI Log
        self.state["logs"].append(entry)
        if len(self.state["logs"]) > 5: self.state["logs"].pop(0)
        
        # Server Accumulator
        self.log_accumulator.append(entry)

        # File Log
        if self.current_session_log:
            try:
                with open(os.path.join(LOG_DIR, self.current_session_log), "a", encoding="utf-8") as f: 
                    f.write(entry + "\n")
            except: pass

    # --- SERVER SYNC ---
    def sync_with_server(self):
        prog = self.state["progress"]
        line_txt = self.state["current_line"]
        if self.state["current_desc"]:
            line_txt += f" ({self.state['current_desc']})"

        payload = {
            "file": self.state["filename"],
            "line": line_txt,
            "progress": prog,
            "est": self.state["est"],
            "status": self.state["status"],
            "logs": "\n".join(self.log_accumulator)
        }
        self.log_accumulator = [] 

        try:
            r = requests.post(f"{SERVER_URL}/pi/sync", json=payload, timeout=0.5)
            if r.status_code == 200:
                commands = r.json().get("commands", [])
                for cmd in commands:
                    self.handle_server_command(cmd)
        except: pass

    def handle_server_command(self, cmd):
        ev = cmd["event"]
        if ev == "PAUSE": 
            self.is_paused = True
            self.state["status"] = "Paused"
            self.log("⏸ Paused (Remote)")
        elif ev == "RESUME": 
            self.is_paused = False
            self.state["status"] = "Running"
            self.log("▶ Resumed (Remote)")
        elif ev == "CLEAR": 
            self.is_running = False
            self.state["status"] = "Idle"
            self.log("🛑 Stopped (Remote)")
        elif ev == "NEW_FILE": 
            self.download_file(cmd["filename"])
        elif ev == "SERIAL_SEND":
            if self.ser: self.ser.write((cmd["data"] + "\n").encode())

    # --- FILE PARSING ---
    def parse_gcode_file(self, lines):
        steps = []
        pending_desc = ""
        for line in lines:
            raw = line.strip()
            if not raw: continue
            if raw.startswith(";"):
                pending_desc = raw.replace(";", "").strip()
            else:
                steps.append({"cmd": raw, "desc": pending_desc if pending_desc else ""})
                pending_desc = ""
        return steps

    def download_file(self, filename):
        self.log(f"📥 Loading {filename}...")
        try:
            local_path = os.path.join(LOCAL_DIR, filename)
            
            with open(local_path, "r", encoding="utf-8") as f: 
                raw_lines = f.readlines()
            
            self.protocol_steps = self.parse_gcode_file(raw_lines)
            self.state["filename"] = filename
            self.ptr = 0
            self.seq_num = 1
            self.is_running = True
            self.is_paused = False
            self.state["status"] = "Running"
            
            self.start_time = time.time()
            self.smoothed_seconds = 0
            self.state["est"] = "Calculating..."
            
            self.start_new_log_session(filename)
            if self.ser: self.ser.reset_input_buffer()
                
        except Exception as e:
            self.log(f"❌ Load Error: {e}")

    # --- UI COMMANDS ---
    def ui_send_gcode(self, gcode): self.command_queue.put(("MANUAL", gcode))
    def ui_load_and_run(self, filename): self.command_queue.put(("LOAD", filename))
    def ui_pause_resume(self): self.command_queue.put(("TOGGLE_PAUSE", None))
    def ui_stop(self): self.command_queue.put(("STOP", None))

    def start(self):
        t = threading.Thread(target=self._run_loop, daemon=True)
        t.start()

    # --- MAIN LOOP ---
    def _run_loop(self):
        last_sync = time.time()
        
        while True:
            self.calculate_estimate()
            
            if time.time() - last_sync > 0.5:
                self.sync_with_server()
                last_sync = time.time()
            try:
                # PROCESS UI COMMANDS
                while not self.command_queue.empty():
                    cmd_type, data = self.command_queue.get_nowait()
                    if cmd_type == "MANUAL" and self.ser: 
                        self.log(f"🔧 Manual TX: {data}")
                        self.ser.write((data + "\n").encode())
                    elif cmd_type == "LOAD": self.download_file(data)
                    elif cmd_type == "STOP": 
                        self.is_running = False
                        self.state["status"] = "Idle"
                        self.log("🛑 Stopped (UI)")
                    elif cmd_type == "TOGGLE_PAUSE": 
                        self.is_paused = not self.is_paused
                        if self.is_paused:
                            self.state["status"] = "Paused"
                            self.log("⏸ Paused (UI)")
                        else:
                            self.state["status"] = "Running"
                            self.log("▶ Resumed (UI)")
            except: pass

            if self.is_running and not self.is_paused and self.protocol_steps:
                if self.ptr >= len(self.protocol_steps):
                    self.log("✅ Done")
                    self.is_running = False
                    self.state["status"] = "Done"
                    self.state["progress"] = 100
                    self.state["est"] = "00:00:00:00"
                    continue

                step = self.protocol_steps[self.ptr]
                gcode_cmd = step["cmd"]
                
                self.state["current_line"] = gcode_cmd
                self.state["current_desc"] = step["desc"]
                self.state["status"] = "Running"

                packet = f"N{gcode_cmd}*{self.seq_num}"
                self.log(f"TX: {packet}") 

                if self.ser:
                    self.ser.reset_input_buffer()
                    self.ser.write((packet + "\n").encode())

                    waiting = True
                    while waiting:
                        # Allow UI Stop/Pause Interrupts
                        if not self.command_queue.empty(): break 
                        
                        self.calculate_estimate()
                        if time.time() - last_sync > 0.5:
                            self.sync_with_server()
                            last_sync = time.time()

                        if self.ser.in_waiting:
                            try:
                                resp = self.ser.readline().decode().strip()
                                if resp: self.log(f"RX: {resp}")

                                if "PAUSE" in resp:
                                    self.is_paused = True
                                    self.state["status"] = "Paused"
                                    self.log("⏸ Pico Paused")
                                    self.ptr += 1; self.seq_num += 1
                                    waiting = False
                                elif "OK" in resp:
                                    self.ptr += 1; self.seq_num += 1
                                    waiting = False
                                elif "ERR" in resp:
                                    self.is_running = False; waiting = False
                            except: pass
                        time.sleep(0.005)
                else:
                    time.sleep(0.5); self.ptr += 1
            
            time.sleep(0.05) """
   
#Reboot detection + UARt 4 rx 5 tx + play and resume sync and working pause/resume via GPIO          
""" import requests
import serial
import time
import os
import threading
import queue
import RPi.GPIO as GPIO
from datetime import datetime

# --- CONFIGURATION ---
SERVER_URL = "http://192.168.31.236:5000" 
BASE_DIR = "/home/lhr/Robot_Client"
LOCAL_DIR = os.path.join(BASE_DIR, "recent_protocols")
LOG_DIR = os.path.join(BASE_DIR, "logs")

for d in [LOCAL_DIR, LOG_DIR]: os.makedirs(d, exist_ok=True)

class RobotClient:
    def __init__(self):
        self.state = {
            "status": "Idle", "filename": "None", "progress": 0,
            "current_line": "Ready", "current_desc": "", "logs": [],             
            "est": "--:--:--:--", "connection": "Offline"
        }
        self.command_queue = queue.Queue()
        self.start_time = None
        self.smoothed_seconds = 0
        self.log_accumulator = []
        self.current_session_log = None

        # --- GPIO SETUP ---
        self.PIN_RESET = 17   # Connected to Pico RUN
        self.PIN_PAUSE = 27   # Connected to Pico GP11
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        
        # Setup Pins
        GPIO.setup(self.PIN_RESET, GPIO.OUT)
        GPIO.setup(self.PIN_PAUSE, GPIO.OUT)
        
        # Default States
        GPIO.output(self.PIN_PAUSE, 0) # LOW = Running
        
        # Perform Initial Reset
        self.hard_reset_pico()

        # --- SERIAL CONNECTION ---
        try:
            print("🔌 Connecting to Serial (GPIO)...")
            self.ser = serial.Serial('/dev/ttyAMA3', 115200, timeout=0.1)
            self.ser.reset_input_buffer()
            self.state["connection"] = "Connected"
            print("✅ Serial Connected.")
        except Exception as e:
            print(f"⚠️ Serial Error: {e}")
            self.state["connection"] = "Error"
            self.ser = None

        self.is_running = False
        self.is_paused = False
        self.protocol_steps = []  
        self.ptr = 0
        self.seq_num = 1 

    def hard_reset_pico(self):
        # Toggles GPIO 17 to reset the Pico
        print("⚡ Hard Resetting Pico...")
        GPIO.output(self.PIN_RESET, 0) # Pull LOW (Reset)
        time.sleep(0.2)
        GPIO.output(self.PIN_RESET, 1) # Pull HIGH (Run)
        time.sleep(1.5) # Wait for boot

    def calculate_estimate(self):
        if not self.is_running or self.is_paused or not self.start_time: return
        total = len(self.protocol_steps)
        if total == 0: return
        progress_pct = (self.ptr / total) * 100
        self.state["progress"] = int(progress_pct)
        if progress_pct > 1:
            elapsed = time.time() - self.start_time
            raw_remaining = (elapsed / progress_pct) * (100 - progress_pct)
            if self.smoothed_seconds == 0: self.smoothed_seconds = raw_remaining
            else: self.smoothed_seconds = (0.99 * self.smoothed_seconds) + (0.01 * raw_remaining)
            self.state["est"] = self.format_time_dhms(self.smoothed_seconds)
        else:
            self.state["est"] = "Calculating..."

    def format_time_dhms(self, seconds):
        if seconds <= 0: return "00:00:00:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        return f"{d:02}:{h:02}:{m:02}:{s:02}"

    def start_new_log_session(self, filename):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_session_log = f"{filename}_{timestamp}.log"
        self.log(f"🚀 Started Protocol: {filename}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        print(entry)
        self.state["logs"].append(entry)
        if len(self.state["logs"]) > 5: self.state["logs"].pop(0)
        self.log_accumulator.append(entry)
        if self.current_session_log:
            try:
                with open(os.path.join(LOG_DIR, self.current_session_log), "a", encoding="utf-8") as f: 
                    f.write(entry + "\n")
            except: pass

    def sync_with_server(self):
        line_txt = self.state["current_line"]
        if self.state["current_desc"]: line_txt += f" ({self.state['current_desc']})"
        payload = {
            "file": self.state["filename"], "line": line_txt,
            "progress": self.state["progress"], "est": self.state["est"],
            "status": self.state["status"], "logs": "\n".join(self.log_accumulator)
        }
        self.log_accumulator = [] 
        try:
            r = requests.post(f"{SERVER_URL}/pi/sync", json=payload, timeout=0.5)
            if r.status_code == 200:
                for cmd in r.json().get("commands", []): self.handle_server_command(cmd)
        except: pass

    def handle_server_command(self, cmd):
        ev = cmd["event"]
        if ev == "PAUSE":
            self.state["status"] = "Paused"
            GPIO.output(self.PIN_PAUSE, 1) # HIGH
            self.log("⏸ PAUSE (Remote)")
        elif ev == "RESUME": 
            self.state["status"] = "Running"
            GPIO.output(self.PIN_PAUSE, 0) # LOW
            self.log("▶ RESUME (Remote)")
                            
        elif ev == "CLEAR": self.ui_stop()
        elif ev == "NEW_FILE": self.download_file(cmd["filename"])

    def parse_gcode_file(self, lines):
        steps = []
        pending_desc = ""
        for line in lines:
            raw = line.strip()
            if not raw: continue
            if raw.startswith(";"): pending_desc = raw.replace(";", "").strip()
            else:
                steps.append({"cmd": raw, "desc": pending_desc if pending_desc else ""})
                pending_desc = ""
        return steps

    def download_file(self, filename):
        self.log(f"📥 Loading {filename}...")
        try:
            local_path = os.path.join(LOCAL_DIR, filename)
            with open(local_path, "r", encoding="utf-8") as f: raw_lines = f.readlines()
            self.protocol_steps = self.parse_gcode_file(raw_lines)
            self.state["filename"] = filename
            self.ptr = 0; self.seq_num = 1
            self.is_running = True; self.is_paused = False
            self.state["status"] = "Running"
            self.start_time = time.time(); self.smoothed_seconds = 0; self.state["est"] = "Calculating..."
            
            # Reset hardware state
            GPIO.output(self.PIN_PAUSE, 0)
            self.start_new_log_session(filename)
            if self.ser: self.ser.reset_input_buffer()
        except Exception as e: self.log(f"❌ Load Error: {e}")

    def ui_send_gcode(self, gcode): self.command_queue.put(("MANUAL", gcode))
    def ui_load_and_run(self, filename): self.command_queue.put(("LOAD", filename))
    def ui_pause_resume(self): self.command_queue.put(("TOGGLE_PAUSE", None))
    def ui_stop(self): self.command_queue.put(("STOP", None))

    def start(self):
        t = threading.Thread(target=self._run_loop, daemon=True)
        t.start()

    def _run_loop(self):
        last_sync = time.time()
        waiting_for_response = False
        
        while True:
            # 1. Update Time Estimate & Sync Server
            self.calculate_estimate()
            if time.time() - last_sync > 0.5:
                self.sync_with_server(); last_sync = time.time()

            # 2. Handle UI Commands (Pause/Stop/Load)
            try:
                while not self.command_queue.empty():
                    cmd_type, data = self.command_queue.get_nowait()
                    if cmd_type == "MANUAL" and self.ser: 
                        self.log(f"🔧 Manual TX: {data}")
                        self.ser.write((data + "\n").encode())
                    elif cmd_type == "LOAD": 
                        self.download_file(data)
                        waiting_for_response = False # New file, reset waiting
                    
                    elif cmd_type == "STOP": 
                        self.hard_reset_pico()
                        self.is_running = False
                        self.state["status"] = "Idle"
                        waiting_for_response = False
                        self.log("🛑 STOPPED")

                    elif cmd_type == "TOGGLE_PAUSE": 
                        self.is_paused = not self.is_paused
                        if self.is_paused:
                            self.state["status"] = "Paused"
                            GPIO.output(self.PIN_PAUSE, 1) # HIGH
                            self.log("⏸ PAUSE (UI)")
                        else:
                            self.state["status"] = "Running"
                            GPIO.output(self.PIN_PAUSE, 0) # LOW
                            self.log("▶ RESUME (UI)")
            except: pass

            # 3. Read Serial (Listen for OK or E-Stop)
            if self.ser and self.ser.in_waiting:
                try:
                    resp = self.ser.readline().decode().strip()
                    if resp: self.log(f"RX: {resp}")

                    # Emergency Stop Check
                    if "Initialized" in resp and self.is_running:
                        self.log("🚨 E-STOP DETECTED (Pico Reset)")
                        self.is_running = False
                        self.state["status"] = "Error"
                        waiting_for_response = False
                    
                    # Normal Protocol Response
                    if self.is_running and not self.is_paused:
                        if "PAUSE" in resp:
                            self.is_paused = True
                            self.state["status"] = "Paused"
                            self.log("⏸ Pico Paused")
                            self.ptr += 1; self.seq_num += 1
                            waiting_for_response = False 
                        if "OK" in resp: 
                            self.ptr += 1
                            self.seq_num += 1
                            waiting_for_response = False # <--- SUCCESS: Clear flag, allow next send
                        elif "ERR" in resp: 
                            self.log(f"❌ Critical Error: {resp}")
                            self.is_running = False
                            waiting_for_response = False
                except: pass

            # 4. Send Next Command (ONLY if not waiting)
            if self.is_running and not self.is_paused and self.protocol_steps:
                if self.ptr < len(self.protocol_steps):
                    
                    # BLOCKING LOGIC: Only send if we are NOT waiting
                    if not waiting_for_response:
                        step = self.protocol_steps[self.ptr]
                        self.state["current_line"] = step["cmd"]
                        self.state["current_desc"] = step["desc"]
                        self.state["status"] = "Running"
                        
                        packet = f"N{step['cmd']}*{self.seq_num}"
                        self.log(f"TX: {packet}")
                        self.ser.write((packet + "\n").encode())
                        
                        waiting_for_response = True  # <--- LOCK: Wait indefinitely for OK
                else:
                    self.log("✅ Done"); self.is_running = False
                    self.state["status"] = "Done"; self.state["progress"] = 100
            
            time.sleep(0.005) # Fast cycle """
import requests
import serial
import time
import os
import threading
import queue
import RPi.GPIO as GPIO
from datetime import datetime

# --- CONFIGURATION ---
SERVER_URL = "http://192.168.31.236:5000" 
BASE_DIR = "/home/lhr/Robot_Client"
LOCAL_DIR = os.path.join(BASE_DIR, "recent_protocols")
LOG_DIR = os.path.join(BASE_DIR, "logs")

for d in [LOCAL_DIR, LOG_DIR]: os.makedirs(d, exist_ok=True)

class RobotClient:
    def __init__(self):
        self.state = {
            "status": "Idle", "filename": "None", "progress": 0,
            "current_line": "Ready", "current_desc": "", "logs": [],             
            "est": "--:--:--:--", "connection": "Offline",
            "stop_reason": None, "pause_reason": None, "error_msg": None, "completed": False
        }
        self.command_queue = queue.Queue()
        self.start_time = None
        self.smoothed_seconds = 0
        self.log_accumulator = []
        self.current_session_log = None
        self.stop_source = None 
        self.server_connected = False
        self.expect_reset = False

        # --- GPIO SETUP ---
        self.PIN_RESET = 17   
        self.PIN_PAUSE = 27   
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PIN_RESET, GPIO.OUT)
        GPIO.setup(self.PIN_PAUSE, GPIO.OUT)
        GPIO.output(self.PIN_PAUSE, 0)
        self.hard_reset_pico()

        # --- SERIAL ---
        try:
            print("🔌 Connecting to Serial...")
            self.ser = serial.Serial('/dev/ttyAMA3', 115200, timeout=0.1)
            self.ser.reset_input_buffer()
            self.state["connection"] = "Connected"
        except Exception as e:
            print(f"⚠️ Serial Error: {e}")
            self.state["connection"] = "Error"
            self.ser = None

        self.is_running = False
        self.is_paused = False
        self.protocol_steps = []  
        self.ptr = 0
        self.seq_num = 1 

    def hard_reset_pico(self):
        print("⚡ Hard Resetting Pico...")
        GPIO.output(self.PIN_RESET, 0)
        time.sleep(0.2)
        GPIO.output(self.PIN_RESET, 1)
        time.sleep(1.5)

    def calculate_estimate(self):
        if not self.is_running or self.is_paused or not self.start_time: return
        total = len(self.protocol_steps)
        if total == 0: return
        progress_pct = (self.ptr / total) * 100
        self.state["progress"] = int(progress_pct)
        if progress_pct > 1:
            elapsed = time.time() - self.start_time
            raw_remaining = (elapsed / progress_pct) * (100 - progress_pct)
            if self.smoothed_seconds == 0: self.smoothed_seconds = raw_remaining
            else: self.smoothed_seconds = (0.99 * self.smoothed_seconds) + (0.01 * raw_remaining)
            self.state["est"] = self.format_time_dhms(self.smoothed_seconds)
        else:
            self.state["est"] = "Calculating..."

    def format_time_dhms(self, seconds):
        if seconds <= 0: return "00:00:00:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        return f"{d:02}:{h:02}:{m:02}:{s:02}"

    def start_new_log_session(self, filename):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_session_log = f"{filename}_{timestamp}.log"
        self.log(f"🚀 Started Protocol: {filename}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        print(entry)
        self.state["logs"].append(entry)
        if len(self.state["logs"]) > 5: self.state["logs"].pop(0)
        self.log_accumulator.append(entry)
        if self.current_session_log:
            try:
                with open(os.path.join(LOG_DIR, self.current_session_log), "a", encoding="utf-8") as f: 
                    f.write(entry + "\n")
            except: pass

    def sync_with_server(self):
        line_txt = self.state["current_line"]
        if self.state["current_desc"]: line_txt += f" ({self.state['current_desc']})"
        payload = {
            "file": self.state["filename"], "line": line_txt,
            "progress": self.state["progress"], "est": self.state["est"],
            "status": self.state["status"], "logs": "\n".join(self.log_accumulator)
        }
        self.log_accumulator = [] 
        try:
            r = requests.post(f"{SERVER_URL}/pi/sync", json=payload, timeout=0.5)
            if r.status_code == 200:
                if not self.server_connected:
                    self.log("✅ Connected to Server")
                    self.server_connected = True
                for cmd in r.json().get("commands", []): self.handle_server_command(cmd)
        except: 
            if self.server_connected:
                self.log("⚠️ Lost connection to Server")
                self.server_connected = False
            pass

    def handle_server_command(self, cmd):
        ev = cmd["event"]
        if ev == "PAUSE":
            self.command_queue.put(("REMOTE_PAUSE", None))
        elif ev == "RESUME": 
            self.command_queue.put(("REMOTE_RESUME", None))
        elif ev == "CLEAR": 
            self.command_queue.put(("REMOTE_STOP", None))
        elif ev == "NEW_FILE": 
            self.download_file(cmd["filename"])
        elif ev == "SERIAL_SEND":
            if self.ser:
                self.log(f"TX (Remote): {cmd['data']}")
                self.ser.write((cmd["data"] + "\n").encode())

    def parse_gcode_file(self, lines):
        steps = []
        pending_desc = ""
        for line in lines:
            raw = line.strip()
            if not raw: continue
            if raw.startswith(";"): pending_desc = raw.replace(";", "").strip()
            else:
                steps.append({"cmd": raw, "desc": pending_desc if pending_desc else ""})
                pending_desc = ""
        return steps

    def download_file(self, filename):
        self.log(f"📥 Downloading {filename}...")
        try:
            local_path = os.path.join(LOCAL_DIR, filename)
            url = f"{SERVER_URL}/download/{filename}"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                with open(local_path, "wb") as f: f.write(r.content)
            
            with open(local_path, "r", encoding="utf-8") as f: raw_lines = f.readlines()
            self.protocol_steps = self.parse_gcode_file(raw_lines)
            self.state["filename"] = filename
            self.ptr = 0; self.seq_num = 1
            self.is_running = True; self.is_paused = False
            self.state["status"] = "Running"
            
            self.state["stop_reason"] = None
            self.state["pause_reason"] = None
            self.state["error_msg"] = None
            self.state["completed"] = False
            self.start_time = time.time(); self.smoothed_seconds = 0; self.state["est"] = "Calculating..."
            
            GPIO.output(self.PIN_PAUSE, 0)
            self.start_new_log_session(filename)
            if self.ser: self.ser.reset_input_buffer()
        except Exception as e: self.log(f"❌ Load Error: {e}")

    def ui_send_gcode(self, gcode): self.command_queue.put(("MANUAL", gcode))
    def ui_load_and_run(self, filename): self.command_queue.put(("LOAD", filename))
    def ui_pause_resume(self): self.command_queue.put(("TOGGLE_PAUSE", None))
    def ui_stop(self): self.command_queue.put(("STOP", None))
    
    # --- UI ACKNOWLEDGEMENT (UPDATED: CLEARS EVERYTHING) ---
    def ui_ack_stop(self): 
        """Called when user clicks OK on Stop/Done popup. Resets all state variables."""
        self.state["stop_reason"] = None 
        self.state["completed"] = False
        self.state["filename"] = "None"
        self.state["status"] = "Idle"
        self.state["current_line"] = "Ready"
        self.state["current_desc"] = ""
        self.state["progress"] = 0
        self.state["est"] = "--:--:--:--"
    
    def ui_ack_error(self):
        """Called when user clicks OK on Error popup."""
        self.state["error_msg"] = None
        self.state["filename"] = "None"
        self.state["status"] = "Idle"
        self.state["current_line"] = "Ready"
        self.state["current_desc"] = ""
        self.state["progress"] = 0
        self.state["est"] = "--:--:--:--"

    def start(self):
        t = threading.Thread(target=self._run_loop, daemon=True)
        t.start()

    def _run_loop(self):
        last_sync = time.time()
        waiting_for_response = False
        
        while True:
            self.calculate_estimate()
            if time.time() - last_sync > 0.5:
                self.sync_with_server(); last_sync = time.time()

            try:
                while not self.command_queue.empty():
                    cmd_type, data = self.command_queue.get_nowait()
                    
                    if cmd_type == "MANUAL" and self.ser: 
                        self.ser.write((data + "\n").encode())
                    
                    elif cmd_type == "LOAD": 
                        self.download_file(data)
                        waiting_for_response = False
                    
                    elif cmd_type == "STOP" or cmd_type == "REMOTE_STOP":
                        source = "Remote" if cmd_type == "REMOTE_STOP" else "UI"
                        self.state["stop_reason"] = source 
                        self.is_running = False
                        self.state["status"] = f"Stopped ({source})"
                        
                        # FORCE RESET INTERNAL STATE
                        self.state["progress"] = 0
                        self.state["est"] = "--:--:--:--"
                        self.state["current_line"] = "Ready" 
                        self.state["current_desc"] = ""
                        
                        self.expect_reset = True 
                        waiting_for_response = False
                        self.log(f"🛑 STOPPED ({source})")
                        self.hard_reset_pico()

                    # --- PAUSE / RESUME LOGIC ---
                    elif cmd_type in ["TOGGLE_PAUSE", "REMOTE_PAUSE", "REMOTE_RESUME"]:
                        should_pause = False
                        if cmd_type == "REMOTE_PAUSE": should_pause = True
                        elif cmd_type == "REMOTE_RESUME": should_pause = False
                        else: should_pause = not self.is_paused 

                        self.is_paused = should_pause
                        
                        if self.is_paused:
                            reason = "Remote" if cmd_type == "REMOTE_PAUSE" else "UI"
                            self.state["pause_reason"] = reason
                            self.state["status"] = f"Paused ({reason})"
                            GPIO.output(self.PIN_PAUSE, 1) 
                            self.log(f"⏸ PAUSE ({reason})")
                        else:
                            source = "Remote" if cmd_type == "REMOTE_RESUME" else "UI"
                            if self.state["pause_reason"] == "Pico":
                                self.log(f"▶ RESUME ({source}) - Advancing Wait Command")
                                self.ptr += 1
                                self.seq_num += 1
                                waiting_for_response = False 
                            else:
                                self.log(f"▶ RESUME ({source})")
                            
                            self.state["status"] = "Running"
                            self.state["pause_reason"] = None 
                            GPIO.output(self.PIN_PAUSE, 0) 

            except: pass

            if self.ser and self.ser.in_waiting:
                try:
                    resp = self.ser.readline().decode().strip()
                    if resp: self.log(f"RX: {resp}")

                    if "Initialized" in resp:
                        if self.expect_reset:
                            self.log("✅ Reset Confirmed (Software)")
                            self.expect_reset = False
                        else: 
                            self.log("🚨 EMERGENCY STOP (Physical)")
                            self.is_running = False
                            self.state["status"] = "Error"
                            self.state["stop_reason"] = "Physical"
                            self.state["current_line"] = "E-STOP"
                            self.state["est"] = "HALTED"
                            waiting_for_response = False
                    
                    if "ERR" in resp:
                        parts = resp.split(":", 1) 
                        clean_err = parts[1].strip() if len(parts) > 1 else "Unknown Hardware Error"
                        self.log(f"❌ PICO ERROR: {clean_err}")
                        self.is_running = False
                        self.state["status"] = "Error"
                        self.state["error_msg"] = clean_err 
                        self.state["current_line"] = "Error"
                        self.state["current_desc"] = "Halted"
                        self.state["est"] = "ERROR"
                        waiting_for_response = False
                        self.expect_reset = True 
                        self.hard_reset_pico()

                    if self.is_running:
                        if "PAUSE" in resp:
                            self.is_paused = True
                            self.state["status"] = "Paused (Pico)"
                            self.state["pause_reason"] = "Pico"
                            self.log("⏸ Pico Paused (Wait Command)")
                            GPIO.output(self.PIN_PAUSE, 1) 
                        elif "OK" in resp: 
                            self.ptr += 1; self.seq_num += 1; waiting_for_response = False 
                except: pass

            if self.is_running and not self.is_paused and self.protocol_steps:
                if self.ptr < len(self.protocol_steps):
                    if not waiting_for_response:
                        step = self.protocol_steps[self.ptr]
                        self.state["current_line"] = step["cmd"]
                        self.state["current_desc"] = step["desc"]
                        self.state["status"] = "Running"
                        packet = f"N{step['cmd']}*{self.seq_num}"
                        self.log(f"TX: {packet}")
                        if self.ser:
                            self.ser.write((packet + "\n").encode())
                            waiting_for_response = True
                        else:
                            self.is_running = False
                else:
                    self.log("✅ Done"); self.is_running = False
                    self.state["status"] = "Done"; self.state["progress"] = 100
                    self.state["completed"] = True 
            
            time.sleep(0.005)