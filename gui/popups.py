# gui/popups.py
import tkinter as tk
from gui.styles import *
from gui.widgets import *
import os
# --- BASE MODAL ---
class ModalOverlay(tk.Toplevel):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.withdraw()
        root = parent.winfo_toplevel(); root.update_idletasks()
        x = root.winfo_rootx(); y = root.winfo_rooty(); w = root.winfo_width(); h = root.winfo_height()
        self.geometry(f"{w}x{h}+{x}+{y}"); self.overrideredirect(True); self.config(cursor="none")
        self.bg_img = get_blur_bg(root)
        self.cv = tk.Canvas(self, width=w, height=h, highlightthickness=0, bg="white")
        self.cv.pack(fill="both", expand=True)
        if self.bg_img: self.cv.create_image(0, 0, image=self.bg_img, anchor="nw")
        else: self.cv.configure(bg="#FAFAFA")
        self.bind("<Button-1>", lambda e: self.config(cursor="none"))

# --- WIFI POPUP (Same as before) ---
class WifiPasswordPopup(tk.Toplevel):
    def __init__(self, parent, ssid, on_connect):
        super().__init__(parent)
        self.ssid = ssid
        self.on_connect = on_connect
        self.kb_win = None
        self.is_visible = False
        
        self.overrideredirect(True)
        self.config(bg="white", cursor="none")
        self.bind("<Button-1>", lambda e: self.config(cursor="none"))
        self.attributes("-topmost", True)
        
        w, h = 380, 190 
        x = parent.winfo_rootx() + (parent.winfo_width()//2) - (w//2)
        y = 10 
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        main_f = tk.Frame(self, bg="white", highlightthickness=2, highlightbackground=CLR_PRIMARY)
        main_f.pack(fill="both", expand=True)
        
        tk.Label(main_f, text=f"Join Network", font=("Arial", 10, "bold"), bg="white", fg="#90A4AE").pack(pady=(15, 0))
        tk.Label(main_f, text=ssid, font=("Arial", 14, "bold"), bg="white", fg="#37474F").pack(pady=(0, 10))
        
        input_container = tk.Frame(main_f, bg="white", bd=0)
        input_container.pack(pady=5, padx=30, fill="x")
        
        underline = tk.Frame(input_container, bg=CLR_PRIMARY, height=2)
        underline.pack(side="bottom", fill="x")
        
        entry_area = tk.Frame(input_container, bg="white")
        entry_area.pack(side="top", fill="x")
        
        self.entry = tk.Entry(entry_area, font=("Arial", 14), show="•", bg="white", bd=0, 
                              highlightthickness=0, insertbackground=CLR_PRIMARY)
        self.entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.entry.bind("<Button-1>", self.open_keyboard)
        self.entry.focus_force()
        
        self.eye_btn = tk.Label(entry_area, text="👁", font=("Arial", 16), bg="white", fg="#90A4AE")
        self.eye_btn.pack(side="right", padx=(5,0))
        self.eye_btn.bind("<Button-1>", self.toggle_visibility)
        
        btn_frame = tk.Frame(main_f, bg="white")
        btn_frame.pack(pady=(15, 5), fill="x", padx=30)
        
        tk.Button(btn_frame, text="Cancel", command=self.cancel, bg="#ECEFF1", bd=0, padx=15, pady=8, font=("Arial", 11)).pack(side="left")
        tk.Button(btn_frame, text="Connect", command=self.submit, bg=CLR_PRIMARY, fg="white", bd=0, padx=15, pady=8, font=("Arial", 11, "bold")).pack(side="right")
        
        self.open_keyboard(None)

    def toggle_visibility(self, event):
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.entry.config(show="")
            self.eye_btn.config(text="🔒", fg=CLR_PRIMARY)
        else:
            self.entry.config(show="•")
            self.eye_btn.config(text="👁", fg="#90A4AE")

    def open_keyboard(self, event):
        if not self.kb_win or not self.kb_win.winfo_exists():
            self.kb_win = TouchKeyboard(self, self.entry)

    def cancel(self):
        if self.kb_win: self.kb_win.destroy()
        self.destroy()

    def submit(self):
        pwd = self.entry.get()
        if self.kb_win: self.kb_win.destroy()
        self.destroy()
        self.on_connect(self.ssid, pwd)

class CustomPopup(ModalOverlay):
    def __init__(self, parent, title, header, message, color, icon_text, height=290, icon_size=45):
        super().__init__(parent)
        cw, ch = 380, height 
        cx = parent.winfo_width() / 2; cy = parent.winfo_height() / 2
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=color, width=2)
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4); self.cv.create_window(cx, cy, window=self.f)
        head_box = tk.Frame(self.f, bg="white"); head_box.pack(pady=(15, 2))
        tk.Label(head_box, text=icon_text, font=("Arial", icon_size), fg=color, bg="white").pack(side="top")
        tk.Label(head_box, text=header, font=("Arial", 20, "bold"), fg=color, bg="white").pack(side="top")
        tk.Frame(self.f, height=3, bg=color, width=300 ,cursor='none').pack(pady=8)
        msg_frame = tk.Frame(self.f, bg="white"); msg_frame.pack(pady=2, padx=15)
        tk.Label(msg_frame, text=message, font=("Arial", 12), bg="white", fg="#444", wraplength=340).pack(anchor="n")
        btn_f = tk.Frame(self.f, bg="white", cursor="none"); btn_f.pack(side="bottom", pady=20)
        RoundedButton(btn_f, text="OK", command=self.destroy, width=130, height=45, bg_color=color, hover_color=color, ).pack()
        self.deiconify(); self.update_idletasks(); self.lift(); self.grab_set()

class CustomConfirmPopup(ModalOverlay):
    def __init__(self, parent, title, header, message, width=420, height=240 ,color=CLR_DANGER ):
        super().__init__(parent); self.result = False
        #addd cursor none 
        cw, ch = width, height; cx = parent.winfo_width() / 2; cy = parent.winfo_height() / 2
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=color, width=2)
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4); self.f.pack_propagate(False); self.cv.create_window(cx, cy, window=self.f)
        head_box = tk.Frame(self.f, bg="white"); head_box.pack(pady=(15, 5))
        tk.Label(head_box, text=title, font=("Arial", 40), fg=color, bg="white").pack(side="top")
        tk.Label(head_box, text=header, font=("Arial", 18, "bold"), fg=color, bg="white").pack(side="top")
        tk.Frame(self.f, height=2, bg=color, width=300).pack(pady=5)
        tk.Label(self.f, text=message, font=("Arial", 12), bg="white", fg="#444", wraplength=cw-40).pack(pady=5)
        btn_f = tk.Frame(self.f, bg="white", cursor="none"); btn_f.pack(side="bottom", pady=20)
        RoundedButton(btn_f, text="CANCEL", command=self.on_cancel, width=120, height=50, bg_color="#9E9E9E", hover_color="#757575",).pack(side="left", padx=15)
        RoundedButton(btn_f, text="CONFIRM", command=self.on_confirm, width=120, height=50, bg_color=color).pack(side="left", padx=15,)
        self.deiconify(); self.lift(); self.grab_set(); self.wait_window()
        
    def on_confirm(self): self.result = True; self.destroy()
    def on_cancel(self): self.result = False; self.destroy()

# --- BLOCKER POPUP (Full Screen) ---
class CalibrationBlockerPopup(ModalOverlay):
    def __init__(self, parent):
        super().__init__(parent)
        cw, ch = 460, 280; cx = parent.winfo_width() / 2; cy = parent.winfo_height() / 2
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=CLR_WARNING, width=3)
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4); self.cv.create_window(cx, cy, window=self.f)
        tk.Label(self.f, text="🔒", font=("Arial", 45), fg=CLR_WARNING, bg="white").pack(pady=(30, 5))
        tk.Label(self.f, text="SYSTEM LOCKED", font=("Arial", 22, "bold"), fg=CLR_WARNING, bg="white").pack(pady=(5, 5))
        tk.Frame(self.f, height=2, bg=CLR_WARNING, width=300).pack(pady=10)
        msg = "Calibration active on Remote Client.\nPlease wait for it to finish."
        tk.Label(self.f, text=msg, font=("Arial", 12), fg="#555", bg="white").pack(pady=5)
        self.deiconify(); self.lift()

# --- CALIBRATION STATUS POPUP (Fixed Size, No Logs) ---
class CalibrationStatusPopup(ModalOverlay):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent # Save reference to KioskApp to access the backend
        
        # Increased height from 240 to 290 to make room for the Stop button
        cw, ch = 420, 290 
        cx = parent.winfo_width() / 2
        cy = parent.winfo_height() / 2
        
        # Shadow & Border (Default Blue)
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.border_id = self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=CLR_PRIMARY, width=2)
        
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4)
        self.f.pack_propagate(False)
        self.cv.create_window(cx, cy, window=self.f)
        
        # Header Row
        self.head_box = tk.Frame(self.f, bg="white")
        self.head_box.pack(pady=(30, 10))
        
        self.lbl_icon = tk.Label(self.head_box, text="⌂", font=("Arial", 32), fg=CLR_PRIMARY, bg="white")
        self.lbl_icon.pack(side="left", padx=15)
        
        self.lbl_title = tk.Label(self.head_box, text="HOMING...", font=("Arial", 20, "bold"), fg=CLR_PRIMARY, bg="white")
        self.lbl_title.pack(side="left")
        
        # Divider
        tk.Frame(self.f, height=2, bg="#E0E0E0", width=350).pack(pady=5)
        
        # Subtitle
        self.lbl_desc = tk.Label(self.f, text="Please wait while the robot finds home.", font=("Arial", 12), bg="white", fg="#555")
        self.lbl_desc.pack(pady=(15, 10))
        
        # --- SPINNER & BUTTON CONTAINER ---
        anim = tk.Frame(self.f, bg="white")
        anim.pack(pady=0)
        
        self.spinner = HourglassSpinner(anim, size=32, bg="white", color=CLR_PRIMARY)
        self.spinner.pack()
        
        # The New Emergency Stop Button
        self.btn_stop = RoundedButton(anim, text="STOP", width=120, height=40, 
                                      bg_color=CLR_DANGER, hover_color=CLR_DANGER_HOVER, 
                                      command=self.emergency_stop)
        self.btn_stop.pack(pady=(15, 0))
        
        self.deiconify()
        self.update_idletasks()
        self.lift()

    def emergency_stop(self):
        print("🛑 Calibration Aborted - Resetting Pico...")
        
        # 1. Trigger  self.hard_reset_pico() in backend.py
        self.app.backend.hard_reset_pico()
        
        # 2. Force Calibration Mode OFF
        self.app.backend.set_calibration_mode(False, None)
        
        # 3. Force UI to Home Screen
        self.app.show_frame("Home")
        
        # 4. Destroy popup
        self.destroy()

    def update_info(self, status):
        # Update Visuals based on State
        if status == "Homing":
            self.lbl_icon.config(text="⌂", fg=CLR_PRIMARY)
            self.lbl_title.config(text="HOMING...", fg=CLR_PRIMARY)
            self.lbl_desc.config(text="Homing axes to zero position...")
            self.cv.itemconfig(self.border_id, outline=CLR_PRIMARY)
            self.spinner.color = CLR_PRIMARY
        elif status == "Moving":
            self.lbl_icon.config(text="⌖", fg=CLR_WARNING)
            self.lbl_title.config(text="MOVING...", fg=CLR_WARNING)
            self.lbl_desc.config(text="Moving to calibration point...")
            self.cv.itemconfig(self.border_id, outline=CLR_WARNING)
            self.spinner.color = CLR_WARNING
    
# --- UPDATE: PROTOCOL SETUP POPUP (Target Temp + FAN MODE AND SPEED) ---
class ProtocolSetupPopup(ModalOverlay):
    def __init__(self, parent, backend):
        super().__init__(parent)
        self.backend = backend
        self.result = False
        
        # State
        self.temp_val = str(backend.state.get("target_temp", 25))
        self.fan_val = str(backend.state.get("fan_manual_val", 0))
        self.mode = backend.state.get("fan_mode", "Manual")
        self.active_field = "temp" 

        # Layout
        cw, ch = 540, 420 
        cx, cy = parent.winfo_width()/2, parent.winfo_height()/2
        self.cv.create_rectangle(cx-cw/2, cy-ch/2, cx+cw/2, cy+ch/2, fill="white", outline=CLR_PRIMARY, width=3)
        self.f = tk.Frame(self.cv, bg="white", width=cw-6, height=ch-6); self.f.pack_propagate(False)
        self.cv.create_window(cx, cy, window=self.f)
        
        tk.Label(self.f, text="PROTOCOL SETUP", font=("Arial", 16, "bold"), bg="white", fg=CLR_PRIMARY).pack(pady=(15, 5))

        # Main Grid
        content = tk.Frame(self.f, bg="white"); content.pack(fill="both", expand=True, padx=20, pady=5)
        left_col = tk.Frame(content, bg="white"); left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # --- INPUT 1: TEMP ---
        self.lbl_temp_info = tk.Label(left_col, text="TARGET TEMP (15-35°C)", font=("Arial", 11, "bold"), fg="#90A4AE", bg="white")
        self.lbl_temp_info.pack(anchor="w", pady=(5, 2))
        
        self.btn_temp = SelectableButton(left_col, text=f"{self.temp_val}", width=210, height=65, 
                                         font=("Arial", 26, "bold"), 
                                         bg_color="#FAFAFA", fg_color="black", 
                                         border_color="#E0E0E0", border_width=1,
                                         command=lambda: self.select_field("temp"))
        self.btn_temp.pack(anchor="w")

        # --- INPUT 2: FAN ---
        self.lbl_fan_info = tk.Label(left_col, text="FAN SPEED (0-100%)", font=("Arial", 11, "bold"), fg="#90A4AE", bg="white")
        self.btn_fan = SelectableButton(left_col, text=f"{self.fan_val}", width=210, height=65, 
                                        font=("Arial", 26, "bold"),
                                        bg_color="#FAFAFA", fg_color="black",
                                        border_color="#E0E0E0", border_width=1,
                                        command=lambda: self.select_field("fan"))
        # (Packed later)

        # --- MODE TOGGLE ---
        tk.Label(left_col, text="FAN MODE", font=("Arial", 11, "bold"), fg="#90A4AE", bg="white").pack(anchor="w", pady=(15, 2))
        self.toggle_sw = ToggleSwitch(left_col, command=self.on_mode_change)
        self.toggle_sw.set_value(self.mode)
        self.toggle_sw.pack(anchor="w")

        # --- KEYPAD ---
        right_col = tk.Frame(content, bg="white"); right_col.pack(side="right")
        keys = ['1','2','3', '4','5','6', '7','8','9', '.', '0', '⌫']
        r, c = 0, 0
        for k in keys:
            cmd = lambda x=k: self.on_key(x)
            tk.Button(right_col, text=k, font=("Arial", 16, "bold"), width=4, height=2, 
                      bg="#FAFAFA", activebackground="#E3F2FD", relief="flat", command=cmd).grid(row=r, column=c, padx=3, pady=3)
            c += 1; 
            if c > 2: c=0; r+=1

        bot = tk.Frame(self.f, bg="white"); bot.pack(side="bottom", fill="x", pady=15, padx=30)
        RoundedButton(bot, text="CANCEL", command=self.destroy, width=120, height=50, bg_color="#CFD8DC").pack(side="left")
        self.btn_start = RoundedButton(bot, text="START", command=self.on_confirm, width=120, height=50, bg_color=CLR_SUCCESS)
        self.btn_start.pack(side="right")
        
        self.update_visibility()
        self.select_field("temp") 
        self.deiconify(); self.lift(); self.grab_set(); self.wait_window()

    def update_visibility(self):
        if self.mode == "Manual":
            self.lbl_fan_info.pack(anchor="w", pady=(15, 2))
            self.btn_fan.pack(anchor="w")
        else:
            self.lbl_fan_info.pack_forget()
            self.btn_fan.pack_forget()

    def on_mode_change(self, val):
        self.mode = val
        self.update_visibility()
        if self.mode == "Auto" and self.active_field == "fan": self.select_field("temp")

    def select_field(self, field):
        self.active_field = field
        
        # Reset Borders
        self.btn_temp.set_color("#FAFAFA", "black")
        self.btn_temp.set_border("#E0E0E0", 1)
        
        self.btn_fan.set_color("#FAFAFA", "black")
        self.btn_fan.set_border("#E0E0E0", 1)
        
        # Highlight Active (Light Blue BG + Primary Color Border)
        active_btn = self.btn_temp if field == "temp" else self.btn_fan
        active_btn.set_color("#E3F2FD", CLR_PRIMARY) # Blue Text/BG
        active_btn.set_border(CLR_PRIMARY, 2)        # Blue Border

    def on_key(self, key):
        curr = self.temp_val if self.active_field == "temp" else self.fan_val
        if key == '.':
            if self.active_field == "fan": return 
            if '.' in curr: return
        if key == '⌫': curr = curr[:-1]
        else:
            if curr == "0" and key != '.': curr = key
            else: curr += key
        if not curr: curr = "0"
        
        if self.active_field == "temp":
            self.temp_val = curr; self.btn_temp.itemconfig(self.btn_temp.text_id, text=curr)
            self.lbl_temp_info.config(fg="#90A4AE", text="TARGET TEMP (15-35°C)")
        else:
            self.fan_val = curr; self.btn_fan.itemconfig(self.btn_fan.text_id, text=curr)
            self.lbl_fan_info.config(fg="#90A4AE", text="FAN SPEED (0-100%)")

    def on_confirm(self):
        try: t = float(self.temp_val)
        except: t = 0
        try: f = int(float(self.fan_val))
        except: f = 0
        
        valid = True
        
        # CHECK TEMP RANGE
        if not (15 <= t <= 35):
            self.btn_temp.set_color("#FFEBEE", CLR_DANGER) # Red BG
            self.btn_temp.set_border(CLR_DANGER, 2)        # Red Border
            self.lbl_temp_info.config(fg=CLR_DANGER, text="INVALID: Must be 15-35°C")
            valid = False
            
        # CHECK FAN RANGE
        if self.mode == "Manual" and not (0 <= f <= 100):
            self.btn_fan.set_color("#FFEBEE", CLR_DANGER) # Red BG
            self.btn_fan.set_border(CLR_DANGER, 2)        # Red Border
            self.lbl_fan_info.config(fg=CLR_DANGER, text="INVALID: Must be 0-100%")
            valid = False
            
        if not valid: return
        self.backend.state["target_temp"] = int(t)
        self.backend.state["fan_mode"] = self.mode
        self.backend.state["fan_manual_val"] = f
        self.result = True
        self.destroy()

class LogViewerPopup(ModalOverlay):
    def __init__(self, parent):
        super().__init__(parent)
        self.f = tk.Frame(self.cv, bg="white", width=700, height=400)
        self.cv.create_window(parent.winfo_width()/2, parent.winfo_height()/2, window=self.f)

        tk.Label(self.f, text="SYSTEM LOGS", font=("Arial", 14, "bold"), bg="white").pack(pady=10)
        self.text_area = tk.Text(self.f, font=("Courier", 10), height=15, width=80)
        self.text_area.pack(pady=10)
        RoundedButton(self.f, "CLOSE", self.destroy, width=100, height=40).pack()

        self.refresh_logs()
        self.deiconify()

    def refresh_logs(self):
        try:
            with open("/home/lhr/Robot_Client/logs/gui_debug.log", "r") as f:
                logs = f.readlines()[-20:]
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, "".join(logs))
        except: pass