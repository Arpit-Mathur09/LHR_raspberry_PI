import tkinter as tk
from gui.styles import * # Import all constants
import math
import os
# --- IMAGE IMPORTS & BLUR UTILITY ---
try:
    from PIL import Image, ImageTk, ImageGrab, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠️ PIL not found. Popups will have solid backgrounds.")

def get_blur_bg(root):
    """Captures the root window and applies a Gaussian blur."""
    if not HAS_PIL:
        return None
        
    try:
        root.update_idletasks()
        x = root.winfo_rootx()
        y = root.winfo_rooty()
        w = root.winfo_width()
        h = root.winfo_height()
        
        # Grab the bounding box of the app window
        img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
        img = img.filter(ImageFilter.GaussianBlur(radius=12))
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"⚠️ Could not generate blur background: {e}")
        return None
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
