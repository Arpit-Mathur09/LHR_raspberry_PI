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
DIR_RECENT = os.path.join(BASE_DIR, "recent_protocols")
DIR_TEST = os.path.join(BASE_DIR, "test_protocols")
LOG_DIR = os.path.join(BASE_DIR, "logs")

for d in [DIR_RECENT, DIR_TEST, LOG_DIR]: os.makedirs(d, exist_ok=True)

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
            # SERVER sent this, so we MUST download it
            self.command_queue.put(("DOWNLOAD_AND_RUN", cmd["filename"]))
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

    # --- NEW: LOCAL LOAD LOGIC (Offline Safe) ---
    def load_local_protocol(self, filename):
        self.log(f"📂 Loading Local File: {filename}")
        
        # 1. Search in Recent, then Test
        target_path = None
        path_recent = os.path.join(DIR_RECENT, filename)
        path_test = os.path.join(DIR_TEST, filename)
        
        if os.path.exists(path_recent):
            target_path = path_recent
        elif os.path.exists(path_test):
            target_path = path_test
            
        if not target_path:
            self.log(f"❌ File not found locally: {filename}")
            self.state["error_msg"] = f"File not found: {filename}"
            return

        # 2. Read & Parse
        try:
            with open(target_path, "r", encoding="utf-8") as f: 
                raw_lines = f.readlines()
            
            self.protocol_steps = self.parse_gcode_file(raw_lines)
            self.state["filename"] = filename
            self.ptr = 0
            self.seq_num = 1
            self.is_running = True
            self.is_paused = False
            self.state["status"] = "Running"
            
            self.state["stop_reason"] = None
            self.state["pause_reason"] = None
            self.state["error_msg"] = None
            self.state["completed"] = False
            self.start_time = time.time()
            self.smoothed_seconds = 0
            self.state["est"] = "Calculating..."
            
            GPIO.output(self.PIN_PAUSE, 0)
            self.start_new_log_session(filename)
            if self.ser: self.ser.reset_input_buffer()
            
        except Exception as e:
            self.log(f"❌ Read Error: {e}")
            self.state["error_msg"] = "Failed to read file"

    # --- NEW: DOWNLOAD LOGIC (Server Only) ---
    def download_protocol(self, filename):
        self.log(f"📥 Downloading from Server: {filename}...")
        try:
            local_path = os.path.join(DIR_RECENT, filename)
            url = f"{SERVER_URL}/download/{filename}"
            r = requests.get(url, timeout=3)
            
            if r.status_code == 200:
                with open(local_path, "wb") as f: 
                    f.write(r.content)
                self.log("✅ Download Complete")
                # After download, load it locally
                self.load_local_protocol(filename)
            else:
                self.log(f"❌ Server Error: {r.status_code}")
        except Exception as e:
            self.log(f"❌ Download Failed: {e}")

    def ui_send_gcode(self, gcode): self.command_queue.put(("MANUAL", gcode))
    
    # UI Calls this -> Puts "LOAD_LOCAL" in queue
    def ui_load_and_run(self, filename): self.command_queue.put(("LOAD_LOCAL", filename))
    
    def ui_pause_resume(self): self.command_queue.put(("TOGGLE_PAUSE", None))
    def ui_stop(self): self.command_queue.put(("STOP", None))
    
    def ui_ack_stop(self): 
        self.state["stop_reason"] = None 
        self.state["completed"] = False
        self.state["filename"] = "None"
        self.state["status"] = "Idle"
        self.state["current_line"] = "Ready"
        self.state["current_desc"] = ""
        self.state["progress"] = 0
        self.state["est"] = "--:--:--:--"
    
    def ui_ack_error(self):
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
                    
                    # --- LOCAL LOAD (UI triggered) ---
                    elif cmd_type == "LOAD_LOCAL": 
                        self.load_local_protocol(data)
                        waiting_for_response = False

                    # --- DOWNLOAD (Server triggered) ---
                    elif cmd_type == "DOWNLOAD_AND_RUN":
                        self.download_protocol(data)
                        waiting_for_response = False
                    
                    elif cmd_type == "STOP" or cmd_type == "REMOTE_STOP":
                        source = "Remote" if cmd_type == "REMOTE_STOP" else "UI"
                        self.state["stop_reason"] = source 
                        self.is_running = False
                        self.state["status"] = f"Stopped ({source})"
                        self.state["progress"] = 0
                        self.state["est"] = "--:--:--:--"
                        self.state["current_line"] = "Ready" 
                        self.state["current_desc"] = ""
                        self.expect_reset = True 
                        waiting_for_response = False
                        self.log(f"🛑 STOPPED ({source})")
                        self.hard_reset_pico()

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