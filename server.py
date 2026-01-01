#v1.0
# import os
# import time
# from datetime import datetime
# from flask import Flask, request, render_template_string, send_from_directory, jsonify

# app = Flask(__name__)

# # --- CONFIGURATION ---
# UPLOAD_FOLDER = 'pc_protocols'
# PC_LOG_ROOT = 'pc_logs'
# PROTOCOLS_LOG_DIR = os.path.join(PC_LOG_ROOT, 'protocols_log')
# SYSTEM_LOG_FILE = os.path.join(PC_LOG_ROOT, 'system.log')

# for folder in [UPLOAD_FOLDER, PC_LOG_ROOT, PROTOCOLS_LOG_DIR]:
#     os.makedirs(folder, exist_ok=True)

# # --- SHARED STATE ---
# state = {
#     "file_running": None,       
#     "current_line": "Idle",     
#     "progress": 0,              
#     "est_completion": "N/A",    
#     "status_text": "Offline",     
#     "pending_commands": [],
#     "started_by": "Unknown",
    
#     # Calibration Sync State
#     "calib_active": False,
#     "calib_source": None,
#     "calib_status": "Idle", # "Homing", "Moving", "Ready"
#     "is_calibrated": False  # New Flag: True only after successful save
# }

# # --- HELPER FUNCTIONS ---
# def system_log(msg):
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     entry = f"[{timestamp}] {msg}"
#     print(entry, flush=True) 
#     with open(SYSTEM_LOG_FILE, "a", encoding="utf-8") as f:
#         f.write(entry + "\n")

# def protocol_log(filename, log_data):
#     if not filename: return
#     log_path = os.path.join(PROTOCOLS_LOG_DIR, f"{filename}.log")
#     with open(log_path, "a", encoding="utf-8") as f:
#         f.write(log_data) 

# # --- BROWSER ROUTES ---
# @app.route('/')
# def index():
#     return render_template_string(HTML_CODE)

# @app.route('/upload', methods=['POST'])
# def upload():
#     # 1. Block if actively calibrating
#     if state["calib_active"]:
#         return "System is Calibrating. Please finish first.", 403
        
#     # 2. Block if NOT calibrated yet
#     if not state["is_calibrated"]:
#         return "System requires calibration before running.", 403

#     file = request.files['upload']
#     if file:
#         file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        
#         # Immediate UI Update
#         state["file_running"] = file.filename
#         state["status_text"] = "Starting..."
#         state["progress"] = 0
#         state["started_by"] = "Remote"
        
#         # Queue Command for Pi
#         state["pending_commands"].append({"event": "NEW_FILE", "filename": file.filename})
#         system_log(f"USER: Uploaded {file.filename}")
#         return "OK"
#     return "Error", 400

# # --- CONTROL ROUTES ---
# @app.route('/pause')
# def pause():
#     state["pending_commands"].append({"event": "PAUSE"})
#     state["status_text"] = "Paused (Remote)" 
#     return "OK"

# @app.route('/resume')
# def resume():
#     state["pending_commands"].append({"event": "RESUME"})
#     state["status_text"] = "Resuming..."
#     return "OK"

# @app.route('/clear')
# def clear():
#     state["pending_commands"].append({"event": "CLEAR"})
#     state["file_running"] = None
#     state["status_text"] = "Stopped (Remote)"
#     state["progress"] = 0
#     state["est_completion"] = "--:--:--:--"
#     return "OK"

# # --- CALIBRATION ROUTES (REMOTE) ---
# @app.route('/start-calibrate')
# def start_calibrate():
#     # Prevent Remote start if Local User is already calibrating
#     if state["calib_active"] and state["calib_source"] == "User":
#         return "LOCKED", 403
        
#     # Send Start Command (Backend handles T00 logic)
#     state["pending_commands"].append({"event": "CALIB_START"})
#     state["status_text"] = "Calibration Mode"
#     system_log("USER: Entered Calibration Mode (Remote)")
#     return "OK"

# @app.route('/calibrate')
# def calibrate():
#     dx = request.args.get('dx', 0)
#     dy = request.args.get('dy', 0)
#     dz = request.args.get('dz', 0)
#     cmd = f"C dx={dx}, dy={dy}, dz={dz}" 
#     state["pending_commands"].append({"event": "SERIAL_SEND", "data": cmd})
#     return "OK"

# @app.route('/calibrate-completed')
# def calib_done():
#     # Send OK_C to trigger save. 
#     # NOTE: We do NOT send CALIB_END here. The Backend waits for C_OK response 
#     # from hardware to confirm save and unlock automatically.
#     state["pending_commands"].append({"event": "SERIAL_SEND", "data": "OK_C"})
#     state["status_text"] = "Saving Offsets..."
#     system_log("USER: Sent Save Command (Remote)")
#     return "OK"

# # --- DATA ROUTES ---
# @app.route('/status')
# def get_status():
#     return jsonify(state)

# @app.route('/logs')
# def get_logs():
#     if not os.path.exists(SYSTEM_LOG_FILE): return "Waiting for logs..."
#     with open(SYSTEM_LOG_FILE, 'r', encoding="utf-8") as f:
#         lines = f.readlines()
#         return "".join(lines[-50:])

# # --- PI INTERACTION ROUTES ---
# @app.route('/download/<filename>')
# def download(filename):
#     return send_from_directory(UPLOAD_FOLDER, filename)

# @app.route('/pi/sync', methods=['POST'])
# def pi_sync():
#     data = request.json
    
#     # 1. Update Standard State
#     state["file_running"] = data.get("file")
#     state["current_line"] = data.get("line")
#     state["progress"] = data.get("progress")
#     state["est_completion"] = data.get("est")
#     state["status_text"] = data.get("status", "Connected")
#     if "started_by" in data:
#         state["started_by"] = data["started_by"]
    
#     # 2. Update Calibration State
#     if "calib_active" in data:
#         state["calib_active"] = data["calib_active"]
#         state["calib_source"] = data.get("calib_source")
#         state["calib_status"] = data.get("calib_status", "Idle")
#         state["is_calibrated"] = data.get("is_calibrated", False)

#     # 3. Handle Logs
#     logs = data.get("logs")
#     if logs:
#         protocol_log(state["file_running"], logs)
#         system_log(f"[PI] {logs.strip()}")

#     # 4. Send Commands back to Pi
#     cmds_to_send = state["pending_commands"][:]
#     state["pending_commands"] = [] 
    
#     return jsonify({"commands": cmds_to_send})


# # --- HTML UI CODE ---
# HTML_CODE = r"""
# <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="utf-8" />
#     <meta name="viewport" content="width=device-width, initial-scale=1" />
#     <title>Liquid Handling Dashboard</title>
#     <style>
#         :root { --primary: #007bff; --success: #28a745; --warning: #ffc107; --danger: #dc3545; --dark: #343a40; --light: #f8f9fa; }
#         body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #e9ecef; margin: 0; padding: 20px; }
#         .container { max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        
#         header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid var(--light); padding-bottom: 20px; }
#         .status-badge { display: inline-block; padding: 8px 20px; border-radius: 30px; font-weight: bold; background: var(--dark); color: white; margin-top: 10px; font-size: 1.2rem;}
        
#         .card { background: var(--light); padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid var(--primary); box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
#         h2 { margin-top: 0; font-size: 1.2rem; color: var(--dark); }

#         .upload-area { display: flex; gap: 10px; align-items: center; justify-content: center; }
#         input[type="file"] { border: 1px solid #ccc; padding: 5px; border-radius: 4px; background: white; }
        
#         .btn { padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; color: white; transition: transform 0.1s; font-size:1rem;}
#         .btn:active { transform: scale(0.98); }
#         .btn-primary { background: var(--primary); }
#         .btn-success { background: var(--success); }
#         .btn-danger { background: var(--danger); }
#         .btn-warning { background: var(--warning); color: #000; }
        
#         .control-grid { display: flex; gap: 15px; justify-content: center; margin-bottom: 20px; }

#         .calib-grid { display: grid; grid-template-columns: repeat(3, 60px); gap: 10px; justify-content: center; margin: 15px 0; }
#         .calib-btn { padding: 15px; font-size: 1.5rem; background: white; border: 2px solid #ccc; cursor: pointer; border-radius: 8px; }
#         .calib-btn:active { background: #ddd; }
        
#         pre { background: #212529; color: #00ff41; padding: 15px; border-radius: 5px; height: 250px; overflow-y: auto; font-size: 0.9rem; white-space: pre-wrap; }
        
#         .progress-container { width: 100%; background: #ddd; height: 30px; border-radius: 15px; margin-top: 15px; overflow: hidden; position: relative; }
#         .progress-bar { height: 100%; background: linear-gradient(90deg, #28a745, #218838); width: 0%; transition: width 0.5s; }
#         .progress-text { position: absolute; width: 100%; text-align: center; line-height: 30px; font-weight: bold; color: #333; top: 0; }

#         /* --- BLOCKER OVERLAY --- */
#         .blocker-overlay {
#             display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%;
#             background-color: rgba(255, 255, 255, 0.95); text-align: center; padding-top: 15%;
#         }
#         .blocker-box {
#             display: inline-block; padding: 40px; border: 4px solid #ffc107; border-radius: 15px;
#             background: white; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
#         }

#         /* --- INFO MODALS (Homing/Moving) --- */
#         .info-modal { display: none; position: fixed; z-index: 1001; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
#         .info-content {
#             background-color: white; margin: 20% auto; padding: 30px; border-radius: 10px; width: 300px; 
#             text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.3);
#         }
#         .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px auto; }
#         @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

#         /* --- GENERIC MODAL --- */
#         .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.6); }
#         .modal-content { 
#             background-color: #fefefe; margin: 15% auto; padding: 0; border-radius: 8px; width: 400px; 
#             box-shadow: 0 4px 20px rgba(0,0,0,0.2); animation: popin 0.3s ease;
#         }
#         @keyframes popin { from {transform: scale(0.5); opacity: 0;} to {transform: scale(1); opacity: 1;} }
        
#         .modal-header { padding: 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; color: white; text-align: center; font-size: 1.5rem; font-weight: bold; }
#         .modal-body { padding: 20px; text-align: center; font-size: 1.1rem; color: #333; }
#         .modal-footer { padding: 15px; text-align: center; border-top: 1px solid #eee; }
        
#         .bg-red { background: var(--danger); }
#         .bg-green { background: var(--success); }
#         .bg-blue { background: var(--primary); }
#         .bg-orange { background: var(--warning); color: black !important; }
#     </style>
# </head>
# <body>
#     <div id="blockerModal" class="blocker-overlay">
#         <div class="blocker-box">
#             <div style="font-size: 4rem;">🔒</div>
#             <h1 style="color: #ffc107; margin: 10px 0;">SYSTEM LOCKED</h1>
#             <p style="font-size: 1.2rem; color: #555;">Calibration in progress on Local Device (User)</p>
#             <p style="color: #999;">Please wait until it finishes.</p>
#         </div>
#     </div>

#     <div id="homingModal" class="info-modal">
#         <div class="info-content">
#             <div class="spinner"></div>
#             <h2>🏠 HOMING...</h2>
#             <p>Please wait while the robot finds home position.</p>
#         </div>
#     </div>

#     <div id="movingModal" class="info-modal">
#         <div class="info-content">
#             <div class="spinner" style="border-top-color: #ffc107;"></div>
#             <h2>⚙️ MOVING...</h2>
#             <p>Moving to calibration point...</p>
#         </div>
#     </div>

#     <div class="container">
#         <header>
#             <h1>💧 Liquid Handling Robot</h1>
#             <div id="connectionStatus" style="color:red; font-weight:bold; display:none; margin-bottom:5px;">⚠️ SERVER DISCONNECTED</div>
#             <div class="status-badge" id="robotState">Waiting for Pi...</div>
#             <div id="sourceDisplay" style="margin-top:5px; color:#555; font-weight:bold;">
#             Source:
#             </div>
#         </header>

#         <div class="card" style="border-color: var(--warning);">
#             <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
#                 <div><strong>File:</strong> <span id="filename">None</span></div>
#                 <div><strong>Line:</strong> <span id="currentLine" style="font-family: monospace;">-</span></div>
#                 <div><strong>Time:</strong> <span id="estTime">-</span></div>
#             </div>
            
#             <div class="progress-container">
#                 <div id="progressBar" class="progress-bar"></div>
#                 <div id="progressText" class="progress-text">0%</div>
#             </div>

#             <div class="control-grid" style="margin-top: 25px;">
#                 <button class="btn btn-warning" onclick="sendCmd('pause')">❚❚ Pause</button>
#                 <button class="btn btn-primary" onclick="sendCmd('resume')">▶ Resume</button>
#                 <button class="btn btn-danger" onclick="sendCmd('clear')">■ Stop</button>
#             </div>
#         </div>

#         <div class="card" style="border-color: var(--primary);">
#             <h2>📂 File Upload</h2>
#             <form id="uploadForm" class="upload-area">
#                 <input type="file" name="upload" accept=".gcode,.txt" required>
#                 <button type="submit" class="btn btn-success">Upload & Run</button>
#             </form>
#             <div id="uploadMsg" style="text-align:center; margin-top:5px;"></div>
#         </div>

#         <div class="card" style="border-color: var(--dark);">
#             <h2>🔧 Calibration</h2>
#             <div style="text-align: center;">
#                 <button id="btnStartCalib" class="btn btn-primary" onclick="startCalibrate()">Enter Mode</button>
#                 <div id="calibControls" style="display:none;">
#                     <div class="calib-grid">
#                         <div></div><button class="calib-btn" onclick="move('up')">Y+</button><div></div>
#                         <button class="calib-btn" onclick="move('left')">X-</button><button class="calib-btn" onclick="move('down')">Y-</button><button class="calib-btn" onclick="move('right')">X+</button>
#                     </div>
#                     <div>
#                         <button class="btn btn-primary" onclick="move('zup')">Z+</button>
#                         <button class="btn btn-primary" onclick="move('zdown')">Z-</button>
#                     </div>
#                     <div style="margin-top:10px;">
#                         <label>Step: <select id="stepSize"><option value="0.1">0.1mm</option><option value="1" selected>1mm</option><option value="10">10mm</option></select></label>
#                         <button class="btn btn-success" onclick="saveOffsets()">💾 Save</button>
#                     </div>
#                 </div>
#             </div>
#         </div>

#         <div class="card" style="border-color: #6c757d;">
#             <h2>📜 Logs</h2>
#             <pre id="logs">Loading...</pre>
#         </div>
#     </div>

#     <div id="statusModal" class="modal">
#         <div class="modal-content">
#             <div id="modalHeader" class="modal-header">Title</div>
#             <div id="modalBody" class="modal-body">Message</div>
#             <div class="modal-footer">
#                 <button class="btn btn-primary" onclick="closeModal('statusModal')">OK</button>
#             </div>
#         </div>
#     </div>

#     <div id="calibNeededModal" class="modal">
#         <div class="modal-content">
#             <div class="modal-header bg-red">🛑 CALIBRATION REQUIRED</div>
#             <div class="modal-body">
#                 <div style="font-size: 3rem;">⚠️</div>
#                 <p>You must calibrate the system before running any protocol.</p>
#             </div>
#             <div class="modal-footer">
#                 <button class="btn btn-primary" onclick="closeModal('calibNeededModal')">OK</button>
#             </div>
#         </div>
#     </div>

#     <script>
#         let lastStatus = "";
#         let lastFilename = "None"; 
#         let wasCalibActive = false;
#         let lastCalibSource = "";
        
#         const modal = document.getElementById("statusModal");
#         const mHeader = document.getElementById("modalHeader");
#         const mBody = document.getElementById("modalBody");
#         const blocker = document.getElementById("blockerModal");
#         const homingModal = document.getElementById("homingModal");
#         const movingModal = document.getElementById("movingModal");
#         const calibNeededModal = document.getElementById("calibNeededModal");

#         function showModal(title, msg, type) {
#             mHeader.innerText = title;
#             mBody.innerText = msg;
#             mHeader.className = "modal-header bg-" + type;
#             modal.style.display = "block";
#         }

#         function closeModal(id) { 
#             document.getElementById(id).style.display = "none"; 
#         }
        
#         function sendCmd(endpoint) { fetch('/' + endpoint); }

#         function startCalibrate() {
#             fetch('/start-calibrate').then(r => {
#                 if(r.status === 403) alert("Cannot start: Device User is already calibrating.");
#                 else {
#                     document.getElementById('btnStartCalib').style.display = 'none';
#                     // We don't show controls yet; we wait for 'Ready' status
#                 }
#             });
#         }
        
#         function move(dir) {
#             const step = document.getElementById('stepSize').value;
#             let dx=0, dy=0, dz=0;
#             if(dir==='up') dy = step; if(dir==='down') dy = -step;
#             if(dir==='right') dx = step; if(dir==='left') dx = -step;
#             if(dir==='zup') dz = step; if(dir==='zdown') dz = -step;
#             fetch(`/calibrate?dx=${dx}&dy=${dy}&dz=${dz}`);
#         }

#         function saveOffsets() {
#             fetch('/calibrate-completed').then(() => {
#                 alert("Offsets Saved!");
#                 document.getElementById('calibControls').style.display = 'none';
#                 document.getElementById('btnStartCalib').style.display = 'inline-block';
#             });
#         }

#         document.getElementById('uploadForm').onsubmit = async (e) => {
#             e.preventDefault();
#             const formData = new FormData(e.target);
#             const msg = document.getElementById('uploadMsg');
#             msg.innerText = "Uploading...";
#             try {
#                 const res = await fetch('/upload', { method: 'POST', body: formData });
#                 if(res.ok) {
#                     msg.innerText = "✅ Started"; 
#                 } else if (res.status === 403) {
#                     msg.innerText = "🛑 Blocked";
#                     // SHOW CALIBRATION NEEDED POPUP
#                     calibNeededModal.style.display = "block";
#                 } else {
#                     msg.innerText = "❌ Failed";
#                 }
#             } catch(err) { msg.innerText = "❌ Error"; }
#         };

#         setInterval(() => {
#             fetch('/status').then(r => r.json()).then(data => {
#                 const status = data.status_text || "Idle";
#                 const filename = data.file_running || "None";
#                 const startedBy = data.started_by || "Unknown";
                
#                 // --- BLOCKER LOGIC (Web) ---
#                 if (data.calib_active && data.calib_source !== "Remote") {
#                     blocker.style.display = "block";
#                 } else {
#                     blocker.style.display = "none";
#                 }

#                 // --- CALIBRATION STATUS POPUPS (For Remote User) ---
#                 if (data.calib_active && data.calib_source === "Remote") {
#                     if (data.calib_status === "Homing") {
#                         homingModal.style.display = "block";
#                         movingModal.style.display = "none";
#                         document.getElementById('calibControls').style.display = 'none';
#                     } else if (data.calib_status === "Moving") {
#                         homingModal.style.display = "none";
#                         movingModal.style.display = "block";
#                         document.getElementById('calibControls').style.display = 'none';
#                     } else if (data.calib_status === "Ready") {
#                         homingModal.style.display = "none";
#                         movingModal.style.display = "none";
#                         document.getElementById('calibControls').style.display = 'block';
#                     }
#                 } else {
#                     homingModal.style.display = "none";
#                     movingModal.style.display = "none";
#                     if (!data.calib_active) {
#                         document.getElementById('calibControls').style.display = 'none';
#                         document.getElementById('btnStartCalib').style.display = 'inline-block';
#                     }
#                 }

#                 // --- COMPLETION NOTIFICATION (Correct Logic) ---
#                 if (wasCalibActive && !data.calib_active) {
#                     // Check if strictly Calibrated (saved)
#                     if (data.is_calibrated === true) {
#                         if (lastCalibSource !== "Remote") { 
#                              const now = new Date().toLocaleTimeString();
#                              showModal("🔔 NOTIFICATION", `Calibration finished by User.\nTime: ${now}`, "green");
#                         }
#                     }
#                 }
#                 wasCalibActive = data.calib_active;
#                 lastCalibSource = data.calib_source;

#                // --- UI UPDATES ---
#                 document.getElementById('robotState').innerText = status;
                
#                 // --- FIX IS HERE (Corrected .innerText) ---
#                 document.getElementById('filename').innerText = filename; 
                
#                 document.getElementById('sourceDisplay').innerText = "Source: " + startedBy;
#                 document.getElementById('currentLine').innerText = data.current_line || "-";
#                 document.getElementById('estTime').innerText = data.est_completion || "-";
                
#                 const pct = data.progress || 0;
#                 document.getElementById('progressBar').style.width = pct + "%";
#                 document.getElementById('progressText').innerText = pct + "%";
 
#                 if ( source !== "Unknown" && filename !== "None" && filename !== lastFilename ) {
#                      showModal("🚀 STARTED", `Protocol: ${filename}\nSource: ${startedBy}`, "blue");
#                 }
#                 lastFilename = filename;

#                 if (status !== lastStatus) {
#                     if (status.includes("Error")) {
#                         showModal("❌ ERROR", "Hardware Error Detected.\nCheck Logs.", "red");
#                     } else if (status === "Done") {
#                         showModal("🎉 COMPLETED", "Protocol Finished Successfully.", "green");
#                     } else if (status.includes("Stopped")) {
#                         showModal("⚠️ STOPPED", `Protocol was stopped.\nStatus: ${status}`, "orange");
#                     }
#                     lastStatus = status;
#                 }
#                 document.getElementById('connectionStatus').style.display = 'none';
#             }).catch(() => document.getElementById('connectionStatus').style.display = 'block');

#             fetch('/logs').then(r => r.text()).then(txt => {
#                 const logEl = document.getElementById('logs');
#                 const isBottom = logEl.scrollHeight - logEl.clientHeight <= logEl.scrollTop + 50;
#                 logEl.innerText = txt;
#                 if(isBottom) logEl.scrollTop = logEl.scrollHeight;
#             });
#         }, 1000);
#     </script>
# </body>
# </html>
# """

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)

#v1.3 lidopen popup and sensor readings 
# import os
# import time
# from datetime import datetime
# from flask import Flask, request, render_template_string, send_from_directory, jsonify

# app = Flask(__name__)

# # --- CONFIGURATION ---
# UPLOAD_FOLDER = 'pc_protocols'
# PC_LOG_ROOT = 'pc_logs'
# PROTOCOLS_LOG_DIR = os.path.join(PC_LOG_ROOT, 'protocols_log')
# SYSTEM_LOG_FILE = os.path.join(PC_LOG_ROOT, 'system.log')

# for folder in [UPLOAD_FOLDER, PC_LOG_ROOT, PROTOCOLS_LOG_DIR]:
#     os.makedirs(folder, exist_ok=True)

# # --- SHARED STATE ---
# state = {
#     "file_running": None,       
#     "current_line": "Idle",     
#     "progress": 0,              
#     "est_completion": "N/A",    
#     "status_text": "Offline",     
#     "pending_commands": [],
#     "started_by": "Unknown",
    
#     # Calibration Sync State
#     "calib_active": False,
#     "calib_source": None,
#     "calib_status": "Idle", # "Homing", "Moving", "Ready"
#     "is_calibrated": False,  # New Flag: True only after successful save
#     "light_on": False,
#     "lid_open": False,
#     "sensors": {}
# }

# # --- HELPER FUNCTIONS ---
# def system_log(msg):
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     entry = f"[{timestamp}] {msg}"
#     print(entry, flush=True) 
#     with open(SYSTEM_LOG_FILE, "a", encoding="utf-8") as f:
#         f.write(entry + "\n")

# def protocol_log(filename, log_data):
#     if not filename: return
#     log_path = os.path.join(PROTOCOLS_LOG_DIR, f"{filename}.log")
#     with open(log_path, "a", encoding="utf-8") as f:
#         f.write(log_data) 

# # --- BROWSER ROUTES ---
# @app.route('/')
# def index():
#     return render_template_string(HTML_CODE)

# @app.route('/upload', methods=['POST'])
# def upload():
#     # 1. Block if actively calibrating
#     if state["calib_active"]:
#         return "System is Calibrating. Please finish first.", 403
        
#     # 2. Block if NOT calibrated yet
#     if not state["is_calibrated"]:
#         return "System requires calibration before running.", 403

#     file = request.files['upload']
#     if file:
#         file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        
#         # Immediate UI Update
#         state["file_running"] = file.filename
#         state["status_text"] = "Starting..."
#         state["progress"] = 0
#         state["started_by"] = "Remote"
        
#         # Queue Command for Pi
#         state["pending_commands"].append({"event": "NEW_FILE", "filename": file.filename})
#         system_log(f"USER: Uploaded {file.filename}")
#         return "OK"
#     return "Error", 400

# # --- CONTROL ROUTES ---
# @app.route('/pause')
# def pause():
#     state["pending_commands"].append({"event": "PAUSE"})
#     state["status_text"] = "Paused (Remote)" 
#     return "OK"

# @app.route('/resume')
# def resume():
#     state["pending_commands"].append({"event": "RESUME"})
#     state["status_text"] = "Resuming..."
#     return "OK"

# @app.route('/clear')
# def clear():
#     state["pending_commands"].append({"event": "CLEAR"})
#     state["file_running"] = None
#     state["status_text"] = "Stopped (Remote)"
#     state["progress"] = 0
#     state["est_completion"] = "--:--:--:--"
#     return "OK"

# # --- CALIBRATION ROUTES (REMOTE) ---
# @app.route('/start-calibrate')
# def start_calibrate():
#     # Prevent Remote start if Local User is already calibrating
#     if state["calib_active"] and state["calib_source"] == "User":
#         return "LOCKED", 403
        
#     # Send Start Command (Backend handles T00 logic)
#     state["pending_commands"].append({"event": "CALIB_START"})
#     state["status_text"] = "Calibration Mode"
#     system_log("USER: Entered Calibration Mode (Remote)")
#     return "OK"

# @app.route('/calibrate')
# def calibrate():
#     dx = request.args.get('dx', 0)
#     dy = request.args.get('dy', 0)
#     dz = request.args.get('dz', 0)
#     cmd = f"C dx={dx}, dy={dy}, dz={dz}" 
#     state["pending_commands"].append({"event": "SERIAL_SEND", "data": cmd})
#     return "OK"

# @app.route('/calibrate-completed')
# def calib_done():
#     # Send OK_C to trigger save. 
#     # NOTE: We do NOT send CALIB_END here. The Backend waits for C_OK response 
#     # from hardware to confirm save and unlock automatically.
#     state["pending_commands"].append({"event": "SERIAL_SEND", "data": "OK_C"})
#     state["status_text"] = "Saving Offsets..."
#     system_log("USER: Sent Save Command (Remote)")
#     return "OK"

# # --- DATA ROUTES ---
# @app.route('/status')
# def get_status():
#     return jsonify(state)

# @app.route('/logs')
# def get_logs():
#     if not os.path.exists(SYSTEM_LOG_FILE): return "Waiting for logs..."
#     with open(SYSTEM_LOG_FILE, 'r', encoding="utf-8") as f:
#         lines = f.readlines()
#         return "".join(lines[-50:])

# # --- PI INTERACTION ROUTES ---
# @app.route('/download/<filename>')
# def download(filename):
#     return send_from_directory(UPLOAD_FOLDER, filename)

# @app.route('/pi/sync', methods=['POST'])
# def pi_sync():
#     data = request.json
    
#     # 1. Update Standard State
#     state["file_running"] = data.get("file")
#     state["current_line"] = data.get("line")
#     state["progress"] = data.get("progress")
#     state["est_completion"] = data.get("est")
#     state["status_text"] = data.get("status", "Connected")
#     if "started_by" in data:
#         state["started_by"] = data["started_by"]
    
#     # 2. Update Calibration State
#     if "calib_active" in data:
#         state["calib_active"] = data["calib_active"]
#         state["calib_source"] = data.get("calib_source")
#         state["calib_status"] = data.get("calib_status", "Idle")
#         state["is_calibrated"] = data.get("is_calibrated", False)

#     # 3. CAPTURE NEW SENSORS & LID
#     state["light_on"] = data.get("light_on", False)
#     state["lid_open"] = data.get("lid_open", False) # True = OPEN (Danger)
#     state["sensors"] = data.get("sensors", {}) # Stores all temps/fans

#     # 4. Handle Logs
#     logs = data.get("logs")
#     if logs:
#         protocol_log(state["file_running"], logs)
#         system_log(f"[PI] {logs.strip()}")

#     # 5. Send Commands back to Pi
#     cmds_to_send = state["pending_commands"][:]
#     state["pending_commands"] = [] 
    
#     return jsonify({"commands": cmds_to_send})


# # --- HTML UI CODE ---
# HTML_CODE = r"""
# <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="utf-8" />
#     <meta name="viewport" content="width=device-width, initial-scale=1" />
#     <title>Liquid Handling Dashboard</title>
#     <style>
#         :root { --primary: #007bff; --success: #28a745; --warning: #ffc107; --danger: #dc3545; --dark: #343a40; --light: #f8f9fa; }
#         body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #e9ecef; margin: 0; padding: 20px; }
#         .container { max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        
#         header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid var(--light); padding-bottom: 20px; }
#         .status-badge { display: inline-block; padding: 8px 20px; border-radius: 30px; font-weight: bold; background: var(--dark); color: white; margin-top: 10px; font-size: 1.2rem;}
        
#         .card { background: var(--light); padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid var(--primary); box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
#         h2 { margin-top: 0; font-size: 1.2rem; color: var(--dark); border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 15px; }

#         .btn { padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; color: white; transition: transform 0.1s; font-size:1rem;}
#         .btn:active { transform: scale(0.98); }
#         .btn-primary { background: var(--primary); }
#         .btn-success { background: var(--success); }
#         .btn-danger { background: var(--danger); }
#         .btn-warning { background: var(--warning); color: #000; }
        
#         .control-grid { display: flex; gap: 15px; justify-content: center; margin-bottom: 20px; }
#         .calib-grid { display: grid; grid-template-columns: repeat(3, 60px); gap: 10px; justify-content: center; margin: 15px 0; }
#         .calib-btn { padding: 15px; font-size: 1.5rem; background: white; border: 2px solid #ccc; cursor: pointer; border-radius: 8px; }
        
#         pre { background: #212529; color: #00ff41; padding: 15px; border-radius: 5px; height: 250px; overflow-y: auto; font-size: 0.9rem; white-space: pre-wrap; }
        
#         .progress-container { width: 100%; background: #ddd; height: 30px; border-radius: 15px; margin-top: 15px; overflow: hidden; position: relative; }
#         .progress-bar { height: 100%; background: linear-gradient(90deg, #28a745, #218838); width: 0%; transition: width 0.5s; }
#         .progress-text { position: absolute; width: 100%; text-align: center; line-height: 30px; font-weight: bold; color: #333; top: 0; }

#         /* SENSOR GRID */
#         .sensor-box { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; text-align: center; }
#         .sensor-item { background: white; padding: 10px; border-radius: 5px; border: 1px solid #ddd; }
#         .sensor-val { font-size: 1.4rem; font-weight: bold; color: var(--dark); }
#         .sensor-label { font-size: 0.85rem; color: #6c757d; margin-top: 5px; }
        
#         .lid-badge { font-weight: bold; padding: 5px 10px; border-radius: 4px; display: inline-block; margin-left: 10px; }
#         .lid-open { background: #ffcdd2; color: #c62828; border: 1px solid #ef5350; }
#         .lid-closed { background: #c8e6c9; color: #2e7d32; border: 1px solid #66bb6a; }

#         /* MODALS */
#         .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.6); }
#         .modal-content { background-color: #fefefe; margin: 15% auto; padding: 0; border-radius: 8px; width: 400px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); animation: popin 0.3s ease; }
#         .modal-header { padding: 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; color: white; text-align: center; font-size: 1.5rem; font-weight: bold; }
#         .modal-body { padding: 20px; text-align: center; font-size: 1.1rem; color: #333; }
#         .modal-footer { padding: 15px; text-align: center; border-top: 1px solid #eee; display: flex; justify-content: center; gap: 10px; }
        
#         .bg-red { background: var(--danger); }
#         .bg-green { background: var(--success); }
#         .bg-blue { background: var(--primary); }
#         .bg-orange { background: var(--warning); color: black !important; }
        
#         /* CALIBRATION INFO MODALS */
#         .info-modal { display: none; position: fixed; z-index: 1001; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
#         .info-content {
#             background-color: white; margin: 20% auto; padding: 30px; border-radius: 10px; width: 300px; 
#             text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.3);
#         }
        
#         .blocker-overlay { display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.95); text-align: center; padding-top: 15%; }
#         .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px auto; }
#         @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
#     </style>
# </head>
# <body>
#     <div id="blockerModal" class="blocker-overlay">
#         <div style="display: inline-block; padding: 40px; border: 4px solid #ffc107; border-radius: 15px; background: white;">
#             <h1>🔒 SYSTEM LOCKED</h1><p>Local User is Calibrating...</p>
#         </div>
#     </div>

#     <div id="homingModal" class="info-modal">
#         <div class="info-content">
#             <div class="spinner"></div>
#             <h2>🏠 HOMING...</h2>
#             <p>Please wait while the robot finds home position.</p>
#         </div>
#     </div>

#     <div id="movingModal" class="info-modal">
#         <div class="info-content">
#             <div class="spinner" style="border-top-color: #ffc107;"></div>
#             <h2>⚙️ MOVING...</h2>
#             <p>Moving to calibration point...</p>
#         </div>
#     </div>

#     <div id="lidWarningModal" class="modal">
#         <div class="modal-content">
#             <div class="modal-header bg-orange">⚠️ LID IS OPEN</div>
#             <div class="modal-body">
#                 <p>The safety lid is currently open.</p>
#                 <p>Do you want to proceed anyway?</p>
#             </div>
#             <div class="modal-footer">
#                 <button class="btn btn-danger" onclick="closeModal('lidWarningModal')">Cancel</button>
#                 <button class="btn btn-success" onclick="confirmUpload()">Continue Anyway</button>
#             </div>
#         </div>
#     </div>

#     <div class="container">
#         <header>
#             <h1>💧 Liquid Handling Dashboard</h1>
#             <div id="connectionStatus" style="color:red; display:none;">⚠️ DISCONNECTED</div>
#             <div class="status-badge" id="robotState">Waiting...</div>
#             <span id="lidStatus" class="lid-badge lid-closed">Lid Closed</span>
#             <div id="sourceDisplay" style="margin-top:5px; color:#555;">Source: -</div>
#         </header>

#         <div class="card" style="border-color: #17a2b8;">
#             <h2>📊 Sensor Readings</h2>
#             <div class="sensor-box">
#                 <div class="sensor-item"><div id="val_env_t" class="sensor-val">--</div><div class="sensor-label">Enclosure °C</div></div>
#                 <div class="sensor-item"><div id="val_hum" class="sensor-val">--</div><div class="sensor-label">Humidity %</div></div>
#                 <div class="sensor-item"><div id="val_bed_t" class="sensor-val">--</div><div class="sensor-label">Bed Temp °C</div></div>
#                 <div class="sensor-item"><div id="val_cpu_t" class="sensor-val">--</div><div class="sensor-label">CPU °C</div></div>
#                 <div class="sensor-item"><div id="val_cpu_load" class="sensor-val">--</div><div class="sensor-label">CPU Load %</div></div>
#             </div>
#         </div>

#         <div class="card" style="border-color: var(--warning);">
#             <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
#                 <div><strong>File:</strong> <span id="filename">None</span></div>
#                 <div><strong>Line:</strong> <span id="currentLine">-</span></div>
#                 <div><strong>Time:</strong> <span id="estTime">-</span></div>
#             </div>
#             <div class="progress-container">
#                 <div id="progressBar" class="progress-bar"></div>
#                 <div id="progressText" class="progress-text">0%</div>
#             </div>
#             <div class="control-grid" style="margin-top: 25px;">
#                 <button class="btn btn-warning" onclick="sendCmd('pause')">❚❚ Pause</button>
#                 <button class="btn btn-primary" onclick="sendCmd('resume')">▶ Resume</button>
#                 <button class="btn btn-danger" onclick="sendCmd('clear')">■ Stop</button>
#             </div>
#         </div>

#         <div class="card" style="border-color: var(--primary);">
#             <h2>📂 File Upload</h2>
#             <form id="uploadForm" style="display: flex; gap: 10px; justify-content: center;">
#                 <input type="file" id="fileInput" name="upload" accept=".gcode,.txt" required>
#                 <button type="submit" class="btn btn-success">Upload & Run</button>
#             </form>
#             <div id="uploadMsg" style="text-align:center; margin-top:5px;"></div>
#         </div>

#         <div class="card" style="border-color: var(--dark);">
#             <h2>🔧 Calibration</h2>
#             <div style="text-align: center;">
#                 <button id="btnStartCalib" class="btn btn-primary" onclick="startCalibrate()">Enter Mode</button>
#                 <div id="calibControls" style="display:none;">
#                     <div class="calib-grid">
#                         <div></div><button class="calib-btn" onclick="move('up')">Y+</button><div></div>
#                         <button class="calib-btn" onclick="move('left')">X-</button><button class="calib-btn" onclick="move('down')">Y-</button><button class="calib-btn" onclick="move('right')">X+</button>
#                     </div>
#                     <div><button class="btn btn-primary" onclick="move('zup')">Z+</button> <button class="btn btn-primary" onclick="move('zdown')">Z-</button></div>
#                     <div style="margin-top:10px;">
#                         <button class="btn btn-success" onclick="saveOffsets()">💾 Save</button>
#                     </div>
#                 </div>
#             </div>
#         </div>

#         <div class="card" style="border-color: #6c757d;">
#             <h2>📜 Logs</h2>
#             <pre id="logs">Loading...</pre>
#         </div>
#     </div>

#     <div id="msgModal" class="modal">
#         <div class="modal-content">
#             <div id="msgHeader" class="modal-header"></div>
#             <div id="msgBody" class="modal-body"></div>
#             <div class="modal-footer"><button class="btn btn-primary" onclick="closeModal('msgModal')">OK</button></div>
#         </div>
#     </div>

#     <script>
#         let lastStatus = "";
#         let pendingUploadData = null; 
#         let isLidOpen = false;
#         let isCalibrated = false;

#         const blocker = document.getElementById("blockerModal");
#         const lidModal = document.getElementById("lidWarningModal");
#         const homingModal = document.getElementById("homingModal"); // RESTORED
#         const movingModal = document.getElementById("movingModal"); // RESTORED

#         function closeModal(id) { document.getElementById(id).style.display = "none"; }
#         function sendCmd(ep) { fetch('/' + ep); }

#         function showMsg(title, body, cls) {
#             document.getElementById('msgHeader').className = "modal-header bg-" + cls;
#             document.getElementById('msgHeader').innerText = title;
#             document.getElementById('msgBody').innerText = body;
#             document.getElementById('msgModal').style.display = "block";
#         }

#         // --- CALIBRATION ---
#         function startCalibrate() {
#             fetch('/start-calibrate').then(r => {
#                 if(r.status===403) alert("Busy");
#                 else document.getElementById('btnStartCalib').style.display = 'none';
#             });
#         }
#         function move(dir) { fetch(`/calibrate?dx=${dir==='left'?-1:dir==='right'?1:0}&dy=${dir==='down'?-1:dir==='up'?1:0}&dz=${dir==='zdown'?-1:dir==='zup'?1:0}`); }
#         function saveOffsets() {
#             fetch('/calibrate-completed').then(() => {
#                 document.getElementById('calibControls').style.display = 'none';
#                 document.getElementById('btnStartCalib').style.display = 'inline-block';
#             });
#         }

#         // --- UPLOAD LOGIC ---
#         document.getElementById('uploadForm').onsubmit = (e) => {
#             e.preventDefault();
#             const formData = new FormData(e.target);
#             const msg = document.getElementById('uploadMsg');
            
#             // 1. Check Calibration
#             if (!isCalibrated) {
#                 showMsg("🛑 ERROR", "Calibration Required first!", "red");
#                 msg.innerText = "🛑 Calibration Required";
#                 return; 
#             }
#             // 2. Check Lid
#             if (isLidOpen) {
#                 pendingUploadData = formData; 
#                 lidModal.style.display = "block"; 
#                 return;
#             }
#             doUpload(formData);
#         };

#         function confirmUpload() {
#             closeModal('lidWarningModal');
#             if(pendingUploadData) doUpload(pendingUploadData);
#         }

#         async function doUpload(formData) {
#             const msg = document.getElementById('uploadMsg');
#             msg.innerText = "Uploading...";
#             try {
#                 const res = await fetch('/upload', { method: 'POST', body: formData });
#                 if(res.ok) msg.innerText = "✅ Started";
#                 else msg.innerText = "❌ Failed";
#             } catch(e) { msg.innerText = "❌ Error"; }
#         }

#         // --- MAIN LOOP ---
#         setInterval(() => {
#             fetch('/status').then(r => r.json()).then(data => {
#                 isLidOpen = data.lid_open;
#                 isCalibrated = data.is_calibrated;

#                 document.getElementById('robotState').innerText = data.status_text || "Idle";
#                 document.getElementById('filename').innerText = data.file_running || "None";
#                 document.getElementById('sourceDisplay').innerText = "Source: " + (data.started_by || "-");
#                 document.getElementById('currentLine').innerText = data.current_line || "-";
#                 document.getElementById('estTime').innerText = data.est_completion || "-";
                
#                 const pct = data.progress || 0;
#                 document.getElementById('progressBar').style.width = pct + "%";
#                 document.getElementById('progressText').innerText = pct + "%";

#                 const lidEl = document.getElementById('lidStatus');
#                 if(isLidOpen) {
#                     lidEl.className = "lid-badge lid-open";
#                     lidEl.innerText = "⚠️ Lid Open";
#                 } else {
#                     lidEl.className = "lid-badge lid-closed";
#                     lidEl.innerText = "🔒 Lid Closed";
#                 }

#                 const s = data.sensors || {};
#                 document.getElementById('val_env_t').innerText = (s.bme_temp || 0).toFixed(1) + "°";
#                 document.getElementById('val_hum').innerText = (s.bme_hum || 0).toFixed(0) + "%";
#                 document.getElementById('val_bed_t').innerText = (s.adt_temp || 0).toFixed(1) + "°";
#                 document.getElementById('val_cpu_t').innerText = (s.cpu_temp || 0) + "°";
#                 document.getElementById('val_cpu_load').innerText = (s.cpu_load || 0) + "%";

#                 // --- CALIBRATION STATUS LOGIC (RESTORED) ---
#                 if (data.calib_active && data.calib_source === "Remote") {
#                     if (data.calib_status === "Homing") {
#                         homingModal.style.display = "block";
#                         movingModal.style.display = "none";
#                         document.getElementById('calibControls').style.display = 'none';
#                     } else if (data.calib_status === "Moving") {
#                         homingModal.style.display = "none";
#                         movingModal.style.display = "block";
#                         document.getElementById('calibControls').style.display = 'none';
#                     } else if (data.calib_status === "Ready") {
#                         homingModal.style.display = "none";
#                         movingModal.style.display = "none";
#                         document.getElementById('calibControls').style.display = 'block';
#                     }
#                 } else {
#                     homingModal.style.display = "none";
#                     movingModal.style.display = "none";
#                     if (!data.calib_active) {
#                         document.getElementById('calibControls').style.display = 'none';
#                         document.getElementById('btnStartCalib').style.display = 'inline-block';
#                     }
#                 }
                
#                 // BLOCKER LOGIC
#                 if(data.calib_active && data.calib_source !== "Remote") {
#                     blocker.style.display = "block";
#                 } else {
#                     blocker.style.display = "none";
#                 }

#                 document.getElementById('connectionStatus').style.display = 'none';
#             }).catch(() => document.getElementById('connectionStatus').style.display = 'block');
            
#             fetch('/logs').then(r => r.text()).then(txt => {
#                 const logEl = document.getElementById('logs');
#                 if(logEl.scrollHeight - logEl.clientHeight <= logEl.scrollTop + 50) {
#                     logEl.innerText = txt;
#                     logEl.scrollTop = logEl.scrollHeight;
#                 } else {
#                     logEl.innerText = txt;
#                 }
#             });
#         }, 1000);
#     </script>
# </body>
# </html>
# """

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)

#v1.3 Added protocol setup + z1 z2 calibration buttons
import os
import time
from datetime import datetime
from flask import Flask, request, render_template_string, send_from_directory, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
UPLOAD_FOLDER = 'pc_protocols'
PC_LOG_ROOT = 'pc_logs'
PROTOCOLS_LOG_DIR = os.path.join(PC_LOG_ROOT, 'protocols_log')
SYSTEM_LOG_FILE = os.path.join(PC_LOG_ROOT, 'system.log')

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

# --- HELPER FUNCTIONS ---
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
@app.route('/')
def index():
    return render_template_string(HTML_CODE)

""" @app.route('/upload', methods=['POST'])
def upload():
    # 1. Block if actively calibrating
    if state["calib_active"]:
        return "System is Calibrating. Please finish first.", 403
        
    # 2. Block if NOT calibrated yet
    if not state["is_calibrated"]:
        return "System requires calibration before running.", 403

    file = request.files['upload']
    if file:
        file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        
        # Immediate UI Update
        state["file_running"] = file.filename
        state["status_text"] = "Starting..."
        state["progress"] = 0
        state["started_by"] = "Remote"
        
        # Queue Command for Pi
        state["pending_commands"].append({"event": "NEW_FILE", "filename": file.filename})
        system_log(f"USER: Uploaded {file.filename}")
        return "OK"
    return "Error", 400 """
    
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
    with open(SYSTEM_LOG_FILE, 'r', encoding="utf-8") as f:
        lines = f.readlines()
        return "".join(lines[-50:])

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
        .container { max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        
        header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid var(--light); padding-bottom: 20px; }
        .status-badge { display: inline-block; padding: 8px 20px; border-radius: 30px; font-weight: bold; background: var(--dark); color: white; margin-top: 10px; font-size: 1.2rem;}
        
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
        .sensor-box { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; text-align: center; }
        .sensor-item { background: white; padding: 10px; border-radius: 5px; border: 1px solid #ddd; }
        .sensor-val { font-size: 1.4rem; font-weight: bold; color: var(--dark); }
        .sensor-label { font-size: 0.85rem; color: #6c757d; margin-top: 5px; }
        
        .lid-badge { font-weight: bold; padding: 5px 10px; border-radius: 4px; display: inline-block; margin-left: 10px; }
        .lid-open { background: #ffcdd2; color: #c62828; border: 1px solid #ef5350; }
        .lid-closed { background: #c8e6c9; color: #2e7d32; border: 1px solid #66bb6a; }

        /* MODALS */
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.6); }
        .modal-content { background-color: #fefefe; margin: 15% auto; padding: 0; border-radius: 8px; width: 400px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); animation: popin 0.3s ease; }
        .modal-header { padding: 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; color: white; text-align: center; font-size: 1.5rem; font-weight: bold; }
        .modal-body { padding: 20px; text-align: center; font-size: 1.1rem; color: #333; }
        .modal-footer { padding: 15px; text-align: center; border-top: 1px solid #eee; display: flex; justify-content: center; gap: 10px; }
        
        .bg-red { background: var(--danger); }
        .bg-green { background: var(--success); }
        .bg-blue { background: var(--primary); }
        .bg-orange { background: var(--warning); color: black !important; }
        
        /* CALIBRATION INFO MODALS */
        .info-modal { display: none; position: fixed; z-index: 1001; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
        .info-content {
            background-color: white; margin: 20% auto; padding: 30px; border-radius: 10px; width: 300px; 
            text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        
        .blocker-overlay { display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.95); text-align: center; padding-top: 15%; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        /* PROTOCOL SETUP STYLES */
        .form-group { margin-bottom: 15px; text-align: left; }
        .form-label { display: block; font-weight: bold; margin-bottom: 5px; color: #555; }
        .form-input { width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 6px; font-size: 1.1rem; box-sizing: border-box; }
        .form-input:focus { border-color: var(--primary); outline: none; }
        .toggle-btn { background: #ddd; color: #555; }
        .toggle-active { background: var(--primary); color: white; }
        
    </style>
</head>
<body>
    <div id="blockerModal" class="blocker-overlay">
        <div style="display: inline-block; padding: 40px; border: 4px solid #ffc107; border-radius: 15px; background: white;">
            <h1>🔒 SYSTEM LOCKED</h1><p>Local User is Calibrating...</p>
        </div>
    </div>

    <div id="homingModal" class="info-modal">
        <div class="info-content">
            <div class="spinner"></div>
            <h2>🏠 HOMING...</h2>
            <p>Please wait while the robot finds home position.</p>
        </div>
    </div>

    <div id="movingModal" class="info-modal">
        <div class="info-content">
            <div class="spinner" style="border-top-color: #ffc107;"></div>
            <h2>⚙️ MOVING...</h2>
            <p>Moving to calibration point...</p>
        </div>
    </div>

    <div id="lidWarningModal" class="modal">
        <div class="modal-content">
            <div class="modal-header bg-orange">⚠️ LID IS OPEN</div>
            <div class="modal-body">
                <p>The safety lid is currently open.</p>
                <p>Do you want to proceed anyway?</p>
            </div>
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
                <div class="form-group">
                    <label class="form-label">Target Temperature (15 - 35 °C)</label>
                    <input type="number" id="inpTemp" class="form-input" value="25" min="15" max="35">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Fan Mode</label>
                    <div style="display:flex; gap:10px;">
                        <button id="btnAuto" type="button" class="btn toggle-active" style="flex:1" onclick="setMode('Auto')">Auto</button>
                        <button id="btnManual" type="button" class="btn toggle-btn" style="flex:1" onclick="setMode('Manual')">Manual</button>
                    </div>
                </div>

                <div id="fanSpeedGroup" class="form-group" style="display:none;">
                    <label class="form-label">Fan Speed (0 - 100 %)</label>
                    <input type="number" id="inpFan" class="form-input" value="0" min="0" max="100">
                </div>
                <div id="setupError" style="color: red; font-weight: bold; margin-top: 10px;"></div>
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
            <div id="sourceDisplay" style="margin-top:5px; color:#555;">Source: -</div>
        </header>

        <div class="card" style="border-color: #17a2b8;">
            <h2>📊 Sensor Readings</h2>
            <div class="sensor-box">
                <div class="sensor-item"><div id="val_env_t" class="sensor-val">--</div><div class="sensor-label">Enclosure °C</div></div>
                <div class="sensor-item"><div id="val_hum" class="sensor-val">--</div><div class="sensor-label">Humidity %</div></div>
                <div class="sensor-item"><div id="val_bed_t" class="sensor-val">--</div><div class="sensor-label">Bed Temp °C</div></div>
                <div class="sensor-item"><div id="val_cpu_t" class="sensor-val">--</div><div class="sensor-label">CPU °C</div></div>
                <div class="sensor-item"><div id="val_cpu_load" class="sensor-val">--</div><div class="sensor-label">CPU Load %</div></div>
            </div>
        </div>

        <div class="card" style="border-color: var(--warning);">
            <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
                <div><strong>File:</strong> <span id="filename">None</span></div>
                <div><strong>Line:</strong> <span id="currentLine">-</span></div>
                <div><strong>Time:</strong> <span id="estTime">-</span></div>
            </div>
            <div class="progress-container">
                <div id="progressBar" class="progress-bar"></div>
                <div id="progressText" class="progress-text">0%</div>
            </div>
            <div class="control-grid" style="margin-top: 25px;">
                <button class="btn btn-warning" onclick="sendCmd('pause')">❚❚ Pause</button>
                <button class="btn btn-primary" onclick="sendCmd('resume')">▶ Resume</button>
                <button class="btn btn-danger" onclick="sendCmd('clear')">■ Stop</button>
            </div>
        </div>

        <div class="card" style="border-color: var(--primary);">
            <h2>📂 File Upload</h2>
            <form id="uploadForm" style="display: flex; gap: 10px; justify-content: center;">
                <input type="file" id="fileInput" name="upload" accept=".gcode,.txt" required>
                <button type="submit" class="btn btn-success">Upload & Run</button>
            </form>
            <div id="uploadMsg" style="text-align:center; margin-top:5px;"></div>
        </div>

        <div class="card" style="border-color: var(--dark);">
            <h2>🔧 Calibration</h2>
            <div style="text-align: center;">
                <button id="btnStartCalib" class="btn btn-primary" onclick="startCalibrate()">Enter Mode</button>
               
               
                   <div id="calibControls" style="display:none;">
                    <div style="margin-bottom: 15px;">
                        <label style="font-weight:bold; color:#555;">Step Size: </label>
                        <select id="stepSize" style="padding: 5px; border-radius: 4px; font-size: 1rem;">
                            <option value="0.1">0.1 mm</option>
                            <option value="1" selected>1.0 mm</option>
                            <option value="10">10.0 mm</option>
                        </select>
                    </div>
                
                
                
                    <div class="calib-grid">
                        <div></div><button class="calib-btn" onclick="move('up')">Y+</button><div></div>
                        <button class="calib-btn" onclick="move('left')">X-</button><button class="calib-btn" onclick="move('down')">Y-</button><button class="calib-btn" onclick="move('right')">X+</button>
                    </div>
                    <div style="margin: 10px 0;">
    <span style="font-weight:bold; color:#555;">Z1:</span>
    <button class="btn btn-primary" style="padding: 8px 15px;" onclick="move('z1up')">▲</button> 
    <button class="btn btn-primary" style="padding: 8px 15px;" onclick="move('z1down')">▼</button>
    
    <span style="font-weight:bold; color:#555; margin-left:15px;">Z2:</span>
    <button class="btn btn-primary" style="padding: 8px 15px;" onclick="move('z2up')">▲</button> 
    <button class="btn btn-primary" style="padding: 8px 15px;" onclick="move('z2down')">▼</button>
</div> 
                    <div style="margin-top:10px;">
                        <button class="btn btn-success" onclick="saveOffsets()">💾 Save</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="card" style="border-color: #6c757d;">
            <h2>📜 Logs</h2>
            <pre id="logs">Loading...</pre>
        </div>
    </div>

    <div id="msgModal" class="modal">
        <div class="modal-content">
            <div id="msgHeader" class="modal-header"></div>
            <div id="msgBody" class="modal-body"></div>
            <div class="modal-footer"><button class="btn btn-primary" onclick="closeModal('msgModal')">OK</button></div>
        </div>
    </div>

    <script>
        // --- GLOBAL STATE ---
        let lastStatus = "";
        let pendingFormData = null;  // <--- Ensure this is GLOBAL
        let isLidOpen = false;
        let isCalibrated = false;
        let fanMode = "Auto";
      
        const blocker = document.getElementById("blockerModal");
        const lidModal = document.getElementById("lidWarningModal");
        const homingModal = document.getElementById("homingModal");
        const movingModal = document.getElementById("movingModal");
      
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

            // VALIDATION
            if (isNaN(t) || t < 15 || t > 35) { err.innerText = "Temp must be 15 - 35 °C"; return; }
            if (fanMode === 'Manual' && (isNaN(f) || f < 0 || f > 100)) { err.innerText = "Fan must be 0 - 100 %"; return; }
            
            // CHECK IF FORM DATA EXISTS
            if(!pendingFormData) {
                err.innerText = "Error: File lost. Please try uploading again.";
                return;
            }

            // APPEND DATA
            pendingFormData.append('target_temp', t);
            pendingFormData.append('fan_mode', fanMode);
            pendingFormData.append('fan_speed', f);
            
            closeModal('setupModal');
            doUpload(pendingFormData);
        }

        // --- UPLOAD LOGIC ---
        document.getElementById('uploadForm').onsubmit = (e) => {
            e.preventDefault();
            
            // 1. Check Calibration
            if (!isCalibrated) {
                showMsg("🛑 ERROR", "Calibration Required first!", "red");
                document.getElementById('uploadMsg').innerText = "🛑 Calibration Required";
                return; 
            }

            // 2. Capture Form Data GLOBALLY
            pendingFormData = new FormData(e.target);

            // 3. Check Lid -> Setup OR Direct Setup
            if (isLidOpen) {
                lidModal.style.display = "block"; 
            } else {
                openSetup(); 
            }
        };

        // --- HELPER TO START CALIBRATION ---
        function startCalibrate() {
            fetch('/start-calibrate').then(r => {
                if(r.status===403) alert("Busy");
                else document.getElementById('btnStartCalib').style.display = 'none';
            });
        }
        function move(dir) { 
            // 1. Get Step Size
            const step = parseFloat(document.getElementById('stepSize').value);
            
            // 2. Initialize axes
            let dx=0, dy=0, dz1=0, dz2=0;

            // 3. Apply Logic (Direction * Step)
            // X Axis
            if (dir === 'left') dx = -1 * step;
            else if (dir === 'right') dx = 1 * step;
            
            // Y Axis
            else if (dir === 'down') dy = -1 * step;
            else if (dir === 'up') dy = 1 * step;
            
            // Z1 Axis
            else if (dir === 'z1down') dz1 = -1 * step;
            else if (dir === 'z1up') dz1 = 1 * step;
            
            // Z2 Axis
            else if (dir === 'z2down') dz2 = -1 * step;
            else if (dir === 'z2up') dz2 = 1 * step;

            // 4. Send Command
            fetch(`/calibrate?dx=${dx}&dy=${dy}&dz1=${dz1}&dz2=${dz2}`); 
        }
        
        function saveOffsets() {
            fetch('/calibrate-completed').then(() => {
                document.getElementById('calibControls').style.display = 'none';
                document.getElementById('btnStartCalib').style.display = 'inline-block';
            });
        }

        async function doUpload(formData) {
            const msg = document.getElementById('uploadMsg');
            msg.innerText = "Uploading...";
            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                if(res.ok) msg.innerText = "✅ Started";
                else msg.innerText = "❌ Failed";
            } catch(e) { msg.innerText = "❌ Error"; }
        }

        // --- MAIN STATUS LOOP ---
        setInterval(() => {
            fetch('/status').then(r => r.json()).then(data => {
                isLidOpen = data.lid_open;
                isCalibrated = data.is_calibrated;

                document.getElementById('robotState').innerText = data.status_text || "Idle";
                document.getElementById('filename').innerText = data.file_running || "None";
                document.getElementById('sourceDisplay').innerText = "Source: " + (data.started_by || "-");
                document.getElementById('currentLine').innerText = data.current_line || "-";
                document.getElementById('estTime').innerText = data.est_completion || "-";
                
                const pct = data.progress || 0;
                document.getElementById('progressBar').style.width = pct + "%";
                document.getElementById('progressText').innerText = pct + "%";

                const lidEl = document.getElementById('lidStatus');
                if(isLidOpen) {
                    lidEl.className = "lid-badge lid-open";
                    lidEl.innerText = "⚠️ Lid Open";
                } else {
                    lidEl.className = "lid-badge lid-closed";
                    lidEl.innerText = "🔒 Lid Closed";
                }

                const s = data.sensors || {};
                document.getElementById('val_env_t').innerText = (s.bme_temp || 0).toFixed(1) + "°";
                document.getElementById('val_hum').innerText = (s.bme_hum || 0).toFixed(0) + "%";
                document.getElementById('val_bed_t').innerText = (s.adt_temp || 0).toFixed(1) + "°";
                document.getElementById('val_cpu_t').innerText = (s.cpu_temp || 0) + "°";
                document.getElementById('val_cpu_load').innerText = (s.cpu_load || 0) + "%";

                // CALIBRATION POPUPS
                if (data.calib_active && data.calib_source === "Remote") {
                    document.getElementById('btnStartCalib').style.display = 'none';
                    if (data.calib_status === "Homing") {
                        homingModal.style.display = "block"; movingModal.style.display = "none";
                        document.getElementById('calibControls').style.display = 'none';
                    } else if (data.calib_status === "Moving") {
                        homingModal.style.display = "none"; movingModal.style.display = "block";
                        document.getElementById('calibControls').style.display = 'none';
                    } else if (data.calib_status === "Ready") {
                        homingModal.style.display = "none"; movingModal.style.display = "none";
                        document.getElementById('calibControls').style.display = 'block';
                    }
                } else {
                    homingModal.style.display = "none"; movingModal.style.display = "none";
                    if (!data.calib_active) {
                        document.getElementById('calibControls').style.display = 'none';
                        document.getElementById('btnStartCalib').style.display = 'inline-block';
                    }
                }
                
                if(data.calib_active && data.calib_source !== "Remote") {
                    blocker.style.display = "block";
                } else {
                    blocker.style.display = "none";
                }

                document.getElementById('connectionStatus').style.display = 'none';
            }).catch(() => document.getElementById('connectionStatus').style.display = 'block');
            
            fetch('/logs').then(r => r.text()).then(txt => {
                const logEl = document.getElementById('logs');
                if(logEl.scrollHeight - logEl.clientHeight <= logEl.scrollTop + 50) {
                    logEl.innerText = txt;
                    logEl.scrollTop = logEl.scrollHeight;
                } else {
                    logEl.innerText = txt;
                }
            });
        }, 1000);
    </script>
</body>
</html>
"""
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
