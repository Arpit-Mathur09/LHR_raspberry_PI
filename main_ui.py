#v1.4 ProtocolSetupPopup + Running Screen updated (Fan and Sensor Status bar) + Lid open Close + Enhanced Widgets
import tkinter as tk
from tkinter import ttk
import os
import backend 
from datetime import datetime
import math
import subprocess
import time
import functools
import threading # Required for async scanning
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
# --- TRY IMPORTING PIL ---
try:
    from PIL import Image, ImageTk, ImageGrab, ImageFilter
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
CLR_TRAY = "#F7F9FB"         # Cloud White Background
CLR_TRAY_TEXT = "#37474F"    # Dark Blue-Grey Text
CLR_TILE_BG = "#FFFFFF"      # Pure White Cards
CLR_TILE_BORDER = "#DAE0E5"  # Subtle Border color
CLR_TILE_SHADOW = "#CFD8DC"  # Bottom border "Shadow"
CLR_ACCENT_BG = "#E3F2FD"  # <--- THIS WAS MISSING (Light Blue for Active Tiles)
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


# --- UPDATED :  Added set_color ---
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
        # Draw Fill (Initial empty)
        self.fill_id = self.create_rounded_rect(0, 0, 0, height, radius=height, fill=fill_color, tags="fill")

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def set_progress(self, pct):
        self.target_pct = max(0, min(100, pct))
        self.animate()

    def set_color(self, color):
        """Updates color and forces a redraw immediately."""
        if self.fill_color != color:
            self.fill_color = color
            self.redraw_fill()

    def redraw_fill(self):
        """Draws the bar with the current width and color."""
        self.delete("fill")
        raw_width = (self.current_pct / 100) * self.w
        # Ensure min width matches height for perfect roundness, unless 0
        new_width = max(self.h, raw_width) if self.current_pct > 0.5 else 0
        
        if new_width > 0:
            self.create_rounded_rect(0, 0, new_width, self.h, radius=self.h, fill=self.fill_color, tags="fill")

    def animate(self):
        diff = self.target_pct - self.current_pct
        if abs(diff) < 0.5: 
            self.current_pct = self.target_pct
        else: 
            self.current_pct += diff * 0.1 
        
        self.redraw_fill()
        
        if self.current_pct != self.target_pct: 
            self.after(20, self.animate)
    
    
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
        self.scroll_start_y = 0 

    def _on_canvas_configure(self, event): self.canvas.itemconfig(self.window_id, width=event.width)
    def _start_scroll(self, event): self.last_y = event.y_root; self.scroll_start_y = event.y_root
    def _do_scroll(self, event):
        dy = event.y_root - self.last_y; self.last_y = event.y_root
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
def get_blur_bg(root_window):
    if not HAS_PIL: return None
    try:
        root_window.update() 
        x = root_window.winfo_rootx(); y = root_window.winfo_rooty()
        w = root_window.winfo_width(); h = root_window.winfo_height()
        if w <= 1 or h <= 1: return None
        img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
        white_layer = Image.new("RGB", img.size, (255, 255, 255))
        blended = Image.blend(img, white_layer, 0.85)
        # Apply Gaussian Blur for that "frosted glass" effect
        #blended = blended.filter(ImageFilter.GaussianBlur(radius=5)) 
        return ImageTk.PhotoImage(blended)
    except Exception as e:
        print(f"BG Blur Error: {e}"); return None

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


# --- CUSTOM BRIGHTNESS WIDGET ---
class BrightnessControl(tk.Canvas):
    def __init__(self, parent, width=180, height=280, initial=50, command=None, bg_color="#F7F9FC"):
        super().__init__(parent, width=width, height=height, bg=bg_color, highlightthickness=0)
        self.w = width; self.h = height
        self.val = initial; self.command = command
        
        self.cx = width / 2
        self.cy_sun = 45        
        self.bar_w = 90          
        self.bar_x = (width - self.bar_w) / 2
        self.bar_top = 90       
        self.bar_bot = height - 20 
        self.bar_h = self.bar_bot - self.bar_top
        
        self.bind("<Button-1>", self.on_touch)
        self.bind("<B1-Motion>", self.on_touch)
        self.draw()

    def draw(self):
        self.delete("all")
        pct = self.val / 100.0
        
        # Modern Sun Colors
        if pct < 0.3: sun_fill = "#B0BEC5"      # Inactive Grey
        elif pct < 0.8: sun_fill = "#FFB300"    # Warm Orange
        else: sun_fill = "#FF6F00"              # Hot Orange
        
        # Tiny Sun (Clean look)
        core_r = 6 + (2 * pct)
        ray_len = 5 + (3 * pct) 
        
        for i in range(0, 360, 45):
            rad = math.radians(i + (pct * 90))
            x1 = self.cx + ((core_r + 4) * math.cos(rad))
            y1 = self.cy_sun + ((core_r + 4) * math.sin(rad))
            x2 = self.cx + ((core_r + 4 + ray_len) * math.cos(rad))
            y2 = self.cy_sun + ((core_r + 4 + ray_len) * math.sin(rad))
            self.create_line(x1, y1, x2, y2, fill=sun_fill, width=2, capstyle="round")
            
        self.create_oval(self.cx-core_r, self.cy_sun-core_r, self.cx+core_r, self.cy_sun+core_r, fill=sun_fill, outline="")

        # Bar Background (Subtle Track)
        self.create_rectangle(self.bar_x, self.bar_top, self.bar_x + self.bar_w, self.bar_bot, 
                              fill="#ECEFF1", outline="", width=0)
        
        # Active Fill (Gradient Simulation using solid colors)
        fill_h = self.bar_h * pct
        fill_top = self.bar_bot - fill_h
        
        # Color shifts from Blue -> Cyan based on height
        fill_col = CLR_PRIMARY if pct <= 0.7 else "#00BCD4"
        
        self.create_rectangle(self.bar_x, fill_top, self.bar_x + self.bar_w, self.bar_bot, 
                              fill=fill_col, outline="")
        
        # Text inside the bar
        text_col = "white" if pct > 0.15 else "#90A4AE"
        self.create_text(self.cx, self.bar_bot - 20, text=f"{int(self.val)}%", 
                         font=("Arial", 14, "bold"), fill=text_col)

    def update_from_y(self, y):
        rel_y = max(self.bar_top, min(self.bar_bot, y))
        travel = self.bar_bot - self.bar_top
        current = self.bar_bot - rel_y
        self.val = int((current / travel) * 100)
        self.draw()
        if self.command: self.command(self.val)

    def on_touch(self, e): self.update_from_y(e.y)


#   --- DYNAMIC SUN ICON (Reflects Brightness) ---
class SunIcon(tk.Canvas):
    def __init__(self, parent, size=60, bg_color="#FFFFFF", brightness=100):
        super().__init__(parent, width=size, height=size, bg=bg_color, highlightthickness=0)
        self.size = size
        self.brightness = brightness
        self.draw()

    def set_brightness(self, pct):
        self.brightness = pct
        self.draw()

    def draw(self):
        self.delete("all")
        cx, cy = self.size/2, self.size/2
        pct = self.brightness / 100.0
        
        # Color & Size Logic
        if pct < 0.3:
            # Low Brightness: Dim Grey/Blue
            core_col = "#B0BEC5" 
            outline_col = "#90A4AE"
            ray_col = "#CFD8DC"
            ray_len = 4
            core_r = 10
        elif pct < 0.7:
            # Medium Brightness: Warm Yellow
            core_col = "#FFEE58"
            outline_col = "#FBC02D"
            ray_col = "#FDD835"
            ray_len = 6
            core_r = 12
        else:
            # High Brightness: Hot Orange
            core_col = "#FFEB3B"
            outline_col = "#F57F17"
            ray_col = "#FF9800"
            ray_len = 9
            core_r = 14
            
        # Draw Rays
        gap = core_r + 4
        
        for i in range(0, 360, 45):
            rad = math.radians(i + (pct * 45)) # Rotate slightly based on brightness
            x1 = cx + (gap * math.cos(rad))
            y1 = cy + (gap * math.sin(rad))
            x2 = cx + ((gap + ray_len) * math.cos(rad))
            y2 = cy + ((gap + ray_len) * math.sin(rad))
            self.create_line(x1, y1, x2, y2, fill=ray_col, width=3, capstyle="round")

        # Draw Core
        self.create_oval(cx-core_r, cy-core_r, cx+core_r, cy+core_r, fill=core_col, outline=outline_col, width=2)            
# --- CUSTOM BULB ICON (Modern) ---
class BulbIcon(tk.Canvas):
    def __init__(self, parent, size=60, bg_color="#FFFFFF"):
        super().__init__(parent, width=size, height=size, bg=bg_color, highlightthickness=0)
        self.size = size
        self.is_on = False
        self.draw()
        
    def set_state(self, is_on, new_bg):
        self.is_on = is_on
        self.config(bg=new_bg)
        self.draw()

    def draw(self):
        self.delete("all")
        cx, cy = self.size/2, self.size/2
        
        if self.is_on:
            fill_col = "#FFC107" # Amber
            outline_col = "#FFA000"
            glow_ray = "#FFD54F"
            # Draw Rays
            for i in range(0, 360, 45):
                rad = math.radians(i)
                x1 = cx + (18 * math.cos(rad))
                y1 = cy - 5 + (18 * math.sin(rad))
                x2 = cx + (26 * math.cos(rad))
                y2 = cy - 5 + (26 * math.sin(rad))
                self.create_line(x1, y1, x2, y2, fill=glow_ray, width=2, capstyle="round")
        else:
            fill_col = "" 
            outline_col = "#90A4AE" # Cool Grey
            glow_ray = None

        # Bulb Body
        self.create_oval(cx-12, cy-22, cx+12, cy+2, outline=outline_col, fill=fill_col, width=2)
        # Base
        self.create_rectangle(cx-6, cy+2, cx+6, cy+14, fill="#CFD8DC", outline=outline_col, width=0)
        # Threads
        self.create_line(cx-5, cy+6, cx+5, cy+6, fill="#90A4AE", width=1)
        self.create_line(cx-5, cy+10, cx+5, cy+10, fill="#90A4AE", width=1)
        # Tip
        self.create_oval(cx-2, cy+14, cx+2, cy+16, fill="#78909C", outline="")
# --- CUSTOM DOOR ICON (Dynamic State) ---
class DoorIcon(tk.Canvas):
    def __init__(self, parent, size=60, bg_color="#FFFFFF"):
        super().__init__(parent, width=size, height=size, bg=bg_color, highlightthickness=0)
        self.size = size
        self.is_open = False
        self.draw()

    def set_state(self, is_open, new_bg):
        self.is_open = is_open
        self.config(bg=new_bg)
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.size, self.size
        cx, cy = w/2, h/2
        
        # Draw Frame (Always visible)
        self.create_rectangle(10, 5, w-10, h-5, width=3, outline="#546E7A")

        if self.is_open:
            # DANGER: Door swinging open (Trapezoid)
            # Fill is a lighter red to stand out against the red bg
            points = [10, 5,  w-20, 15,  w-20, h-15,  10, h-5]
            self.create_polygon(points, fill="#FFCDD2", outline="#C62828", width=2)
            
            # Warning Exclamation
            self.create_text(w-15, cy, text="!", font=("Arial", 22, "bold"), fill="#C62828")
        else:
            # SAFE: Door closed (Rectangle fills frame)
            # Fill is a lighter green
            self.create_rectangle(12, 7, w-12, h-7, fill="#C8E6C9", outline="#2E7D32", width=2)
            
            # Handle
            self.create_oval(w-22, cy-4, w-14, cy+4, fill="white", outline="#2E7D32")

# --- CUSTOM WIFI ICON (Dynamic Color) ---
class WiFiIcon(tk.Canvas):
    def __init__(self, parent, size=60, bg_color="#FFFFFF", is_connected=False):
        super().__init__(parent, width=size, height=size, bg=bg_color, highlightthickness=0)
        self.is_connected = is_connected
        self.draw()

    def set_status(self, is_connected):
        self.is_connected = is_connected
        self.draw()

    def draw(self):
        self.delete("all")
        cx, cy = 30, 45 
        
        # Color Logic
        if self.is_connected:
            col = CLR_PRIMARY  # Accent Blue
            width_val = 5      # Thicker when connected
        else:
            col = "#546E7A"    # Dark Grey/Blackish
            width_val = 4

        # Small Dot
        self.create_oval(cx-4, cy-4, cx+4, cy+4, fill=col, outline="")
        
        # Arcs
        self.create_arc(cx-12, cy-12, cx+12, cy+12, start=45, extent=90, style="arc", outline=col, width=width_val)
        self.create_arc(cx-20, cy-20, cx+20, cy+20, start=45, extent=90, style="arc", outline=col, width=width_val)
        self.create_arc(cx-28, cy-28, cx+28, cy+28, start=45, extent=90, style="arc", outline=col, width=width_val)


# --- CUSTOM KEYBOARD BUTTON (Responsive Canvas) ---
class KeyboardKey(tk.Canvas):
    def __init__(self, parent, text, width, height, command=None, bg_color="#FFFFFF", fg_color="#000000", is_special=False):
        super().__init__(parent, width=width, height=height, bg="#D1D5DB", highlightthickness=0)
        self.command = command
        self.text = text
        self.w = width
        self.h = height
        self.base_bg = bg_color
        self.base_fg = fg_color
        self.is_special = is_special
        
        self.draw_button(self.base_bg, self.base_fg)
        
        self.bind("<Button-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

    def draw_button(self, fill_col, text_col):
        self.delete("all")
        m = 2 
        r = 10 
        
        # Draw Rounded Rect
        self.create_arc(m, m, m+2*r, m+2*r, start=90, extent=90, fill=fill_col, outline="")
        self.create_arc(self.w-m-2*r, m, self.w-m, m+2*r, start=0, extent=90, fill=fill_col, outline="")
        self.create_arc(self.w-m-2*r, self.h-m-2*r, self.w-m, self.h-m, start=270, extent=90, fill=fill_col, outline="")
        self.create_arc(m, self.h-m-2*r, m+2*r, self.h-m, start=180, extent=90, fill=fill_col, outline="")
        self.create_rectangle(m+r, m, self.w-m-r, self.h-m, fill=fill_col, outline="")
        self.create_rectangle(m, m+r, self.w-m, self.h-m-r, fill=fill_col, outline="")
        
        f_size = 14 if len(self.text) > 1 else 18
        if self.is_special: f_size = 12
        self.create_text(self.w/2, self.h/2, text=self.text, font=("Arial", f_size, "bold"), fill=text_col)

    def on_press(self, e):
        press_col = "#E0E0E0" if self.base_bg == "#FFFFFF" else "#90A4AE"
        self.draw_button(press_col, self.base_fg)
        if self.command: self.command()

    def on_release(self, e):
        self.draw_button(self.base_bg, self.base_fg)
    
    def update_text(self, new_text):
        self.text = new_text
        self.draw_button(self.base_bg, self.base_fg)
    
    def set_color(self, new_bg, new_fg):
        self.base_bg = new_bg
        self.base_fg = new_fg
        self.draw_button(new_bg, new_fg)


# --- FULL WIDTH RESPONSIVE KEYBOARD ---
class KeyboardKey(tk.Canvas):
    def __init__(self, parent, text, width, height, command=None, bg_color="#FFFFFF", fg_color="#000000", is_special=False):
        super().__init__(parent, width=width, height=height, bg="#D1D5DB", highlightthickness=0)
        self.command = command
        self.text = text
        self.w = width
        self.h = height
        self.base_bg = bg_color
        self.base_fg = fg_color
        self.is_special = is_special
        
        self.draw_button(self.base_bg, self.base_fg)
        
        self.bind("<Button-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

    def draw_button(self, fill_col, text_col):
        self.delete("all")
        m = 2; r = 10
        
        # Rounded Rect
        self.create_arc(m, m, m+2*r, m+2*r, start=90, extent=90, fill=fill_col, outline="")
        self.create_arc(self.w-m-2*r, m, self.w-m, m+2*r, start=0, extent=90, fill=fill_col, outline="")
        self.create_arc(self.w-m-2*r, self.h-m-2*r, self.w-m, self.h-m, start=270, extent=90, fill=fill_col, outline="")
        self.create_arc(m, self.h-m-2*r, m+2*r, self.h-m, start=180, extent=90, fill=fill_col, outline="")
        self.create_rectangle(m+r, m, self.w-m-r, self.h-m, fill=fill_col, outline="")
        self.create_rectangle(m, m+r, self.w-m, self.h-m-r, fill=fill_col, outline="")
        
        f_size = 14 if len(self.text) > 1 else 18
        if self.is_special: f_size = 12
        self.create_text(self.w/2, self.h/2, text=self.text, font=("Arial", f_size, "bold"), fill=text_col)

    def on_press(self, e):
        press_col = "#E0E0E0" if self.base_bg == "#FFFFFF" else "#90A4AE"
        self.draw_button(press_col, self.base_fg)
        if self.command: self.command()

    def on_release(self, e):
        self.draw_button(self.base_bg, self.base_fg)
    
    def update_text(self, new_text):
        self.text = new_text
        self.draw_button(self.base_bg, self.base_fg)
    
    def set_color(self, new_bg, new_fg):
        self.base_bg = new_bg
        self.base_fg = new_fg
        self.draw_button(new_bg, new_fg)


# --- FULL WIDTH RESPONSIVE KEYBOARD (Fixed Layout & Animations) ---
class TouchKeyboard(tk.Toplevel):
    def __init__(self, parent, target_entry, on_close=None):
        super().__init__(parent)
        self.target = target_entry
        self.on_close = on_close
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.config(bg="#D1D5DB", cursor="none")
        
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.kb_h = 280 
        self.geometry(f"{screen_w}x{self.kb_h}+0+{screen_h - self.kb_h}")
        
        # Dynamic Widths
        self.base_key_w = int(screen_w / 10) - 4
        self.base_key_h = 55 
        
        self.container = tk.Frame(self, bg="#D1D5DB", padx=2, pady=5)
        self.container.pack(fill="both", expand=True)
        
        self.is_shift = False
        self.is_symbols = False
        self.letter_keys = [] 
        
        self.render_layout()
        self.popover = None

    def show_popover(self, key_widget, text):
        if len(text) > 1: return # Only for single chars
        
        x = key_widget.winfo_rootx()
        y = key_widget.winfo_rooty()
        w = key_widget.winfo_width()
        
        if self.popover: self.popover.destroy()
        
        self.popover = tk.Toplevel(self)
        self.popover.overrideredirect(True)
        self.popover.attributes("-topmost", True)
        
        pop_w, pop_h = 60, 70
        pos_x = x + (w//2) - (pop_w//2)
        pos_y = y - pop_h + 10
        
        self.popover.geometry(f"{pop_w}x{pop_h}+{pos_x}+{pos_y}")
        
        cv = tk.Canvas(self.popover, width=pop_w, height=pop_h, bg="white", highlightthickness=0)
        cv.pack()
        cv.create_rectangle(2, 2, pop_w-2, pop_h-2, outline="#B0BEC5", width=1)
        cv.create_text(pop_w/2, pop_h/2 - 5, text=text, font=("Arial", 28, "bold"), fill="black")
        
        self.after(150, lambda: self.popover.destroy())

    def render_layout(self):
        for w in self.container.winfo_children(): w.destroy()
        self.letter_keys = []
        
        if self.is_symbols:
            rows = [
                ['1','2','3','4','5','6','7','8','9','0'],
                ['@','#','$','_','&','-','+','(',')','/'],
                ['*','"',"'",':',';','!','?',',','.']
            ]
        else:
            rows = [
                ['q','w','e','r','t','y','u','i','o','p'],
                ['a','s','d','f','g','h','j','k','l'],
                ['z','x','c','v','b','n','m']
            ]

        # --- ROWS 1 & 2 ---
        for row_keys in rows[:2]:
            row_f = tk.Frame(self.container, bg="#D1D5DB")
            row_f.pack(expand=True, fill="both", pady=2)
            for k in row_keys:
                txt = k.upper() if (self.is_shift and not self.is_symbols) else k
                btn = KeyboardKey(row_f, text=txt, width=self.base_key_w, height=self.base_key_h, bg_color="#FFFFFF")
                # FIX 1: Ensure Symbols also get the popover animation
                btn.command = lambda b=btn, char=txt: (self.press(char), self.show_popover(b, char))
                btn.pack(side="left", padx=2, expand=True)
                
                if not self.is_symbols: self.letter_keys.append(btn)

        # --- ROW 3 ---
        row3_f = tk.Frame(self.container, bg="#D1D5DB")
        row3_f.pack(expand=True, fill="both", pady=2)
        
        special_w = int(self.base_key_w * 1.5)
        
        if self.is_symbols:
             # FIX 2: Layout overflow fix for Symbols
             # Symbols Row 3 has 9 keys. Adding a Wide Backspace (1.5x) makes 10.5x width -> Overflow.
             # Solution: Use Standard Width (base_key_w) for Backspace in Symbol mode.
             
             for k in rows[2]:
                btn = KeyboardKey(row3_f, text=k, width=self.base_key_w, height=self.base_key_h, bg_color="#FFFFFF")
                # FIX 1: Animation for symbols row 3
                btn.command = lambda b=btn, c=k: (self.press(c), self.show_popover(b, c))
                btn.pack(side="left", padx=2, expand=True)
             
             # Standard Width Backspace for Symbols
             btn_bs = KeyboardKey(row3_f, text="⌫", width=self.base_key_w, height=self.base_key_h, bg_color="#B0BEC5", is_special=True)
             btn_bs.command = self.backspace
             btn_bs.pack(side="left", padx=2, expand=True)

        else:
            # Alpha Layout (Fits perfectly with 1.5x Shift/Backspace)
            bg_shift = "#FFFFFF" if self.is_shift else "#B0BEC5"
            fg_shift = CLR_PRIMARY if self.is_shift else "#000000"
            
            self.btn_shift = KeyboardKey(row3_f, text="⇧", width=special_w, height=self.base_key_h, bg_color=bg_shift, fg_color=fg_shift, is_special=True)
            self.btn_shift.command = self.toggle_shift
            self.btn_shift.pack(side="left", padx=2)
            
            for k in rows[2]:
                txt = k.upper() if self.is_shift else k
                btn = KeyboardKey(row3_f, text=txt, width=self.base_key_w, height=self.base_key_h)
                btn.command = lambda b=btn, char=txt: (self.press(char), self.show_popover(b, char))
                btn.pack(side="left", padx=2, expand=True)
                self.letter_keys.append(btn)
                
            btn_bs = KeyboardKey(row3_f, text="⌫", width=special_w, height=self.base_key_h, bg_color="#B0BEC5", is_special=True)
            btn_bs.command = self.backspace
            btn_bs.pack(side="left", padx=2)

        # --- ROW 4 ---
        row4_f = tk.Frame(self.container, bg="#D1D5DB")
        row4_f.pack(expand=True, fill="both", pady=2)
        
        side_btn_w = int(self.base_key_w * 2) 
        space_w = int(self.base_key_w * 5)
        
        lbl_sym = "ABC" if self.is_symbols else "123"
        btn_sym = KeyboardKey(row4_f, text=lbl_sym, width=side_btn_w, height=self.base_key_h, bg_color="#B0BEC5", is_special=True)
        btn_sym.command = self.toggle_symbols
        btn_sym.pack(side="left", padx=2, expand=True)
        
        btn_spc = KeyboardKey(row4_f, text="space", width=space_w, height=self.base_key_h, bg_color="#FFFFFF")
        btn_spc.command = lambda: self.press(" ")
        btn_spc.pack(side="left", padx=2, expand=True)
        
        btn_done = KeyboardKey(row4_f, text="Done", width=side_btn_w, height=self.base_key_h, bg_color=CLR_PRIMARY, fg_color="#FFFFFF", is_special=True)
        btn_done.command = self.close_kb
        btn_done.pack(side="left", padx=2, expand=True)

    def press(self, char):
        self.target.insert(tk.END, char)

    def backspace(self):
        txt = self.target.get()
        self.target.delete(0, tk.END)
        self.target.insert(0, txt[:-1])

    def toggle_shift(self):
        self.is_shift = not self.is_shift
        new_fg = CLR_PRIMARY if self.is_shift else "#000000"
        new_bg = "#FFFFFF" if self.is_shift else "#B0BEC5"
        self.btn_shift.set_color(new_bg, new_fg)
        
        for btn in self.letter_keys:
            old_txt = btn.text
            new_txt = old_txt.upper() if self.is_shift else old_txt.lower()
            btn.update_text(new_txt)
            btn.command = lambda b=btn, char=new_txt: (self.press(char), self.show_popover(b, char))

    def toggle_symbols(self):
        self.is_symbols = not self.is_symbols
        self.render_layout()

    def close_kb(self):
        if self.on_close: self.on_close()
        self.destroy()


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

#  --- SMOOTH SCROLL (With Noise Filtering) ---
class SmoothScroll(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Tuning
        self.threshold = 5      # Pixel movement required to START scrolling
        self.filter_size = 4    # Number of coordinates to average (Higher = Smoother but slower)
        
        self.scrolling = False
        self.start_y = 0
        self.history = []       # Stores recent Y coordinates for averaging

        self.bind("<Button-1>", self.on_start)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)

    def bind_recursive(self, widget):
        widget.bind("<Button-1>", self.on_start, add="+")
        widget.bind("<B1-Motion>", self.on_drag, add="+")
        widget.bind("<ButtonRelease-1>", self.on_release, add="+")
        for child in widget.winfo_children():
            self.bind_recursive(child)

    def on_start(self, event):
        self.start_y = event.y
        self.scrolling = False
        self.history = [event.y] * self.filter_size # Reset filter
        self.scan_mark(event.x, event.y)

    def on_drag(self, event):
        # 1. Add current position to history
        self.history.append(event.y)
        if len(self.history) > self.filter_size:
            self.history.pop(0)
            
        # 2. Calculate Smoothed Y (Average)
        avg_y = sum(self.history) // len(self.history)
        
        delta = avg_y - self.start_y
        
        # 3. START THRESHOLD (Prevents accidental jitters when tapping)
        if not self.scrolling:
            if abs(delta) < self.threshold: return
            self.scrolling = True

        # 4. BOUNDARY CHECK
        top, bot = self.yview()
        if top <= 0.0 and bot >= 1.0: return  # Content fits on screen -> Lock
        if top <= 0.0 and delta > 0:          # Stop at Top
            self.scan_mark(event.x, avg_y)
            self.start_y = avg_y
            return
        if bot >= 1.0 and delta < 0:          # Stop at Bottom
            self.scan_mark(event.x, avg_y)
            self.start_y = avg_y
            return

        # 5. EXECUTE SCROLL (Using averaged Y)
        # We pass 'gain=1' for natural 1:1 tracking
        self.scan_dragto(event.x, avg_y, gain=1)

    def on_release(self, event):
        self.scrolling = False
        self.history = []
        
class RoundedTile(tk.Canvas):
    def __init__(self, parent, width=125, height=110, bg_color="#FFFFFF", border_color="#E0E0E0", command=None):
        super().__init__(parent, width=width, height=height, bg=CLR_TRAY, highlightthickness=0, cursor="none")
        self.w = width
        self.h = height
        self.base_bg = bg_color
        self.border_col = border_color
        self.command = command
        self.icon_widget = None 
        
        # Click Tracking
        self.is_pressed = False
        self.start_x = 0
        self.start_y = 0
        self.tap_tolerance = 15 # Pixels (High tolerance = easier to click)
        
        self.draw(self.base_bg, self.border_col)
        
        # Bind Canvas
        self.bind("<Button-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        
        # Bind Internal Items
        self.tag_bind("all", "<Button-1>", self.on_press)
        self.tag_bind("all", "<ButtonRelease-1>", self.on_release)

    def set_icon_widget(self, widget):
        self.icon_widget = widget
        widget.config(cursor="none")
        
        # Forward events
        widget.bind("<Button-1>", self.on_press)
        widget.bind("<ButtonRelease-1>", self.on_release)
        
        if hasattr(widget, "winfo_children"):
            for child in widget.winfo_children():
                child.config(cursor="none")
                child.bind("<Button-1>", self.on_press)
                child.bind("<ButtonRelease-1>", self.on_release)

    def round_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def draw(self, fill_col, border_col):
        self.delete("bg_shape")
        r = 15; bw = 2; inset = bw / 2
        self.round_rect(inset, inset, self.w-inset, self.h-inset, radius=r, 
                        fill=fill_col, outline=border_col, width=bw, tags="bg_shape")
        self.tag_lower("bg_shape")

    def update_colors(self, new_bg, new_border):
        self.base_bg = new_bg
        self.border_col = new_border
        self.draw(new_bg, new_border)
        if self.icon_widget:
            self.icon_widget.config(bg=new_bg)
            if hasattr(self.icon_widget, 'bg_color'):
                self.icon_widget.bg_color = new_bg
                if hasattr(self.icon_widget, 'draw'): self.icon_widget.draw()

    def on_press(self, e):
        self.is_pressed = True
        # Record where the finger started
        self.start_x = e.x_root
        self.start_y = e.y_root
        
        # Visual Feedback
        self.draw(CLR_ACCENT_BG, CLR_PRIMARY)
        if self.icon_widget: 
            self.icon_widget.config(bg=CLR_ACCENT_BG)
            if hasattr(self.icon_widget, 'draw'): self.icon_widget.draw()
        
    def on_release(self, e):
        self.after(100, lambda: self.restore_visuals())
        
        if self.is_pressed and self.command:
            # CALCULATE MOVEMENT DISTANCE
            dist = abs(e.x_root - self.start_x) + abs(e.y_root - self.start_y)
            
            # THE FIX: If moved less than 15px, treat as CLICK. 
            # If moved more, treat as scroll/jitter and IGNORE.
            if dist < self.tap_tolerance:
                self.command(None)
                
        self.is_pressed = False

    def restore_visuals(self):
        self.draw(self.base_bg, self.border_col)
        if self.icon_widget:
            self.icon_widget.config(bg=self.base_bg)
            if hasattr(self.icon_widget, 'draw'): self.icon_widget.draw()
# --- MODERN BRIGHTNESS SLIDER (No Cursor, Clean Fill) ---
class ModernBrightness(tk.Canvas):
    def __init__(self, parent, width=140, height=300, initial=50, command=None, bg_color="#F7F9FC"):
        super().__init__(parent, width=width, height=height, bg=bg_color, highlightthickness=0, cursor="none")
        self.w = width
        self.h = height
        self.val = initial
        self.command = command
        
        self.pad = 20
        self.bar_w = 100
        self.bar_x = (width - self.bar_w) / 2
        self.bar_h = height - (self.pad * 2)
        self.bar_top = self.pad
        self.bar_bot = height - self.pad
        
        self.bind("<Button-1>", self.on_touch)
        self.bind("<B1-Motion>", self.on_touch)
        self.draw()

    def create_rounded_rect(self, x1, y1, x2, y2, r, fill, outline, width=1):
        points = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
        return self.create_polygon(points, smooth=True, fill=fill, outline=outline, width=width)

    def draw_sun_icon(self, cx, cy, pct):
        if pct < 0.3:
            core_col, ray_col = "#B0BEC5", "#CFD8DC"
            ray_len, core_r = 4, 10
        elif pct < 0.7:
            core_col, ray_col = "#FFEE58", "#FDD835"
            ray_len, core_r = 6, 12
        else:
            core_col, ray_col = "#FFEB3B", "#FF9800"
            ray_len, core_r = 9, 14
            
        gap = core_r + 4
        for i in range(0, 360, 45):
            rad = math.radians(i + (pct * 45))
            x1 = cx + (gap * math.cos(rad))
            y1 = cy + (gap * math.sin(rad))
            x2 = cx + ((gap + ray_len) * math.cos(rad))
            y2 = cy + ((gap + ray_len) * math.sin(rad))
            self.create_line(x1, y1, x2, y2, fill=ray_col, width=3, capstyle="round")
        self.create_oval(cx-core_r, cy-core_r, cx+core_r, cy+core_r, fill=core_col, outline="", width=0)

    def draw(self):
        self.delete("all")
        pct = self.val / 100.0
        r = 25
        
        # Color Scheme
        if pct < 0.3: outline_col = "#90A4AE"
        elif pct < 0.7: outline_col = "#FBC02D"
        else: outline_col = "#FF9800"

        # 1. Track Background (Has Color Outline)
        self.create_rounded_rect(self.bar_x, self.bar_top, self.bar_x+self.bar_w, self.bar_bot, 
                                 r, "#CFD8DC", outline_col, width=2)
        
        # 2. Active Fill (Pure White, NO Outline)
        fill_h = self.bar_h * pct
        fill_top = self.bar_bot - fill_h
        if fill_top < self.bar_top: fill_top = self.bar_top
        
        if pct > 0.05:
            self.create_rounded_rect(self.bar_x, fill_top, self.bar_x+self.bar_w, self.bar_bot, 
                                     r, "#FFFFFF", "", width=0) # <-- outline="" removes border

        # 3. Sun Icon
        cx = self.w / 2
        cy = self.bar_bot - 40
        self.draw_sun_icon(cx, cy, pct)
        
        # 4. Text
        self.create_text(cx, self.bar_bot - 90, text=f"{int(self.val)}%", font=("Arial", 20, "bold"), fill="#37474F")

    def update_from_y(self, y):
        rel_y = max(self.bar_top, min(self.bar_bot, y))
        travel = self.bar_bot - self.bar_top
        dist_from_bot = self.bar_bot - rel_y
        self.val = int((dist_from_bot / travel) * 100)
        self.draw()
        if self.command: self.command(self.val)
    
    def on_touch(self, e): self.update_from_y(e.y)

# --- UPDATED : MARQUEE LABEL (For Long Text Scrolling) ---
class MarqueeLabel(tk.Canvas):
    def __init__(self, parent, text, width, height, font=("Arial", 14, "bold"), fg="#37474F", bg="white"):
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0)
        self.text = text
        self.fps = 30
        self.step = 1
        self.margin = 30
        self.animating = False
        
        # Create Text
        self.text_id = self.create_text(0, height/2, text=text, font=font, fill=fg, anchor="w")
        
        self.canvas_width = width
        self.text_width = 0
        self.offset = 0
        
        self.bind("<Configure>", self.on_resize)
        self.bind("<Destroy>", self.on_destroy)

    def set_text(self, new_text):
        """Updates the text dynamically and resets animation if needed."""
        if self.text == new_text: return
        self.text = new_text
        self.itemconfig(self.text_id, text=new_text)
        self.offset = 0
        self.coords(self.text_id, 0, int(self["height"])/2)
        
        # Re-check width immediately if possible
        if self.winfo_exists():
            bbox = self.bbox(self.text_id)
            if bbox:
                self.text_width = bbox[2] - bbox[0]
                self.animating = False # Stop current
                if self.text_width > self.canvas_width:
                    self.animating = True
                    self.animate()

    def on_destroy(self, event):
        self.animating = False

    def on_resize(self, event):
        if not self.winfo_exists(): return
        self.canvas_width = event.width
        bbox = self.bbox(self.text_id)
        if bbox:
            self.text_width = bbox[2] - bbox[0]
            if self.text_width > self.canvas_width and not self.animating:
                self.animating = True
                self.animate()

    def animate(self):
        if not self.winfo_exists() or not self.animating: return
        try:
            self.offset -= self.step
            if abs(self.offset) > (self.text_width - self.canvas_width + self.margin):
                self.after(1500, self.reset)
                return
            self.coords(self.text_id, self.offset, int(self["height"])/2)
            self.after(self.fps, self.animate)
        except: self.animating = False

    def reset(self):
        if not self.winfo_exists() or not self.animating: return
        try:
            self.offset = 0
            self.coords(self.text_id, 0, int(self["height"])/2)
            self.after(1000, self.animate)
        except: self.animating = False
        
    
class SettingsTray(tk.Frame):
    def __init__(self, parent_root, controller, floating_btn):
        super().__init__(parent_root)
        self.c = controller
        self.floating_btn = floating_btn
        self.floating_btn.withdraw()
        
        # CRITICAL FIX: Force focus so first click always works
        self.focus_force()
        
        self.bg_img = get_blur_bg(parent_root)
        self.place(x=0, y=0, relwidth=1, relheight=1)
        
        w = parent_root.winfo_width()
        h = parent_root.winfo_height()
        
        self.cv = tk.Canvas(self, width=w, height=h, highlightthickness=0, bg="white", cursor="none")
        self.cv.pack(fill="both", expand=True)

        if self.bg_img: self.cv.create_image(0, 0, image=self.bg_img, anchor="nw")
        else: self.cv.configure(bg="#F7F9FC")
            
        self.tray_w = 320
        self.tray_h = h
        self.f = tk.Frame(self.cv, bg=CLR_TRAY, width=self.tray_w, height=self.tray_h, cursor="none")
        self.f.pack_propagate(False)
        self.tray_win = self.cv.create_window(w, 0, window=self.f, anchor="nw")
        
        # Header
        h_frame = tk.Frame(self.f, bg=CLR_TRAY, height=80)
        h_frame.pack(fill="x", side="top", pady=(20,0))
        tk.Label(h_frame, text="Control Center", font=("Arial", 16, "bold"), fg=CLR_TRAY_TEXT, bg=CLR_TRAY).pack(side="left", padx=25)
        
        close_btn = tk.Label(h_frame, text="✕", font=("Arial", 22), fg="#90A4AE", bg=CLR_TRAY)
        close_btn.pack(side="right", padx=25)
        close_btn.bind("<Button-1>", lambda e: self.close())

        self.content = tk.Frame(self.f, bg=CLR_TRAY, cursor="none")
        self.content.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.bulb_widgets = None
        if not hasattr(self.c, "light_on"): self.c.light_on = False

        self.show_main_menu()
        self.animate_open(w, 0)

    # ... keep animate_open and close same ...
    def animate_open(self, screen_w, step):
        target_x = screen_w - self.tray_w
        current_x = screen_w - (step * 50) 
        if current_x > target_x:
            self.cv.coords(self.tray_win, current_x, 0)
            self.after(5, lambda: self.animate_open(screen_w, step + 1))
        else:
            self.cv.coords(self.tray_win, target_x, 0)

    def close(self):
        self.floating_btn.deiconify()
        self.destroy()

    def show_main_menu(self):
        # 1. Gather Data
        current_bright = 50
        wifi_connected = False
        lid_status = False 
        
        if hasattr(self.c, 'backend'):
            current_bright = self.c.backend.get_brightness()
            ssid = self.c.backend.get_connected_ssid()
            if ssid: wifi_connected = True
            lid_status = self.c.backend.state.get("lid_open", False)

        for w in self.content.winfo_children(): w.destroy()
        
        grid = tk.Frame(self.content, bg=CLR_TRAY)
        grid.pack(anchor="center", pady=10)
        
        # --- COLORS ---
        sun_col = "#FBC02D" if current_bright > 30 else "#90A4AE"
        wifi_col = CLR_PRIMARY if wifi_connected else "#E0E0E0"
        
        is_light_on = self.c.backend.state.get("light_on", False) if hasattr(self.c, 'backend') else False
        light_border = "#FFD54F" if is_light_on else "#E0E0E0"
        
        # --- LID COLOR LOGIC ---
        if lid_status: 
            # OPEN = DANGER
            lid_bg = "#FFEBEE"     
            lid_border = "#EF5350" 
            lid_text_col = "#C62828"
            lid_label = "Lid Open"
        else:
            # CLOSED = SAFE
            lid_bg = "#E8F5E9"     
            lid_border = "#66BB6A" 
            lid_text_col = "#2E7D32"
            lid_label = "Lid Closed"

        # --- TILE CREATOR (FIXED: Added icon_col back) ---
        def mk_tile(parent, icon_char, text, col, row, cmd, custom_icon_cls=None, border_col="#E0E0E0", bg_col=CLR_TILE_BG, text_col="#455A64", icon_col="#546E7A"):
            tile = RoundedTile(parent, width=125, height=110, bg_color=bg_col, border_color=border_col, command=cmd)
            tile.grid(row=row, column=col, padx=8, pady=8)
            
            if custom_icon_cls:
                if custom_icon_cls == SunIcon:
                    icn = custom_icon_cls(tile, size=60, bg_color=bg_col, brightness=current_bright)
                elif custom_icon_cls == WiFiIcon:
                    icn = custom_icon_cls(tile, size=60, bg_color=bg_col, is_connected=wifi_connected)
                elif custom_icon_cls == DoorIcon:
                    icn = custom_icon_cls(tile, size=60, bg_color=bg_col)
                    icn.set_state(lid_status, bg_col)
                else:
                    icn = custom_icon_cls(tile, size=60, bg_color=bg_col)

                tile.create_window(62, 45, window=icn, tags="content")
                tile.set_icon_widget(icn)
                if custom_icon_cls == BulbIcon: self.bulb_widgets = {"tile": tile, "icon": icn}
            else:
                # Text-based icons (Thermometer, etc.)
                # FIX: We now use the passed 'icon_col' correctly
                tile.create_text(62, 45, text=icon_char, font=("Arial", 32), fill=icon_col, tags="content")

            # Label Text
            tile.create_text(62, 90, text=text, font=("Arial", 11, "bold"), fill=text_col, tags="content")
            return tile

        # --- ROW 0 ---
        mk_tile(grid, None, "WiFi", 0, 0, lambda e: self.show_wifi(), custom_icon_cls=WiFiIcon, border_col=wifi_col)
        mk_tile(grid, None, "Display", 1, 0, lambda e: self.show_brightness(), custom_icon_cls=SunIcon, border_col=sun_col)
        
        # --- ROW 1 ---
        mk_tile(grid, None, "Light", 0, 1, lambda e: self.toggle_light(), custom_icon_cls=BulbIcon, border_col=light_border)
        
        # Sensors (This line caused the error, now it works because icon_col is back)
        mk_tile(grid, "🌡", "Sensors", 1, 1, lambda e: self.show_sensors(), border_col=CLR_SUCCESS, icon_col=CLR_SUCCESS)
        
        # --- ROW 2 ---
        mk_tile(grid, None, lid_label, 0, 2, lambda e: None, custom_icon_cls=DoorIcon, border_col=lid_border, bg_col=lid_bg, text_col=lid_text_col)

        # STACKED BUTTONS
        stack_frame = tk.Frame(grid, bg=CLR_TRAY)
        stack_frame.grid(row=2, column=1, padx=8, pady=8, sticky="nsew")
        
        def mk_mini_tile(parent, text, icon, color, cmd):
            mt = RoundedTile(parent, width=125, height=50, bg_color=CLR_TILE_BG, border_color=color, command=cmd)
            mt.pack(pady=3)
            mt.create_text(25, 25, text=icon, font=("Arial", 16), fill=color, tags="content")
            mt.create_text(75, 25, text=text, font=("Arial", 11, "bold"), fill="#455A64", tags="content")
            return mt

        mk_mini_tile(stack_frame, "Info", "ℹ", "#546E7A", lambda e: self.show_about())
        mk_mini_tile(stack_frame, "Power", "⏻", CLR_DANGER, lambda e: self.show_power())
        
        self.update_bulb_visuals()  
   
    def show_about(self):
        # UPDATED TO V1.4
        popup = CustomPopup(self.winfo_toplevel(), "About", "SYSTEM INFO", 
                            "Liquid Handler v1.4\nRunning on Raspberry Pi 4", 
                            CLR_PRIMARY, "ℹ")
        self.wait_window(popup)

    def update_bulb_visuals(self):
        """Updates the Light Tile instantly without reloading the whole menu."""
        # 1. Safety Check: Do we have the widgets saved?
        if not hasattr(self, 'bulb_widgets') or not self.bulb_widgets:
            return
            
        # 2. Get State from Backend
        is_on = False
        if hasattr(self.c, 'backend'):
            is_on = self.c.backend.state.get("light_on", False)
            
        # 3. Define Colors
        # Active = Amber Border, Inactive = Grey Border
        border_col = "#FFD54F" if is_on else "#E0E0E0"
        tile_bg = CLR_TILE_BG # Or "#FFFFFF" depending on your theme constant

        # 4. Update the Tile Border
        tile = self.bulb_widgets["tile"]
        # We use the update_colors method we wrote in RoundedTile
        tile.update_colors(tile_bg, border_col)

        # 5. Update the Icon (Redraws the bulb)
        icon = self.bulb_widgets["icon"]
        icon.set_state(is_on, tile_bg)

    def toggle_light(self):
        """Toggles backend state and refreshes UI instantly."""
        # 1. Toggle in Backend
        if hasattr(self.c, 'backend'):
            self.c.backend.toggle_light()
        
        # 2. Update ONLY the bulb visuals (Fast & Smooth)
        self.update_bulb_visuals()


    def show_brightness(self):
        self.clear_content("Display")
        
        center_f = tk.Frame(self.content, bg=CLR_TRAY)
        center_f.pack(expand=True)
        
        # Header
        tk.Label(center_f, text="Display Brightness", fg="#37474F", bg=CLR_TRAY, font=("Arial", 16, "bold")).pack(pady=(0, 25))
        
        current_val = self.c.backend.get_brightness()
        def on_change(val): self.c.backend.set_brightness(val)
        
        # NEW Modern Widget
        mb = ModernBrightness(center_f, width=140, height=320, initial=current_val, command=on_change, bg_color=CLR_TRAY)
        mb.pack()

    # ... (Keep show_wifi, show_power, show_sensors, show_about, etc. unchanged) ...
    def show_wifi(self):
        self.clear_content("WiFi Networks")
        
        # --- HEADER ---
        ctrl_bar = tk.Frame(self.content, bg=CLR_TRAY)
        ctrl_bar.pack(fill="x", padx=10, pady=(0, 10))
        
        # 1. Status Label (Restored)
        self.lbl_status = tk.Label(ctrl_bar, text="Ready", font=("Arial", 11, "italic"), fg="#78909C", bg=CLR_TRAY)
        self.lbl_status.pack(side="left")
        
        btn_rescan = tk.Button(ctrl_bar, text="↻ Rescan", font=("Arial", 11, "bold"), 
                               bg="white", fg=CLR_PRIMARY, bd=0, padx=15, pady=8)
        btn_rescan.pack(side="right")
        
        # --- CONTAINER ---
        container = tk.Frame(self.content, bg=CLR_TRAY)
        container.pack(fill="both", expand=True, pady=5)
        
        # Canvas
        canvas = SmoothScroll(container, bg=CLR_TRAY, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)
        
        # Scroll Indicator
        scroll_bg = tk.Canvas(container, width=8, bg="#ECEFF1", highlightthickness=0)
        scroll_bg.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        thumb = scroll_bg.create_oval(1, 0, 7, 30, fill="#90A4AE", outline="")
        
        self.wifi_list_frame = tk.Frame(canvas, bg=CLR_TRAY)
        canvas_window = canvas.create_window((0, 0), window=self.wifi_list_frame, anchor="nw")
        
        # Logic
        def update_scrollbar():
            try:
                first, last = canvas.yview()
                h = scroll_bg.winfo_height()
                thumb_h = max(30, h * (last - first))
                thumb_y = h * first
                scroll_bg.coords(thumb, 1, thumb_y, 7, thumb_y + thumb_h)
            except: pass

        def on_scroll_move(e): update_scrollbar()
        canvas.bind("<B1-Motion>", on_scroll_move, add="+")

        def on_config(e): canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind("<Configure>", on_config)
        
        def update_region(e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            update_scrollbar()
        self.wifi_list_frame.bind("<Configure>", update_region)
        
        # --- POPULATE ---
        def populate_wifi(networks):
            try:
                if not self.wifi_list_frame.winfo_exists(): return
            except: return
            
            for w in self.wifi_list_frame.winfo_children(): w.destroy()
            
            # Update Label
            self.lbl_status.config(text=f"Found {len(networks)} networks")
            
            if not networks:
                tk.Label(self.wifi_list_frame, text="No networks found", bg=CLR_TRAY, fg="#B0BEC5").pack(pady=20)
                return

            for net in networks:
                ssid = net["ssid"]
                signal = net["signal"]
                is_connected = net.get("connected", False)
                
                r = tk.Frame(self.wifi_list_frame, bg="white", pady=12, padx=10, highlightbackground="#E0E0E0", highlightthickness=1)
                r.pack(fill="x", pady=5, padx=5)
                
                # Bind Scroll
                r.bind("<Button-1>", canvas.on_start)
                r.bind("<B1-Motion>", canvas.on_drag)
                r.bind("<ButtonRelease-1>", canvas.on_release)

                # --- ICONS ---
                if is_connected:
                    # Connected Checkmark
                    lbl = tk.Label(r, text="✓", font=("Arial", 24, "bold"), fg="#4CAF50", bg="white" , cursor="none")
                    lbl.pack(side="right", padx=10)
                    r.config(highlightbackground="#4CAF50", highlightthickness=2)
                    lbl.bind("<Button-1>", canvas.on_start); lbl.bind("<B1-Motion>", canvas.on_drag); lbl.bind("<ButtonRelease-1>", canvas.on_release)
                else:
                    # NEW: Sleek "Add/Link" Button (Blue Plus Circle)
                    # We use a Label acting as a button for cleaner look
                    btn = tk.Label(r, text="+", font=("Arial", 18, "bold"), fg=CLR_PRIMARY, bg="white", cursor="none")
                    btn.pack(side="right", padx=15)
                    
                    # Bind Click (Connect) - Stops propagation so it doesn't trigger scroll
                    btn.bind("<Button-1>", lambda e, s=ssid: WifiPasswordPopup(self.winfo_toplevel(), s, self.trigger_connect))
                
                # Signal Text
                lbl_sig = tk.Label(r, text=f"{signal}%", font=("Arial", 11), fg="#90A4AE", bg="white")
                lbl_sig.pack(side="right", padx=10)
                lbl_sig.bind("<Button-1>", canvas.on_start); lbl_sig.bind("<B1-Motion>", canvas.on_drag); lbl_sig.bind("<ButtonRelease-1>", canvas.on_release)

                # Marquee Name
                mq = MarqueeLabel(r, text=ssid, width=150, height=35, bg="white")
                mq.pack(side="left", padx=5)
                mq.bind("<Button-1>", canvas.on_start)
                mq.bind("<B1-Motion>", canvas.on_drag)
                mq.bind("<ButtonRelease-1>", canvas.on_release)

            self.wifi_list_frame.update_idletasks()
            update_region()

        def run_scan():
            try:
                if not self.winfo_exists(): return
                self.lbl_status.config(text="Scanning...")
                btn_rescan.config(state="disabled", bg="#ECEFF1", text="Scanning...")
                for w in self.wifi_list_frame.winfo_children(): w.destroy()
            except: return
            nets = self.c.backend.get_wifi_networks()
            def update_ui():
                try:
                    if not self.winfo_exists(): return
                    populate_wifi(nets)
                    btn_rescan.config(state="normal", bg="white", text="↻ Rescan")
                except: return
            self.after(0, update_ui)

        btn_rescan.config(command=lambda: threading.Thread(target=run_scan, daemon=True).start())
        threading.Thread(target=run_scan, daemon=True).start()
        
            
    def show_power(self):
        self.clear_content("Power Options")
        bf = tk.Frame(self.content, bg=CLR_TRAY); bf.pack(pady=20)
        def mk_pwr(icon, txt):
            f = tk.Frame(bf, bg="white", width=260, height=60, highlightbackground="#E0E0E0", highlightthickness=1)
            f.pack_propagate(False); f.pack(pady=8)
            l_i = tk.Label(f, text=icon, font=("Arial", 22), fg="#546E7A", bg="white")
            l_i.pack(side="left", padx=20)
            l_t = tk.Label(f, text=txt, font=("Arial", 12, "bold"), fg="#37474F", bg="white")
            l_t.pack(side="left")
            for w in [f, l_i, l_t]: w.bind("<Button-1>", lambda e: self.close()) 
        mk_pwr("☾", "Sleep Mode"); mk_pwr("⟳", "Restart System"); mk_pwr("⏻", "Power Off")


    
    def show_sensors(self):
        self.clear_content("Sensor Readings")
        
        # 1. Setup Canvas
        container = tk.Frame(self.content, bg=CLR_TRAY)
        container.pack(fill="both", expand=True)
        
        canvas = SmoothScroll(container, bg=CLR_TRAY, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)
        
        inner = tk.Frame(canvas, bg=CLR_TRAY)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")
        
        # Resizing
        def on_conf(e): canvas.itemconfig(win, width=e.width)
        canvas.bind("<Configure>", on_conf)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # --- SECTION 1: Enclosure Environment ---
        lbl_env = tk.Label(inner, text="Enclosure Environment", font=("Arial", 12, "bold"), fg=CLR_PRIMARY, bg=CLR_TRAY)
        lbl_env.pack(anchor="w", pady=(10, 5), padx=20)
        
        grid1 = tk.Frame(inner, bg=CLR_TRAY)
        grid1.pack(fill="x", padx=10)

        def mk_card(parent, title, unit, icon, col, row, color="#546E7A"):
            card = tk.Frame(parent, bg="white", padx=15, pady=15, highlightbackground="#E0E0E0", highlightthickness=1)
            card.grid(row=row, column=col, sticky="ew", padx=5, pady=5)
            parent.columnconfigure(col, weight=1)
            
            tk.Label(card, text=icon, font=("Arial", 20), fg=color, bg="white").pack(anchor="nw")
            tk.Label(card, text=title, font=("Arial", 10), fg="#90A4AE", bg="white").pack(anchor="nw", pady=(5,0))
            
            lbl_val = tk.Label(card, text="--", font=("Arial", 18, "bold"), fg="#37474F", bg="white")
            lbl_val.pack(anchor="nw")
            
            tk.Label(card, text=unit, font=("Arial", 14, "bold"), fg="#546E7A", bg="white").pack(anchor="ne")
            return lbl_val

        # CHANGED: Titles updated here
        lbl_bme_temp = mk_card(grid1, "Enclosure Temp", "°C", "🌡", 0, 0, "#FF7043")
        lbl_bme_hum  = mk_card(grid1, "Humidity", "%",  "💧", 1, 0, "#42A5F5")
        lbl_adt_temp = mk_card(grid1, "Bed Temp", "°C", "📟", 0, 1, "#FFA726")
        lbl_bme_pres = mk_card(grid1, "Pressure", "hPa", "⏲", 1, 1, "#78909C")

        # --- SECTION 2: System Status ---
        div = tk.Frame(inner, bg="#E0E0E0", height=1)
        div.pack(fill="x", pady=20, padx=20)
        
        # CHANGED: Removed "(Raspberry Pi)" from text
        lbl_sys = tk.Label(inner, text="System Status", font=("Arial", 12, "bold"), fg=CLR_PRIMARY, bg=CLR_TRAY)
        lbl_sys.pack(anchor="w", pady=(0, 5), padx=20)
        
        grid2 = tk.Frame(inner, bg=CLR_TRAY)
        grid2.pack(fill="x", padx=10)
        
        lbl_cpu_temp = mk_card(grid2, "CPU Temp", "°C", "🖥", 0, 0, "#EF5350")
        lbl_cpu_load = mk_card(grid2, "CPU Load", "%", "⚡", 1, 0, "#66BB6A")
        

        # Apply Scroll Binding
        canvas.bind_recursive(inner)

        # Update Logic
        def update_values():
            if not inner.winfo_exists(): return
            try:
                if hasattr(self.c, 'backend'): data = self.c.backend.state.get("sensor_data", {})
                else: data = self.c.state.get("sensor_data", {})

                lbl_cpu_temp.config(text=f"{data.get('cpu_temp', 0)}")
                lbl_cpu_load.config(text=f"{data.get('cpu_load', 0)}")
        
                
                lbl_bme_temp.config(text=f"{data.get('bme_temp', 0):.1f}")
                lbl_bme_hum.config(text=f"{data.get('bme_hum', 0):.0f}")
                lbl_bme_pres.config(text=f"{data.get('bme_press', 0)}")
                lbl_adt_temp.config(text=f"{data.get('adt_temp', 0):.1f}")
            except: pass
            self.after(1000, update_values)

        inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        update_values()
    
    
    def trigger_connect(self, ssid, password):
        self.clear_content("Connecting...")
        tk.Label(self.content, text=f"Joining {ssid}...", font=("Arial", 12), fg=CLR_PRIMARY, bg=CLR_TRAY).pack(pady=30)
        def run_connect():
            success = self.c.backend.connect_wifi(ssid, password)
            self.after(0, lambda: self.show_connection_result(success, ssid))
        threading.Thread(target=run_connect, daemon=True).start()

    def show_connection_result(self, success, ssid):
        self.clear_content("Connection Status")
        color = CLR_SUCCESS if success else CLR_DANGER
        msg = f"Connected to {ssid}" if success else "Connection Failed"
        icon = "✓" if success else "⚠"
        tk.Label(self.content, text=icon, font=("Arial", 40), fg=color, bg=CLR_TRAY).pack(pady=(40, 10))
        tk.Label(self.content, text=msg, font=("Arial", 14, "bold"), fg=color, bg=CLR_TRAY).pack()
        self.after(2000, self.show_main_menu)

    def clear_content(self, title):
        for w in self.content.winfo_children(): w.destroy()
        
        nav = tk.Frame(self.content, bg=CLR_TRAY)
        nav.pack(fill="x", pady=(0, 20))
        
        # Frame cursor
        btn_frame = tk.Frame(nav, bg=CLR_TRAY, cursor="none") 
        btn_frame.pack(side="left")
        
        # Label cursor (This was likely missing)
        btn_lbl = tk.Label(btn_frame, text="❮ Back", font=("Arial", 12, "bold"), fg=CLR_PRIMARY, bg=CLR_TRAY, cursor="none")
        btn_lbl.pack(padx=5, pady=10)
        
        go_back = lambda e=None: self.show_main_menu()
        for w in [btn_frame, btn_lbl]: 
            w.bind("<Button-1>", go_back)
            
        tk.Label(nav, text=title, font=("Arial", 14, "bold"), fg=CLR_TRAY_TEXT, bg=CLR_TRAY).pack(side="right")
# --- FLOATING BUTTON (Independent Toplevel) ---
class FloatingSettingsButton(tk.Toplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.c = controller
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        w, h = 50, 50
        screen_w = self.winfo_screenwidth()
        self.geometry(f"{w}x{h}+{screen_w - w - 15}+15")
        self.config(bg=CLR_BG, cursor="none")
        
        self.cv = tk.Canvas(self, width=w, height=h, bg=CLR_BG, highlightthickness=0)
        self.cv.pack()
        
        self.circle = self.cv.create_oval(2, 2, 48, 48, fill="white", outline="#CFD8DC", width=2, tags="btn")
        self.icon_id = self.cv.create_text(25, 26, text="⚙", font=("Arial", 28), fill="#455A64", tags="btn")
        
        self.cv.tag_bind("btn", "<Button-1>", self.open_tray)
        self.lift_timer()

    def open_tray(self, e):
        # Pass the MAIN WINDOW (master) as the parent for the Frame
        SettingsTray(self.master, self.c, self)

    def lift_timer(self):
        self.lift()
        self.after(2000, self.lift_timer)

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
    def __init__(self, parent, title, header, message, width=420, height=240 ,color=CLR_DANGER ):
        super().__init__(parent); self.result = False
        cw, ch = width, height; cx = parent.winfo_width() / 2; cy = parent.winfo_height() / 2
        self.cv.create_rectangle(cx - cw/2 + 6, cy - ch/2 + 6, cx + cw/2 + 6, cy + ch/2 + 6, fill=CLR_SHADOW, outline="")
        self.cv.create_rectangle(cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2, fill="white", outline=color, width=2)
        self.f = tk.Frame(self.cv, bg="white", width=cw-4, height=ch-4); self.f.pack_propagate(False); self.cv.create_window(cx, cy, window=self.f)
        head_box = tk.Frame(self.f, bg="white"); head_box.pack(pady=(15, 5))
        tk.Label(head_box, text=title, font=("Arial", 40), fg=color, bg="white").pack(side="top")
        tk.Label(head_box, text=header, font=("Arial", 18, "bold"), fg=color, bg="white").pack(side="top")
        tk.Frame(self.f, height=2, bg=color, width=300).pack(pady=5)
        tk.Label(self.f, text=message, font=("Arial", 12), bg="white", fg="#444", wraplength=cw-40).pack(pady=5)
        btn_f = tk.Frame(self.f, bg="white"); btn_f.pack(side="bottom", pady=20)
        RoundedButton(btn_f, text="CANCEL", command=self.on_cancel, width=120, height=50, bg_color="#9E9E9E", hover_color="#757575").pack(side="left", padx=15)
        RoundedButton(btn_f, text="CONFIRM", command=self.on_confirm, width=120, height=50, bg_color=color).pack(side="left", padx=15)
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
        card = ShadowCard(self, bg=CLR_CARD)
        card.place(relx=0.5, rely=0.5, anchor="center", width=500, height=300)
        tk.Label(card.inner, text="Liquid Handler v1.4", font=("Arial", 22, "bold"), bg=CLR_CARD).pack(pady=(20, 25))
        RoundedButton(card.inner, text="CALIBRATION", width=250, height=55, bg_color="#FF9800", hover_color=CLR_WARNING_HOVER, command=lambda: controller.show_frame("Calibrate")).pack(pady=10)
        RoundedButton(card.inner, text="PROTOCOLS", width=250, height=55, bg_color=CLR_PRIMARY, hover_color=CLR_PRIMARY_HOVER, command=lambda: controller.show_frame("ProtocolList")).pack(pady=10)

class Calibrate(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        header = tk.Frame(self, bg=CLR_BG, pady=5); header.pack(fill="x", pady=(20, 5)) 
        tk.Label(header, text="SYSTEM CALIBRATION", font=("Arial", 16, "bold"), bg=CLR_BG, fg=CLR_PRIMARY).pack(side="left", padx=20)
        main = tk.Frame(self, bg=CLR_BG); main.pack(fill="both", expand=True, padx=10, pady=5)
        main.grid_columnconfigure(0, weight=3); main.grid_columnconfigure(1, weight=2); main.grid_columnconfigure(2, weight=1) 
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
        z_outer = tk.Frame(main, bg=CLR_BG); z_outer.grid(row=0, column=1, sticky="nsew", padx=5)
        self.z_card = ShadowCard(z_outer, bg=CLR_CARD, border_color=CLR_WARNING); self.z_card.pack(fill="both", expand=True)
        tk.Label(self.z_card.inner, text="Z AXIS", font=("Arial", 14, "bold"), bg=CLR_CARD, fg=CLR_WARNING_DARK).pack(pady=(10, 5))
        z_grid = tk.Frame(self.z_card.inner, bg=CLR_CARD); z_grid.pack()
        def mk_z_btn(parent, txt, axis, d): 
            b = RoundedButton(parent, text=txt, command=None, width=90, height=75, bg_color=CLR_INACTIVE, hover_color="#B0BEC5", fg_color="black")
            b.command = lambda: self.move(axis, d, b); return b
        tk.Label(z_grid, text="Z1", font=("Arial", 12, "bold"), bg=CLR_CARD).grid(row=0, column=0, pady=(0, 15), sticky="s")
        mk_z_btn(z_grid, "▲", "Z1", 1).grid(row=1, column=0, pady=(0, 10), padx=15)
        mk_z_btn(z_grid, "▼", "Z1", -1).grid(row=2, column=0, pady=10, padx=15)
        tk.Label(z_grid, text="Z2", font=("Arial", 12, "bold"), bg=CLR_CARD).grid(row=0, column=1, pady=(0, 15), sticky="s")
        mk_z_btn(z_grid, "▲", "Z2", 1).grid(row=1, column=1, pady=(0, 10), padx=15)
        mk_z_btn(z_grid, "▼", "Z2", -1).grid(row=2, column=1, pady=10, padx=15)
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
            b = RoundedButton(step_f, text=str(val), command=lambda v=val: self.set_step(v), width=50, height=50, bg_color=CLR_INACTIVE, hover_color="#B0BEC5", fg_color="black")
            b.pack(side="left", padx=3); self.step_btns[val] = b
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
        if self.c.backend.state["calibration_active"]:
            self.lbl_x.config(text="X : 0.0"); self.lbl_y.config(text="Y : 0.0"); self.lbl_z1.config(text="Z1: 0.0"); self.lbl_z2.config(text="Z2: 0.0")
            for k in self.c.offsets: self.c.offsets[k].set(0.0)
            return
        self.c.backend.set_calibration_mode(True, "User")
        self.c.backend.sync_with_server() 
        self.c.backend.ui_send_gcode("T00")
        self.c.update() 
        self.lbl_x.config(text="X : 0.0"); self.lbl_y.config(text="Y : 0.0"); self.lbl_z1.config(text="Z1: 0.0"); self.lbl_z2.config(text="Z2: 0.0")
        for k in self.c.offsets: self.c.offsets[k].set(0.0)

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
        self.float_animation(target_lbl, txt_sign)
        self.animate_counter(target_lbl, axis_prefix, current, new_val)
        self.c.backend.ui_send_gcode(f"C dx={dx}, dy={dy}, dz1={dz1}, dz2={dz2}")

    def float_animation(self, target_widget, text):
        lbl = tk.Label(self.info_box, text=text, fg=CLR_SUCCESS, bg=CLR_INFO_BOX, font=("Arial", 14, "bold"))
        x = target_widget.winfo_x() + 110; y = target_widget.winfo_y()
        lbl.place(x=x, y=y)
        def anim_loop(step=0):
            if step < 10: lbl.place(y=y - step*2); self.after(30, lambda: anim_loop(step+1))
            else: lbl.destroy() 
        anim_loop()

    def animate_counter(self, lbl, prefix, start, end, step_count=10):
        diff = end - start; step_size = diff / step_count
        def update_step(i):
            if i <= step_count:
                current = start + (step_size * i); lbl.config(text=f"{prefix}{current:.1f}", fg=CLR_SUCCESS) 
                self.after(15, lambda: update_step(i+1))
            else: lbl.config(text=f"{prefix}{end:.1f}", fg="#333")
        update_step(1)

    def confirm_exit(self):
        c = CustomConfirmPopup(self.c, "?", "EXIT CALIBRATION", "Unsaved changes will be lost.")
        if c.result:
            self.c.backend.set_calibration_mode(False, None)
            self.c.show_frame("Home")

    def confirm_save(self):
        c = CustomConfirmPopup(self.c, "?", "SAVE OFFSETS", "Update calibration settings?")
        if c.result:
            self.update() 
            self.c.backend.ui_send_gcode("OK_C")
            popup = CustomPopup(self.c, "Saved", "CALIBRATION COMPLETED", "Offsets saved.\nYou may now run a protocol.", CLR_SUCCESS, "✔", height=300, icon_size=38)
            self.wait_window(popup)
            self.c.show_frame("Home")

# --- UPDATE: FOR Fan Mode SEGMENTED TOGGLE SWITCH (Auto | Manual) ---
class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, options=["Auto", "Manual"], command=None, width=160, height=40):
        super().__init__(parent, width=width, height=height, bg="white", highlightthickness=0)
        self.options = options
        self.command = command
        self.w, self.h = width, height
        self.selected_idx = 0 # 0 = Left, 1 = Right
        
        self.draw()
        self.bind("<Button-1>", self.toggle)

    def set_value(self, val):
        if val in self.options:
            self.selected_idx = self.options.index(val)
            self.draw()

    def get_value(self):
        return self.options[self.selected_idx]

    def toggle(self, event=None):
        self.selected_idx = 1 - self.selected_idx
        self.draw()
        if self.command: self.command(self.get_value())

    def draw(self):
        self.delete("all")
        # Background Pill (Gray)
        self.create_rectangle(2, 2, self.w-2, self.h-2, fill="#ECEFF1", outline="#CFD8DC", width=1, tags="bg")
        
        # Active Pill (Blue) - Moves Left/Right
        padding = 4
        half_w = (self.w / 2) - padding
        if self.selected_idx == 0:
            x1, x2 = padding, (self.w/2) - (padding/2)
            col = CLR_SUCCESS # Green for Auto
        else:
            x1, x2 = (self.w/2) + (padding/2), self.w - padding
            col = CLR_PRIMARY # Blue for Manual
            
        self.create_rectangle(x1, padding, x2, self.h-padding, fill=col, outline="", tags="active")
        
        # Text Labels
        # Left Text
        fg0 = "white" if self.selected_idx == 0 else "#90A4AE"
        self.create_text(self.w/4, self.h/2, text=self.options[0], font=("Arial", 11, "bold"), fill=fg0)
        
        # Right Text
        fg1 = "white" if self.selected_idx == 1 else "#90A4AE"
        self.create_text(self.w*0.75, self.h/2, text=self.options[1], font=("Arial", 11, "bold"), fill=fg1)

# --- UPDAtE: FAN SLIDER (Supports Auto/Read-Only) ---
class AnimatedFanSlider(tk.Canvas):
    def __init__(self, parent, width=300, height=50, min_val=0, max_val=100, command=None, bg_color=CLR_BG):
        super().__init__(parent, width=width, height=height, bg=bg_color, highlightthickness=0)
        self.w, self.h = width, height
        self.min_val, self.max_val = min_val, max_val
        self.value = 0
        self.command = command
        self.angle = 0
        self.dragging = False
        self.read_only = False # New flag
        self.label_text = "FAN SPEED"
        
        self.draw()
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.animate()

    def set_value(self, val):
        self.value = max(self.min_val, min(self.max_val, val))
        self.draw()
        
    def set_read_only(self, is_read_only):
        self.read_only = is_read_only
        self.label_text = "FAN (AUTO)" if is_read_only else "FAN SPEED"
        self.draw()

    def draw(self):
        self.delete("all")
        r = 25 
        
        # 1. Container Background
        self.create_rounded_rect(0, 0, self.w-1, self.h-1, r, fill="white", outline="black", width=1)
        
        # 2. Active Fill
        # Auto mode uses a slightly different color (Greenish) to indicate system control, or keep blue.
        # Let's keep Blue for consistency, maybe lighter if Auto.
        fill_col = "#C8E6C9" if self.read_only else "#E3F2FD" 
        
        max_fill_w = self.w - 2
        current_fill_w = (self.value / 100) * max_fill_w
        
        if current_fill_w > 0:
            self.create_rounded_rect(1, 1, 1 + current_fill_w, self.h-1, r, fill=fill_col, outline="")
            
        # 3. Fan Icon
        icon_col = CLR_SUCCESS if self.read_only else CLR_PRIMARY
        self.draw_fan(30, self.h/2, 18, icon_col)
        
        # 4. Percentage Text
        text_col = CLR_SUCCESS if self.read_only else CLR_PRIMARY
        self.create_text(self.w - 40, self.h/2, text=f"{int(self.value)}%", font=("Arial", 14, "bold"), fill=text_col)
        
        # 5. Label
        self.create_text(self.w/2, self.h/2, text=self.label_text, font=("Arial", 9, "bold"), fill="#90A4AE")

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def draw_fan(self, cx, cy, r, color):
        for i in range(0, 360, 90):
            rad = math.radians(self.angle + i)
            x2 = cx + (r * math.cos(rad))
            y2 = cy + (r * math.sin(rad))
            self.create_line(cx, cy, x2, y2, fill=color, width=3, capstyle="round")
        self.create_oval(cx-4, cy-4, cx+4, cy+4, fill="white", outline=color)

    def on_click(self, e):
        if self.read_only: return # Ignore clicks in Auto mode
        self.dragging = True; self.update_from_event(e)

    def on_drag(self, e):
        if self.read_only: return
        if self.dragging: self.update_from_event(e)

    def on_release(self, e):
        if self.read_only: return
        self.dragging = False; 
        if self.command: self.command(self.value)

    def update_from_event(self, e):
        pct = max(0, min(1, e.x / self.w)); self.value = int(pct * 100); self.draw()

    def animate(self):
        if self.value > 0:
            self.angle = (self.angle + (5 + self.value*0.5)) % 360
            self.draw()
        self.after(50, self.animate)

 # --- THERMAL SETUP POPUP (With Borders) ---

# --- UPDAtE: SELECTABLE BUTTON (Inherits RoundedButton ) ---
class SelectableButton(RoundedButton):
    def __init__(self, parent, text, width=120, height=50, font=("Arial", 12, "bold"), 
                 bg_color="#FAFAFA", fg_color="black", border_color="#E0E0E0", border_width=1, command=None):
        
        # 1. Call the Original RoundedButton __init__ correctly
        # Signature: parent, text, command, width, height, radius, bg, hover, fg, font
        super().__init__(parent, text, command, width=width, height=height, 
                         bg_color=bg_color, hover_color=bg_color, # Disable hover shift for inputs
                         fg_color=fg_color, font=font)
        
        # 2. Add Border Logic (Post-Init)
        self.border_color = border_color
        self.border_width = border_width
        
        # Apply the border to the rectangle created by the parent class
        self.itemconfig(self.rect_id, outline=self.border_color, width=self.border_width)

    def set_border(self, color, width):
        """Updates the border dynamically."""
        self.border_color = color
        self.border_width = width
        self.itemconfig(self.rect_id, outline=color, width=width)

    def set_color(self, bg, fg):
        """Overrides parent set_color to handle text color (fg) too."""
        self.bg_color = bg
        self.hover_color = bg # Keep hover same as bg for inputs
        self.itemconfig(self.rect_id, fill=bg)
        self.itemconfig(self.text_id, fill=fg)

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

# --- UPDATED: ADDED PROTOCOL SETUP POPUP  ----
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
        
        def on_click(e):
            dist = abs(e.y_root - self.scroll_frame_widget.scroll_start_y)
            if dist < 10: self.select_file(filename, card, inner, icon_lbl, name_lbl, sel_lbl, del_btn)

        for w in [card, inner, icon_lbl, name_lbl]: 
            w.bind("<ButtonPress-1>", self.scroll_frame_widget._start_scroll)
            w.bind("<B1-Motion>", self.scroll_frame_widget._do_scroll)
            w.bind("<ButtonRelease-1>", on_click)

    def delete_file(self, filename):
        c = CustomConfirmPopup(self.c, "🗑️", "DELETE FILE", f"Permanently delete\n{filename}?")
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
        if self.c.backend.state["calibration_active"]:
            popup = CustomPopup(self.c, "Locked", "SYSTEM BUSY", "Cannot run protocol while calibrating.", CLR_WARNING, "⚠")
            self.c.wait_window(popup); return
        if not self.c.backend.state.get("is_calibrated", False):
            popup = CustomPopup(self.c, "Required", "CALIBRATION NEEDED", "You must calibrate the system before running a protocol.", CLR_DANGER, "🛑")
            self.c.wait_window(popup); return
        # --- 2. LID SAFETY CHECK (NEW) ---
        is_lid_open = self.c.backend.state.get("lid_open", False)
        
        if is_lid_open:
            # Define what happens if they click "YES"
            def run_anyway():
                self.c.backend.ui_load_and_run(filename)
                self.show_run_screen()
          
            # Show the Confirmation Popup
            # Arguments: parent, title, message, yes_callback
            c=CustomConfirmPopup(self.c, 
                         "⚠️", 
                         "LID OPEN",
                         "The enclosure lid is open.\nDo you want to start anyway?",420,280,CLR_WARNING)
            
            if not c.result:
                return
  
        # 3. THERMAL SETUP POPUP (NEW)
        setup = ProtocolSetupPopup(self.c, self.c.backend)
        if not setup.result: return # User cancelled  
        
        if not self.selected_card: return
        fname = self.c.selected_file.get(); self.c.backend.ui_load_and_run(fname); self.c.show_frame("Running")  

# --- UPDATED: ADDED FAN + MARQUEE TEXT + SENOSOR STAUS BAR + COLOR PROGRESS BAR  ---
class Running(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        
        # --- HEADER ---
        header = tk.Frame(self, bg=CLR_BG); header.pack(side="top", fill="x", pady=(15, 5), padx=30)
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=3)
        header.columnconfigure(2, weight=1)
        
        # LEFT: Filename & Source
        left_box = tk.Frame(header, bg=CLR_BG); left_box.grid(row=0, column=0, sticky="w")
        self.lbl_filename = MarqueeLabel(left_box, text="--", width=250, height=30, 
                                         font=("Arial", 18, "bold"), fg=CLR_PRIMARY, bg=CLR_BG)
        self.lbl_filename.pack(anchor="w")
        self.source_lbl = tk.Label(left_box, text="Source: --", font=("Arial", 11), fg="#90A4AE", bg=CLR_BG, anchor="w")
        self.source_lbl.pack(anchor="w", pady=(2, 0))
        
        # CENTER: SENSOR DASHBOARD
        dash = tk.Frame(header, bg="white", padx=10, pady=5, highlightbackground="#CFD8DC", highlightthickness=1)
        dash.grid(row=0, column=1) 
        
        def mk_readout(parent, title, val_id, unit, col):
            f = tk.Frame(parent, bg="white"); f.pack(side="left", padx=8)
            tk.Label(f, text=title, font=("Arial", 7, "bold"), fg="#90A4AE", bg="white").pack(anchor="n")
            l = tk.Label(f, text=f"-- {unit}", font=("Arial", 12, "bold"), fg=col, bg="white")
            l.pack(anchor="n")
            setattr(self, val_id, l)
            
        mk_readout(dash, "TARGET", "lbl_dash_target", "°C", CLR_PRIMARY)
        mk_readout(dash, "ENCL.", "lbl_dash_env", "°C", "#546E7A")
        mk_readout(dash, "BED", "lbl_dash_bed", "°C", "#FFA726")
        mk_readout(dash, "HUMID", "lbl_dash_hum", "%", "#42A5F5")
        mk_readout(dash, "PRESS", "lbl_dash_pres", "hPa", "#78909C")
        mk_readout(dash, "CPU", "lbl_dash_cpu", "°C", "#EF5350")

        # RIGHT: GEAR
        right_box = tk.Frame(header, bg=CLR_BG); right_box.grid(row=0, column=2, sticky="e")
        tk.Label(right_box, text="⚙️", font=("Arial", 24), bg=CLR_BG, fg="#B0BEC5").pack()

        # --- MAIN CARD ---
        card_outer = ShadowCard(self, bg="white"); card_outer.pack(fill="both", expand=True, padx=40, pady=(10, 10))
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

        # --- FOOTER ---
        footer = tk.Frame(self, bg=CLR_BG, height=80); footer.pack(side="bottom", fill="x", pady=(5, 20), padx=40)
        footer.columnconfigure(0, weight=0); footer.columnconfigure(1, weight=1); footer.columnconfigure(2, weight=0)
        
        self.btn_pause = RoundedButton(footer, text="PAUSE", command=lambda: self.c.backend.ui_pause_resume(), width=130, height=55, bg_color=CLR_WARNING, hover_color=CLR_WARNING_HOVER)
        self.btn_pause.grid(row=0, column=0, sticky="w")
        
        self.f_center = tk.Frame(footer, bg=CLR_BG); self.f_center.grid(row=0, column=1)
        
        # --- FAN SLIDER & HINT ---
        # Hint Label (Visible only in Manual)
        self.lbl_fan_hint = tk.Label(self.f_center, text="← Drag to Adjust →", font=("Arial", 8, "bold"), fg="#90A4AE", bg=CLR_BG)
        self.lbl_fan_hint.pack(pady=(0, 2)) # Small padding bottom
        
        self.fan_slider = AnimatedFanSlider(self.f_center, width=320, height=55, bg_color=CLR_BG, command=self.on_fan_change)
        self.fan_slider.pack()
        
        RoundedButton(footer, text="STOP", command=self.cancel_run, width=130, height=55, bg_color=CLR_DANGER, hover_color=CLR_DANGER_HOVER).grid(row=0, column=2, sticky="e")

    def on_fan_change(self, val): self.c.backend.state["fan_manual_val"] = int(val)
    def cancel_run(self):
        confirm = CustomConfirmPopup(self.c, "⏹️", "STOP PROTOCOL", "Are you sure you want to abort?")
        if confirm.result: self.c.backend.ui_stop()

    def update_view(self, state):
        self.lbl_filename.set_text(self.c.selected_file.get())
        
        progress = state["progress"]; status = state["status"]; cmd_text = state["current_line"]; desc_text = state.get("current_desc", "")
        self.source_lbl.config(text=f"Source: {state.get('started_by','-')}")
        self.percent_lbl.config(text=f"{int(progress)}%"); self.prog.set_progress(progress); self.time_lbl.config(text=f"Est: {state.get('est','--:--')}")
        
        is_paused = "Paused" in status
        is_error = "Error" in status or "Stopped" in status
        
        self.spinner.set_paused(is_paused)
        
        if is_error:
            self.status_badge.config(text=status.upper(), fg=CLR_DANGER, bg="#FFEBEE")
            self.cmd_lbl.config(text=status, fg=CLR_DANGER); self.desc_lbl.config(text="Operation Halted", fg="#B71C1C")
            self.percent_lbl.config(fg=CLR_DANGER); self.prog.set_color(CLR_DANGER); self.btn_pause.set_color("#CFD8DC", "#CFD8DC")
        elif is_paused:
            reason = state.get('pause_reason', 'UNKNOWN').upper()
            self.status_badge.config(text=f"● PAUSED ({reason})", fg="#E65100", bg="#FFF3E0")
            self.cmd_lbl.config(text=f"PAUSED ({reason})", fg="#E65100"); self.desc_lbl.config(text="System waiting for resume...", fg="#BF360C")
            self.btn_pause.itemconfig(self.btn_pause.text_id, text="RESUME"); self.btn_pause.set_color(CLR_SUCCESS, CLR_SUCCESS_HOVER)
            self.percent_lbl.config(fg=CLR_WARNING); self.prog.set_color(CLR_WARNING)
        else:
            self.status_badge.config(text="● RUNNING", fg=CLR_SUCCESS, bg="#E8F5E9")
            self.cmd_lbl.config(text=cmd_text, fg="#263238"); self.desc_lbl.config(text=desc_text if desc_text else "Processing...", fg="#546E7A")
            self.btn_pause.itemconfig(self.btn_pause.text_id, text="PAUSE"); self.btn_pause.set_color(CLR_WARNING, CLR_WARNING_HOVER)
            self.percent_lbl.config(fg=CLR_PRIMARY); self.prog.set_color(CLR_PRIMARY)
        
        sens = state.get("sensor_data", {})
        self.lbl_dash_target.config(text=f"{state.get('target_temp',0)} °C")
        self.lbl_dash_env.config(text=f"{sens.get('bme_temp',0):.1f} °C")
        self.lbl_dash_bed.config(text=f"{sens.get('adt_temp',0):.1f} °C")
        self.lbl_dash_hum.config(text=f"{int(sens.get('bme_hum',0))} %")
        self.lbl_dash_pres.config(text=f"{int(sens.get('bme_press',0))} hPa")
        self.lbl_dash_cpu.config(text=f"{sens.get('cpu_temp',0)} °C")

        # --- FAN LOGIC (Updated to Show/Hide Hint) ---
        mode = state.get("fan_mode", "Manual")
        if mode == "Auto":
            self.fan_slider.set_read_only(True)
            self.fan_slider.set_value(state.get("fan_duty", 0))
            self.lbl_fan_hint.pack_forget() # HIDE Hint in Auto
        else:
            self.fan_slider.set_read_only(False)
            self.lbl_fan_hint.pack(before=self.fan_slider, pady=(0, 2)) # SHOW Hint in Manual     
            
                        
if __name__ == "__main__":
    app = KioskApp()
    app.mainloop()