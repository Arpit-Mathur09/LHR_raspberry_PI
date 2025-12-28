#v1.2 added Calibration Locking Logic and Status Popup Updates 
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
CLR_SUCCESS_DARK = "#388E3C"   # <--- FIXED: Added back
CLR_DANGER = "#D32F2F"   
CLR_DANGER_HOVER = "#B71C1C"
CLR_WARNING = "#FBC02D" 
CLR_WARNING_HOVER = "#F57F17" 
CLR_WARNING_DARK = "#F57F17"   # <--- FIXED: Added back
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
    def __init__(self, parent, size=30, bg="white", color=CLR_SAND):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0)
        self.size = size; self.cx = size / 2; self.cy = size / 2; self.padding = 5
        self.angle = 0; self.sand_pct = 0; self.state = "draining" 
        self.color = color
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
            self.create_polygon(rot_pts[2], rot_pts[3], rot_pts[4], fill=self.color, outline="")
        else:
            pct_rem = (100 - sand_level) / 100.0; t_h, t_w = r * pct_rem, w * pct_rem
            t_pts = [(-t_w, -t_h), (t_w, -t_h), (0, 0)]; self._draw_rot_poly(t_pts, cos_a, sin_a, self.color)
            pct_fill = sand_level / 100.0; s_w = w * (1.0 - pct_fill); s_h = r * (1.0 - pct_fill)
            b_pts = [(-w, r), (w, r), (s_w, s_h), (-s_w, s_h)]; self._draw_rot_poly(b_pts, cos_a, sin_a, self.color)
            if sand_level < 95: self.create_line(self.cx, self.cy, self.cx, self.cy + (r*0.8), fill=self.color, width=1)

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
        self.w = width; self.h = height; self.fill_color = fill_color; self.bg_color = bg_color
        self.current_pct = 0.0; self.target_pct = 0.0
        self.create_rounded_rect(0, 0, width, height, radius=height, fill=bg_color, tags="bg")
        self.fill_id = self.create_rounded_rect(0, 0, 0, height, radius=height, fill=fill_color, tags="fill")

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def set_progress(self, pct):
        self.target_pct = max(0, min(100, pct)); self.animate()

    def animate(self):
        diff = self.target_pct - self.current_pct
        if abs(diff) < 0.5: self.current_pct = self.target_pct
        else: self.current_pct += diff * 0.1 
        raw_width = (self.current_pct / 100) * self.w
        new_width = max(self.h, raw_width) if self.current_pct > 0.5 else 0
        self.delete("fill")
        if new_width > 0: self.create_rounded_rect(0, 0, new_width, self.h, radius=self.h, fill=self.fill_color, tags="fill")
        if self.current_pct != self.target_pct: self.after(20, self.animate)
            
# --- SCROLLABLE FRAME ---
class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=kwargs.get("bg", "white"), highlightthickness=0)
        self.scrollable_frame = tk.Frame(self.canvas, bg=kwargs.get("bg", "white"))
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.last_y = 0

    def _on_canvas_configure(self, event): self.canvas.itemconfig(self.window_id, width=event.width)
    def _start_scroll(self, event): self.last_y = event.y
    def _do_scroll(self, event):
        dy = event.y - self.last_y; self.last_y = event.y
        bbox = self.canvas.bbox("all")
        if not bbox: return
        content_height = bbox[3]; view_height = self.canvas.winfo_height()
        if content_height <= view_height: return
        fraction = -dy / float(content_height) 
        current_top, _ = self.canvas.yview(); new_top = current_top + fraction
        if new_top < 0: new_top = 0
        max_scroll = 1.0 - (view_height / content_height)
        if new_top > max_scroll: new_top = max_scroll
        self.canvas.yview_moveto(new_top)

 # --- BACKGROUND GENERATOR (FIXED) ---
# --- FIND THIS FUNCTION AND UPDATE IT ---
def get_blur_bg(root_window):
    if not HAS_PIL: return None
    try:
        # CRITICAL FIX: Use update() instead of update_idletasks()
        # This forces the GPU to finish painting the new screen before we grab it.
        root_window.update() 
        
        x = root_window.winfo_rootx()
        y = root_window.winfo_rooty()
        w = root_window.winfo_width()
        h = root_window.winfo_height()
        
        if w <= 1 or h <= 1: return None
        
        img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
        white_layer = Image.new("RGB", img.size, (255, 255, 255))
        blended = Image.blend(img, white_layer, 0.85)
        return ImageTk.PhotoImage(blended)
    except Exception as e:
        print(f"BG Blur Error: {e}")
        return None
    
    
# --- BASE MODAL ---
class ModalOverlay(tk.Toplevel):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.withdraw()
        
        root = parent.winfo_toplevel()
        # Force update before measuring
        root.update_idletasks()
        
        x = root.winfo_rootx(); y = root.winfo_rooty()
        w = root.winfo_width(); h = root.winfo_height()
        
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.overrideredirect(True)
        self.config(cursor="none")
        
        self.bg_img = get_blur_bg(root)
        
        self.cv = tk.Canvas(self, width=w, height=h, highlightthickness=0, bg="white")
        self.cv.pack(fill="both", expand=True)
        
        if self.bg_img: 
            self.cv.create_image(0, 0, image=self.bg_img, anchor="nw")
        else: 
            # Fallback color if capture fails
            self.cv.configure(bg="#FAFAFA")
            
        self.bind("<Button-1>", lambda e: self.config(cursor="none"))

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
        tk.Frame(self.f, height=3, bg=color, width=300).pack(pady=8)
        msg_frame = tk.Frame(self.f, bg="white"); msg_frame.pack(pady=2, padx=15)
        tk.Label(msg_frame, text=message, font=("Arial", 12), bg="white", fg="#444", wraplength=340).pack(anchor="n")
        btn_f = tk.Frame(self.f, bg="white"); btn_f.pack(side="bottom", pady=20)
        RoundedButton(btn_f, text="OK", command=self.destroy, width=130, height=45, bg_color=color, hover_color=color).pack()
        self.deiconify(); self.update_idletasks(); self.lift(); self.grab_set()

class CustomConfirmPopup(ModalOverlay):
    def __init__(self, parent, title, header, message, width=420, height=240):
        super().__init__(parent); self.result = False
        cw, ch = width, height; cx = parent.winfo_width() / 2; cy = parent.winfo_height() / 2
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=CLR_DANGER, width=2)
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4); self.f.pack_propagate(False); self.cv.create_window(cx, cy, window=self.f)
        head_box = tk.Frame(self.f, bg="white"); head_box.pack(pady=(15, 5))
        tk.Label(head_box, text="?", font=("Arial", 40), fg=CLR_DANGER, bg="white").pack(side="top")
        tk.Label(head_box, text=header, font=("Arial", 18, "bold"), fg=CLR_DANGER, bg="white").pack(side="top")
        tk.Frame(self.f, height=2, bg=CLR_DANGER, width=300).pack(pady=5)
        tk.Label(self.f, text=message, font=("Arial", 12), bg="white", fg="#444", wraplength=cw-40).pack(pady=5)
        btn_f = tk.Frame(self.f, bg="white"); btn_f.pack(side="bottom", pady=20)
        RoundedButton(btn_f, text="CANCEL", command=self.on_cancel, width=120, height=50, bg_color="#9E9E9E", hover_color="#757575").pack(side="left", padx=15)
        RoundedButton(btn_f, text="CONFIRM", command=self.on_confirm, width=120, height=50, bg_color=CLR_DANGER, hover_color=CLR_DANGER_HOVER).pack(side="left", padx=15)
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
        
        # Match CustomConfirmPopup size
        cw, ch = 420, 240 
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
        self.lbl_desc.pack(pady=(15, 15))
        
        # Spinner
        anim = tk.Frame(self.f, bg="white")
        anim.pack(pady=0)
        self.spinner = HourglassSpinner(anim, size=32, bg="white", color=CLR_PRIMARY)
        self.spinner.pack()
        
        self.deiconify()
        self.update_idletasks()
        self.lift()

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

# --- MAIN APP ---
class KioskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
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
        # Ensure we are on Calibrate screen BEFORE showing any popups
        if is_calib_active and self.current_page_name != "Calibrate":
            self.show_frame("Calibrate")
            self.update_idletasks()
            self.update() # Force paint
            
            # FIX 1: Reduced delay to 50ms (was 200ms) to minimize "Flash"
            # but keep it non-zero to ensure the OS paints the background for the blur.
            self.after(50, self.start_ui_updater)
            return 

        # 1. Blocker (Only if Remote is doing it)
        is_locked = is_calib_active and calib_source == "Remote"
        
        if is_locked:
            if not self.calib_blocker: self.calib_blocker = CalibrationBlockerPopup(self)
            
            # Ensure Status Popup is GONE if locked (Blocker takes precedence)
            if self.calib_status_popup:
                self.calib_status_popup.destroy()
                self.calib_status_popup = None
        else:
            if self.calib_blocker: self.calib_blocker.destroy(); self.calib_blocker = None

        # 2. CALIBRATION STATUS POPUP (Show only if NOT locked by remote blocker)
        # We only show specific Homing/Moving popups if the User is doing it locally.
        # If Remote is doing it, the Blocker covers everything anyway.
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
                # Check if strictly Calibrated (saved)
                if state.get("is_calibrated", False) == True:
                    time_now = datetime.now().strftime("%H:%M:%S")
                    msg = f"Calibration finished by Remote Client.\nTime: {time_now}"
                    popup = CustomPopup(self, "Notification", "CALIBRATION DONE", msg, CLR_SUCCESS, "🔔", height=290)
                    self.wait_window(popup)
                
                # FIX 2: FORCE RETURN TO HOME
                # After remote finishes (saved or not), go back to Home.
                self.show_frame("Home")

        self.last_calib_active = is_calib_active
        self.last_calib_source = calib_source

        # ... (Rest of updater logic remains the same) ...
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
        
        if self.current_page_name == "Running": self.frames["Running"].update_view(state)
            
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
class Home(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        
        # Reduced card height (350 -> 300) for less empty space
        card = ShadowCard(self, bg=CLR_CARD)
        card.place(relx=0.5, rely=0.5, anchor="center", width=500, height=300)
        
        # Updated Version Label & Reduced Padding
        tk.Label(card.inner, text="Liquid Handler v1.2", font=("Arial", 22, "bold"), bg=CLR_CARD).pack(pady=(20, 25))
        
        # Reduced button height & padding for tighter layout
        RoundedButton(card.inner, text="CALIBRATION", width=250, height=55, bg_color="#FF9800", hover_color=CLR_WARNING_HOVER, command=lambda: controller.show_frame("Calibrate")).pack(pady=10)
        
        # Changed text "RUN PROTOCOL" -> "PROTOCOLS"
        RoundedButton(card.inner, text="PROTOCOLS", width=250, height=55, bg_color=CLR_PRIMARY, hover_color=CLR_PRIMARY_HOVER, command=lambda: controller.show_frame("ProtocolList")).pack(pady=10)
class Calibrate(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        
        # --- HEADER ---
        header = tk.Frame(self, bg=CLR_BG, pady=5)
        header.pack(fill="x", pady=(20, 5)) 
        tk.Label(header, text="SYSTEM CALIBRATION", font=("Arial", 16, "bold"), bg=CLR_BG, fg=CLR_PRIMARY).pack(side="left", padx=20)
        
        main = tk.Frame(self, bg=CLR_BG)
        main.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Adjusted Columns: XY(3), Z(2), Live(1)
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)
        main.grid_columnconfigure(2, weight=1) 

        # 1. XY CARD
        xy_outer = tk.Frame(main, bg=CLR_BG); xy_outer.grid(row=0, column=0, sticky="nsew", padx=5)
        self.xy_card = ShadowCard(xy_outer, bg=CLR_CARD, border_color=CLR_PRIMARY); self.xy_card.pack(fill="both", expand=True)
        tk.Label(self.xy_card.inner, text="XY AXIS", font=("Arial", 14, "bold"), bg=CLR_CARD, fg=CLR_PRIMARY).pack(pady=10)
        dpad = tk.Frame(self.xy_card.inner, bg=CLR_CARD); dpad.pack()
        
        def mk_btn(parent, txt, axis, d): 
            b = RoundedButton(parent, text=txt, command=None, width=78, height=65, bg_color=CLR_INACTIVE, hover_color="#B0BEC5", fg_color="black")
            b.command = lambda: self.move(axis, d, b); return b
        
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
            # Larger Z buttons
            b = RoundedButton(parent, text=txt, command=None, width=90, height=75, bg_color=CLR_INACTIVE, hover_color="#B0BEC5", fg_color="black")
            b.command = lambda: self.move(axis, d, b); return b

        tk.Label(z_grid, text="Z1", font=("Arial", 12, "bold"), bg=CLR_CARD).grid(row=0, column=0, pady=(0, 15), sticky="s")
        mk_z_btn(z_grid, "▲", "Z1", 1).grid(row=1, column=0, pady=(0, 10), padx=15)
        mk_z_btn(z_grid, "▼", "Z1", -1).grid(row=2, column=0, pady=10, padx=15)
        
        tk.Label(z_grid, text="Z2", font=("Arial", 12, "bold"), bg=CLR_CARD).grid(row=0, column=1, pady=(0, 15), sticky="s")
        mk_z_btn(z_grid, "▲", "Z2", 1).grid(row=1, column=1, pady=(0, 10), padx=15)
        mk_z_btn(z_grid, "▼", "Z2", -1).grid(row=2, column=1, pady=10, padx=15)

        # 3. LIVE CHANGES
        data_outer = tk.Frame(main, bg=CLR_BG); data_outer.grid(row=0, column=2, sticky="nsew", padx=5)
        self.data_card = ShadowCard(data_outer, bg=CLR_CARD, border_color=CLR_SUCCESS); self.data_card.pack(fill="both", expand=True)
        tk.Label(self.data_card.inner, text="LIVE CHANGES", font=("Arial", 14, "bold"), bg=CLR_CARD, fg=CLR_SUCCESS_DARK).pack(pady=10)
        
        self.info_box = tk.Frame(self.data_card.inner, bg=CLR_INFO_BOX, padx=10, pady=10)
        self.info_box.pack(fill="x", pady=5)
        
        lbl_style = {"font": ("Courier", 14, "bold"), "bg": CLR_INFO_BOX, "fg": "#333"}
        self.lbl_x = tk.Label(self.info_box, text="X : 0.0", **lbl_style); self.lbl_x.pack(anchor="w")
        self.lbl_y = tk.Label(self.info_box, text="Y : 0.0", **lbl_style); self.lbl_y.pack(anchor="w")
        self.lbl_z1 = tk.Label(self.info_box, text="Z1: 0.0", **lbl_style); self.lbl_z1.pack(anchor="w")
        self.lbl_z2 = tk.Label(self.info_box, text="Z2: 0.0", **lbl_style); self.lbl_z2.pack(anchor="w")
        
        tk.Label(self.data_card.inner, text="STEP SIZE (mm)", font=("Arial", 12, "bold"), bg=CLR_CARD, fg="#555").pack(pady=(15, 5))
        step_f = tk.Frame(self.data_card.inner, bg=CLR_CARD); step_f.pack()
        self.step_btns = {}
        for val in [0.1, 1.0, 10.0]:
            b = RoundedButton(step_f, text=str(val), command=lambda v=val: self.set_step(v), width=50, height=50, bg_color=CLR_INACTIVE, hover_color="#B0BEC5", fg_color="black")
            b.pack(side="left", padx=3)
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
        # --- FIX: Prevent overriding Remote session ---
        # If calibration is already active (started by Remote), do NOT override source to "User".
        # We just update the visual labels and return.
        if self.c.backend.state["calibration_active"]:
            self.lbl_x.config(text="X : 0.0")
            self.lbl_y.config(text="Y : 0.0")
            self.lbl_z1.config(text="Z1: 0.0")
            self.lbl_z2.config(text="Z2: 0.0")
            for k in self.c.offsets: self.c.offsets[k].set(0.0)
            return

        # --- Normal User Start (Only if Idle) ---
        self.c.backend.set_calibration_mode(True, "User")
        self.c.backend.sync_with_server() 
        self.c.backend.ui_send_gcode("T00")
        self.c.update() 
        
        self.lbl_x.config(text="X : 0.0")
        self.lbl_y.config(text="Y : 0.0")
        self.lbl_z1.config(text="Z1: 0.0")
        self.lbl_z2.config(text="Z2: 0.0")
        for k in self.c.offsets: self.c.offsets[k].set(0.0)

    # --- RESTORED ANIMATION LOGIC ---
    def move(self, axis, direction, btn_instance):
        btn_instance.flash(CLR_PRIMARY)
        step = self.c.step_size.get() * direction
        dx, dy, dz1, dz2 = 0, 0, 0, 0
        current = self.c.offsets[axis].get(); new_val = round(current + step, 2); self.c.offsets[axis].set(new_val)
        
        target_lbl, axis_prefix = None, ""
        if axis == "X": axis_prefix = "X : "; target_lbl = self.lbl_x; dx = step
        elif axis == "Y": axis_prefix = "Y : "; target_lbl = self.lbl_y; dy = step
        elif axis == "Z1": axis_prefix = "Z1: "; target_lbl = self.lbl_z1; dz1 = step
        elif axis == "Z2": axis_prefix = "Z2: "; target_lbl = self.lbl_z2; dz2 = step
        
        txt_sign = f"+{step}" if step > 0 else f"{step}"
        
        # Trigger Animations
        self.float_animation(target_lbl, txt_sign)
        self.animate_counter(target_lbl, axis_prefix, current, new_val)
        
        self.c.backend.ui_send_gcode(f"C dx={dx}, dy={dy}, dz1={dz1}, dz2={dz2}")

    def float_animation(self, target_widget, text):
        lbl = tk.Label(self.info_box, text=text, fg=CLR_SUCCESS, bg=CLR_INFO_BOX, font=("Arial", 14, "bold"))
        # FIX: Decreased offset to 110 (was 150) to ensure visibility in narrower column
        x = target_widget.winfo_x() + 110 
        y = target_widget.winfo_y()
        lbl.place(x=x, y=y)
        
        def anim_loop(step=0):
            if step < 10:
                lbl.place(y=y - step*2) 
                self.after(30, lambda: anim_loop(step+1))
            else:
                lbl.destroy() 
        anim_loop()

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

    def confirm_exit(self):
        c = CustomConfirmPopup(self.c, "Exit?", "EXIT CALIBRATION", "Unsaved changes will be lost.")
        if c.result:
            self.c.backend.set_calibration_mode(False, None)
            self.c.show_frame("Home")

    def confirm_save(self):
        c = CustomConfirmPopup(self.c, "Save?", "SAVE OFFSETS", "Update calibration settings?")
        if c.result:
            self.update() 
            # Send Command ONLY
            self.c.backend.ui_send_gcode("OK_C")
            
            # REMOVED: self.c.backend.set_calibration_mode(False, None)
            # We let the Backend listen for C_OK to unlock automatically.
            
            popup = CustomPopup(self.c, "Saved", "CALIBRATION SAVED", "Calibration completed.\nSystem is ready to run.", CLR_SUCCESS, "💾", height=300, icon_size=38)
            self.wait_window(popup)
            self.c.show_frame("Home")
            
class ProtocolList(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        self.current_dir = DIR_TEST
        self.del_icon_img = None
        if HAS_PIL:
            try:
                icon_path = os.path.join(BASE_DIR, "icons", "delete.png")
                pil_img = Image.open(icon_path)
                pil_img = pil_img.resize((24, 24), Image.Resampling.LANCZOS)
                self.del_icon_img = ImageTk.PhotoImage(pil_img)
            except Exception as e: print(f"⚠️ Could not load delete.png: {e}")

        header = tk.Frame(self, bg=CLR_BG, pady=5); header.pack(side="top", fill="x", pady=(20, 5)) 
        tk.Label(header, text="SYSTEM PROTOCOLS", font=("Arial", 16, "bold"), bg=CLR_BG, fg=CLR_PRIMARY).pack(side="left", padx=30)

        tabs_container = tk.Frame(self, bg=CLR_BG); tabs_container.pack(side="top", fill="x", pady=(10, 10), padx=30)
        def create_tab(parent, icon, text, tab_type, default_bg, default_fg):
            f = tk.Frame(parent, bg=default_bg, pady=8, cursor="none"); c = tk.Frame(f, bg=default_bg, cursor="none"); c.pack(anchor="center")
            lbl_icon = tk.Label(c, text=icon, font=("Arial", 26), bg=default_bg, fg=default_fg, cursor="none"); lbl_icon.pack(side="left", padx=(0, 8))
            lbl_text = tk.Label(c, text=text, font=("Arial", 14, "bold"), bg=default_bg, fg=default_fg, cursor="none"); lbl_text.pack(side="left")
            for w in [f, c, lbl_icon, lbl_text]: w.bind("<Button-1>", lambda e: self.switch_tab(tab_type))
            return f, lbl_icon, lbl_text

        self.tab_test_frame, self.tab_test_icon, self.tab_test_text = create_tab(tabs_container, "🔬", "TEST PROTOCOLS", "TEST", CLR_PRIMARY, "white")
        self.tab_test_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.tab_recent_frame, self.tab_recent_icon, self.tab_recent_text = create_tab(tabs_container, "🕒", "RECENT FILES", "RECENT", CLR_INACTIVE, "#555")
        self.tab_recent_frame.pack(side="left", fill="x", expand=True, padx=(10, 0))

        footer = tk.Frame(self, bg=CLR_BG, height=80); footer.pack(side="bottom", fill="x", pady=(10, 25), padx=30)
        RoundedButton(footer, text="BACK", command=lambda: controller.show_frame("Home"), width=120, height=50, bg_color="#90A4AE", hover_color="#78909C", fg_color="white").pack(side="left")
        self.btn_start = RoundedButton(footer, text="START", command=self.load_and_run, width=120, height=50, bg_color=CLR_SUCCESS, hover_color=CLR_SUCCESS_HOVER)
        self.btn_start.pack(side="right")

        list_outer = ShadowCard(self, bg="white"); list_outer.pack(side="top", fill="both", expand=True, padx=30, pady=(0, 10))
        self.scroll_frame_widget = ScrollableFrame(list_outer.inner, bg="white"); self.scroll_frame_widget.pack(fill="both", expand=True)
        self.selected_card = None; self.switch_tab("TEST")

    def toggle_start_button(self, enable):
        if enable: self.btn_start.set_color(CLR_SUCCESS, CLR_SUCCESS_HOVER); self.btn_start.command = self.load_and_run
        else: self.btn_start.set_color(CLR_INACTIVE, CLR_INACTIVE); self.btn_start.command = None

    def switch_tab(self, tab_name):
        self.current_dir = DIR_TEST if tab_name == "TEST" else DIR_RECENT
        if tab_name == "TEST": self.set_tab_style(self.tab_test_frame, self.tab_test_icon, self.tab_test_text, True); self.set_tab_style(self.tab_recent_frame, self.tab_recent_icon, self.tab_recent_text, False)
        else: self.set_tab_style(self.tab_test_frame, self.tab_test_icon, self.tab_test_text, False); self.set_tab_style(self.tab_recent_frame, self.tab_recent_icon, self.tab_recent_text, True)
        self.refresh_files(self.current_dir)

    def set_tab_style(self, frame, icon, text, active):
        bg = CLR_PRIMARY if active else CLR_INACTIVE; fg = "white" if active else "#555"
        frame.config(bg=bg); frame.winfo_children()[0].config(bg=bg); icon.config(bg=bg, fg=fg); text.config(bg=bg, fg=fg)

    def refresh_files(self, folder_path):
        self.scroll_frame_widget.canvas.yview_moveto(0); self.scroll_frame_widget.last_y = 0 
        self.selected_card = None; self.toggle_start_button(False)
        target_frame = self.scroll_frame_widget.scrollable_frame
        for widget in target_frame.winfo_children(): widget.destroy()
        self.scroll_frame_widget.update_idletasks()
        try:
            files = sorted([f for f in os.listdir(folder_path) if f.endswith(('.g', '.nc', '.gc', '.gcode', '.txt'))])
            if not files: tk.Label(target_frame, text="No protocols found.", font=("Arial", 14), bg="white", fg="gray").pack(pady=40); return
            for f in files: self.create_file_card(f, target_frame)
        except Exception as e: print(f"Error refreshing files: {e}")

    def create_file_card(self, filename, parent_frame):
        card = tk.Frame(parent_frame, bg="white", bd=1, relief="solid"); card.pack(fill="x", padx=10, pady=6)
        inner = tk.Frame(card, bg="white", padx=15, pady=15); inner.pack(fill="both", expand=True)
        del_btn = None
        if self.current_dir == DIR_RECENT:
            if self.del_icon_img: del_btn = tk.Label(inner, image=self.del_icon_img, bg="white", cursor="none"); del_btn.image = self.del_icon_img
            else: del_btn = tk.Label(inner, text="X", font=("Arial", 18, "bold"), bg="white", fg=CLR_DANGER)
            del_btn.pack(side="right", padx=10); del_btn.bind("<Button-1>", lambda e: self.delete_file(filename))
        sel_lbl = tk.Label(inner, text="✔", font=("Arial", 18, "bold"), bg="white", fg=CLR_PRIMARY)
        icon_lbl = tk.Label(inner, text="📄", font=("Arial", 22), bg="white", fg="#78909C", width=3); icon_lbl.pack(side="left")
        name_lbl = tk.Label(inner, text=filename, font=("Helvetica", 14, "bold"), bg="white", fg="#263238", anchor="w"); name_lbl.pack(side="left", fill="x", expand=True, padx=5)
        def on_click(e): self.select_file(filename, card, inner, icon_lbl, name_lbl, sel_lbl, del_btn)
        for w in [card, inner, icon_lbl, name_lbl]: w.bind("<ButtonPress-1>", self.scroll_frame_widget._start_scroll); w.bind("<B1-Motion>", self.scroll_frame_widget._do_scroll); w.bind("<ButtonRelease-1>", on_click)

    def delete_file(self, filename):
        c = CustomConfirmPopup(self.c, "Delete?", "DELETE FILE", f"Permanently delete\n{filename}?", width=480, height=280)
        if c.result:
            try: os.remove(os.path.join(self.current_dir, filename)); self.refresh_files(self.current_dir)
            except Exception as e: print(f"Error deleting file: {e}")

    def select_file(self, filename, card_frame, inner_frame, icon, name, sel_indicator, del_btn=None):
        if self.selected_card:
            prev_card, prev_inner, prev_icon, prev_name, prev_sel, prev_del = self.selected_card
            prev_card.config(bg="white"); prev_inner.config(bg="white"); prev_icon.config(bg="white", fg="#78909C"); prev_name.config(bg="white"); prev_sel.pack_forget() 
            if prev_del: prev_del.pack(side="right", padx=10); prev_del.config(bg="white")
        card_frame.config(bg=CLR_LIGHT_BLUE); inner_frame.config(bg=CLR_LIGHT_BLUE); icon.config(bg=CLR_LIGHT_BLUE, fg=CLR_PRIMARY); name.config(bg=CLR_LIGHT_BLUE)
        if del_btn: del_btn.pack_forget()
        sel_indicator.config(bg=CLR_LIGHT_BLUE); sel_indicator.pack(side="right", padx=10)
        self.c.selected_file.set(filename); self.selected_card = (card_frame, inner_frame, icon, name, sel_indicator, del_btn); self.toggle_start_button(True)

    def load_and_run(self):
        # 1. Block if actively calibrating
        if self.c.backend.state["calibration_active"]:
            popup = CustomPopup(self.c, "Locked", "SYSTEM BUSY", "Cannot run protocol while calibrating.", CLR_WARNING, "⚠")
            self.c.wait_window(popup)
            return

        # 2. Block if NOT calibrated (New Requirement)
        if not self.c.backend.state.get("is_calibrated", False):
            popup = CustomPopup(self.c, "Required", "CALIBRATION NEEDED", "You must calibrate the system before running a protocol.", CLR_DANGER, "🛑")
            self.c.wait_window(popup)
            # Optional: Switch to calibrate screen automatically
            self.c.show_frame("Calibrate")
            return

        if not self.selected_card: return
        fname = self.c.selected_file.get()
        self.c.backend.ui_load_and_run(fname)
        self.c.show_frame("Running")

class Running(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        header = tk.Frame(self, bg=CLR_BG); header.pack(side="top", fill="x", pady=(20, 5), padx=50)
        self.lbl_filename = tk.Label(header, textvariable=controller.selected_file, font=("Arial", 20, "bold"), fg=CLR_PRIMARY, bg=CLR_BG, anchor="w"); self.lbl_filename.pack(fill="x")
        self.source_lbl = tk.Label(header, text="Source: --", font=("Arial", 11, "bold"), fg="#90A4AE", bg=CLR_BG, anchor="w"); self.source_lbl.pack(fill="x", pady=(2, 0))
        card_outer = ShadowCard(self, bg="white"); card_outer.pack(fill="both", expand=True, padx=50, pady=(15, 10))
        main_inner = tk.Frame(card_outer.inner, bg="white", padx=30, pady=20); main_inner.pack(fill="both", expand=True)
        top_row = tk.Frame(main_inner, bg="white"); top_row.pack(fill="x", pady=(0, 10))
        self.percent_lbl = tk.Label(top_row, text="0%", font=("Arial", 48, "bold"), fg=CLR_PRIMARY, bg="white"); self.percent_lbl.pack(side="left")
        info_col = tk.Frame(top_row, bg="white"); info_col.pack(side="right", anchor="e")
        self.status_badge = tk.Label(info_col, text="● STARTING", font=("Arial", 11, "bold"), fg="#555", bg="#F5F5F5", padx=10, pady=5); self.status_badge.pack(anchor="e", pady=(0, 2))
        time_box = tk.Frame(info_col, bg="white"); time_box.pack(anchor="e", pady=(10, 0)) 
        self.spinner = HourglassSpinner(time_box, size=24, bg="white"); self.spinner.pack(side="left", padx=(0, 8))
        self.time_lbl = tk.Label(time_box, text="Est: --:--:--:--", font=("Arial", 14, "bold"), fg="#555", bg="white"); self.time_lbl.pack(side="left")
        self.prog = ModernProgressBar(main_inner, width=640, height=20, fill_color=CLR_PRIMARY); self.prog.pack(pady=(2, 20))
        console_frame = tk.Frame(main_inner, bg="#F7F9FA", bd=1, relief="solid", highlightbackground="#ECEFF1", highlightthickness=1); console_frame.pack(fill="both", expand=True, pady=(0, 5))
        c_inner = tk.Frame(console_frame, bg="#F7F9FA", padx=15, pady=10); c_inner.pack(fill="both", expand=True)
        tk.Label(c_inner, text="CURRENT OPERATION:", font=("Arial", 9, "bold"), fg="#90A4AE", bg="#F7F9FA").pack(anchor="w")
        self.cmd_lbl = tk.Label(c_inner, text="Waiting...", font=("Courier New", 16, "bold"), fg="#263238", bg="#F7F9FA", anchor="w", wraplength=600, justify="left"); self.cmd_lbl.pack(fill="x", pady=(2, 0))
        self.desc_lbl = tk.Label(c_inner, text="--", font=("Arial", 12, "italic"), fg="#546E7A", bg="#F7F9FA", anchor="w", wraplength=600, justify="left"); self.desc_lbl.pack(fill="x", pady=(4, 0))
        footer = tk.Frame(self, bg=CLR_BG, height=80); footer.pack(side="bottom", fill="x", pady=(5, 20), padx=50)
        self.btn_pause = RoundedButton(footer, text="PAUSE", command=lambda: self.c.backend.ui_pause_resume(), width=150, height=55, bg_color=CLR_WARNING, hover_color=CLR_WARNING_HOVER); self.btn_pause.pack(side="left")
        RoundedButton(footer, text="STOP", command=self.cancel_run, width=150, height=55, bg_color=CLR_DANGER, hover_color=CLR_DANGER_HOVER).pack(side="right")

    def cancel_run(self):
        confirm = CustomConfirmPopup(self.c, "Stop Confirmation", "STOP PROTOCOL", "Are you sure you want to abort?")
        if confirm.result: self.c.backend.ui_stop()

    def update_view(self, state):
        progress = state["progress"]; status = state["status"]; cmd_text = state["current_line"]; desc_text = state.get("current_desc", ""); est_time = state.get("est", "--:--:--:--"); source = state.get("started_by", "Unknown")
        self.source_lbl.config(text=f"Source: {source}"); self.percent_lbl.config(text=f"{int(progress)}%"); self.prog.set_progress(progress); self.time_lbl.config(text=f"Est: {est_time}")
        is_paused = "Paused" in status; self.spinner.set_paused(is_paused)
        if is_paused:
            reason = state.get('pause_reason', 'UNKNOWN').upper(); self.status_badge.config(text=f"● PAUSED ({reason})", fg="#E65100", bg="#FFF3E0")
            self.cmd_lbl.config(text=f"PAUSED ({reason})", fg="#E65100"); self.desc_lbl.config(text="System waiting for resume...", fg="#BF360C")
            self.btn_pause.itemconfig(self.btn_pause.text_id, text="RESUME"); self.btn_pause.set_color(CLR_SUCCESS, CLR_SUCCESS_HOVER)
        else:
            self.status_badge.config(text="● RUNNING", fg=CLR_SUCCESS, bg="#E8F5E9")
            self.cmd_lbl.config(text=cmd_text, fg="#263238"); self.desc_lbl.config(text=desc_text if desc_text else "Processing...", fg="#546E7A")
            self.btn_pause.itemconfig(self.btn_pause.text_id, text="PAUSE"); self.btn_pause.set_color(CLR_WARNING, CLR_WARNING_HOVER)
            
if __name__ == "__main__":
    app = KioskApp()
    app.mainloop()