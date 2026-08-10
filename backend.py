""" 
1. M110 -> Queue -> Ack/EROr -> return to the Home screen
                        |
                        -> T00 -> Queue -> Ack/Error
                        -> Gcode Streaming ->queue -> Ack/Error
2. T11 -> STM32 -> ASk for the Pipette detail when boot up
3. Stm32 -> pi -> T11 P1=<data> P2=<data>
4. Serial Packet Format: N<seq> <cmd> *<checksum> (Xor checksum)
5. STM32 -> RS: <seq> (Resend Request) -> Pi -> Resend the requested line (to be checked form pi side) 
6. 4.7ft uart wire working 
7. wait_for_response flag to pace the command queue and prevent flooding the STM32 parser (issue is that the STM32 parser is single-threaded and can only process one command at a time, so if we send too many commands too quickly, it will delay because of the ACK)
8. in main_ui.py (Repsonse time out popup is set for this delay as well)
9. M110 in stm32 call check the limit button and if the limit button is pressed, it will return an error to the pi and the pi will raise a popup TO LET THE USER know which limit switch is engaged and the user can fix it before continuing the protocol or calibration.
10.<To DO> Issue Stop button in calibration popup and protocol screen is not working since not connected in v2 pcb board we will be using the reset button on directly to the stm32 reset pin, so <TO DO> we will need to figure real usage 
11. Same for the pause button figure it out.
"""
import os
import time
import queue
import serial
import threading
import glob
from datetime import datetime

# Modular local imports
from hardware import (
    GPIO,
    PWMDevice,
    FanController,
    PIDController,
    SensorManager,
    LightController,
    PipetteManager,
    BacklightController,
)
from network_interface import HttpNetworkInterface

BASE_DIR = "/home/lhr/Robot_Client"
DIR_RECENT = os.path.join(BASE_DIR, "recent_protocols")
DIR_TEST = os.path.join(BASE_DIR, "test_protocols")
LOG_ROOT = os.path.join(BASE_DIR, "logs")
DIR_PROTO_LOGS = os.path.join(LOG_ROOT, "protocol_logs")
DIR_CALIB_LOGS = os.path.join(LOG_ROOT, "calibration_logs")

# Initialize directories immediately
for d in [DIR_RECENT, DIR_TEST, LOG_ROOT, DIR_PROTO_LOGS, DIR_CALIB_LOGS]: 
    os.makedirs(d, exist_ok=True)

# Helper function for XOR Checksum calculation
def calculate_gcode_checksum(payload: str) -> int:
    cs = 0
    for char in payload:
        cs ^= ord(char)
    return cs


class RobotClient:
    def __init__(self):
        self.DIR_RECENT = DIR_RECENT
        self.DIR_TEST = DIR_TEST
        
        # Initialize low-level GPIO layout first
        self.PIN_LID_LIM = 22
        self.PIN_RESET = 17
        self.PIN_PAUSE = 27
        self._init_gpio_pins()
        
        # Construct hardware modules
        self.pipettes = PipetteManager()
        self.sensors = SensorManager()
        self.heater = PWMDevice(pin=12, freq=50)
        self.cooling_fan = FanController(pwm_pin=13, tacho_pin=6, name="Cooling Fan")
        self.heater_fan = FanController(pwm_pin=19, tacho_pin=26, name="Heater Fan")
        self.light = LightController(pin=18, num_pixels=6)
        self.pid = PIDController(kp=5.0, ki=0.05, kd=1.0)
        self.backlight = BacklightController()
        self.server_connected = False
        self.sync_fail_count = 0
        
        # Generate internal state template structure
        self.state = {
            "status": "Idle", "filename": "None", "progress": 0,
            "current_line": "Ready", "current_desc": "", "logs": [],            
            "est": "--:--:--:--", "connection": "Offline",
            "stop_reason": None, "pause_reason": None, "error_msg": None, 
            "completed": False, "started_by": "Unknown", "just_started": False,
            "calibration_active": False, "calibration_source": None, "calib_status": "Idle", "is_calibrated": False,
            "lid_open": False, "light_on": False, 
            "sensor_data": {},    # Initialized as empty dict to maintain memory pointer
            "target_temp": 0, "fan_mode": "Manual", "fan_manual_val": 0,   
            "heater_duty": 0, "fan_rpm": 0, "heater_fan_rpm": 0,
            "pipettes": self.pipettes.get_state(),
        }
        
        self.command_queue = queue.Queue()
        self.network = HttpNetworkInterface(self)
        # Internal flags for sequencing
        self._pending_calib_start = False
        self._m110_sent_time = None
        self._pending_protocol_start = False
        self._protocol_start_sent_time = None
        self._awaiting_serial_response = False
        self._serial_timeout_triggered = False
        self._serial_wait_deadline = None
        self._last_tx_cmd = None
        
        self.start_time = None; self.smoothed_seconds = 0
        self.log_accumulator = []; self.current_session_log_path = None
        self.expect_reset = False  # for reset detection after E-STOP or error
        self.connection_time = time.time(); self.grace_period = 3.0 

        self.cleanup_old_logs()
        self.hard_reset_pico()
        self._init_serial_port()

        self.is_running = False; self.is_paused = False
        self.protocol_steps = []; self.ptr = 0; self.seq_num = 1 
        self.backlight_path = self._find_backlight_path()
        self.max_brightness = self._get_max_brightness()

    def _mark_serial_tx(self, raw_cmd: str):
        self._awaiting_serial_response = True
        self._serial_timeout_triggered = False
        self._serial_wait_deadline = time.time() + 5.0
        self._last_tx_cmd = raw_cmd.strip()

    def _clear_serial_wait(self):
        self._awaiting_serial_response = False
        self._serial_wait_deadline = None
        self._last_tx_cmd = None

    def _handle_serial_timeout(self):
        if self._serial_timeout_triggered:
            return
        self._serial_timeout_triggered = True
        self._awaiting_serial_response = False
        self._serial_wait_deadline = None
        self._pending_calib_start = False
        self._m110_sent_time = None
        self._pending_protocol_start = False
        self._protocol_start_sent_time = None
        self._clear_command_queue()
        self.log("⏱️ No response from controller for 5s — raising hardware error")
        self.is_running = False
        self.state["status"] = "Error"
        self.state["error_msg"] = "No response from controller"
        self.state["current_line"] = "Error"
        self.state["stop_reason"] = "Controller Timeout"
        self.expect_reset = True
        self.reset_all_state(reset_calibration=True)
        self.hard_reset_pico()

    def _clear_command_queue(self):
        try:
            while not self.command_queue.empty():
                self.command_queue.get_nowait()
        except Exception:
            pass

    def send_packet(self, raw_cmd: str, seq: int = None):
        """Encapsulates raw commands into 'N<seq> <cmd> *<checksum>' format."""
        if not self.ser:
            return
            
        if seq is None:
            seq = self.seq_num

        cleaned_cmd = raw_cmd.strip()
        self.last_sent_cmd = cleaned_cmd  # Track outgoing command string
        unchecksummed_payload = f"N{seq} {cleaned_cmd} "
        cs = calculate_gcode_checksum(unchecksummed_payload)
        formatted_packet = f"{unchecksummed_payload}*{cs}\n"
        
        self.log(f"TX: {formatted_packet.strip()}")
        try:
            self.ser.write(formatted_packet.encode())
            self._mark_serial_tx(cleaned_cmd)
        except Exception as e:
            self.log(f"⚠️ Serial TX Error: {e}")

    def _find_backlight_path(self):
        return getattr(self.backlight, "backlight_path", None)

    def _get_max_brightness(self):
        return getattr(self.backlight, "max_brightness", 255)

    def _init_gpio_pins(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.PIN_LID_LIM, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_RESET, GPIO.OUT)
        GPIO.setup(self.PIN_PAUSE, GPIO.OUT)
        GPIO.output(self.PIN_PAUSE, 0)

    def _init_serial_port(self):
        try:
            print("🔌 Connecting to Serial...", flush=True)
            self.ser = serial.Serial('/dev/ttyAMA3', 115200, timeout=0.1)
            self.ser.reset_input_buffer()
            self.state["connection"] = "Connected"
            self.connection_time = time.time()
            
            # 1. Reset sequence numbers on Pi and STM32 parser
            self.seq_num = 1
            self.send_packet("M110 N0", seq=0)
            time.sleep(0.05)
            
            # 2. Query initial pipette state (transmits as N1 T11 *43)
            self.send_packet("T11")
        except Exception as e:
            print(f"⚠️ Serial Error: {e}", flush=True)
            self.state["connection"] = "Error"
            self.ser = None

    def send_initial_calibration_gcode(self):
        if not self.ser:
            return
        # Route calibration start through the queue so it uses the same pacing/timeout path as all other commands.
        self.command_queue.put(("SEQ_PKT", ("T00", 1)))
            
    def _parse_t11_report(self, resp: str):
        """Parses inbound 'T11 P1=p300_single_v2.1 P2=none' from STM32."""
        # STRICT GUARD: Ignore strings that don't contain data key-value pairs
        if "P1=" not in resp and "P2=" not in resp:
            return

        try:
            p1_model = "none"
            p2_model = "none"
            
            parts = resp.split()
            for part in parts:
                if part.startswith("P1="):
                    p1_model = part.split("=", 1)[1]
                elif part.startswith("P2="):
                    p2_model = part.split("=", 1)[1]

            # Update PipetteManager state
            hardware_changed = self.pipettes.update_from_t11(p1_model, p2_model)
            self.state["pipettes"].clear()
            self.state["pipettes"].update(self.pipettes.get_state())

            if hardware_changed:
                self.log(f"🧬 Pipette Telemetry: P1={p1_model}, P2={p2_model}")
        except Exception as e:
            self.log(f"⚠️ Failed to parse T11 report: {e}")
   
    def _process_inbound_line(self, line: str, waiting_for_response: bool) -> bool:
        """Structured dispatcher for inbound STM32 responses."""
        if not line:
            return waiting_for_response

        self._clear_serial_wait()

        # 1. ACK / Command Completed (e.g., "OK 1" or "OK 30")
        if line.startswith("OK"):
            parts = line.split()
            ack_seq = -1
            if len(parts) > 1 and parts[1].isdigit():
                ack_seq = int(parts[1])
                self.seq_num = ack_seq + 1
            else:
                self.seq_num += 1

            # Check if the command just completed was OK_C (Save Offsets)
            last_cmd = getattr(self, "last_sent_cmd", "")
            if last_cmd.startswith("OK_C"):
                self.log("✅ Calibration Offsets Saved")
                self.state["is_calibrated"] = True
                
                self.last_sent_cmd = ""
                self.ptr += 1
                return False

            # Calibration start: after M110 ACK, queue T00
            if ack_seq == 0 and getattr(self, "_pending_calib_start", False):
                try:
                    self._pending_calib_start = False
                    self._m110_sent_time = None
                    if self.state.get("status") != "Error":
                        self.command_queue.put(("SEQ_PKT", ("T00", 1)))
                        self.log("🔁 M110 ACK received — queued T00")
                    else:
                        self.log("🔁 M110 ACK received but controller already in error state")
                except Exception as e:
                    self.log(f"⚠️ Failed to queue T00 after M110 ACK: {e}")

            # Protocol start: after M110 ACK, allow file streaming to begin
            if ack_seq == 0 and getattr(self, "_pending_protocol_start", False):
                try:
                    self._pending_protocol_start = False
                    self._protocol_start_sent_time = None
                    if self.state.get("status") != "Error":
                        self.log("🔁 Protocol M110 ACK received — file streaming can begin")
                    else:
                        self.log("🔁 Protocol M110 ACK received but controller already in error state")
                except Exception as e:
                    self.log(f"⚠️ Failed to finalize protocol start after M110 ACK: {e}")

            if self.state["calibration_active"] and ack_seq != 0:
                if self.state["calib_status"] != "Ready":
                    self.state["calib_status"] = "Ready"
                    self.sync_with_server()

            self.ptr += 1
            return False  # Clear waiting_for_response flag

        # 2. Resend Request (e.g., "RS: 3")
        elif line.startswith("RS:"):
            try:
                requested_line = int(line.split(":")[1].strip())
                self.log(f"🔄 Resend requested for line N{requested_line}")
                self.seq_num = requested_line
                self.ptr = max(0, requested_line - 1)
            except ValueError:
                pass
            return False

        # 3. Pipette Telemetry
        elif line.startswith("T11"):
            self._parse_t11_report(line)
            return waiting_for_response

        # 4. Machine Position/Status Report
        elif line.startswith("STAT:"):
            return waiting_for_response

        # 5. Hardware Error
        elif line.startswith("ERR:"):
            self._clear_command_queue()
            self._pending_calib_start = False
            self._m110_sent_time = None
            if time.time() - self.connection_time < self.grace_period:
                self.log(f"⚠️ Ignored Startup Noise: {line}")
            else:
                clean_err = line.split(":", 1)[1].strip() if ":" in line else "Hardware Error"
                self.log(f"❌ SYSTEM ERROR: {clean_err}")
                self.is_running = False
                self.reset_all_state(reset_calibration=True)
                self.state["status"] = "Error"
                self.state["error_msg"] = clean_err
                self.state["current_line"] = "Error"
                self.expect_reset = True
                self.hard_reset_pico()
            return False

        # 6. System Boot / Reset Confirmation
        elif "Initialized" in line or "RESET" in line:
            if self.expect_reset:
                self.log("✅ Reset Confirmed")
                self.expect_reset = False
            elif self.is_running:
                self.log("🚨 EMERGENCY STOP (Physical)")
                self.is_running = False
                self.state["status"] = "Error"  
                self.state["stop_reason"] = "Physical"
            else:
                self.log("🔌 MCU Online / Rebooted (System Idle)")
                self.state["connection"] = "Connected"
            return False

        # 7. Calibration Completion Event
        elif self.state["calibration_active"]:
            line_lower = line.lower()
            
            # Transition from "Homing" -> "Moving" ONLY when coming out of homing during T00
            if self.state["calib_status"] == "Homing" and ("moveto" in line_lower or "moving" in line_lower):
                self.state["calib_status"] = "Moving"
                self.sync_with_server()
                
           
            """ if "C_OK" in line or "OK_C" in line:
                self.log("✅ Calibration Offsets Saved")
                self.state["is_calibrated"] = True
                self.set_calibration_mode(False, None)
                self.sync_with_server() """

        # 8. Pause Command Feedback
        elif "PAUSE" in line and self.is_running:
            self.is_paused = True
            self.state["status"] = "Paused (System)"
            self.state["pause_reason"] = "System"
            self.log("⏸ System Paused (Wait Command)")
            GPIO.output(self.PIN_PAUSE, 1)
        
        

        # Raw debug logs (e.g. "moveto Axis homed...", "Moving XY...") pass through safely without triggering popups
        return waiting_for_response
    
    # --- UI PASSTHROUGH INTERFACES ---
    def sync_with_server(self):
        self.network.sync_with_server()

    def get_connected_ssid(self):
        return self.network.get_connected_ssid()

    def get_wifi_networks(self): 
        return self.network.get_wifi_networks()

    def connect_wifi(self, ssid, password):
        return self.network.connect_wifi(ssid, password)

    def get_brightness(self):
        return self.backlight.get_brightness()

    def set_brightness(self, level_pct):
        self.backlight.set_brightness(level_pct)

    def ui_send_gcode(self, gcode): self.command_queue.put(("MANUAL", gcode))
    def ui_load_and_run(self, filename): self.command_queue.put(("LOAD_LOCAL", (filename, "User")))
    def ui_pause_resume(self): self.command_queue.put(("TOGGLE_PAUSE", None))
    def ui_stop(self): self.command_queue.put(("STOP", None))
    def ui_ack_start(self): self.state["just_started"] = False
    def ui_ack_stop(self): self.reset_all_state(reset_calibration=False)
    def ui_ack_error(self):
        self.seq_num = 1
        self.reset_all_state(reset_calibration=True)

    def start(self):
        threading.Thread(target=self._run_loop, daemon=True).start()
        self.network.start()

    def get_telemetry_snapshot(self):
        self.state["lid_open"] = (GPIO.input(self.PIN_LID_LIM) == GPIO.HIGH)
        
        # Mutate sensor data pointer tree in-place
        sensors = self.sensors.get_all()
        self.state["sensor_data"].clear()
        self.state["sensor_data"].update(sensors)
        
        line_txt = self.state["current_line"]
        if self.state["current_desc"]: line_txt += f" ({self.state['current_desc']})"
        
        payload = {
            "file": self.state["filename"], "line": line_txt, "progress": self.state["progress"],
            "est": self.state["est"], "status": self.state["status"], "logs": "\n".join(self.log_accumulator),
            "started_by": self.state["started_by"],
            "calib_active": self.state["calibration_active"],
            "calib_source": self.state["calibration_source"],
            "calib_status": self.state["calib_status"],
            "is_calibrated": self.state["is_calibrated"],
            "light_on": self.state["light_on"],
            "sensors": self.state["sensor_data"],
            "lid_open": self.state["lid_open"],
            "pipettes": self.state["pipettes"]
        }
        self.log_accumulator.clear()
        return payload

    def update_thermal_control(self):
        sensors = self.sensors.get_all()
        current_temp = sensors.get("bme_temp", 0)
        target = self.state["target_temp"]

        if current_temp <= 0.1 or target <= 0:
            self.heater.set_duty(0)
            self.heater_fan.set_speed(self.state["fan_manual_val"] if self.state["fan_mode"] == "Manual" else 0)
            self.state["heater_duty"] = 0
            
            # Mutate dictionary in-place
            self.state["sensor_data"].clear()
            self.state["sensor_data"].update(sensors)
            return

        self.pid.target = target
        output = self.pid.update(current_temp)

        heater_val = output if output > 0 else 0
        fan_val = abs(output) if output <= 0 else 0

        if self.state["fan_mode"] == "Manual":
            fan_val = self.state["fan_manual_val"]

        if heater_val > 0:
            self.heater_fan.set_speed(fan_val)
            self.cooling_fan.set_speed(0)
        else:
            self.heater_fan.set_speed(0)
            self.cooling_fan.set_speed(fan_val)
            
        self.state["heater_duty"] = heater_val
        self.state["fan_rpm"] = self.cooling_fan.get_rpm()
        self.state["heater_fan_rpm"] = self.heater_fan.get_rpm()
        
        # Mutate dictionary in-place
        self.state["sensor_data"].clear()
        self.state["sensor_data"].update(sensors)
        
    def toggle_light(self):
        new_state = not self.state["light_on"]
        self.state["light_on"] = new_state
        self.light.toggle(new_state)
        self.log(f"💡 Light {'ON' if new_state else 'OFF'}")

    def _run_loop(self):
        waiting_for_response = False
        last_sensor_read = 0  
        
        while True:
            if time.time() - last_sensor_read > 0.5:
                self.update_thermal_control()
                last_sensor_read = time.time()

            self.calculate_estimate()

            # --- 1. Process Command Queue (Paced with waiting_for_response) ---
            try:
                # Only pop and transmit next command if we are NOT waiting for an ACK
                if not waiting_for_response and not self.command_queue.empty():
                    cmd_type, data = self.command_queue.get_nowait()

                    if cmd_type == "MANUAL" and self.ser:
                        raw_cmd = data.strip()
                        self.send_packet(raw_cmd)
                        waiting_for_response = True  # Paced transmission

                    elif cmd_type == "SEQ_PKT" and self.ser:
                        raw_cmd, seq = data
                        raw_cmd = raw_cmd.strip()
                        # send with explicit sequence (e.g., M110 N0 -> seq=0)
                        self.send_packet(raw_cmd, seq=seq)
                        # mark that we're waiting for its ACK
                        waiting_for_response = True
                        
                    elif cmd_type in ["LOAD_LOCAL", "DOWNLOAD_AND_RUN"]:
                        fname, source = data
                        self.load_local_protocol(fname, source)
                        waiting_for_response = False
                    elif cmd_type == "TOGGLE_LIGHT":
                        self.toggle_light()
                    elif cmd_type == "SET_THERMAL":
                        self.state["target_temp"] = int(data.get("target_temp", 0))
                        self.state["fan_mode"] = data.get("fan_mode", "Auto")
                        self.state["fan_manual_val"] = int(data.get("fan_manual_val", 0))
                        self.log(f"🌡 Settings Rx: {self.state['target_temp']}C, Fan: {self.state['fan_mode']}")
                    elif cmd_type == "CONNECT_WIFI":
                        ssid, pw = data
                        threading.Thread(target=self.network.connect_wifi, args=(ssid, pw), daemon=True).start()
                    elif cmd_type in ["STOP", "REMOTE_STOP"]:
                        source = "Remote" if cmd_type == "REMOTE_STOP" else "User"
                        self.is_running = False
                        self.log(f"🛑 STOPPED ({source})")
                        last_file = self.state["filename"]
                        self.reset_all_state(reset_calibration=True)
                        self.state["filename"] = last_file
                        self.state["status"] = f"Stopped ({source})"
                        self.state["stop_reason"] = source
                        self.expect_reset = True
                        waiting_for_response = False
                        self.hard_reset_pico()
                    elif cmd_type in ["TOGGLE_PAUSE", "REMOTE_PAUSE", "REMOTE_RESUME"]:
                        should_pause = (cmd_type == "REMOTE_PAUSE") if cmd_type in ["REMOTE_PAUSE", "REMOTE_RESUME"] else not self.is_paused
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
            except Exception as e:
                self.log(f"⚠️ Queue Exception: {e}")

            # --- 2. Serial Receiver Handler ---
            if self.ser and self.ser.in_waiting:
                try:
                    resp = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if resp:
                        self.log(f"RX: {resp}")
                        waiting_for_response = self._process_inbound_line(resp, waiting_for_response)
                except Exception as e:
                    self.log(f"⚠️ Serial RX Error: {e}")

            if self._awaiting_serial_response and self._serial_wait_deadline and time.time() >= self._serial_wait_deadline:
                self._handle_serial_timeout()

            # --- 3. Protocol Transmit Loop with XOR Checksum ---
            if self.is_running and not self.is_paused and self.protocol_steps and not self._pending_protocol_start:
                if self.ptr < len(self.protocol_steps):
                    if not waiting_for_response:
                        step = self.protocol_steps[self.ptr]
                        raw_cmd = step["cmd"].strip()
                        self.state["current_line"] = raw_cmd
                        self.state["current_desc"] = step["desc"]
                        self.state["status"] = "Running"
                        
                        self.send_packet(raw_cmd, seq=self.seq_num)
                        waiting_for_response = True
                else:
                    self.log("✅ Done")
                    self.is_running = False
                    self.state["status"] = "Done"
                    self.state["progress"] = 100
                    self.state["completed"] = True
                # If calibration or protocol start is pending and we never get the ACK, raise a controller timeout error.
                try:
                    if getattr(self, "_pending_calib_start", False) and getattr(self, "_m110_sent_time", None):
                        if time.time() - self._m110_sent_time > 5.0:
                            self._pending_calib_start = False
                            self._m110_sent_time = None
                            self._handle_serial_timeout()

                    if getattr(self, "_pending_protocol_start", False) and getattr(self, "_protocol_start_sent_time", None):
                        if time.time() - self._protocol_start_sent_time > 5.0:
                            self._pending_protocol_start = False
                            self._protocol_start_sent_time = None
                            self._handle_serial_timeout()
                except Exception:
                    pass

                time.sleep(0.005)

    def parse_gcode_file(self, lines):
        steps = []
        pending_desc = ""
        for line in lines:
            raw = line.strip()
            if not raw:
                continue
            if raw.startswith(";"):
                pending_desc = raw.lstrip(";").strip()
                continue
            
            # Strip inline comments to prevent transmitting comment bytes over checksummed serial
            if ";" in raw:
                cmd_part, comment_part = raw.split(";", 1)
                cmd_part = cmd_part.strip()
                comment_part = comment_part.strip()
                if cmd_part:
                    desc = comment_part if comment_part else pending_desc
                    steps.append({"cmd": cmd_part, "desc": desc})
                    pending_desc = ""
            else:
                steps.append({"cmd": raw, "desc": pending_desc})
                pending_desc = ""
        return steps

    def load_local_protocol(self, filename, source="Unknown"):
        self.log(f"📂 Loading: {filename} (Source: {source})")
        target_path = None
        if os.path.exists(os.path.join(DIR_RECENT, filename)): 
            target_path = os.path.join(DIR_RECENT, filename)
        elif os.path.exists(os.path.join(DIR_TEST, filename)): 
            target_path = os.path.join(DIR_TEST, filename)
        
        if not target_path: 
            self.log(f"❌ File not found: {filename}")
            return

        try:
            with open(target_path, "r", encoding="utf-8") as f: 
                raw_lines = f.readlines()
            self.protocol_steps = self.parse_gcode_file(raw_lines)
            
            self.state["filename"] = filename
            self.state["started_by"] = source
            self.state["just_started"] = (source == "Remote")
            
            self.ptr = 0; self.seq_num = 1
            self.is_running = True; self.is_paused = False
            self.state["status"] = "Starting"
            self.state["stop_reason"] = None; self.state["error_msg"] = None; self.state["completed"] = False
            self.start_time = time.time(); self.smoothed_seconds = 0; self.state["est"] = "Calculating..."

            self._clear_command_queue()
            self._pending_protocol_start = True
            self._protocol_start_sent_time = time.time()
            self.command_queue.put(("SEQ_PKT", ("M110 N0", 0)))
            
            GPIO.output(self.PIN_PAUSE, 0)
            self.start_new_log_session(filename)
            if self.ser: 
                self.ser.reset_input_buffer()
        except Exception as e: 
            self.log(f"❌ Read Error: {e}")

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
            
            # 1. Reset sequence counters on both Pi and STM32
            self.seq_num = 1
            # Enqueue an explicit M110 packet with seq=0 so the run-loop will send it
            self.command_queue.put(("SEQ_PKT", ("M110 N0", 0)))
            self._pending_calib_start = True
            self._m110_sent_time = time.time()
        else:
            self.log("🔧 Calibration Ended")
            self.state["calib_status"] = "Idle"
            self.state["filename"] = "None"
            self.state["started_by"] = "Unknown"
            self.state["status"] = "Idle"
        try:
            self.sync_with_server()
        except Exception:
            pass
                    
    def reset_all_state(self, reset_calibration=False):
        self.state["stop_reason"] = None; self.state["completed"] = False; self.state["error_msg"] = None
        self.state["filename"] = "None"; self.state["started_by"] = "Unknown"
        self.state["status"] = "Idle"; self.state["current_line"] = "Ready"; self.state["current_desc"] = ""
        self.state["progress"] = 0; self.state["est"] = "--:--:--:--"
        # Condition Check: Only wipe calibration if explicitly triggered
        if reset_calibration:
            self.state["is_calibrated"] = False
        self.state["calibration_active"] = False
        self.state["calib_status"] = "Idle"
        self.state["calibration_source"] = None
        try:
            self.sync_with_server()
        except Exception:
            pass

    def hard_reset_pico(self):
        print("⚡ Hard Resetting MCU...", flush=True)
        self.expect_reset = True
        GPIO.output(self.PIN_RESET, 0)
        time.sleep(0.2)
        GPIO.output(self.PIN_RESET, 1)
        time.sleep(1.5)
        self.connection_time = time.time()
        self.state["is_calibrated"] = False

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

    def start_new_log_session(self, filename):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target_dir = DIR_CALIB_LOGS if "Calibration" in filename else DIR_PROTO_LOGS
        name = f"{filename}.log" if timestamp in filename else f"{filename}_{timestamp}.log"
        self.current_session_log_path = os.path.join(target_dir, name)
        self.log(f"🚀 Session Started: {name}")

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        print(entry, flush=True); self.state["logs"].append(entry)
        if len(self.state["logs"]) > 5: self.state["logs"].pop(0)
        self.log_accumulator.append(entry)
        
        try:
            with open(os.path.join(LOG_ROOT, "system_boot.log"), "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except:
            pass

        if self.current_session_log_path:
            try:
                with open(self.current_session_log_path, "a", encoding="utf-8") as f: 
                    f.write(entry + "\n")
            except: 
                pass

    def cleanup_old_logs(self, days=7):
        cutoff = time.time() - (days * 86400)
        def clean_dir(directory):
            c = 0
            try:
                for f in os.listdir(directory):
                    fpath = os.path.join(directory, f)
                    if os.path.isfile(fpath) and os.path.getctime(fpath) < cutoff:
                        os.remove(fpath); c += 1
            except: pass
            return c
        clean_dir(DIR_PROTO_LOGS); clean_dir(DIR_CALIB_LOGS)