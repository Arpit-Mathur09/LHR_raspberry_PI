
import requests
import serial
import time
import os
import threading
import queue
import RPi.GPIO as GPIO
from datetime import datetime, timedelta
import subprocess
import glob


# --- ADD THESE IMPORTS AT TOP ---
import random 
# Try importing hardware libraries, fail gracefully if missing
try:
    import smbus2
    import board
    import neopixel # Requires: pip install rpi_ws281x adafruit-circuitpython-neopixel
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False

try:
    import bme280 # Requires: pip install RPi.bme280
except ImportError:
    bme280 = None
# --- CONFIGURATION ---
SERVER_URL = "http://192.168.31.236:5000" 
BASE_DIR = "/home/lhr/Robot_Client"
DIR_RECENT = os.path.join(BASE_DIR, "recent_protocols")
DIR_TEST = os.path.join(BASE_DIR, "test_protocols")

# --- LOG DIRECTORIES ---
LOG_ROOT = os.path.join(BASE_DIR, "logs")
DIR_PROTO_LOGS = os.path.join(LOG_ROOT, "protocol_logs")
DIR_CALIB_LOGS = os.path.join(LOG_ROOT, "calibration_logs")

# Ensure all exist
for d in [DIR_RECENT, DIR_TEST, LOG_ROOT, DIR_PROTO_LOGS, DIR_CALIB_LOGS]: 
    os.makedirs(d, exist_ok=True)

# --- 1. SENSOR MANAGER CLASS ---
class SensorManager:
    def __init__(self):
        self.bus = None
        self.bme_address = 0x76 # Default I2C address (sometimes 0x77)
        
        try:
            # Initialize I2C Bus
            self.bus = smbus2.SMBus(1)
            
            # Load BME280 Calibration Parameters (Critical for accuracy)
            if bme280:
                self.bme_calibration = bme280.load_calibration_params(self.bus, self.bme_address)
        except Exception as e:
            print(f"⚠️ Sensor Init Error: {e}")

    def get_cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return round(int(f.read()) / 1000.0, 1)
        except: return 0.0

    def get_cpu_usage(self):
        try:
            with open("/proc/loadavg", "r") as f:
                load = float(f.read().split()[0])
            return min(100, round((load / 4.0) * 100, 1))
        except: return 0.0

    

    def get_bme280(self):
        # REAL READING LOGIC
        if not self.bus or not bme280:
            # Fallback if disconnected
            return {"temp": 0, "hum": 0, "press": 0}
            
        try:
            # Read single sample
            data = bme280.sample(self.bus, self.bme_address, self.bme_calibration)
            return {
                "temp": round(data.temperature, 1),
                "hum": round(data.humidity, 1),
                "press": round(data.pressure, 1)
            }
        except Exception:
            # If read fails (e.g. loose wire), return 0
            return {"temp": 0, "hum": 0, "press": 0}

    def get_adt75(self):
        # ADT75 (Address 0x48)
        if not self.bus: return 0.0
        try:
            data = self.bus.read_i2c_block_data(0x48, 0, 2)
            val = (data[0] << 8) | data[1]
            val >>= 4
            return val * 0.0625
        except: return 0.0

    def get_all(self):
        bme = self.get_bme280()
        return {
            "cpu_temp": self.get_cpu_temp(),
            "cpu_load": self.get_cpu_usage(),
            
            
            "bme_temp": bme["temp"],
            "bme_hum": bme["hum"],
            "bme_press": bme["press"],
            "adt_temp": self.get_adt75()
        }

# --- 2. LIGHT CONTROLLER (WS2812) ---
class LightController:
    def __init__(self, pin=18, num_pixels=8):
        self.active = False
        self.strip = None
        if HARDWARE_AVAILABLE:
            try:
                # Defaulting to GPIO 18 (PWM0)
                self.strip = neopixel.NeoPixel(board.D18, num_pixels, brightness=0.5, auto_write=False)
            except: pass

    def toggle(self, state):
        self.active = state
        if not self.strip: return
        
        color = (255, 255, 255) if state else (0, 0, 0)
        self.strip.fill(color)
        self.strip.show()

class RobotClient:
    def __init__(self):
        self.state = {
            "status": "Idle", "filename": "None", "progress": 0,
            "current_line": "Ready", "current_desc": "", "logs": [],            
            "est": "--:--:--:--", "connection": "Offline",
            "stop_reason": None, "pause_reason": None, "error_msg": None, 
            "completed": False, "started_by": "Unknown", "just_started": False,
            
            # --- CALIBRATION STATE ---
            "calibration_active": False,
            "calibration_source": None,
            "calib_status": "Idle", 
            "is_calibrated": False
        }
        self.PIN_LID_SWITCH = 22 # Change to your actual pin
        GPIO.setup(self.PIN_LID_SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Add to state
        self.state["lid_open"] = False
        
        self.sensors = SensorManager()
        self.lights = LightController(pin=18, num_pixels=12) # Adjust pixel count here
        
        # Add to State
        self.state["light_on"] = False
        self.state["sensor_data"] = {}
        
        self.command_queue = queue.Queue()
        self.start_time = None; self.smoothed_seconds = 0
        self.log_accumulator = []; self.current_session_log_path = None
        self.server_connected = False; self.expect_reset = False
        self.connection_time = time.time(); self.grace_period = 3.0 

        # --- 1. CLEANUP OLD LOGS ON STARTUP ---
        self.cleanup_old_logs()

        # GPIO
        self.PIN_RESET = 17; self.PIN_PAUSE = 27   
        GPIO.setwarnings(False); GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PIN_RESET, GPIO.OUT); GPIO.setup(self.PIN_PAUSE, GPIO.OUT)
        GPIO.output(self.PIN_PAUSE, 0)
        self.hard_reset_pico()

        # Serial
        try:
            print("🔌 Connecting to Serial...", flush=True)
            self.ser = serial.Serial('/dev/ttyAMA3', 115200, timeout=0.1)
            self.ser.reset_input_buffer()
            self.state["connection"] = "Connected"
            self.connection_time = time.time() 
        except Exception as e:
            print(f"⚠️ Serial Error: {e}", flush=True)
            self.state["connection"] = "Error"; self.ser = None

        self.is_running = False; self.is_paused = False
        self.protocol_steps = []; self.ptr = 0; self.seq_num = 1 
        self.backlight_path = self._find_backlight_path()
        self.max_brightness = self._get_max_brightness()
        
        # ... keep your existing socket/server connection code here ...
        print(f"DEBUG: Backlight Path: {self.backlight_path}")
        
    def toggle_light(self):
        """Toggles WS2812 LEDs."""
        new_state = not self.state["light_on"]
        self.state["light_on"] = new_state
        self.lights.toggle(new_state)
        self.log(f"💡 Light {'ON' if new_state else 'OFF'}")
        self.sync_with_server() # Push change to server
         
    def get_connected_ssid(self):
        """Reliably gets the current WiFi SSID."""
        # Method 1: Try 'iwgetid' (Standard on Raspberry Pi)
        try:
            # Output looks like: wlan0     ESSID:"MyWifiName"
            output = subprocess.check_output(["iwgetid", "-r"], encoding="utf-8").strip()
            if output: return output
        except:
            pass
            
        # Method 2: nmcli active connection check
        try:
            # Get active connection names
            result = subprocess.check_output(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"], 
                encoding="utf-8"
            )
            for line in result.split("\n"):
                # active line looks like: MyWifiName:802-11-wireless
                if "802-11-wireless" in line or "wifi" in line:
                    return line.split(":")[0]
        except:
            pass
            
        return None

    def get_wifi_networks(self):
        """Forces a fresh scan and returns networks."""
        
        # 1. Get current SSID
        current_ssid = self.get_connected_ssid()
        if current_ssid: current_ssid = current_ssid.strip()
        print(f"DEBUG: Active SSID is '{current_ssid}'")

        try:
            # --- FORCE RESCAN ---
            # This tells the hardware to actually look for networks now.
            # It connects asynchronously, so we wait a moment or just run it.
            # 'nmcli dev wifi rescan' returns immediately but scan takes time.
            print("DEBUG: Triggering hardware rescan...")
            subprocess.run(["nmcli", "dev", "wifi", "rescan"], stderr=subprocess.DEVNULL)
            
            # Optional: Sleep briefly to allow scan to populate (0.5s - 1s)
            import time
            time.sleep(1) 
            
            # 2. READ RESULTS
            cmd = ["nmcli", "-t", "-f", "SSID,SIGNAL", "dev", "wifi"]
            result = subprocess.check_output(cmd, encoding="utf-8")
            
            unique_nets = {}
            
            for line in result.split("\n"):
                if not line: continue
                parts = line.split(":")
                if len(parts) < 2: continue
                
                raw_ssid = ":".join(parts[:-1]) 
                ssid = raw_ssid.strip()
                if not ssid: continue 
                
                try: signal = int(parts[-1])
                except: signal = 0
                
                is_connected = False
                if current_ssid and ssid == current_ssid:
                    is_connected = True
                
                if ssid not in unique_nets:
                    unique_nets[ssid] = {"ssid": ssid, "signal": signal, "connected": is_connected}
                else:
                    if is_connected: unique_nets[ssid]["connected"] = True
                    if signal > unique_nets[ssid]["signal"]:
                        unique_nets[ssid]["signal"] = signal

            networks = list(unique_nets.values())
            networks.sort(key=lambda x: (not x["connected"], -x["signal"]))
            return networks[:15]
            
        except Exception as e:
            print(f"WiFi Scan Error: {e}")
            return []   
    
    def connect_wifi(self, ssid, password):
        print(f"Connecting to {ssid}...")
        try:
            subprocess.run(
                ["nmcli", "dev", "wifi", "connect", ssid, "password", password],
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _find_backlight_path(self):
        """Auto-detects the backlight controller path."""
        # Common locations for Raspberry Pi DSI / GPIO displays
        search_paths = [
            "/sys/class/backlight/rpi_backlight",
            "/sys/class/backlight/*", # Wildcard search for others
        ]
        
        for p in search_paths:
            matches = glob.glob(p)
            for match in matches:
                # Check if 'brightness' file exists inside
                if os.path.exists(os.path.join(match, "brightness")):
                    return match
        return None

    def _get_max_brightness(self):
        """Reads the maximum hardware brightness value."""
        if not self.backlight_path: return 255
        try:
            with open(os.path.join(self.backlight_path, "max_brightness"), "r") as f:
                return int(f.read().strip())
        except:
            return 255

    def get_brightness(self):
        """Reads current brightness as a percentage (0-100)."""
        if not self.backlight_path:
            return 50 # Default fallback
            
        try:
            with open(os.path.join(self.backlight_path, "brightness"), "r") as f:
                val = int(f.read().strip())
                
            # Convert hardware value to percentage
            pct = int((val / self.max_brightness) * 100)
            return pct
        except Exception as e:
            print(f"Error reading brightness: {e}")
            return 50

    def set_brightness(self, level_pct):
        """Sets brightness using the detected hardware limits."""
        if not self.backlight_path:
            self.log("⚠ No supported backlight controller found.")
            return

        try:
            # Clamp percentage 5-100 (Prevent turning screen off completely)
            level_pct = max(5, min(100, level_pct))
            
            # Calculate hardware value
            val = int((level_pct / 100.0) * self.max_brightness)
            
            path = os.path.join(self.backlight_path, "brightness")
            
            with open(path, "w") as f:
                f.write(str(val))
            
            # self.log(f"☀ Set to {level_pct}%") # Optional logging
            
        except PermissionError:
            self.log("⚠ Permission Denied. Run: sudo chmod 777 " + os.path.join(self.backlight_path, "brightness"))
        except Exception as e:
            self.log(f"⚠ Brightness Error: {e}")
    # --- UPDATED: CLEANUP BOTH FOLDERS ---
    def cleanup_old_logs(self, days=7):
        print("🧹 Checking for old logs...", flush=True)
        now = time.time()
        cutoff = now - (days * 86400)
        count = 0
        
        # Helper to clean a specific dir
        def clean_dir(directory):
            c = 0
            try:
                for f in os.listdir(directory):
                    fpath = os.path.join(directory, f)
                    if os.path.isfile(fpath):
                        if os.path.getctime(fpath) < cutoff:
                            os.remove(fpath); c += 1
            except: pass
            return c

        count += clean_dir(DIR_PROTO_LOGS)
        count += clean_dir(DIR_CALIB_LOGS)
        
        if count > 0: print(f"✅ Deleted {count} logs older than {days} days.")

    def hard_reset_pico(self):
        print("⚡ Hard Resetting Pico...", flush=True)
        GPIO.output(self.PIN_RESET, 0); time.sleep(0.2)
        GPIO.output(self.PIN_RESET, 1); time.sleep(1.5)
        self.connection_time = time.time()

    def calculate_estimate(self):
        if not self.is_running or self.is_paused or not self.start_time: return
        total = len(self.protocol_steps)
        if total == 0: return
        if self.ptr == 0: self.state["est"] = "Calculating..."; return
        progress_pct = (self.ptr / total) * 100
        self.state["progress"] = int(progress_pct)
        if progress_pct > 1:
            elapsed = time.time() - self.start_time
            raw_remaining = (elapsed / progress_pct) * (100 - progress_pct)
            if self.smoothed_seconds == 0: self.smoothed_seconds = raw_remaining
            else: self.smoothed_seconds = (0.95 * self.smoothed_seconds) + (0.05 * raw_remaining)
            self.state["est"] = self.format_time_dhms(self.smoothed_seconds)
        else: self.state["est"] = "Calculating..."

    def format_time_dhms(self, seconds):
        if seconds <= 0: return "00:00:00:00"
        m, s = divmod(int(seconds), 60); h, m = divmod(m, 60); d, h = divmod(h, 24)
        return f"{d:02}:{h:02}:{m:02}:{s:02}"

    # --- UPDATED: INTELLIGENT LOG PATH SELECTION ---
    def start_new_log_session(self, filename):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Decide Folder based on content
        if "Calibration" in filename:
            target_dir = DIR_CALIB_LOGS
        else:
            target_dir = DIR_PROTO_LOGS
            
        # Construct Filename (Prevent double timestamping)
        if timestamp not in filename:
            name = f"{filename}_{timestamp}.log"
        else:
            name = f"{filename}.log"
            
        self.current_session_log_path = os.path.join(target_dir, name)
        self.log(f"🚀 Session Started: {name}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        print(entry, flush=True); self.state["logs"].append(entry)
        if len(self.state["logs"]) > 5: self.state["logs"].pop(0)
        self.log_accumulator.append(entry)
        
        if self.current_session_log_path:
            try:
                with open(self.current_session_log_path, "a", encoding="utf-8") as f: f.write(entry + "\n")
            except: pass

    def sync_with_server(self):
        is_open = GPIO.input(self.PIN_LID_SWITCH) == GPIO.HIGH
        self.state["lid_open"] = is_open
        self.state["sensor_data"] = self.sensors.get_all()
        line_txt = self.state["current_line"]
        if self.state["current_desc"]: line_txt += f" ({self.state['current_desc']})"
        payload = {
            "file": self.state["filename"], "line": line_txt, "progress": self.state["progress"],
            "est": self.state["est"], "status": self.state["status"], "logs": "\n".join(self.log_accumulator),
            "started_by": self.state["started_by"],
            # --- SYNC LOCK & STATUS ---
            "calib_active": self.state["calibration_active"],
            "calib_source": self.state["calibration_source"],
            "calib_status": self.state["calib_status"],
            "is_calibrated": self.state["is_calibrated"],
            
            "file": self.state["filename"],
            "status": self.state["status"],
            
            # ADD THESE NEW FIELDS
            "light_on": self.state["light_on"],
            "sensors": self.state["sensor_data"],
            "lid_open": self.state["lid_open"]
        }
        self.log_accumulator = [] 
        try:
            r = requests.post(f"{SERVER_URL}/pi/sync", json=payload, timeout=0.5)
            if r.status_code == 200:
                if not self.server_connected: self.log("✅ Connected to Server"); self.server_connected = True
                for cmd in r.json().get("commands", []): self.handle_server_command(cmd)
        except: 
            if self.server_connected: self.log("⚠️ Lost connection to Server"); self.server_connected = False

    def handle_server_command(self, cmd):
        ev = cmd["event"]
        if ev == "PAUSE": self.command_queue.put(("REMOTE_PAUSE", None))
        elif ev == "RESUME": self.command_queue.put(("REMOTE_RESUME", None))
        elif ev == "CLEAR": self.command_queue.put(("REMOTE_STOP", None))
        elif ev == "NEW_FILE": self.command_queue.put(("DOWNLOAD_AND_RUN", (cmd["filename"], "Remote"))) 
        elif ev == "SERIAL_SEND":
            if self.ser: self.log(f"TX (Remote): {cmd['data']}"); self.ser.write((cmd["data"] + "\n").encode())
        # --- CALIB START (Remote) ---
        elif ev == "CALIB_START": 
            self.set_calibration_mode(True, "Remote")
            if self.ser: 
                self.ser.write(b"T00\n")
        elif ev == "CALIB_END": 
            self.set_calibration_mode(False, None)

    def parse_gcode_file(self, lines):
        steps = []; pending_desc = ""
        for line in lines:
            raw = line.strip()
            if not raw: continue
            if raw.startswith(";"): pending_desc = raw.replace(";", "").strip()
            else: steps.append({"cmd": raw, "desc": pending_desc if pending_desc else ""}); pending_desc = ""
        return steps

    def load_local_protocol(self, filename, source="Unknown"):
        self.log(f"📂 Loading: {filename} (Source: {source})")
        target_path = None
        if os.path.exists(os.path.join(DIR_RECENT, filename)): target_path = os.path.join(DIR_RECENT, filename)
        elif os.path.exists(os.path.join(DIR_TEST, filename)): target_path = os.path.join(DIR_TEST, filename)
        
        if not target_path: self.log(f"❌ File not found: {filename}"); return

        try:
            with open(target_path, "r", encoding="utf-8") as f: raw_lines = f.readlines()
            self.protocol_steps = self.parse_gcode_file(raw_lines)
            
            self.state["filename"] = filename
            self.state["started_by"] = source
            self.state["just_started"] = (source == "Remote")
            
            self.ptr = 0; self.seq_num = 1
            self.is_running = True; self.is_paused = False
            self.state["status"] = "Running"
            self.state["stop_reason"] = None; self.state["error_msg"] = None; self.state["completed"] = False
            self.start_time = time.time(); self.smoothed_seconds = 0; self.state["est"] = "Calculating..."
            
            GPIO.output(self.PIN_PAUSE, 0)
            self.start_new_log_session(filename)
            if self.ser: self.ser.reset_input_buffer()
        except Exception as e: self.log(f"❌ Read Error: {e}")

    def download_protocol(self, filename, source):
        self.log(f"📥 Downloading: {filename}...")
        try:
            local_path = os.path.join(DIR_RECENT, filename)
            url = f"{SERVER_URL}/download/{filename}"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                with open(local_path, "wb") as f: f.write(r.content)
                self.log("✅ Downloaded"); self.load_local_protocol(filename, source) 
            else: self.log(f"❌ Server Error: {r.status_code}")
        except Exception as e: self.log(f"❌ Download Failed: {e}")

    def ui_send_gcode(self, gcode): self.command_queue.put(("MANUAL", gcode))
    def ui_load_and_run(self, filename): self.command_queue.put(("LOAD_LOCAL", (filename, "User")))
    def ui_pause_resume(self): self.command_queue.put(("TOGGLE_PAUSE", None))
    def ui_stop(self): self.command_queue.put(("STOP", None))
    def ui_ack_start(self): self.state["just_started"] = False
    
    # --- UPDATED: CALIBRATION LOGGING + NAMING FIX ---
    def set_calibration_mode(self, active, source):
        self.state["calibration_active"] = active
        self.state["calibration_source"] = source
        if active:
            clean_source = "Local" if source == "User" else source
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            calib_name = f"Calibration_{clean_source}_{timestamp}"
            
            self.state["filename"] = calib_name
            self.start_new_log_session(calib_name)
            
            self.log(f"🔧 Calibration Started by {clean_source}")
            self.state["calib_status"] = "Homing" 
            self.sync_with_server()
        else:
            self.log("🔧 Calibration Ended")
            self.state["calib_status"] = "Idle"
            
            # --- FIX: HARD RESET STATE ON EXIT ---
            self.state["filename"] = "None" 
            self.state["started_by"] = "Unknown"
            self.state["status"] = "Idle"
            
            self.sync_with_server()
            
    def reset_all_state(self):
        self.state["stop_reason"] = None; self.state["completed"] = False; self.state["error_msg"] = None 
        self.state["filename"] = "None"; self.state["started_by"] = "Unknown" 
        self.state["status"] = "Idle"; self.state["current_line"] = "Ready"; self.state["current_desc"] = ""
        self.state["progress"] = 0; self.state["est"] = "--:--:--:--"
        self.state["is_calibrated"] = False # Force recalibration
        
        # --- FIX: Force Calibration OFF on Reset/Error ---
        self.state["calibration_active"] = False
        self.state["calib_status"] = "Idle"
        self.state["calibration_source"] = None
        self.sync_with_server()

    def ui_ack_stop(self): self.reset_all_state()
    def ui_ack_error(self): self.reset_all_state()

    def start(self):
        t = threading.Thread(target=self._run_loop, daemon=True)
        t.start()

    def _run_loop(self):
        last_sync = time.time()
        waiting_for_response = False
        
        while True:
            self.calculate_estimate()
            if time.time() - last_sync > 0.5: self.sync_with_server(); last_sync = time.time()
            
        
            try:
                while not self.command_queue.empty():
                    cmd_type, data = self.command_queue.get_nowait()
                    
                    if cmd_type == "MANUAL" and self.ser: self.ser.write((data + "\n").encode())
                    elif cmd_type == "LOAD_LOCAL": fname, source = data; self.load_local_protocol(fname, source); waiting_for_response = False
                    elif cmd_type == "DOWNLOAD_AND_RUN": fname, source = data; self.download_protocol(fname, source); waiting_for_response = False
                    
                    # 2. RUNTIME COMMANDS (Guard Clause Added)
                    # If we have no steps loaded, IGNORE these commands
                    # to prevent "Running: None" ghost state.
                    elif not self.protocol_steps:
                        self.log(f"⚠️ Ignored {cmd_type} (No Protocol Loaded)")
                        continue
                    
                    elif cmd_type == "STOP" or cmd_type == "REMOTE_STOP":
                        source = "Remote" if cmd_type == "REMOTE_STOP" else "User"
                        self.is_running = False; self.log(f"🛑 STOPPED ({source})")
                        last_file = self.state["filename"]; self.reset_all_state(); self.state["filename"] = last_file 
                        self.state["status"] = f"Stopped ({source})"; self.state["stop_reason"] = source 
                        self.expect_reset = True; waiting_for_response = False; self.hard_reset_pico()

                    # --- PAUSE / RESUME LOGIC ---
                    elif cmd_type in ["TOGGLE_PAUSE", "REMOTE_PAUSE", "REMOTE_RESUME"]:
                        should_pause = False
                        if cmd_type == "REMOTE_PAUSE": should_pause = True
                        elif cmd_type == "REMOTE_RESUME": should_pause = False
                        else: should_pause = not self.is_paused 
                        
                        self.is_paused = should_pause
                        
                        if self.is_paused:
                            reason = "Remote" if cmd_type == "REMOTE_PAUSE" else "User"
                            self.state["pause_reason"] = reason
                            self.state["status"] = f"Paused ({reason})"
                            GPIO.output(self.PIN_PAUSE, 1)
                            self.log(f"⏸ PAUSE ({reason})")
                        else:
                            source = "Remote" if cmd_type == "REMOTE_RESUME" else "User"
                            if self.state["pause_reason"] == "System": 
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

                    # --- HARDWARE SYNC LOGIC (CALIBRATION) ---
                    if self.state["calibration_active"]:
                        
                        if self.state["calib_status"] == "Homing":
                            if "HOME" in resp: 
                                self.state["calib_status"] = "Moving"
                                self.sync_with_server()
                        
                        elif self.state["calib_status"] == "Moving":
                            if resp == "X": 
                                self.state["calib_status"] = "Ready"
                                self.sync_with_server()

                        # 3. SAVE CONFIRMATION (Unlock Logic)
                        if "C_OK" in resp or "OK_C" in resp: 
                            self.log("✅ Calibration Offsets Saved")
                            self.state["is_calibrated"] = True 
                            self.set_calibration_mode(False, None) # Unlock
                            self.sync_with_server()

                    if "Initialized" in resp:
                        if self.expect_reset: self.log("✅ Reset Confirmed"); self.expect_reset = False
                        else: 
                            self.log("🚨 EMERGENCY STOP (Physical)"); self.is_running = False
                            self.state["status"] = "Error"; self.state["stop_reason"] = "Physical"
                            self.state["current_line"] = "E-STOP"; self.state["est"] = "HALTED"; waiting_for_response = False
                    
                    if "ERR" in resp:
                        if time.time() - self.connection_time < self.grace_period: self.log(f"⚠️ Ignored Startup Noise: {resp}")
                        else:
                            parts = resp.split(":", 1); clean_err = parts[1].strip() if len(parts) > 1 else "Unknown Hardware Error"
                            self.log(f"❌ SYSTEM ERROR: {clean_err}")
                            self.is_running = False; self.state["status"] = "Error"
                            self.state["error_msg"] = clean_err; self.state["current_line"] = "Error"; self.state["current_desc"] = "Halted"
                            self.state["est"] = "ERROR"; waiting_for_response = False; self.expect_reset = True; self.hard_reset_pico()

                    if self.is_running:
                        if "PAUSE" in resp:
                            self.is_paused = True; self.state["status"] = "Paused (System)"
                            self.state["pause_reason"] = "System"
                            self.log("⏸ System Paused (Wait Command)"); GPIO.output(self.PIN_PAUSE, 1) 
                        elif "OK" in resp: self.ptr += 1; self.seq_num += 1; waiting_for_response = False 
                except: pass

            if self.is_running and not self.is_paused and self.protocol_steps:
                if self.ptr < len(self.protocol_steps):
                    if not waiting_for_response:
                        step = self.protocol_steps[self.ptr]
                        self.state["current_line"] = step["cmd"]; self.state["current_desc"] = step["desc"]
                        self.state["status"] = "Running"
                        packet = f"N{step['cmd']}*{self.seq_num}"
                        self.log(f"TX: {packet}")
                        if self.ser: self.ser.write((packet + "\n").encode()); waiting_for_response = True
                        else: self.is_running = False
                else:
                    self.log("✅ Done"); self.is_running = False
                    self.state["status"] = "Done"; self.state["progress"] = 100; self.state["completed"] = True 
            time.sleep(0.005)