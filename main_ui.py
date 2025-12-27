#version 1.1 Claibration screen + popup overlay + animation   
import tkinter as tk
from tkinter import ttk, messagebox
import os
import backend 
from datetime import datetime
import math

# --- TRY IMPORTING PIL ---
try:
    from PIL import Image, ImageTk, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠️ PIL not found. Install with: sudo apt-get install python3-pil.imagetk")

# --- CONFIGURATION ---
BASE_DIR = "/home/lhr/Robot_Client"
DIR_TEST = os.path.join(BASE_DIR, "test_protocols")
DIR_RECENT = os.path.join(BASE_DIR, "recent_protocols")
DIR_ICONS = os.path.join(BASE_DIR, "icons")

for d in [DIR_TEST, DIR_RECENT, DIR_ICONS]: 
    os.makedirs(d, exist_ok=True)

# --- GLOBAL COLORS ---
CLR_BG = "#F0F2F5"
CLR_CARD = "#FFFFFF"
CLR_SHADOW = "#D1D9E6"
CLR_PRIMARY = "#2196F3"     
CLR_PRIMARY_HOVER = "#1976D2"
CLR_INACTIVE = "#CFD8DC"
CLR_INACTIVE_HOVER = "#B0BEC5"      
CLR_SUCCESS = "#4CAF50"
CLR_SUCCESS_HOVER = "#388E3C"
CLR_SUCCESS_DARK = "#388E3C"  
CLR_DANGER = "#D32F2F"   
CLR_DANGER_HOVER = "#B71C1C"
CLR_WARNING = "#FBC02D" 
CLR_WARNING_HOVER = "#F57F17" 
CLR_WARNING_DARK = "#F57F17" 
CLR_TEXT = "#212121"
CLR_INFO_BOX = "#ECEFF1" 
CLR_PROG_BG = "#E0E0E0" 
CLR_SAND = "#FFD700"  
CLR_GLASS = "#555555" 

# --- ROUNDED BUTTON ---
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=120, height=50, radius=20, 
                 bg_color=CLR_PRIMARY, hover_color=CLR_PRIMARY_HOVER, fg_color="white", font=("Arial", 12, "bold")):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0)
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.fg_color = fg_color
        self.rect_id = self.create_rounded_rect(0, 0, width, height, radius, fill=bg_color, outline="")
        self.text_id = self.create_text(width/2, height/2, text=text, fill=fg_color, font=font)
        self.bind("<Enter>", self.on_enter); self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click); self.bind("<ButtonRelease-1>", self.on_release)

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def on_enter(self, e): self.itemconfig(self.rect_id, fill=self.hover_color)
    def on_leave(self, e): self.itemconfig(self.rect_id, fill=self.bg_color)
    def on_click(self, e): self.move(self.rect_id, 1, 1); self.move(self.text_id, 1, 1)
    
    def on_release(self, e): 
        self.move(self.rect_id, -1, -1); self.move(self.text_id, -1, -1); 
        if self.command: self.command()

    def set_color(self, bg, hover): 
        self.bg_color = bg; self.hover_color = hover; self.itemconfig(self.rect_id, fill=bg)

    def flash(self, color=CLR_PRIMARY):
        original = self.bg_color
        self.itemconfig(self.rect_id, fill=color)
        self.after(150, lambda: self.itemconfig(self.rect_id, fill=original))

# --- SHADOW CARD ---
class ShadowCard(tk.Frame):
    def __init__(self, parent, width=200, height=200, bg="white", border_color=None, padding=10):
        super().__init__(parent, bg=parent["bg"])
        self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(0, weight=1)
        self.shadow = tk.Frame(self, bg=CLR_SHADOW); self.shadow.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
        self.card = tk.Frame(self, bg=bg); 
        if border_color: self.card.config(highlightbackground=border_color, highlightthickness=2)
        self.card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
        self.inner = tk.Frame(self.card, bg=bg, padx=padding, pady=padding); self.inner.pack(fill="both", expand=True)

# --- HOURGLASS ---
class HourglassSpinner(tk.Canvas):
    def __init__(self, parent, size=30, bg="white"):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0)
        self.size = size; self.cx = size / 2; self.cy = size / 2; self.padding = 5
        self.angle = 0; self.sand_pct = 0; self.state = "draining" 
        self.rotation_speed = 10; self.drain_speed = 2; self.is_paused = False; self.is_animating = False
        self.animate()

    def set_paused(self, paused):
        self.is_paused = paused
        if not paused and not self.is_animating: self.animate()

    def draw_hourglass(self, angle_deg, sand_level):
        self.delete("all"); r = (self.size / 2) - self.padding; w = r * 0.8 
        base_pts = [(-w, -r), (w, -r), (0, 0), (-w, r), (w, r)]
        rad = math.radians(angle_deg); cos_a = math.cos(rad); sin_a = math.sin(rad)
        rot_pts = []
        for x, y in base_pts:
            nx = (x * cos_a - y * sin_a) + self.cx; ny = (x * sin_a + y * cos_a) + self.cy; rot_pts.append((nx, ny))
        self.create_polygon(rot_pts[0], rot_pts[1], rot_pts[2], outline=CLR_GLASS, width=4, fill="") 
        self.create_polygon(rot_pts[2], rot_pts[3], rot_pts[4], outline=CLR_GLASS, width=4, fill="") 
        if self.state == "rotating":
            self.create_polygon(rot_pts[2], rot_pts[3], rot_pts[4], fill=CLR_SAND, outline="")
        else:
            pct_rem = (100 - sand_level) / 100.0; t_h, t_w = r * pct_rem, w * pct_rem
            t_pts = [(-t_w, -t_h), (t_w, -t_h), (0, 0)]; self._draw_rot_poly(t_pts, cos_a, sin_a, CLR_SAND)
            pct_fill = sand_level / 100.0; s_w = w * (1.0 - pct_fill); s_h = r * (1.0 - pct_fill)
            b_pts = [(-w, r), (w, r), (s_w, s_h), (-s_w, s_h)]; self._draw_rot_poly(b_pts, cos_a, sin_a, CLR_SAND)
            if sand_level < 95: self.create_line(self.cx, self.cy, self.cx, self.cy + (r*0.8), fill=CLR_SAND, width=1)

    def _draw_rot_poly(self, pts, cos, sin, color):
        final = []
        for x, y in pts:
            nx = (x * cos - y * sin) + self.cx; ny = (x * sin + y * cos) + self.cy; final.append(nx); final.append(ny)
        self.create_polygon(final, fill=color, outline="")

    def animate(self):
        if self.is_paused: self.is_animating = False; return
        self.is_animating = True 
        if self.state == "draining":
            self.sand_pct += self.drain_speed
            if self.sand_pct >= 100: self.sand_pct = 100; self.state = "rotating" 
            self.draw_hourglass(0, self.sand_pct) 
        elif self.state == "rotating":
            self.angle += self.rotation_speed
            if self.angle >= 180: self.angle = 0; self.sand_pct = 0; self.state = "draining"
            self.draw_hourglass(self.angle, 100) 
        self.after(50, self.animate)

# --- PROGRESS BAR ---
class ModernProgressBar(tk.Canvas):
    def __init__(self, parent, width=600, height=30, bg_color=CLR_PROG_BG, fill_color=CLR_SUCCESS):
        super().__init__(parent, width=width, height=height, bg=CLR_CARD, highlightthickness=0)
        self.w = width; self.h = height; self.fill_color = fill_color; self.bg_color = bg_color; self.current_pct = 0.0; self.target_pct = 0.0
        self.create_rounded_rect(0, 0, width, height, radius=height, fill=bg_color, tags="bg")
        self.fill_id = self.create_rounded_rect(0, 0, 0, height, radius=height, fill=fill_color, tags="fill")

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def set_progress(self, pct): self.target_pct = max(0, min(100, pct)); self.animate()

    def animate(self):
        diff = self.target_pct - self.current_pct
        if abs(diff) < 0.5: self.current_pct = self.target_pct
        else: self.current_pct += diff * 0.1 
        new_width = (self.current_pct / 100) * self.w; 
        if new_width < self.h: new_width = 0 
        self.delete("fill"); 
        if new_width > 0: self.create_rounded_rect(0, 0, new_width, self.h, radius=self.h, fill=self.fill_color, tags="fill")
        if self.current_pct != self.target_pct: self.after(20, self.animate)

# --- BACKGROUND GENERATOR ---
def get_blur_bg(parent):
    if not HAS_PIL: return None
    try:
        x = parent.winfo_rootx(); y = parent.winfo_rooty(); w = parent.winfo_width(); h = parent.winfo_height()
        img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
        white_layer = Image.new("RGB", img.size, (255, 255, 255))
        blended = Image.blend(img, white_layer, 0.8) 
        return ImageTk.PhotoImage(blended)
    except Exception as e: return None

# --- BASE MODAL ---
class ModalOverlay(tk.Toplevel):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.withdraw()
        x = parent.winfo_rootx(); y = parent.winfo_rooty(); w = parent.winfo_width(); h = parent.winfo_height()
        self.geometry(f"{w}x{h}+{x}+{y}"); self.overrideredirect(True); self.config(cursor="none")
        self.bg_img = get_blur_bg(parent)
        self.cv = tk.Canvas(self, width=w, height=h, highlightthickness=0, bg="white")
        self.cv.pack(fill="both", expand=True)
        if self.bg_img: self.cv.create_image(0, 0, image=self.bg_img, anchor="nw")
        else: self.cv.configure(bg="#EEEEEE")
        self.lift(); self.grab_set()

# --- POPUPS ---
class CustomPopup(ModalOverlay):
    def __init__(self, parent, title, header, message, color, icon_text, height=340, icon_size=50):
        super().__init__(parent)
        cw, ch = 420, height 
        cx = parent.winfo_width() / 2; cy = parent.winfo_height() / 2
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=color, width=2)
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4); self.f.pack_propagate(False)
        self.cv.create_window(cx, cy, window=self.f)
        
        head_box = tk.Frame(self.f, bg="white"); head_box.pack(pady=(25, 5))
        tk.Label(head_box, text=icon_text, font=("Arial", icon_size), fg=color, bg="white").pack(side="top", pady=(0, 5))
        tk.Label(head_box, text=header, font=("Arial", 20, "bold"), fg=color, bg="white").pack(side="top")
        tk.Frame(self.f, height=3, bg=color, width=320).pack(pady=10)
        msg_frame = tk.Frame(self.f, bg="white"); msg_frame.pack(pady=5, padx=20)
        for line in message.split("\n"): 
            tk.Label(msg_frame, text=line, font=("Arial", 12), bg="white", fg="#444").pack(anchor="n")
        btn_f = tk.Frame(self.f, bg="white"); btn_f.pack(side="bottom", pady=25)
        RoundedButton(btn_f, text="OK", command=self.destroy, width=140, height=50, bg_color=color, hover_color=color).pack()
        self.deiconify(); self.update_idletasks()

class CustomConfirmPopup(ModalOverlay):
    def __init__(self, parent, title, header, message):
        super().__init__(parent); self.result = False
        cw, ch = 400, 220  
        cx = parent.winfo_width() / 2; cy = parent.winfo_height() / 2
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=CLR_DANGER, width=2)
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4); self.f.pack_propagate(False)
        self.cv.create_window(cx, cy, window=self.f)
        
        head_box = tk.Frame(self.f, bg="white"); head_box.pack(pady=(10, 2))
        tk.Label(head_box, text="?", font=("Arial", 42), fg=CLR_DANGER, bg="white").pack(side="top", pady=(0, 0))
        tk.Label(head_box, text=header, font=("Arial", 18, "bold"), fg=CLR_DANGER, bg="white").pack(side="top")
        tk.Frame(self.f, height=3, bg=CLR_DANGER, width=300).pack(pady=5)
        tk.Label(self.f, text=message, font=("Arial", 12), bg="white", fg="#444").pack(pady=2)
        
        btn_f = tk.Frame(self.f, bg="white"); btn_f.pack(side="bottom", pady=15)
        RoundedButton(btn_f, text="CANCEL", command=self.on_cancel, width=110, height=45, bg_color="#9E9E9E", hover_color="#757575").pack(side="left", padx=10)
        RoundedButton(btn_f, text="CONFIRM", command=self.on_confirm, width=110, height=45, bg_color=CLR_DANGER, hover_color=CLR_DANGER_HOVER).pack(side="left", padx=10)
        
        self.deiconify(); self.update_idletasks(); self.wait_window()
    def on_confirm(self): self.result = True; self.destroy()
    def on_cancel(self): self.result = False; self.destroy()

# --- HOMING POPUP ---
class HomingPopup(ModalOverlay):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.c = controller
        self.homing_seen = False
        cw, ch = 480, 240 
        cx = parent.winfo_width() / 2; cy = parent.winfo_height() / 2
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=CLR_PRIMARY, width=2)
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4); self.f.pack_propagate(False)
        self.cv.create_window(cx, cy, window=self.f)
        
        self.head_box = tk.Frame(self.f, bg="white"); self.head_box.pack(pady=(20, 5))
        self.lbl_icon = tk.Label(self.head_box, text="⌂", font=("Arial", 28), fg=CLR_PRIMARY, bg="white")
        self.lbl_icon.pack(side="left", padx=10)
        self.lbl_title = tk.Label(self.head_box, text="HOMING...", font=("Arial", 18, "bold"), fg=CLR_PRIMARY, bg="white")
        self.lbl_title.pack(side="left")
        
        tk.Frame(self.f, height=2, bg="#E0E0E0", width=400).pack(pady=5)
        self.lbl_desc = tk.Label(self.f, text="Homing and moving to calibration Point...", font=("Arial", 11), bg="white", fg="#777")
        self.lbl_desc.pack(pady=(5, 10))
        
        anim = tk.Frame(self.f, bg="white"); anim.pack(pady=5)
        self.spinner = HourglassSpinner(anim, size=30, bg="white"); self.spinner.pack(side="left", padx=15)
        
        log_box = tk.Frame(self.f, bg="#F5F5F5", bd=1, relief="solid")
        log_box.pack(pady=10, padx=20, fill="x")
        self.lbl_log = tk.Label(log_box, text="Waiting...", font=("Courier", 10), bg="#F5F5F5", fg="#333")
        self.lbl_log.pack(pady=5)
        self.deiconify(); self.update_idletasks(); self.monitor()

    def monitor(self):
        logs = self.c.backend.state["logs"]
        if logs:
            recent_logs = logs[-3:] 
            last_msg = recent_logs[-1].split("] ")[-1] if "]" in recent_logs[-1] else recent_logs[-1]
            self.lbl_log.config(text=last_msg[:45]) 
            for l in recent_logs:
                if "HOME" in l and not self.homing_seen:
                    self.homing_seen = True
                    self.lbl_title.config(text="MOVING...")
                    # --- FIX: Reduced font size from 40 to 32 ---
                    self.lbl_icon.config(text="⦻", font=("Arial", 32, "bold")) 
                    self.lbl_desc.config(text="Moving to calibration Point...")
            if self.homing_seen:
                for l in recent_logs:
                    if "RX: X" in l or "RX:X" in l:
                        self.after(500, self.destroy)
                        return
        if self.c.backend.state["error_msg"] or "Error" in self.c.backend.state["status"]: self.destroy(); return
        self.after(100, self.monitor)

# --- MAIN APP ---
class KioskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.backend = backend.RobotClient()
        self.backend.start()
        w, h = 800, 480; self.geometry(f"{w}x{h}"); self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (w // 2); y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}"); self.config(bg=CLR_BG, cursor="none")
        style = ttk.Style(); style.theme_use("clam")
        style.configure("Treeview", background="white", foreground=CLR_TEXT, rowheight=50, font=("Arial", 14))
        style.configure("Treeview.Heading", font=('Arial', 14, 'bold'))
        style.map('Treeview', background=[('selected', CLR_PRIMARY)])
        self.offsets = {"X": tk.DoubleVar(value=0.0), "Y": tk.DoubleVar(value=0.0), "Z1": tk.DoubleVar(value=0.0), "Z2": tk.DoubleVar(value=0.0)}
        self.step_size = tk.DoubleVar(value=1.0)
        self.selected_file = tk.StringVar(value="No File Selected")
        self.current_page_name = "Home"
        container = tk.Frame(self, bg=CLR_BG); container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1); container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for F in (Home, Calibrate, ProtocolList, Running):
            page_name = F.__name__; frame = F(parent=container, controller=self)
            self.frames[page_name] = frame; frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("Home"); self.start_ui_updater()

    def show_frame(self, page_name):
        self.current_page_name = page_name; frame = self.frames[page_name]; frame.tkraise()
        if page_name == "Calibrate": frame.on_enter()
        if page_name == "ProtocolList": frame.refresh_files(frame.current_dir)

    def start_ui_updater(self):
        state = self.backend.state
        if "Running" in state["status"] or "Paused" in state["status"]:
            if self.current_page_name != "Running": self.selected_file.set(state["filename"]); self.show_frame("Running")
        if self.current_page_name == "Running": self.frames["Running"].update_view(state)
        if state["stop_reason"]:
            reason = state["stop_reason"].upper(); filename = state["filename"]; time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"File: {filename}\nSource: {reason}\nTime: {time_now}"
            popup = CustomPopup(self, "Stopped", "PROTOCOL STOPPED", msg, CLR_WARNING, "⚠"); self.wait_window(popup); self.backend.ui_ack_stop(); self.show_frame("Home")
        if state["error_msg"]:
            error_text = state["error_msg"]; time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"Time: {time_now}\nDetails: {error_text}"
            popup = CustomPopup(self, "System Error", "HARDWARE ERROR", msg, CLR_DANGER, "✖"); self.wait_window(popup); self.backend.ui_ack_error(); self.show_frame("Home")
        if state["completed"]:
            filename = state["filename"]; time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"File: {filename}\nFinished At: {time_now}"
            if self.current_page_name == "Running":
                popup = CustomPopup(self, "Done", "COMPLETED", msg, CLR_SUCCESS, "✔"); self.wait_window(popup); self.backend.ui_ack_stop(); self.show_frame("Home")
            else: self.backend.state["completed"] = False; self.backend.ui_ack_stop()
        self.after(200, self.start_ui_updater)

# --- HOME SCREEN ---
class Home(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        card = ShadowCard(self, bg=CLR_CARD)
        card.place(relx=0.5, rely=0.5, anchor="center", width=500, height=350)
        tk.Label(card.inner, text="Liquid Handler v1.0", font=("Arial", 22, "bold"), bg=CLR_CARD).pack(pady=(30, 40))
        RoundedButton(card.inner, text="CALIBRATION", width=250, height=60, bg_color="#FF9800", hover_color=CLR_WARNING_HOVER, command=lambda: controller.show_frame("Calibrate")).pack(pady=15)
        RoundedButton(card.inner, text="RUN PROTOCOL", width=250, height=60, bg_color=CLR_PRIMARY, hover_color=CLR_PRIMARY_HOVER, command=lambda: controller.show_frame("ProtocolList")).pack(pady=15)

# --- CALIBRATE SCREEN ---
class Calibrate(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        
        header = tk.Frame(self, bg=CLR_BG, pady=5)
        header.pack(fill="x", pady=(20, 5)) 
        tk.Label(header, text="SYSTEM CALIBRATION", font=("Arial", 16, "bold"), bg=CLR_BG, fg=CLR_PRIMARY).pack(side="left", padx=20)
        
        main = tk.Frame(self, bg=CLR_BG); main.pack(fill="both", expand=True, padx=10, pady=5)
        main.grid_columnconfigure(0, weight=3); main.grid_columnconfigure(1, weight=1); main.grid_columnconfigure(2, weight=2) 

        # 1. XY CARD
        xy_outer = tk.Frame(main, bg=CLR_BG); xy_outer.grid(row=0, column=0, sticky="nsew", padx=5)
        self.xy_card = ShadowCard(xy_outer, bg=CLR_CARD, border_color=CLR_PRIMARY); self.xy_card.pack(fill="both", expand=True)
        tk.Label(self.xy_card.inner, text="XY AXIS", font=("Arial", 14, "bold"), bg=CLR_CARD, fg=CLR_PRIMARY).pack(pady=10)
        dpad = tk.Frame(self.xy_card.inner, bg=CLR_CARD); dpad.pack()
        
        # --- NEW HELPER FOR INTERACTIVE BUTTONS ---
        def mk_btn(parent, txt, axis, d): 
            b = RoundedButton(parent, text=txt, command=None, width=78, height=65, bg_color=CLR_INACTIVE, hover_color="#B0BEC5", fg_color="black")
            b.command = lambda: self.move(axis, d, b)
            return b
        
        mk_btn(dpad, "Y+", "Y", 1).grid(row=0, column=1, pady=5)
        mk_btn(dpad, "X-", "X", -1).grid(row=1, column=0, padx=3)
        mk_btn(dpad, "X+", "X", 1).grid(row=1, column=2, padx=3)
        mk_btn(dpad, "Y-", "Y", -1).grid(row=2, column=1, pady=5)

        # 2. Z CARD
        z_outer = tk.Frame(main, bg=CLR_BG); z_outer.grid(row=0, column=1, sticky="nsew", padx=5)
        self.z_card = ShadowCard(z_outer, bg=CLR_CARD, border_color=CLR_WARNING); self.z_card.pack(fill="both", expand=True)
        tk.Label(self.z_card.inner, text="Z AXIS", font=("Arial", 14, "bold"), bg=CLR_CARD, fg=CLR_WARNING_DARK).pack(pady=(10, 5))
        z_grid = tk.Frame(self.z_card.inner, bg=CLR_CARD); z_grid.pack()
        
        def mk_z_btn(parent, txt, axis, d): 
            b = RoundedButton(parent, text=txt, command=None, width=68, height=60, bg_color=CLR_INACTIVE, hover_color="#B0BEC5", fg_color="black")
            b.command = lambda: self.move(axis, d, b)
            return b

        tk.Label(z_grid, text="Z1", font=("Arial", 12, "bold"), bg=CLR_CARD).grid(row=0, column=0, pady=(0, 20), sticky="s")
        mk_z_btn(z_grid, "▲", "Z1", 1).grid(row=1, column=0, pady=(0, 5), padx=5)
        mk_z_btn(z_grid, "▼", "Z1", -1).grid(row=2, column=0, pady=5, padx=5)
        
        tk.Label(z_grid, text="Z2", font=("Arial", 12, "bold"), bg=CLR_CARD).grid(row=0, column=1, pady=(0, 20), sticky="s")
        mk_z_btn(z_grid, "▲", "Z2", 1).grid(row=1, column=1, pady=(0, 5), padx=5)
        mk_z_btn(z_grid, "▼", "Z2", -1).grid(row=2, column=1, pady=5, padx=5)

        # 3. LIVE CHANGES
        data_outer = tk.Frame(main, bg=CLR_BG); data_outer.grid(row=0, column=2, sticky="nsew", padx=5)
        self.data_card = ShadowCard(data_outer, bg=CLR_CARD, border_color=CLR_SUCCESS); self.data_card.pack(fill="both", expand=True)
        tk.Label(self.data_card.inner, text="LIVE CHANGES", font=("Arial", 14, "bold"), bg=CLR_CARD, fg=CLR_SUCCESS_DARK).pack(pady=10)
        self.info_box = tk.Frame(self.data_card.inner, bg=CLR_INFO_BOX, padx=10, pady=10); self.info_box.pack(fill="x", pady=5)
        lbl_style = {"font": ("Courier", 14, "bold"), "bg": CLR_INFO_BOX, "fg": "#333"}
        self.lbl_x = tk.Label(self.info_box, text="X : 0.0", **lbl_style); self.lbl_x.pack(anchor="w")
        self.lbl_y = tk.Label(self.info_box, text="Y : 0.0", **lbl_style); self.lbl_y.pack(anchor="w")
        self.lbl_z1 = tk.Label(self.info_box, text="Z1: 0.0", **lbl_style); self.lbl_z1.pack(anchor="w")
        self.lbl_z2 = tk.Label(self.info_box, text="Z2: 0.0", **lbl_style); self.lbl_z2.pack(anchor="w")
        
        tk.Label(self.data_card.inner, text="STEP SIZE (mm)", font=("Arial", 12, "bold"), bg=CLR_CARD, fg="#555").pack(pady=(15, 5))
        step_f = tk.Frame(self.data_card.inner, bg=CLR_CARD); step_f.pack()
        self.step_btns = {}
        for val in [0.1, 1.0, 10.0]:
            b = RoundedButton(step_f, text=str(val), command=lambda v=val: self.set_step(v), width=60, height=60, bg_color=CLR_INACTIVE, hover_color="#B0BEC5", fg_color="black")
            b.pack(side="left", padx=5)
            self.step_btns[val] = b
        self.set_step(1.0) 

        footer = tk.Frame(self, bg=CLR_BG, height=70); footer.pack(side="bottom", fill="x", pady=(2, 10), padx=20)
        
        RoundedButton(footer, text="EXIT", command=self.confirm_exit, width=120, height=60, bg_color="#9E9E9E", hover_color="#757575").pack(side="left")
        RoundedButton(footer, text="SAVE", command=self.confirm_save, width=120, height=60, bg_color=CLR_SUCCESS, hover_color=CLR_SUCCESS_HOVER).pack(side="right")

    def set_step(self, val):
        self.c.step_size.set(val)
        for v, btn in self.step_btns.items():
            if v == val: btn.set_color(CLR_PRIMARY, CLR_PRIMARY_HOVER); btn.itemconfig(btn.text_id, fill="white")
            else: btn.set_color(CLR_INACTIVE, CLR_INACTIVE_HOVER); btn.itemconfig(btn.text_id, fill="black")

    def on_enter(self):
        self.c.backend.ui_send_gcode("T00")
        self.c.update() 
        HomingPopup(self.c, self.c) 
        self.lbl_x.config(text="X : 0.0"); self.lbl_y.config(text="Y : 0.0"); self.lbl_z1.config(text="Z1: 0.0"); self.lbl_z2.config(text="Z2: 0.0")
        for k in self.c.offsets: self.c.offsets[k].set(0.0)

    # --- UPDATED MOVE FUNCTION WITH ANIMATION ---
    def move(self, axis, direction, btn_instance):
        btn_instance.flash(CLR_PRIMARY)
        step = self.c.step_size.get() * direction
        dx, dy, dz1, dz2 = 0, 0, 0, 0
        current = self.c.offsets[axis].get(); new_val = round(current + step, 2); self.c.offsets[axis].set(new_val)
        
        target_lbl, axis_prefix = None, ""
        if axis == "X": 
            axis_prefix = "X : "; target_lbl = self.lbl_x; dx = step
        elif axis == "Y": 
            axis_prefix = "Y : "; target_lbl = self.lbl_y; dy = step
        elif axis == "Z1": 
            axis_prefix = "Z1: "; target_lbl = self.lbl_z1; dz1 = step
        elif axis == "Z2": 
            axis_prefix = "Z2: "; target_lbl = self.lbl_z2; dz2 = step
        
        txt_sign = f"+{step}" if step > 0 else f"{step}"
        self.float_animation(target_lbl, txt_sign)
        self.animate_counter(target_lbl, axis_prefix, current, new_val)

        self.c.backend.ui_send_gcode(f"C dx={dx}, dy={dy}, dz1={dz1}, dz2={dz2}")

    def float_animation(self, target_widget, text):
        lbl = tk.Label(self.info_box, text=text, fg=CLR_SUCCESS, bg=CLR_INFO_BOX, font=("Arial", 12, "bold"))
        x = target_widget.winfo_x() + 150 
        y = target_widget.winfo_y()
        lbl.place(x=x, y=y)
        
        def anim_loop(step=0):
            if step < 10:
                lbl.place(y=y - step*2) 
                self.after(30, lambda: anim_loop(step+1))
            else:
                lbl.destroy() 
        anim_loop()

    # --- NEW: VALUE COUNTER ANIMATION ---
    def animate_counter(self, lbl, prefix, start, end, step_count=10):
        diff = end - start
        step_size = diff / step_count
        
        def update_step(i):
            if i <= step_count:
                current = start + (step_size * i)
                # Text turns GREEN during animation
                lbl.config(text=f"{prefix}{current:.1f}", fg=CLR_SUCCESS) 
                self.after(15, lambda: update_step(i+1))
            else:
                # Text returns to DARK GRAY when finished
                lbl.config(text=f"{prefix}{end:.1f}", fg="#333")
        
        update_step(1)

    # --- NEW CONFIRMATION METHODS ---
    def confirm_exit(self):
        c = CustomConfirmPopup(self.c, "Exit?", "EXIT CALIBRATION", "Unsaved changes will be lost.")
        if c.result:
            self.c.show_frame("Home")

    def confirm_save(self):
        c = CustomConfirmPopup(self.c, "Save?", "SAVE OFFSETS", "Update calibration settings?")
        if c.result:
            self.update() # Fix for white background issue
            self.c.backend.ui_send_gcode("OK_C")
            # --- FIX: Height 300 to fix Button Overflow ---
            popup = CustomPopup(self.c, "Saved", "SAVED", "Offsets updated successfully.", CLR_SUCCESS, "💾", height=300, icon_size=38)
            self.wait_window(popup)
            self.c.show_frame("Home")

# --- PROTOCOL LIST (MODERN) ---
class ProtocolList(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller; self.current_dir = DIR_TEST; self.icon_file = None
        try: f_path = os.path.join(DIR_ICONS, "file.png"); self.icon_file = tk.PhotoImage(file=f_path).subsample(15, 15) 
        except: pass
        footer = tk.Frame(self, bg="white", height=80); footer.pack(side="bottom", fill="x", pady=10)
        RoundedButton(footer, text="<< BACK", command=lambda: controller.show_frame("Home"), width=120, height=50, bg_color=CLR_INACTIVE, hover_color=CLR_INACTIVE_HOVER, fg_color="black").pack(side="left", padx=20)
        RoundedButton(footer, text="START >>", command=self.load_and_run, width=120, height=50, bg_color=CLR_SUCCESS, hover_color=CLR_SUCCESS_HOVER).pack(side="right", padx=20)
        header = tk.Frame(self, bg=CLR_BG); header.pack(side="top", fill="x", pady=10, padx=20)
        self.btn_test = tk.Button(header, text="TEST PROTOCOLS", font=("Arial", 13, "bold"), height=2, relief="flat", command=lambda: self.switch_tab("TEST"))
        self.btn_test.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.btn_recent = tk.Button(header, text="RECENT FILES", font=("Arial", 13, "bold"), height=2, relief="flat", command=lambda: self.switch_tab("RECENT"))
        self.btn_recent.pack(side="left", fill="x", expand=True, padx=(2, 0))
        list_frame = ShadowCard(self, bg="white"); list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))
        self.tree = ttk.Treeview(list_frame.inner, columns=("name"), show="tree", selectmode="browse"); self.tree.column("#0", anchor="w"); self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame.inner, orient="vertical", command=self.tree.yview); sb.pack(side="right", fill="y"); self.tree.configure(yscrollcommand=sb.set); self.switch_tab("TEST")
    def switch_tab(self, tab_name):
        self.current_dir = DIR_TEST if tab_name == "TEST" else DIR_RECENT
        self.btn_test.config(bg=CLR_PRIMARY if tab_name == "TEST" else CLR_INACTIVE, fg="white" if tab_name == "TEST" else "black")
        self.btn_recent.config(bg=CLR_PRIMARY if tab_name == "RECENT" else CLR_INACTIVE, fg="white" if tab_name == "RECENT" else "black")
        self.refresh_files(self.current_dir)
    def refresh_files(self, folder_path):
        for item in self.tree.get_children(): self.tree.delete(item)
        try:
            for f in sorted(os.listdir(folder_path)):
                if f.endswith(('.g', '.nc', '.gc', '.gcode', '.txt')):
                    if self.icon_file: self.tree.insert("", "end", iid=f, text=f"  {f}", image=self.icon_file)
                    else: self.tree.insert("", "end", iid=f, text=f"  [FILE]  {f}")
        except: pass
    def load_and_run(self):
        sel = self.tree.selection()
        if not sel: return
        self.c.selected_file.set(sel[0]); self.c.backend.ui_load_and_run(sel[0]); self.c.show_frame("Running")

# --- 4. RUNNING SCREEN (MODERN) ---
class Running(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_CARD)
        self.c = controller
        tk.Label(self, text="RUNNING PROTOCOL", font=("Arial", 12, "bold"), fg=CLR_INACTIVE, bg=CLR_CARD).pack(pady=(20, 0))
        tk.Label(self, textvariable=controller.selected_file, font=("Arial", 18, "bold"), fg=CLR_PRIMARY, bg=CLR_CARD).pack(pady=5)
        info_box = tk.Frame(self, bg=CLR_INFO_BOX, bd=2, relief="groove"); info_box.pack(pady=15, fill="x", padx=40)
        tk.Label(info_box, text="Current Command:", font=("Arial", 10), bg=CLR_INFO_BOX, fg="gray").pack(pady=(10,0))
        self.cmd_lbl = tk.Label(info_box, text="Waiting...", font=("Courier New", 18, "bold"), bg=CLR_INFO_BOX, fg="black"); self.cmd_lbl.pack(pady=5)
        tk.Label(info_box, text="Description:", font=("Arial", 10), bg=CLR_INFO_BOX, fg="gray").pack(pady=(5,0))
        self.desc_lbl = tk.Label(info_box, text="--", font=("Arial", 14, "italic"), fg="#37474F", bg=CLR_INFO_BOX); self.desc_lbl.pack(pady=(0, 10))
        stats_frame = tk.Frame(self, bg=CLR_CARD); stats_frame.pack(fill="x", padx=50, pady=(15, 0))
        self.percent_lbl = tk.Label(stats_frame, text="0%", font=("Arial", 28, "bold"), bg=CLR_CARD, fg=CLR_PRIMARY); self.percent_lbl.pack(side="left")
        right_box = tk.Frame(stats_frame, bg=CLR_CARD); right_box.pack(side="right")
        self.spinner = HourglassSpinner(right_box, size=30, bg=CLR_CARD); self.spinner.pack(side="left", padx=10)
        self.time_lbl = tk.Label(right_box, text="Est: --:--:--:--", font=("Arial", 18, "bold"), bg=CLR_CARD, fg="#555"); self.time_lbl.pack(side="left")
        self.prog = ModernProgressBar(self, width=700, height=25, fill_color=CLR_SUCCESS); self.prog.pack(pady=(5, 20))
        footer = tk.Frame(self, bg=CLR_CARD); footer.pack(side="bottom", pady=30)
        self.btn_pause = RoundedButton(footer, text="❚❚  PAUSE", command=lambda: self.c.backend.ui_pause_resume(), width=160, height=50, bg_color=CLR_WARNING, hover_color=CLR_WARNING_HOVER); self.btn_pause.pack(side="left", padx=20)
        RoundedButton(footer, text="■  STOP", command=self.cancel_run, width=140, height=50, bg_color=CLR_DANGER, hover_color=CLR_DANGER_HOVER).pack(side="left", padx=20)
        self.status_debug = tk.Label(self, text="Status: IDLE", font=("Arial", 10), bg=CLR_CARD, fg="gray"); self.status_debug.place(x=10, y=10)
    def cancel_run(self):
        confirm = CustomConfirmPopup(self.c, "Stop Confirmation", "STOP PROTOCOL", "Are you sure you want to abort?")
        if confirm.result: self.c.backend.ui_stop()
    def update_view(self, state):
        progress = state["progress"]; status = state["status"]; cmd_text = state["current_line"]; desc_text = state.get("current_desc", ""); est_time = state.get("est", "--:--:--:--")
        self.status_debug.config(text=f"System Status: {status}")
        self.prog.set_progress(progress); self.percent_lbl.config(text=f"{int(progress)}%"); self.time_lbl.config(text=f"Est: {est_time}")
        is_paused = "Paused" in status; self.spinner.set_paused(is_paused)
        if is_paused:
            self.cmd_lbl.config(text=f"PAUSED ({state.get('pause_reason', 'UNKNOWN').upper()})", fg="red")
            self.desc_lbl.config(text="Click Resume to continue...", fg="red")
            self.btn_pause.itemconfig(self.btn_pause.text_id, text="▶  RESUME"); self.btn_pause.itemconfig(self.btn_pause.rect_id, fill=CLR_SUCCESS)
            self.btn_pause.bg_color = CLR_SUCCESS; self.btn_pause.hover_color = CLR_SUCCESS_HOVER
        else:
            self.cmd_lbl.config(text=cmd_text, fg="black"); self.desc_lbl.config(text=desc_text, fg="#37474F")
            self.btn_pause.itemconfig(self.btn_pause.text_id, text="❚❚  PAUSE"); self.btn_pause.itemconfig(self.btn_pause.rect_id, fill=CLR_WARNING)
            self.btn_pause.bg_color = CLR_WARNING; self.btn_pause.hover_color = CLR_WARNING_HOVER

if __name__ == "__main__":
    app = KioskApp()
    app.mainloop()