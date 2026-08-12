#server v1.5 web Stream on cloud enabled server
#mediamtx -> webrtc -> https://app.lhrpi.dpdns.org/
# self hosted server with cloudflare tunnel using http version 
#just before Websoket and remote server this version is used
import time
from datetime import datetime
from flask import Flask, request,render_template_string, send_from_directory, jsonify, Response
import subprocess
import threading
import re
import signal
import atexit
from functools import wraps
import requests
#OS added for the files 
import os 
app = Flask(__name__)

# --- CONFIGURATION ---
UPLOAD_FOLDER = '/home/lhr/pc_protocols'
PC_LOG_ROOT = '/home/lhr/pc_logs'
PROTOCOLS_LOG_DIR = os.path.join(PC_LOG_ROOT, 'protocols_log')
SYSTEM_LOG_FILE = os.path.join(PC_LOG_ROOT, 'system.log')
# MediaMTX base URL - hardcoded default but can be overridden with environment variable
MEDIAMTX_BASE = os.environ.get('MEDIAMTX_BASE', 'http://localhost:8889')
VIDEO_STREAM_URL = os.environ.get('VIDEO_STREAM_URL', f"{MEDIAMTX_BASE}/cam/")
#stream variables
cloudflared_process = None
video_public_url = None
stop_event = threading.Event()

for folder in [UPLOAD_FOLDER, PC_LOG_ROOT, PROTOCOLS_LOG_DIR]:
    os.makedirs(folder, exist_ok=True)

# --- SHARED STATE ---
state = {
    "file_running": None,       
    "current_line": "Idle",     
    "progress": 0,              
    "est_completion": "N/A",    
    "status_text": "Offline",     
    "pending_commands": [],
    "started_by": "Unknown",
    
    # Calibration Sync State
    "calib_active": False,
    "calib_source": None,
    "calib_status": "Idle", # "Homing", "Moving", "Ready"
    "is_calibrated": False,  # New Flag: True only after successful save
    "light_on": False,
    "lid_open": False,
    "sensors": {}
}

def system_log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry, flush=True) 
    with open(SYSTEM_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def protocol_log(filename, log_data):
    if not filename: return
    log_path = os.path.join(PROTOCOLS_LOG_DIR, f"{filename}.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_data) 

# --- BROWSER ROUTES ---
USERNAME = "admin"
PASSWORD = "strongpassword"

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        "Authentication required", 401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route("/webrtc/offer", methods=["POST"])
def webrtc_offer():
    # Forward SDP offer to the configured mediamtx WebRTC endpoint using WHEP protocol.
    # WHEP (WebRTC HTTP Egress Protocol) is the standard for WebRTC reading on mediamtx.
    stream_path = "cam"  # The path configured in mediamtx.yml
    targets = [
        f"{MEDIAMTX_BASE}/{stream_path}/whep",
    ]
    
    last_exc = None
    for target in targets:
        try:
            system_log(f"Forwarding WebRTC offer to {target}")
            r = requests.post(
                target,
                data=request.data,
                headers={"Content-Type": "application/sdp"},
                timeout=10
            )
        except Exception as e:
            last_exc = e
            system_log(f"Error forwarding WebRTC offer to {target}: {e}")
            continue

        # Log useful diagnostics
        ct = r.headers.get('Content-Type', '')
        snippet = (r.content[:200] if isinstance(r.content, (bytes, bytearray)) else str(r.content))
        system_log(f"Upstream {target} returned {r.status_code} Content-Type:{ct} len={len(r.content) if r.content else 0} snippet={snippet!r}")

        # WHEP expects 201 Created with SDP answer, but also accept 200 OK for compatibility
        text = r.content.decode('utf-8', errors='replace') if isinstance(r.content, (bytes, bytearray)) else str(r.content)
        if r.status_code in [200, 201] and text.strip().startswith('v='):
            system_log(f"✅ Valid SDP answer received from {target} (status {r.status_code})")
            return (r.content, r.status_code, {"Content-Type": "application/sdp"})

        # Otherwise try next target
    # If we get here, all upstream attempts failed
    if last_exc:
        system_log(f"❌ All mediamtx targets failed. Last error: {last_exc}")
    return ("Upstream WebRTC error or invalid SDP returned", 502)

    
@app.route("/")
@requires_auth
def index():
    return render_template_string(HTML_CODE,video_public_url=VIDEO_STREAM_URL)
    
@app.route('/upload', methods=['POST'])
def upload():
    # 1. Validation Checks
    if state["calib_active"]:
        return "System is Calibrating. Please finish first.", 403
    if not state["is_calibrated"]:
        return "System requires calibration before running.", 403

    if 'upload' not in request.files: return "No file part", 400
    file = request.files['upload']
    if file.filename == '': return "No selected file", 400

    if file:
        file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        
        # 2. CAPTURE THERMAL SETTINGS
        try:
            t = float(request.form.get('target_temp', 0))
            m = request.form.get('fan_mode', 'Auto')
            f = int(float(request.form.get('fan_speed', 0)))
            
            # FIX 1: Wrap in "data" dict so Pi receives a Dictionary
            state["pending_commands"].append({
                "event": "SET_THERMAL", 
                "data": { 
                    "target_temp": t,
                    "fan_mode": m,
                    "fan_manual_val": f
                }
            })
            system_log(f"CMD: Set Thermal {t}°C, {m} Mode")
        except Exception as e:
            system_log(f"Warning: Failed to parse thermal settings: {e}")

        # 3. RUN COMMAND
        state["file_running"] = file.filename
        state["status_text"] = "Starting..."
        state["progress"] = 0
        state["started_by"] = "Remote"
        
        # FIX 2: Wrap in "data" LIST so Pi can unpack it like: fname, source = data
        state["pending_commands"].append({"event": "NEW_FILE", "filename": file.filename})
        system_log(f"USER: Uploaded {file.filename}")
        return "OK"
        
    return "Error", 400
# --- CONTROL ROUTES ---
@app.route('/pause')
def pause():
    state["pending_commands"].append({"event": "PAUSE"})
    state["status_text"] = "Paused (Remote)" 
    return "OK"

@app.route('/resume')
def resume():
    state["pending_commands"].append({"event": "RESUME"})
    state["status_text"] = "Resuming..."
    return "OK"

@app.route('/clear')
def clear():
    state["pending_commands"].append({"event": "CLEAR"})
    state["file_running"] = None
    state["status_text"] = "Stopped (Remote)"
    state["progress"] = 0
    state["est_completion"] = "--:--:--:--"
    return "OK"

# --- CALIBRATION ROUTES (REMOTE) ---
@app.route('/start-calibrate')
def start_calibrate():
    # Prevent Remote start if Local User is already calibrating
    if state["calib_active"] and state["calib_source"] == "User":
        return "LOCKED", 403
        
    # Send Start Command (Backend handles T00 logic)
    state["pending_commands"].append({"event": "CALIB_START"})
    state["status_text"] = "Calibration Mode"
    system_log("USER: Entered Calibration Mode (Remote)")
    return "OK"

@app.route('/calibrate')
def calibrate():
    dx = request.args.get('dx', 0)
    dy = request.args.get('dy', 0)
    # UPDATED: Capture Z1 and Z2 separately
    dz1 = request.args.get('dz1', 0)
    dz2 = request.args.get('dz2', 0)
    cmd = f"C dx={dx}, dy={dy}, dz={dz1}, dz2={dz2}" 
    state["pending_commands"].append({"event": "SERIAL_SEND", "data": cmd})
    return "OK"

@app.route('/calibrate-completed')
def calib_done():
    # Send OK_C to trigger save. 
    # NOTE: We do NOT send CALIB_END here. The Backend waits for C_OK response 
    # from hardware to confirm save and unlock automatically.
    state["pending_commands"].append({"event": "SERIAL_SEND", "data": "OK_C"})
    state["status_text"] = "Saving Offsets..."
    system_log("USER: Sent Save Command (Remote)")
    return "OK"

# --- DATA ROUTES ---
@app.route('/status')
def get_status():
    return jsonify(state)

@app.route('/logs')
def get_logs():
    if not os.path.exists(SYSTEM_LOG_FILE): return "Waiting for logs..."
    if not os.path.isfile(SYSTEM_LOG_FILE): return "Log file is invalid (directory exists)"
    try:
        with open(SYSTEM_LOG_FILE, 'r', encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-50:])
    except Exception as e:
        return f"Error reading logs: {str(e)}"

# --- PI INTERACTION ROUTES ---
@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/pi/sync', methods=['POST'])
def pi_sync():
    data = request.json
    
    # 1. Update Standard State
    state["file_running"] = data.get("file")
    state["current_line"] = data.get("line")
    state["progress"] = data.get("progress")
    state["est_completion"] = data.get("est")
    state["status_text"] = data.get("status", "Connected")
    if "started_by" in data:
        state["started_by"] = data["started_by"]
    
    # 2. Update Calibration State
    if "calib_active" in data:
        state["calib_active"] = data["calib_active"]
        state["calib_source"] = data.get("calib_source")
        state["calib_status"] = data.get("calib_status", "Idle")
        state["is_calibrated"] = data.get("is_calibrated", False)

    # 3. CAPTURE NEW SENSORS & LID
    state["light_on"] = data.get("light_on", False)
    state["lid_open"] = data.get("lid_open", False) # True = OPEN (Danger)
    state["sensors"] = data.get("sensors", {}) # Stores all temps/fans
    state["pipettes"] = data.get("pipettes", {})
    # 4. Handle Logs
    logs = data.get("logs")
    if logs:
        protocol_log(state["file_running"], logs)
        system_log(f"[PI] {logs.strip()}")

    # 5. Send Commands back to Pi
    cmds_to_send = state["pending_commands"][:]
    state["pending_commands"] = [] 
    
    return jsonify({"commands": cmds_to_send})




# --- HTML UI CODE ---
# --- HTML UI CODE ---
HTML_CODE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Liquid Handling Dashboard</title>
    <style>
        :root { --primary: #007bff; --success: #28a745; --warning: #ffc107; --danger: #dc3545; --dark: #343a40; --light: #f8f9fa; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #e9ecef; margin: 0; padding: 20px; }
        .container { max-width: 1100px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        
        header { text-align: center; margin-bottom: 20px; border-bottom: 2px solid var(--light); padding-bottom: 20px; }
        .status-badge { display: inline-block; padding: 8px 20px; border-radius: 30px; font-weight: bold; background: var(--dark); color: white; margin-top: 10px; font-size: 1.2rem;}
        
        /* CARDS */
        .card { background: var(--light); padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid var(--primary); box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        h2 { margin-top: 0; font-size: 1.2rem; color: var(--dark); border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 15px; }

        .btn { padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; color: white; transition: transform 0.1s; font-size:1rem;}
        .btn:active { transform: scale(0.98); }
        .btn-primary { background: var(--primary); }
        .btn-success { background: var(--success); }
        .btn-danger { background: var(--danger); }
        .btn-warning { background: var(--warning); color: #000; }
        
        .control-grid { display: flex; gap: 15px; justify-content: center; margin-bottom: 20px; }
        .calib-grid { display: grid; grid-template-columns: repeat(3, 60px); gap: 10px; justify-content: center; margin: 15px 0; }
        .calib-btn { padding: 15px; font-size: 1.5rem; background: white; border: 2px solid #ccc; cursor: pointer; border-radius: 8px; }
        
        pre { background: #212529; color: #00ff41; padding: 15px; border-radius: 5px; height: 250px; overflow-y: auto; font-size: 0.9rem; white-space: pre-wrap; }
        
        .progress-container { width: 100%; background: #ddd; height: 30px; border-radius: 15px; margin-top: 15px; overflow: hidden; position: relative; }
        .progress-bar { height: 100%; background: linear-gradient(90deg, #28a745, #218838); width: 0%; transition: width 0.5s; }
        .progress-text { position: absolute; width: 100%; text-align: center; line-height: 30px; font-weight: bold; color: #333; top: 0; }

        /* SENSOR GRID */
        .sensor-box { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px; text-align: center; }
        .sensor-item { background: white; padding: 10px; border-radius: 5px; border: 1px solid #ddd; }
        .sensor-val { font-size: 1.2rem; font-weight: bold; color: var(--dark); }
        .sensor-label { font-size: 0.8rem; color: #6c757d; margin-top: 5px; }
        
        .lid-badge { font-weight: bold; padding: 5px 10px; border-radius: 4px; display: inline-block; margin-left: 10px; }
        .lid-open { background: #ffcdd2; color: #c62828; border: 1px solid #ef5350; }
        .lid-closed { background: #c8e6c9; color: #2e7d32; border: 1px solid #66bb6a; }

        /* PIPETTE CARDS (NEW) */
        .pipette-container { display: flex; flex-direction: column; gap: 10px; }
        .pipette-card { 
            background: white; border-radius: 8px; border: 1px solid #ddd; padding: 12px; 
            display: flex; align-items: center; gap: 15px; position: relative; overflow: hidden;
            transition: all 0.2s;
        }
        .pipette-card.active { border-left: 5px solid var(--success); background: #f0fff4; }
        .pipette-card.empty { border-left: 5px solid #ccc; opacity: 0.7; }
        
        .pipette-icon { 
            width: 40px; height: 40px; background: #e9ecef; border-radius: 50%; 
            display: flex; align-items: center; justify-content: center; font-weight:bold; color: #555;
        }
        .pipette-info { flex: 1; }
        .p-model { font-weight: bold; font-size: 1rem; color: var(--dark); margin: 0; }
        .p-serial { font-size: 0.8rem; color: #6c757d; margin: 2px 0 0 0; font-family: monospace; }
        .p-badge { 
            position: absolute; right: 10px; top: 10px; font-size: 0.7rem; 
            font-weight: bold; background: #eee; padding: 2px 6px; border-radius: 4px; color: #555;
        }

        /* MODALS */
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.6); }
        .modal-content { background-color: #fefefe; margin: 10% auto; padding: 0; border-radius: 8px; width: 450px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
        .modal-header { padding: 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; color: white; text-align: center; font-size: 1.5rem; font-weight: bold; }
        .modal-body { padding: 20px; text-align: center; }
        .modal-footer { padding: 15px; text-align: center; border-top: 1px solid #eee; display: flex; justify-content: center; gap: 10px; }
        
        .bg-red { background: var(--danger); }
        .bg-green { background: var(--success); }
        .bg-blue { background: var(--primary); }
        .bg-orange { background: var(--warning); color: black !important; }

        /* SETUP FORM */
        .form-group { margin-bottom: 15px; text-align: left; }
        .form-label { display: block; font-weight: bold; margin-bottom: 5px; color: #555; }
        .form-input { width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 6px; box-sizing: border-box; }
        .toggle-btn { background: #ddd; color: #555; flex: 1; }
        .toggle-active { background: var(--primary); color: white; flex: 1; }

        /* SPINNERS */
        .blocker-overlay { display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.4); text-align: center; padding-top: 15%; }
        .info-modal { display: none; position: fixed; z-index: 1001; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
        .info-content { background-color: white; margin: 20% auto; padding: 30px; border-radius: 10px; width: 300px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div id="blockerModal" class="blocker-overlay">
        <div style="display: inline-block; padding: 40px; border: 4px solid #ffc107; border-radius: 15px; background: white;">
            <h1>🔒 SYSTEM LOCKED</h1><p>Local User is Calibrating...</p>
        </div>
    </div>
    <div id="homingModal" class="info-modal"><div class="info-content"><div class="spinner"></div><h2>🏠 HOMING...</h2><p>Finding home position...</p></div></div>
    <div id="movingModal" class="info-modal"><div class="info-content"><div class="spinner" style="border-top-color: #ffc107;"></div><h2>⚙️ MOVING...</h2><p>Moving to point...</p></div></div>

    <div id="lidWarningModal" class="modal">
        <div class="modal-content">
            <div class="modal-header bg-orange">⚠️ LID IS OPEN</div>
            <div class="modal-body"><p>Safety lid is open.</p><p>Proceed anyway?</p></div>
            <div class="modal-footer">
                <button class="btn btn-danger" onclick="closeModal('lidWarningModal')">Cancel</button>
                <button class="btn btn-success" onclick="openSetup()">Continue Anyway</button>
            </div>
        </div>
    </div>

    <div id="setupModal" class="modal">
        <div class="modal-content">
            <div class="modal-header bg-blue">PROTOCOL SETUP</div>
            <div class="modal-body">
                <div class="form-group"><label class="form-label">Target Temp (15-35°C)</label><input type="number" id="inpTemp" class="form-input" value="25" min="15" max="35"></div>
                <div class="form-group"><label class="form-label">Fan Mode</label>
                    <div style="display:flex; gap:10px;">
                        <button id="btnAuto" class="btn toggle-active" onclick="setMode('Auto')">Auto</button>
                        <button id="btnManual" class="btn toggle-btn" onclick="setMode('Manual')">Manual</button>
                    </div>
                </div>
                <div id="fanSpeedGroup" class="form-group" style="display:none;"><label class="form-label">Fan Speed (0-100%)</label><input type="number" id="inpFan" class="form-input" value="0" min="0" max="100"></div>
                <div id="setupError" style="color:red; font-weight:bold; margin-top:10px;"></div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-danger" onclick="closeModal('setupModal')">Cancel</button>
                <button class="btn btn-success" onclick="confirmSetup()">START RUN</button>
            </div>
        </div>
    </div>

    <div class="container">
        <header>
            <h1>💧 Liquid Handling Dashboard</h1>
            <div id="connectionStatus" style="color:red; display:none;">⚠️ DISCONNECTED</div>
            <div class="status-badge" id="robotState">Waiting...</div>
            <span id="lidStatus" class="lid-badge lid-closed">Lid Closed</span>
        </header>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
            
            <div>
                <div class="card" style="border-color: #17a2b8;">
                    <h2>📊 Sensor Readings</h2>
                    <div class="sensor-box">
                        <div class="sensor-item"><div id="val_env_t" class="sensor-val">--</div><div class="sensor-label">Env °C</div></div>
                        <div class="sensor-item"><div id="val_hum" class="sensor-val">--</div><div class="sensor-label">Hum %</div></div>
                        <div class="sensor-item"><div id="val_bed_t" class="sensor-val">--</div><div class="sensor-label">Bed °C</div></div>
                        <div class="sensor-item"><div id="val_cpu_t" class="sensor-val">--</div><div class="sensor-label">CPU °C</div></div>
                    </div>
                </div>

                <div class="card" style="border-color: var(--warning);">
                    <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
                        <div><strong>File:</strong> <span id="filename">None</span></div>
                        <div><strong>Line:</strong> <span id="currentLine">-</span></div>
                    </div>
                    <div class="progress-container">
                        <div id="progressBar" class="progress-bar"></div>
                        <div id="progressText" class="progress-text">0%</div>
                    </div>
                    <div class="control-grid" style="margin-top: 25px;">
                        <button class="btn btn-warning" onclick="sendCmd('pause')">Pause</button>
                        <button class="btn btn-primary" onclick="sendCmd('resume')">Resume</button>
                        <button class="btn btn-danger" onclick="sendCmd('clear')">Stop</button>
                    </div>
                </div>
            </div>

            <div>
                <div class="card" style="border-color: #6610f2; height: 100%; box-sizing: border-box;">
                    <h2>🧪 Pipettes</h2>
                    <div class="pipette-container">
                        
                        <div id="card_left" class="pipette-card empty">
                            <span class="p-badge">SLOT 1</span>
                            <div class="pipette-icon">1</div>
                            <div class="pipette-info">
                                <p id="p1_model" class="p-model">Empty</p>
                                <p id="p1_serial" class="p-serial">--</p>
                            </div>
                        </div>

                        <div id="card_right" class="pipette-card empty">
                            <span class="p-badge">SLOT 2</span>
                            <div class="pipette-icon">2</div>
                            <div class="pipette-info">
                                <p id="p2_model" class="p-model">Empty</p>
                                <p id="p2_serial" class="p-serial">--</p>
                            </div>
                        </div>
                    </div>

                    <h3 style="margin-top:20px; font-size:1rem; border-bottom:1px solid #eee; padding-bottom:5px;">Load Protocol</h3>
                    <form id="uploadForm" style="display:flex; flex-direction:column; gap:10px;">
                        <input type="file" id="fileInput" name="upload" accept=".gcode,.txt" class="form-input" required>
                        <button type="submit" class="btn btn-success" style="width:100%">Upload & Run</button>
                    </form>
                    <div id="uploadMsg" style="text-align:center; margin-top:5px; font-size:0.9rem;"></div>
                </div>
            </div>
        </div>

        <div class="card" style="border-color: #17a2b8; margin-top: 20px; z-index:1000;">
            <h2>📹 Live Video Stream</h2>
            <video id="video" autoplay muted playsinline controls style="width: 100%; height: 500px; background: #000; border-radius: 8px;"></video>
            <div id="videoStatus" style="text-align: center; margin-top: 10px; font-size: 0.9rem; color: #666;">Connecting to stream...</div>
        </div>

    <script>
    const video = document.getElementById("video");
    const statusDiv = document.getElementById("videoStatus");
    
    const pc = new RTCPeerConnection({
        iceServers: [{ urls: ["stun:stun.l.google.com:19302"] }]
    });
    
    pc.addTransceiver("video", { direction: "recvonly" });
    
    pc.ontrack = e => {
        console.log("Track received:", e.track.kind);
        video.srcObject = e.streams[0];
        
        // Ensure video plays (browsers require explicit play after setting srcObject)
        video.play().catch(err => {
            console.warn("Auto-play blocked by browser, video needs unmute:", err);
        });
        
        statusDiv.innerText = "✅ Stream connected";
        statusDiv.style.color = "#28a745";
    };
    
    pc.onconnectionstatechange = () => {
        console.log("Connection state:", pc.connectionState);
        if (pc.connectionState === "failed") {
            statusDiv.innerText = "❌ Connection failed";
            statusDiv.style.color = "#dc3545";
        }
    };
    
    pc.onerror = (err) => {
        console.error("PeerConnection error:", err);
    };

    let retryCount = 0;
    const MAX_RETRIES = 3;
    const RETRY_DELAY_MS = 2000;

    async function start() {
        try {
            statusDiv.innerText = "🔄 Creating offer...";
            statusDiv.style.color = "#ffc107";
            
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            let sdp = offer.sdp;
            
            // Note: With WHEP protocol, the path is in the URL (/cam/whep)
            // so we don't need to add x-mediamtx-path attribute
            
            console.log("Sending offer to /webrtc/offer...");
            const res = await fetch("/webrtc/offer", {
                method: "POST",
                body: sdp,
                headers: { "Content-Type": "application/sdp" },
                timeout: 5000
            });

            const answerSDP = await res.text();
            console.log("Response status:", res.status);
            
            if (!res.ok) {
                console.error('WebRTC offer failed:', res.status, answerSDP);
                statusDiv.innerText = "❌ Handshake failed: " + res.status;
                statusDiv.style.color = "#dc3545";
                scheduleRetry();
                return;
            }
            
            if (!answerSDP || !answerSDP.trim().startsWith('v=')) {
                console.error('Invalid SDP answer received:', answerSDP.slice(0,300));
                statusDiv.innerText = "❌ Invalid SDP response";
                statusDiv.style.color = "#dc3545";
                scheduleRetry();
                return;
            }
            
            try {
                console.log("Setting remote description...");
                await pc.setRemoteDescription({ type: "answer", sdp: answerSDP });
                console.log("Remote description set successfully");
                statusDiv.innerText = "🔗 Connecting...";
                statusDiv.style.color = "#17a2b8";
                retryCount = 0; // Reset on success
            } catch (err) {
                console.error('Failed to set remote description:', err, answerSDP.slice(0,300));
                statusDiv.innerText = "❌ Failed to set answer: " + err.message;
                statusDiv.style.color = "#dc3545";
                scheduleRetry();
            }
        } catch (err) {
            console.error('Error in WebRTC start:', err);
            statusDiv.innerText = "❌ Error: " + err.message;
            statusDiv.style.color = "#dc3545";
            scheduleRetry();
        }
    }

    function scheduleRetry() {
        if (retryCount < MAX_RETRIES) {
            retryCount++;
            const delay = RETRY_DELAY_MS * retryCount;
            console.log(`Scheduling retry ${retryCount}/${MAX_RETRIES} in ${delay}ms...`);
            statusDiv.innerText = `🔄 Retrying in ${Math.floor(delay/1000)}s... (${retryCount}/${MAX_RETRIES})`;
            statusDiv.style.color = "#ffc107";
            setTimeout(start, delay);
        } else {
            statusDiv.innerText = "❌ Connection failed. Refresh page to retry.";
            statusDiv.style.color = "#dc3545";
        }
    }

    // Start connection on page load
    start();
    </script>

        <div class="card" style="border-color: var(--dark); margin-top: 20px;">
            <h2>🔧 Calibration</h2>
            <div style="text-align: center;">
                <button id="btnStartCalib" class="btn btn-primary" onclick="startCalibrate()">Enter Mode</button>
                <div id="calibControls" style="display:none;">
                    <div style="margin-bottom: 15px;">
                        <label style="font-weight:bold; color:#555;">Step: </label>
                        <select id="stepSize" style="padding: 5px; border-radius: 4px;"><option value="0.1">0.1 mm</option><option value="1" selected>1.0 mm</option><option value="10">10.0 mm</option></select>
                    </div>
                    <div class="calib-grid">
                        <div></div><button class="calib-btn" onclick="move('up')">Y+</button><div></div>
                        <button class="calib-btn" onclick="move('left')">X-</button><button class="calib-btn" onclick="move('down')">Y-</button><button class="calib-btn" onclick="move('right')">X+</button>
                    </div>
                    <div style="margin-top:10px;">
                        <span style="font-weight:bold;">Z1:</span> <button class="btn btn-primary" onclick="move('z1up')">▲</button> <button class="btn btn-primary" onclick="move('z1down')">▼</button>
                        <span style="margin-left:15px; font-weight:bold;">Z2:</span> <button class="btn btn-primary" onclick="move('z2up')">▲</button> <button class="btn btn-primary" onclick="move('z2down')">▼</button>
                    </div>
                    <div style="margin-top:10px;"><button class="btn btn-success" onclick="saveOffsets()">💾 Save</button></div>
                </div>
            </div>
        </div>

        <div class="card" style="border-color: #6c757d;"><h2>📜 Logs</h2><pre id="logs">Loading...</pre></div>
    </div>

    <div id="msgModal" class="modal"><div class="modal-content"><div id="msgHeader" class="modal-header"></div><div id="msgBody" class="modal-body"></div><div class="modal-footer"><button class="btn btn-primary" onclick="closeModal('msgModal')">OK</button></div></div></div>

    <script>
        // GLOBALS
        let pendingFormData = null;
        let isLidOpen = false;
        let isCalibrated = false;
        let fanMode = "Auto";
        let currentPipettes = { 
            left: { found: false }, 
            right: { found: false } 
        };
        
        // DOM HELPERS
        function closeModal(id) { document.getElementById(id).style.display = "none"; }
        function sendCmd(ep) { fetch('/' + ep); }
        function showMsg(title, body, cls) {
            document.getElementById('msgHeader').className = "modal-header bg-" + cls;
            document.getElementById('msgHeader').innerText = title;
            document.getElementById('msgBody').innerText = body;
            document.getElementById('msgModal').style.display = "block";
        }

        // --- SETUP LOGIC ---
        function setMode(m) {
            fanMode = m;
            document.getElementById('btnAuto').className = m==='Auto' ? "btn toggle-active" : "btn toggle-btn";
            document.getElementById('btnManual').className = m==='Manual' ? "btn toggle-active" : "btn toggle-btn";
            document.getElementById('fanSpeedGroup').style.display = m==='Manual' ? "block" : "none";
        }

        function openSetup() {
            closeModal('lidWarningModal');
            document.getElementById('setupModal').style.display = 'block';
            document.getElementById('setupError').innerText = "";
        }

        function confirmSetup() {
            const t = parseFloat(document.getElementById('inpTemp').value);
            const f = parseFloat(document.getElementById('inpFan').value);
            const err = document.getElementById('setupError');
            if (isNaN(t) || t < 15 || t > 35) { err.innerText = "Temp must be 15 - 35 °C"; return; }
            if (fanMode === 'Manual' && (isNaN(f) || f < 0 || f > 100)) { err.innerText = "Fan must be 0 - 100 %"; return; }
            if(!pendingFormData) { err.innerText = "Error: File lost."; return; }

            pendingFormData.append('target_temp', t);
            pendingFormData.append('fan_mode', fanMode);
            pendingFormData.append('fan_speed', f);
            closeModal('setupModal');
            doUpload(pendingFormData);
        }

        // --- UPLOAD ---
        document.getElementById('uploadForm').onsubmit = (e) => {
            e.preventDefault();
            if (!isCalibrated) { showMsg("🛑 ERROR", "Calibration Required first!", "red"); return; }
            pendingFormData = new FormData(e.target);
            if (isLidOpen) document.getElementById('lidWarningModal').style.display = "block";
            else openSetup();
        };

        async function doUpload(formData) {
            const msg = document.getElementById('uploadMsg');
            msg.innerText = "Uploading...";
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                msg.innerText = res.ok ? "✅ Started" : "❌ Failed";
            } catch(e) { msg.innerText = "❌ Error"; }
        }

        // --- CALIBRATION ---
        function startCalibrate() {
            
            // 1. SAFETY CHECK: Are any pipettes attached?
            const p1 = currentPipettes.left && currentPipettes.left.found;
            const p2 = currentPipettes.right && currentPipettes.right.found;

            if (!p1 && !p2) {
                // Both empty -> Block and Show Error
                showMsg("⚠️ NO PIPETTES", "Cannot calibrate without a pipette attached.\nPlease insert a pipette and try again.", "orange");
                return;
            }
            
            fetch('/start-calibrate'); 
            
        }
            
            
        function move(dir) { 
            const step = parseFloat(document.getElementById('stepSize').value);
            let dx=0, dy=0, dz1=0, dz2=0;
            if(dir==='left') dx=-step; else if(dir==='right') dx=step;
            else if(dir==='down') dy=-step; else if(dir==='up') dy=step;
            else if(dir==='z1down') dz1=-step; else if(dir==='z1up') dz1=step;
            else if(dir==='z2down') dz2=-step; else if(dir==='z2up') dz2=step;
            fetch(`/calibrate?dx=${dx}&dy=${dy}&dz1=${dz1}&dz2=${dz2}`);
        }
        function saveOffsets() { fetch('/calibrate-completed'); }

        // --- MAIN STATUS LOOP ---
        setInterval(() => {
            fetch('/status').then(r => r.json()).then(data => {
                isLidOpen = data.lid_open;
                isCalibrated = data.is_calibrated;
                
                document.getElementById('robotState').innerText = data.status_text || "Idle";
                document.getElementById('filename').innerText = data.file_running || "None";
                document.getElementById('currentLine').innerText = data.current_line || "-";
                
                const pct = data.progress || 0;
                document.getElementById('progressBar').style.width = pct + "%";
                document.getElementById('progressText').innerText = pct + "%";

                const lidEl = document.getElementById('lidStatus');
                lidEl.className = isLidOpen ? "lid-badge lid-open" : "lid-badge lid-closed";
                lidEl.innerText = isLidOpen ? "⚠️ Lid Open" : "🔒 Lid Closed";

                const s = data.sensors || {};
                document.getElementById('val_env_t').innerText = (s.bme_temp || 0).toFixed(1) + "°";
                document.getElementById('val_hum').innerText = (s.bme_hum || 0).toFixed(0) + "%";
                document.getElementById('val_bed_t').innerText = (s.adt_temp || 0).toFixed(1) + "°";
                document.getElementById('val_cpu_t').innerText = (s.cpu_temp || 0) + "°";

                // --- PIPETTE UPDATES (THIS WAS MISSING IN YOUR UI) ---
                const pips = data.pipettes || {};
                currentPipettes = data.pipettes || { left: {found:false}, right: {found:false} };
                // Update UI Cards (existing code)
                updatePipetteCard(currentPipettes.left, 'card_left', 'p1_model', 'p1_serial');
                updatePipetteCard(currentPipettes.right, 'card_right', 'p2_model', 'p2_serial');
                currentPipettes = data.pipettes || { left: {found:false}, right: {found:false} };
            
                

                // --- CALIBRATION MODALS ---
                const homing = document.getElementById("homingModal");
                const moving = document.getElementById("movingModal");
                const ctrls = document.getElementById('calibControls');
                const btn = document.getElementById('btnStartCalib');
                const blocker = document.getElementById("blockerModal");

                if (data.calib_active && data.calib_source === "Remote") {
                    btn.style.display = 'none';
                    if (data.calib_status === "Homing") { homing.style.display="block"; moving.style.display="none"; ctrls.style.display="none"; }
                    else if (data.calib_status === "Moving") { homing.style.display="none"; moving.style.display="block"; ctrls.style.display="none"; }
                    else if (data.calib_status === "Ready") { homing.style.display="none"; moving.style.display="none"; ctrls.style.display="block"; }
                } else {
                    homing.style.display="none"; moving.style.display="none";
                    if (!data.calib_active) { ctrls.style.display='none'; btn.style.display='inline-block'; }
                }

                blocker.style.display = (data.calib_active && data.calib_source !== "Remote") ? "block" : "none";
                document.getElementById('connectionStatus').style.display = 'none';
            }).catch(() => document.getElementById('connectionStatus').style.display = 'block');
            
            fetch('/logs').then(r => r.text()).then(txt => {
                const logEl = document.getElementById('logs');
                if(logEl.scrollHeight - logEl.clientHeight <= logEl.scrollTop + 50) logEl.scrollTop = logEl.scrollHeight;
                logEl.innerText = txt;
            });
        }, 1000);

        function updatePipetteCard(data, cardId, modelId, serialId) {
            const card = document.getElementById(cardId);
            const m = document.getElementById(modelId);
            const s = document.getElementById(serialId);
            if(data && data.found) {
                card.className = "pipette-card active";
                m.innerText = data.model || "Unknown";
                m.style.color = "#28a745";
                s.innerText = "SN: " + (data.id || "--");
            } else {
                card.className = "pipette-card empty";
                m.innerText = "Empty";
                m.style.color = "#999";
                s.innerText = "--";
            }
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
