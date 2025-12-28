#version 1.1 Runnig Screen updated
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

for d in [DIR_TEST, DIR_RECENT]: 
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
CLR_LIGHT_BLUE = "#E3F2FD" 

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


# --- PROGRESS BAR (Fixed for low percentages) ---
class ModernProgressBar(tk.Canvas):
    def __init__(self, parent, width=600, height=30, bg_color=CLR_PROG_BG, fill_color=CLR_SUCCESS):
        super().__init__(parent, width=width, height=height, bg=CLR_CARD, highlightthickness=0)
        self.w = width
        self.h = height
        self.fill_color = fill_color
        self.bg_color = bg_color
        self.current_pct = 0.0
        self.target_pct = 0.0
        
        # Draw Background
        self.create_rounded_rect(0, 0, width, height, radius=height, fill=bg_color, tags="bg")
        # Draw Fill (Empty initially)
        self.fill_id = self.create_rounded_rect(0, 0, 0, height, radius=height, fill=fill_color, tags="fill")

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [
            x1+radius, y1,
            x1+radius, y1,
            x2-radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, **kwargs, smooth=True)

    def set_progress(self, pct):
        self.target_pct = max(0, min(100, pct))
        self.animate()

    def animate(self):
        diff = self.target_pct - self.current_pct
        if abs(diff) < 0.5:
            self.current_pct = self.target_pct
        else:
            self.current_pct += diff * 0.1 
        
        # Calculate visual width
        raw_width = (self.current_pct / 100) * self.w
        
        # --- FIX: VISIBILITY FOR LOW % ---
        # If pct > 0.5% but the width is smaller than the height (diameter), 
        # force the width to equal the height so we draw at least a circle.
        if self.current_pct > 0.5:
            new_width = max(self.h, raw_width)
        else:
            new_width = 0

        self.delete("fill")
        if new_width > 0: 
            self.create_rounded_rect(0, 0, new_width, self.h, radius=self.h, fill=self.fill_color, tags="fill")
        
        if self.current_pct != self.target_pct:
            self.after(20, self.animate)
            
# --- SCROLLABLE FRAME ---
class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=kwargs.get("bg", "white"), highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=kwargs.get("bg", "white"))

        # Link scrollbar to canvas
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Ensure inner frame expands to full width
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4: self.canvas.yview_scroll(-1, "units")
        elif event.num == 5: self.canvas.yview_scroll(1, "units")

# --- BACKGROUND GENERATOR (Fixed) ---
def get_blur_bg(root_window):
    if not HAS_PIL: return None
    try:
        # Capture the entire root window (which shows current screen)
        x = root_window.winfo_rootx()
        y = root_window.winfo_rooty()
        w = root_window.winfo_width()
        h = root_window.winfo_height()
        
        # Grab the screen area of the app
        img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
        
        # Blur it (blend with white)
        white_layer = Image.new("RGB", img.size, (255, 255, 255))
        blended = Image.blend(img, white_layer, 0.85) # slightly more opaque for better readability
        return ImageTk.PhotoImage(blended)
    except Exception as e: 
        print(f"BG Error: {e}")
        return None

# --- BASE MODAL (Fixed) ---
class ModalOverlay(tk.Toplevel):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.withdraw()
        
        # Use the root window (app) to get dimensions/pos
        root = parent.winfo_toplevel()
        x = root.winfo_rootx()
        y = root.winfo_rooty()
        w = root.winfo_width()
        h = root.winfo_height()
        
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.overrideredirect(True)
        self.config(cursor="none")
        
        # Capture BG from Root (Current Screen)
        self.bg_img = get_blur_bg(root)
        
        self.cv = tk.Canvas(self, width=w, height=h, highlightthickness=0, bg="white")
        self.cv.pack(fill="both", expand=True)
        if self.bg_img: self.cv.create_image(0, 0, image=self.bg_img, anchor="nw")
        else: self.cv.configure(bg="#EEEEEE")
        
        self.bind("<Button-1>", lambda e: self.config(cursor="none"))

class CustomPopup(ModalOverlay):
    def __init__(self, parent, title, header, message, color, icon_text, height=290, icon_size=45):
        super().__init__(parent)
        
        # --- FIX: Decreased Width to 380 ---
        cw, ch = 380, height 
        cx = parent.winfo_width() / 2
        cy = parent.winfo_height() / 2
        
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=color, width=2)
        
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4)
        self.cv.create_window(cx, cy, window=self.f)
        
        head_box = tk.Frame(self.f, bg="white")
        head_box.pack(pady=(15, 2))
        
        tk.Label(head_box, text=icon_text, font=("Arial", icon_size), fg=color, bg="white").pack(side="top")
        tk.Label(head_box, text=header, font=("Arial", 20, "bold"), fg=color, bg="white").pack(side="top")
        
        tk.Frame(self.f, height=3, bg=color, width=300).pack(pady=8)
        
        msg_frame = tk.Frame(self.f, bg="white")
        msg_frame.pack(pady=2, padx=15)
        
        # Wraplength slightly smaller than cw (380 - padding)
        tk.Label(msg_frame, text=message, font=("Arial", 12), bg="white", fg="#444", wraplength=340).pack(anchor="n")
        
        btn_f = tk.Frame(self.f, bg="white")
        btn_f.pack(side="bottom", pady=20)
        
        RoundedButton(btn_f, text="OK", command=self.destroy, width=130, height=45, bg_color=color, hover_color=color).pack()
        
        self.deiconify()
        self.update_idletasks()
        self.lift()
        self.grab_set()

class CustomConfirmPopup(ModalOverlay):
    def __init__(self, parent, title, header, message, width=420, height=240):
        super().__init__(parent); self.result = False
        
        cw, ch = width, height
        cx = parent.winfo_width() / 2
        cy = parent.winfo_height() / 2
        
        # Shadow & Border
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=CLR_DANGER, width=2)
        
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4)
        self.f.pack_propagate(False) # Keep fixed size requested
        self.cv.create_window(cx, cy, window=self.f)
        
        # Content
        head_box = tk.Frame(self.f, bg="white"); head_box.pack(pady=(15, 5))
        tk.Label(head_box, text="?", font=("Arial", 40), fg=CLR_DANGER, bg="white").pack(side="top")
        tk.Label(head_box, text=header, font=("Arial", 18, "bold"), fg=CLR_DANGER, bg="white").pack(side="top")
        
        tk.Frame(self.f, height=2, bg=CLR_DANGER, width=300).pack(pady=5)
        tk.Label(self.f, text=message, font=("Arial", 12), bg="white", fg="#444", wraplength=cw-40).pack(pady=5)
        
        # Buttons
        btn_f = tk.Frame(self.f, bg="white"); btn_f.pack(side="bottom", pady=20)
        RoundedButton(btn_f, text="CANCEL", command=self.on_cancel, width=120, height=50, bg_color="#9E9E9E", hover_color="#757575").pack(side="left", padx=15)
        RoundedButton(btn_f, text="CONFIRM", command=self.on_confirm, width=120, height=50, bg_color=CLR_DANGER, hover_color=CLR_DANGER_HOVER).pack(side="left", padx=15)
        
        self.deiconify(); self.lift(); self.grab_set(); self.wait_window()
        
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
        
        # --- FIX: Show and Grab here ---
        self.deiconify()
        self.update_idletasks()
        self.lift()
        # Note: We don't grab_set homing usually to allow background update, but if you want modal:
        # self.grab_set() 
        self.monitor()

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
        
        # 1. Initialize Backend
        self.backend = backend.RobotClient()
        self.backend.start()
        
        # 2. Window Setup
        w, h = 800, 480
        self.geometry(f"{w}x{h}")
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.config(bg=CLR_BG, cursor="none")
        
        self.bind("<Button-1>", lambda e: self.config(cursor="none"))
        self.bind("<FocusIn>", lambda e: self.config(cursor="none"))

        style = ttk.Style()
        style.theme_use("clam")
        
        self.offsets = {"X": tk.DoubleVar(value=0.0), "Y": tk.DoubleVar(value=0.0), "Z1": tk.DoubleVar(value=0.0), "Z2": tk.DoubleVar(value=0.0)}
        self.step_size = tk.DoubleVar(value=1.0)
        self.selected_file = tk.StringVar(value="No File Selected")
        self.current_page_name = "Home"
        
        # 3. Frame Stack
        container = tk.Frame(self, bg=CLR_BG)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        
        # --- FIX: Startup Flash ---
        # We create 'Home' LAST. In Tkinter's grid, the last added widget 
        # naturally sits on top until raised. This prevents other screens flashing.
        for F in (Running, ProtocolList, Calibrate, Home): 
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        # Force immediate update to lock in the view
        self.show_frame("Home")
        self.update() 
        
        self.start_ui_updater()

    def show_frame(self, page_name):
        self.current_page_name = page_name
        frame = self.frames[page_name]
        frame.tkraise()
        
        if page_name == "Calibrate": frame.on_enter()
        if page_name == "ProtocolList": frame.refresh_files(frame.current_dir)

    def start_ui_updater(self):
        state = self.backend.state
        
        # Sync Filename
        if "Running" in state["status"] or "Paused" in state["status"]:
            if self.selected_file.get() != state["filename"]:
                self.selected_file.set(state["filename"])

        # Remote Start Popup
        if state["just_started"]:
            self.show_frame("Running")
            self.update_idletasks()
            self.update()
            
            filename = state["filename"]
            source = state["started_by"]
            time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"Protocol: {filename}\nSource: {source}\nTime: {time_now}"
            
            popup = CustomPopup(self, "Started", "PROTOCOL STARTED", msg, CLR_PRIMARY, "🚀", height=290)
            self.wait_window(popup)
            self.backend.ui_ack_start()

        # Update Views
        if "Running" in state["status"] or "Paused" in state["status"] or "Done" in state["status"]:
            if self.current_page_name != "Running": 
                self.show_frame("Running")
        
        if self.current_page_name == "Running": 
            self.frames["Running"].update_view(state)
            
        # Stop Popup
        if state["stop_reason"]:
            reason = state["stop_reason"].upper()
            filename = state["filename"]
            time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"File: {filename}\nSource: {reason}\nTime: {time_now}"
            popup = CustomPopup(self, "Stopped", "PROTOCOL STOPPED", msg, CLR_WARNING, "⚠")
            self.wait_window(popup)
            self.backend.ui_ack_stop()
            self.show_frame("Home")
            
        # Error Popup
        if state["error_msg"]:
            error_text = state["error_msg"]
            time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"Time: {time_now}\nDetails: {error_text}"
            popup = CustomPopup(self, "System Error", "HARDWARE ERROR", msg, CLR_DANGER, "✖")
            self.wait_window(popup)
            self.backend.ui_ack_error()
            self.show_frame("Home")
            
        # --- FIX: SUCCESS POPUP LOGIC ---
        if state["completed"]:
            # 1. Force the Running Screen to update to 100% FIRST
            self.frames["Running"].update_view(state)
            self.update_idletasks()
            self.update() # Forces the paint to happen immediately
            
            # 2. Prepare Popup
            filename = state["filename"]
            time_now = datetime.now().strftime("%H:%M:%S")
            msg = f"File: {filename}\nFinished At: {time_now}"
            
            # 3. Show Popup
            if self.current_page_name == "Running":
                popup = CustomPopup(self, "Done", "COMPLETED", msg, CLR_SUCCESS, "✔")
                self.wait_window(popup)
                self.backend.ui_ack_stop()
                self.show_frame("Home")
            else: 
                self.backend.state["completed"] = False
                self.backend.ui_ack_stop()
                
        self.after(200, self.start_ui_updater)
        
# --- HOME SCREEN ---
class Home(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        card = ShadowCard(self, bg=CLR_CARD)
        card.place(relx=0.5, rely=0.5, anchor="center", width=500, height=350)
        tk.Label(card.inner, text="Liquid Handler v1.1", font=("Arial", 22, "bold"), bg=CLR_CARD).pack(pady=(30, 40))
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
                lbl.config(text=f"{prefix}{current:.1f}", fg=CLR_SUCCESS) 
                self.after(15, lambda: update_step(i+1))
            else:
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
            self.update() 
            self.c.backend.ui_send_gcode("OK_C")
            popup = CustomPopup(self.c, "Saved", "SAVED", "Offsets updated successfully.", CLR_SUCCESS, "💾", height=300, icon_size=38)
            self.wait_window(popup)
            self.c.show_frame("Home")

# --- UPDATED SCROLLABLE FRAME (Hidden Scrollbar + Touch Drag) ---
class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        self.canvas = tk.Canvas(self, bg=kwargs.get("bg", "white"), highlightthickness=0)
        self.scrollable_frame = tk.Frame(self.canvas, bg=kwargs.get("bg", "white"))

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Variables for custom scrolling
        self.last_y = 0

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    # --- CUSTOM SCROLL LOGIC (CLAMPED) ---
    def _start_scroll(self, event):
        self.last_y = event.y

    def _do_scroll(self, event):
        # 1. Calculate how far mouse moved
        dy = event.y - self.last_y
        self.last_y = event.y
        
        # 2. Get Canvas Dimensions
        # bbox returns (x1, y1, x2, y2) -> y2 is the total height of content
        bbox = self.canvas.bbox("all")
        if not bbox: return
        content_height = bbox[3]
        view_height = self.canvas.winfo_height()
        
        # If content fits in view, no scrolling needed
        if content_height <= view_height: return

        # 3. Calculate Scroll Fraction
        # dy is pixels. We need to convert pixels to a 0.0-1.0 fraction relative to content height
        # We multiply by roughly 1.5 to make the scroll feel responsive (sensitivity)
        fraction = -dy / float(content_height) 
        
        # 4. Apply Scroll with Clamping
        current_top, _ = self.canvas.yview()
        new_top = current_top + fraction
        
        # CLAMP: Prevent going below 0 (Top) or above Max (Bottom)
        if new_top < 0: 
            new_top = 0
        
        # Max scroll is 1.0 minus the visible proportion
        max_scroll = 1.0 - (view_height / content_height)
        if new_top > max_scroll: 
            new_top = max_scroll
            
        self.canvas.yview_moveto(new_top)

    def _on_mousewheel(self, event):
        # Keep mousewheel for testing
        if event.num == 4: self.canvas.yview_scroll(-1, "units")
        elif event.num == 5: self.canvas.yview_scroll(1, "units")
# --- UPDATED PROTOCOL LIST ---
class ProtocolList(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        self.current_dir = DIR_TEST
        
        # --- LOAD ICONS ---
        self.del_icon_img = None
        if HAS_PIL:
            try:
                icon_path = os.path.join(BASE_DIR, "icons", "delete.png")
                pil_img = Image.open(icon_path)
                pil_img = pil_img.resize((24, 24), Image.Resampling.LANCZOS)
                self.del_icon_img = ImageTk.PhotoImage(pil_img)
            except Exception as e:
                print(f"⚠️ Could not load delete.png: {e}")

        # --- 1. HEADER ---
        header = tk.Frame(self, bg=CLR_BG, pady=5)
        header.pack(side="top", fill="x", pady=(20, 5)) 
        tk.Label(header, text="SYSTEM PROTOCOLS", font=("Arial", 16, "bold"), bg=CLR_BG, fg=CLR_PRIMARY).pack(side="left", padx=30)

        # --- 2. TABS ROW ---
        tabs_container = tk.Frame(self, bg=CLR_BG)
        tabs_container.pack(side="top", fill="x", pady=(10, 10), padx=30)
        
        # Helper to create tab
        def create_tab(parent, icon, text, tab_type, default_bg, default_fg):
            f = tk.Frame(parent, bg=default_bg, pady=8, cursor="none")
            c = tk.Frame(f, bg=default_bg, cursor="none")
            c.pack(anchor="center")
            
            lbl_icon = tk.Label(c, text=icon, font=("Arial", 26), bg=default_bg, fg=default_fg, cursor="none")
            lbl_icon.pack(side="left", padx=(0, 8))
            
            lbl_text = tk.Label(c, text=text, font=("Arial", 14, "bold"), bg=default_bg, fg=default_fg, cursor="none")
            lbl_text.pack(side="left")
            
            for w in [f, c, lbl_icon, lbl_text]:
                w.bind("<Button-1>", lambda e: self.switch_tab(tab_type))
            return f, lbl_icon, lbl_text

        self.tab_test_frame, self.tab_test_icon, self.tab_test_text = create_tab(
            tabs_container, "🔬", "TEST PROTOCOLS", "TEST", CLR_PRIMARY, "white"
        )
        self.tab_test_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.tab_recent_frame, self.tab_recent_icon, self.tab_recent_text = create_tab(
            tabs_container, "🕒", "RECENT FILES", "RECENT", CLR_INACTIVE, "#555"
        )
        self.tab_recent_frame.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # --- 3. FOOTER (With State-Controlled Start Button) ---
        footer = tk.Frame(self, bg=CLR_BG, height=80)
        footer.pack(side="bottom", fill="x", pady=(10, 25), padx=30)
        
        # BACK Button (No Arrows)
        RoundedButton(footer, text="BACK", command=lambda: controller.show_frame("Home"), width=120, height=50, bg_color="#90A4AE", hover_color="#78909C", fg_color="white").pack(side="left")
        
        # START Button (No Arrows, kept as class variable to modify state)
        self.btn_start = RoundedButton(footer, text="START", command=self.load_and_run, width=120, height=50, bg_color=CLR_SUCCESS, hover_color=CLR_SUCCESS_HOVER)
        self.btn_start.pack(side="right")

        # --- 4. LIST CONTAINER ---
        list_outer = ShadowCard(self, bg="white")
        list_outer.pack(side="top", fill="both", expand=True, padx=30, pady=(0, 10))
        
        self.scroll_frame_widget = ScrollableFrame(list_outer.inner, bg="white")
        self.scroll_frame_widget.pack(fill="both", expand=True)
        
        self.selected_card = None
        self.switch_tab("TEST") # This will also disable the start button initially

    def toggle_start_button(self, enable):
        """Disables or Enables the Start Button visually and functionally"""
        if enable:
            self.btn_start.set_color(CLR_SUCCESS, CLR_SUCCESS_HOVER)
            self.btn_start.command = self.load_and_run
        else:
            self.btn_start.set_color(CLR_INACTIVE, CLR_INACTIVE) # Gray, no hover
            self.btn_start.command = None # Remove command

    def switch_tab(self, tab_name):
        self.current_dir = DIR_TEST if tab_name == "TEST" else DIR_RECENT
        
        if tab_name == "TEST":
            self.set_tab_style(self.tab_test_frame, self.tab_test_icon, self.tab_test_text, True)
            self.set_tab_style(self.tab_recent_frame, self.tab_recent_icon, self.tab_recent_text, False)
        else:
            self.set_tab_style(self.tab_test_frame, self.tab_test_icon, self.tab_test_text, False)
            self.set_tab_style(self.tab_recent_frame, self.tab_recent_icon, self.tab_recent_text, True)
            
        self.refresh_files(self.current_dir)

    def set_tab_style(self, frame, icon, text, active):
        bg = CLR_PRIMARY if active else CLR_INACTIVE
        fg = "white" if active else "#555"
        
        frame.config(bg=bg)
        frame.winfo_children()[0].config(bg=bg) 
        icon.config(bg=bg, fg=fg)
        text.config(bg=bg, fg=fg)

    def refresh_files(self, folder_path):
        # Reset scroll
        self.scroll_frame_widget.canvas.yview_moveto(0)
        self.scroll_frame_widget.last_y = 0 
        
        # Reset Selection and Disable Start Button
        self.selected_card = None
        self.toggle_start_button(False)

        target_frame = self.scroll_frame_widget.scrollable_frame
        
        for widget in target_frame.winfo_children():
            widget.destroy()
        
        self.scroll_frame_widget.update_idletasks()
        
        try:
            files = sorted([f for f in os.listdir(folder_path) if f.endswith(('.g', '.nc', '.gc', '.gcode', '.txt'))])
            if not files:
                tk.Label(target_frame, text="No protocols found.", font=("Arial", 14), bg="white", fg="gray").pack(pady=40)
                return

            for f in files:
                self.create_file_card(f, target_frame)
        except Exception as e:
            print(f"Error refreshing files: {e}")

    def create_file_card(self, filename, parent_frame):
        card = tk.Frame(parent_frame, bg="white", bd=1, relief="solid")
        card.pack(fill="x", padx=10, pady=6)
        
        inner = tk.Frame(card, bg="white", padx=15, pady=15)
        inner.pack(fill="both", expand=True)
        
        # 1. Delete Button
        del_btn = None
        if self.current_dir == DIR_RECENT:
            if self.del_icon_img:
                del_btn = tk.Label(inner, image=self.del_icon_img, bg="white", cursor="none")
                del_btn.image = self.del_icon_img
            else:
                del_btn = tk.Label(inner, text="X", font=("Arial", 18, "bold"), bg="white", fg=CLR_DANGER)
            
            del_btn.pack(side="right", padx=10)
            del_btn.bind("<Button-1>", lambda e: self.delete_file(filename))

        # 2. Selection Indicator
        sel_lbl = tk.Label(inner, text="✔", font=("Arial", 18, "bold"), bg="white", fg=CLR_PRIMARY)
        
        # 3. File Icon
        icon_lbl = tk.Label(inner, text="📄", font=("Arial", 22), bg="white", fg="#78909C", width=3)
        icon_lbl.pack(side="left")
        
        # 4. Filename
        name_lbl = tk.Label(inner, text=filename, font=("Helvetica", 14, "bold"), bg="white", fg="#263238", anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True, padx=5)

        # 5. Logic
        def on_click(e):
            self.select_file(filename, card, inner, icon_lbl, name_lbl, sel_lbl, del_btn)

        # 6. Bind Drag to ALL elements
        for w in [card, inner, icon_lbl, name_lbl]:
            w.bind("<ButtonPress-1>", self.scroll_frame_widget._start_scroll)
            w.bind("<B1-Motion>", self.scroll_frame_widget._do_scroll)
            w.bind("<ButtonRelease-1>", on_click)

    def delete_file(self, filename):
        c = CustomConfirmPopup(self.c, "Delete?", "DELETE FILE", f"Permanently delete\n{filename}?", width=480, height=280)
        if c.result:
            try:
                os.remove(os.path.join(self.current_dir, filename))
                self.refresh_files(self.current_dir)
            except Exception as e:
                print(f"Error deleting file: {e}")

    def select_file(self, filename, card_frame, inner_frame, icon, name, sel_indicator, del_btn=None):
        # Restore previous
        if self.selected_card:
            prev_card, prev_inner, prev_icon, prev_name, prev_sel, prev_del = self.selected_card
            prev_card.config(bg="white")
            prev_inner.config(bg="white")
            prev_icon.config(bg="white", fg="#78909C") 
            prev_name.config(bg="white")
            prev_sel.pack_forget() 
            if prev_del: 
                prev_del.pack(side="right", padx=10)
                prev_del.config(bg="white")

        # Highlight New
        card_frame.config(bg=CLR_LIGHT_BLUE)
        inner_frame.config(bg=CLR_LIGHT_BLUE)
        icon.config(bg=CLR_LIGHT_BLUE, fg=CLR_PRIMARY)
        name.config(bg=CLR_LIGHT_BLUE)
        
        if del_btn: del_btn.pack_forget()

        sel_indicator.config(bg=CLR_LIGHT_BLUE)
        sel_indicator.pack(side="right", padx=10)
        
        self.c.selected_file.set(filename)
        self.selected_card = (card_frame, inner_frame, icon, name, sel_indicator, del_btn)
        
        # ENABLE START BUTTON
        self.toggle_start_button(True)

    def load_and_run(self):
        if not self.selected_card: return
        fname = self.c.selected_file.get()
        self.c.backend.ui_load_and_run(fname)
        self.c.show_frame("Running")  

# --- MODERN RUNNING SCREEN (Refined Layout) ---
class Running(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        
        # --- 1. HEADER (Filename + Source) ---
        header = tk.Frame(self, bg=CLR_BG)
        header.pack(side="top", fill="x", pady=(20, 5), padx=50)
        
        # Filename (Hero Title)
        self.lbl_filename = tk.Label(header, textvariable=controller.selected_file, font=("Arial", 20, "bold"), fg=CLR_PRIMARY, bg=CLR_BG, anchor="w")
        self.lbl_filename.pack(fill="x")
        
        # Source (Directly Below Filename)
        self.source_lbl = tk.Label(header, text="Source: --", font=("Arial", 11, "bold"), fg="#90A4AE", bg=CLR_BG, anchor="w")
        self.source_lbl.pack(fill="x", pady=(2, 0))

        # --- 2. MAIN CARD ---
        card_outer = ShadowCard(self, bg="white")
        card_outer.pack(fill="both", expand=True, padx=50, pady=(15, 10))
        
        main_inner = tk.Frame(card_outer.inner, bg="white", padx=30, pady=20)
        main_inner.pack(fill="both", expand=True)

        # --- A. INFO ROW (Percent Left, Time Right) ---
        top_row = tk.Frame(main_inner, bg="white")
        top_row.pack(fill="x", pady=(0, 10)) # Reduced bottom padding slightly
        
        # Big Percentage
        self.percent_lbl = tk.Label(top_row, text="0%", font=("Arial", 48, "bold"), fg=CLR_PRIMARY, bg="white")
        self.percent_lbl.pack(side="left")
        
        # Right Side Info
        info_col = tk.Frame(top_row, bg="white")
        info_col.pack(side="right", anchor="e")
        
        # 1. Status Badge
        self.status_badge = tk.Label(info_col, text="● STARTING", font=("Arial", 11, "bold"), fg="#555", bg="#F5F5F5", padx=10, pady=5)
        self.status_badge.pack(anchor="e", pady=(0, 2))
        
        # 2. Time & Hourglass Container
        # ADDED TOP PADDING HERE (pady=(5, 0))
        time_box = tk.Frame(info_col, bg="white")
        time_box.pack(anchor="e", pady=(10, 0)) 
        
        # Hourglass Animation
        self.spinner = HourglassSpinner(time_box, size=24, bg="white")
        self.spinner.pack(side="left", padx=(0, 8))
        
        # Time Text
        self.time_lbl = tk.Label(time_box, text="Est: --:--:--:--", font=("Arial", 14, "bold"), fg="#555", bg="white")
        self.time_lbl.pack(side="left")

        # Progress Bar
        # DECREASED TOP PADDING HERE (pady=(2, 20))
        self.prog = ModernProgressBar(main_inner, width=640, height=20, fill_color=CLR_PRIMARY)
        self.prog.pack(pady=(2, 20))

        # --- B. CONSOLE (Light Theme) ---
        console_frame = tk.Frame(main_inner, bg="#F7F9FA", bd=1, relief="solid", highlightbackground="#ECEFF1", highlightthickness=1)
        console_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        c_inner = tk.Frame(console_frame, bg="#F7F9FA", padx=15, pady=10)
        c_inner.pack(fill="both", expand=True)
        
        tk.Label(c_inner, text="CURRENT OPERATION:", font=("Arial", 9, "bold"), fg="#90A4AE", bg="#F7F9FA").pack(anchor="w")
        
        # Command Text
        self.cmd_lbl = tk.Label(c_inner, text="Waiting...", font=("Courier New", 16, "bold"), fg="#263238", bg="#F7F9FA", anchor="w", wraplength=600, justify="left")
        self.cmd_lbl.pack(fill="x", pady=(2, 0))
        
        # Description Text
        self.desc_lbl = tk.Label(c_inner, text="--", font=("Arial", 12, "italic"), fg="#546E7A", bg="#F7F9FA", anchor="w", wraplength=600, justify="left")
        self.desc_lbl.pack(fill="x", pady=(4, 0))

        # --- 3. FOOTER ACTIONS ---
        footer = tk.Frame(self, bg=CLR_BG, height=80)
        footer.pack(side="bottom", fill="x", pady=(5, 20), padx=50)
        
        self.btn_pause = RoundedButton(footer, text="PAUSE", command=lambda: self.c.backend.ui_pause_resume(), width=150, height=55, bg_color=CLR_WARNING, hover_color=CLR_WARNING_HOVER)
        self.btn_pause.pack(side="left")
        
        RoundedButton(footer, text="STOP", command=self.cancel_run, width=150, height=55, bg_color=CLR_DANGER, hover_color=CLR_DANGER_HOVER).pack(side="right")

    def cancel_run(self):
        confirm = CustomConfirmPopup(self.c, "Stop Confirmation", "STOP PROTOCOL", "Are you sure you want to abort?")
        if confirm.result: self.c.backend.ui_stop()

    def update_view(self, state):
        progress = state["progress"]
        status = state["status"]
        cmd_text = state["current_line"]
        desc_text = state.get("current_desc", "")
        est_time = state.get("est", "--:--:--:--")
        source = state.get("started_by", "Unknown")
        
        self.source_lbl.config(text=f"Source: {source}")
        self.percent_lbl.config(text=f"{int(progress)}%")
        self.prog.set_progress(progress)
        self.time_lbl.config(text=f"Est: {est_time}")
        
        is_paused = "Paused" in status
        self.spinner.set_paused(is_paused)

        if is_paused:
            reason = state.get('pause_reason', 'UNKNOWN').upper()
            self.status_badge.config(text=f"● PAUSED ({reason})", fg="#E65100", bg="#FFF3E0")
            
            self.cmd_lbl.config(text=f"PAUSED ({reason})", fg="#E65100")
            self.desc_lbl.config(text="System waiting for resume...", fg="#BF360C")
            
            self.btn_pause.itemconfig(self.btn_pause.text_id, text="RESUME")
            self.btn_pause.set_color(CLR_SUCCESS, CLR_SUCCESS_HOVER)
        else:
            self.status_badge.config(text="● RUNNING", fg=CLR_SUCCESS, bg="#E8F5E9")
            
            self.cmd_lbl.config(text=cmd_text, fg="#263238")
            self.desc_lbl.config(text=desc_text if desc_text else "Processing...", fg="#546E7A")
            
            self.btn_pause.itemconfig(self.btn_pause.text_id, text="PAUSE")
            self.btn_pause.set_color(CLR_WARNING, CLR_WARNING_HOVER)
            
if __name__ == "__main__":
    app = KioskApp()
    app.mainloop()