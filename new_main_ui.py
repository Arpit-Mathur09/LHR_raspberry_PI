#v1.5 Addded power button functionality with confirm popup
# FORCE UI TO USE DISPLAY :0
import sys
import os
import tkinter as tk
from   tkinter import ttk
import backend 
from   datetime import datetime
import math
# import subprocess
import time
import functools
# import threading # Required for async scanning
from gui.styles import *
from gui.frames import Home, Calibrate, ProtocolList, Running, FloatingSettingsButton
from gui.popups import *
import sys

# Redirect all print() statements to a log file
log_file = open("/home/lhr/Robot_Client/logs/gui_debug.log", "a")
sys.stdout = log_file
sys.stderr = log_file
# --- DEBUGGING TOOL ---
def profile(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = (end_time - start_time) * 1000 # Convert to milliseconds
        print(f"⏱️ [{func.__name__}] took {duration:.2f} ms")
        return result
    return wrapper

       
# --- MAIN APP ---
class KioskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # Ensure directories exist
        from gui.styles import DIR_TEST, DIR_RECENT
        for d in [DIR_TEST, DIR_RECENT]: 
            os.makedirs(d, exist_ok=True)
        # --- FIX: HIDDEN START ---
        self.withdraw() # Hide immediately on start
        
        self.backend = backend.RobotClient()
        self.backend.start()
        
        w, h = 800, 480
        self.geometry(f"{w}x{h}")
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.config(bg=CLR_BG, cursor="none")
        self.bind("<Button-1>", lambda e: self.config(cursor="none"))
        self.bind("<FocusIn>", lambda e: self.config(cursor="none"))

        style = ttk.Style(); style.theme_use("clam")
        
        self.offsets = {"X": tk.DoubleVar(value=0.0), "Y": tk.DoubleVar(value=0.0), "Z1": tk.DoubleVar(value=0.0), "Z2": tk.DoubleVar(value=0.0)}
        self.step_size = tk.DoubleVar(value=1.0)
        self.selected_file = tk.StringVar(value="No File Selected")
        self.current_page_name = "Home"
        
        container = tk.Frame(self, bg=CLR_BG)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1); container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        for F in (Home, Calibrate, ProtocolList, Running): 
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.show_frame("Home")
        
        self.calib_blocker = None
        self.calib_status_popup = None
        
        # --- NEW: FLOATING SETTINGS BUTTON ---
        # We pass 'self' as parent (root) so it stays tied to app lifecycle
        # But it is a Toplevel, so it floats above everything
        self.settings_btn = FloatingSettingsButton(self, self)
        
        # --- FIX: SHOW WHEN READY ---
        self.deiconify() 
        self.update() 
        
        # Delay updater slightly to ensure GUI is painted
        self.after(500, self.start_ui_updater)

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        self.current_page_name = page_name
        if page_name == "Calibrate": frame.on_enter()
        if page_name == "ProtocolList": frame.refresh_files(frame.current_dir)

    def start_ui_updater(self):
        state = self.backend.state
        
        # --- CALIBRATION LOGIC ---
        is_calib_active = state.get("calibration_active", False)
        calib_source = state.get("calibration_source", None)
        calib_status = state.get("calib_status", "Idle")

        # 0. FORCE SCREEN SWITCH (Fixes Background Blur Issue)
        if is_calib_active and self.current_page_name != "Calibrate":
            self.show_frame("Calibrate")
            self.update_idletasks()
            self.update() 
            self.after(50, self.start_ui_updater)
            return 

        # 1. Blocker (Only if Remote is doing it)
        is_locked = is_calib_active and calib_source == "Remote"
        
        if is_locked:
            if not self.calib_blocker: self.calib_blocker = CalibrationBlockerPopup(self)
            
            # Ensure Status Popup is GONE if locked
            if self.calib_status_popup:
                self.calib_status_popup.destroy()
                self.calib_status_popup = None
        else:
            if self.calib_blocker: self.calib_blocker.destroy(); self.calib_blocker = None

        # 2. CALIBRATION STATUS POPUP (Show only if NOT locked by remote blocker)
        if is_calib_active and not is_locked and calib_status in ["Homing", "Moving"]:
            if not self.calib_status_popup:
                self.calib_status_popup = CalibrationStatusPopup(self)
            self.calib_status_popup.update_info(calib_status)
        else:
            if self.calib_status_popup:
                self.calib_status_popup.destroy()
                self.calib_status_popup = None

        # 3. COMPLETION NOTIFICATION (Remote finished)
        if not hasattr(self, 'last_calib_active'):
             self.last_calib_active = False; self.last_calib_source = None

        if self.last_calib_active and not is_calib_active:
            if self.last_calib_source == "Remote":
                if state.get("is_calibrated", False) == True:
                    time_now = datetime.now().strftime("%H:%M:%S")
                    msg = f"Calibration finished by Remote Client.\nTime: {time_now}"
                    popup = CustomPopup(self, "Notification", "CALIBRATION DONE", msg, CLR_SUCCESS, "🔔", height=290)
                    self.wait_window(popup)
                self.show_frame("Home")

        self.last_calib_active = is_calib_active
        self.last_calib_source = calib_source

        # ... (Rest of updater) ...
        if "Running" in state["status"] or "Paused" in state["status"]:
            if self.selected_file.get() != state["filename"]: self.selected_file.set(state["filename"])

        if state["just_started"]:
            self.show_frame("Running")
            self.update_idletasks(); self.update()
            filename = state["filename"]; source = state["started_by"]
            time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"Protocol: {filename}\nSource: {source}\nTime: {time_now}"
            popup = CustomPopup(self, "Started", "PROTOCOL STARTED", msg, CLR_PRIMARY, "🚀", height=290)
            self.wait_window(popup)
            self.backend.ui_ack_start()

        if "Running" in state["status"] or "Paused" in state["status"]:
            if self.current_page_name != "Running": self.show_frame("Running")
        
        # --- FIX: UPDATE ACTIVE SCREEN ---
        if self.current_page_name == "Running": 
            self.frames["Running"].update_view(state)
        elif self.current_page_name == "Home":  # <--- ADD THIS BLOCK
            self.frames["Home"].update_view(state)
            
        if state["stop_reason"]:
            reason = state["stop_reason"].upper(); filename = state["filename"]
            time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"File: {filename}\nSource: {reason}\nTime: {time_now}"
            popup = CustomPopup(self, "Stopped", "PROTOCOL STOPPED", msg, CLR_WARNING, "⚠")
            self.wait_window(popup)
            self.backend.ui_ack_stop(); self.show_frame("Home")
            
        if state["error_msg"]:
            error_text = state["error_msg"]; time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"Time: {time_now}\nDetails: {error_text}"
            popup = CustomPopup(self, "System Error", "HARDWARE ERROR", msg, CLR_DANGER, "✖")
            self.wait_window(popup)
            self.backend.ui_ack_error(); self.show_frame("Home")
            
        if state["completed"]:
            self.frames["Running"].update_view(state); self.update_idletasks(); self.update()
            filename = state["filename"]; time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"File: {filename}\nFinished At: {time_now}"
            if self.current_page_name == "Running":
                popup = CustomPopup(self, "Done", "COMPLETED", msg, CLR_SUCCESS, "✔")
                self.wait_window(popup); self.backend.ui_ack_stop(); self.show_frame("Home")
            else: 
                self.backend.state["completed"] = False; self.backend.ui_ack_stop()
                
        self.after(200, self.start_ui_updater)          
       
if __name__ == "__main__":
    app = KioskApp()
    app.mainloop()