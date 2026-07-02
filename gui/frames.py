import tkinter as tk
import threading # Required for async scanning
import subprocess
from gui.styles import *
from gui.widgets import * # Imports RoundedButton, etc.
from gui.popups import * # Imports CustomPopup, ProtocolSetupPopup, etc.
import os

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠️ PIL not found. Running without custom images.")
# ---------------------------
# --- CONFIGURATION ---
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
                            "Liquid Handler v1.5\nRunning on Raspberry Pi 4", 
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
        
        # Container Frame
        bf = tk.Frame(self.content, bg=CLR_TRAY)
        bf.pack(pady=20)

        # --- ACTION FUNCTIONS WITH POPUP ---
        def do_sleep():
            # Sleep usually doesn't need confirmation, but you can add it if you want.
            print("💤 Turning Screen Off...")
            subprocess.run(["xset", "-display", ":0", "dpms", "force", "off"])
            
        def do_restart():
            # 1. Ask for Confirmation
            c = CustomConfirmPopup(self.winfo_toplevel(), 
                                 "⚠️", 
                                 "RESTART SYSTEM",
                                 "Are you sure you want to\nreboot the robot?", 
                                 420, 280, CLR_WARNING)
            
            # 2. Check Result
            if c.result:
                print("⟳ Rebooting...")      
                subprocess.run(["sudo", "reboot"])
            
        def do_shutdown():
            # 1. Ask for Confirmation
            c = CustomConfirmPopup(self.winfo_toplevel(), 
                                 "⏻", 
                                 "POWER OFF",
                                 "Are you sure you want to\nshut down completely?", 
                                 420, 280, CLR_DANGER)
            
            # 2. Check Result
            if c.result:
                print("⏻ Shutting Down...")
                subprocess.run(["sudo", "shutdown", "now"])

        # --- BUTTON MAKER ---
        def mk_pwr(icon, txt, command):
            f = tk.Frame(bf, bg="white", width=260, height=60, 
                         highlightbackground="#E0E0E0", highlightthickness=1)
            f.pack_propagate(False)
            f.pack(pady=8)
            
            l_i = tk.Label(f, text=icon, font=("Arial", 22), fg="#546E7A", bg="white")
            l_i.pack(side="left", padx=20)
            
            l_t = tk.Label(f, text=txt, font=("Arial", 12, "bold"), fg="#37474F", bg="white")
            l_t.pack(side="left")
            
            # Simple bind: Just run the command. The command itself handles the popup now.
            for w in [f, l_i, l_t]: 
                w.bind("<Button-1>", lambda e: command())

        # --- CREATE BUTTONS ---
        mk_pwr("☾", "Sleep Mode", do_sleep)
        mk_pwr("⟳", "Restart System", do_restart)
        mk_pwr("⏻", "Power Off", do_shutdown)

    
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

class Home(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        
        # --- CENTRAL SHADOW CARD ---
        self.card = ShadowCard(self, bg="white")
        self.card.place(relx=0.5, rely=0.5, anchor="center", width=760, height=440)
        
        # Grid: Left (Menu) 35% | Right (Status) 65%
        self.card.inner.columnconfigure(0, weight=35) 
        self.card.inner.columnconfigure(1, weight=65)
        self.card.inner.rowconfigure(0, weight=1)

        # ==========================
        # LEFT PANEL: CONTROLS
        # ==========================
        left_bg = "#F8F9FA" 
        left_panel = tk.Frame(self.card.inner, bg=left_bg)
        left_panel.grid(row=0, column=0, sticky="nsew")
        
        # 1. Branding
        brand_frame = tk.Frame(left_panel, bg=left_bg)
        brand_frame.pack(anchor="center", pady=(40, 20))
        
        tk.Label(brand_frame, text="LIQUID HANDLER", font=("Segoe UI", 16, "bold"), fg=CLR_PRIMARY, bg=left_bg).pack()
        tk.Label(brand_frame, text="v1.5 System Ready", font=("Segoe UI", 10), fg="#90A4AE", bg=left_bg).pack(pady=(2,0))

        # 2. Buttons
        btn_container = tk.Frame(left_panel, bg=left_bg)
        btn_container.pack(expand=True)

        RoundedButton(btn_container, text="CALIBRATION", width=200, height=55, 
                      bg_color="#FF9800", hover_color="#F57C00", font=("Segoe UI", 11, "bold"),
                      command=self.on_calibrate_click).pack(pady=12)
                      
        RoundedButton(btn_container, text="PROTOCOLS", width=200, height=55, 
                      bg_color=CLR_PRIMARY, hover_color=CLR_PRIMARY_HOVER, font=("Segoe UI", 11, "bold"),
                      command=lambda: controller.show_frame("ProtocolList")).pack(pady=12)

        # 3. Status
        self.lbl_status = tk.Label(left_panel, text="● Remote Offline", font=("Segoe UI", 10, "bold"), fg=CLR_DANGER, bg=left_bg)
        self.lbl_status.pack(side="bottom", pady=30)

        # ==========================
        # RIGHT PANEL: MODULES
        # ==========================
        right_panel = tk.Frame(self.card.inner, bg="white", padx=40) # Increased side padding
        right_panel.grid(row=0, column=1, sticky="nsew")

        # Container to vertically center the stack
        stack = tk.Frame(right_panel, bg="white")
        stack.pack(expand=True, fill="x")

        # Header
        tk.Label(stack, text="HARDWARE CONFIGURATION", font=("Segoe UI", 11, "bold"), fg="#90A4AE", bg="white").pack(anchor="w", pady=(0, 20))

        # -- SLOT 1 --
        self.slot1 = self.create_pipette_row(stack, "L", "MOUNT 1 (Left)")
        self.slot1.pack(fill="x", pady=10) # Increased gap

        # -- SLOT 2 --
        self.slot2 = self.create_pipette_row(stack, "R", "MOUNT 2 (Right)")
        self.slot2.pack(fill="x", pady=10) # Increased gap

    def create_pipette_row(self, parent, icon_char, label_text):
        """Creates a SUBSTANTIAL, LARGE pipette card"""
        container = tk.Frame(parent, bg="#FAFAFA", highlightbackground="#ECEFF1", highlightthickness=1, padx=1, pady=1)
        
        # Increased inner padding for a bigger card feel
        inner = tk.Frame(container, bg="#FAFAFA", padx=20, pady=15) 
        inner.pack(fill="both", expand=True)
        
        # 1. Large Icon (Left)
        # Increased size to 55x55
        icon_cv = tk.Canvas(inner, width=55, height=55, bg="#FAFAFA", highlightthickness=0)
        icon_cv.pack(side="left", padx=(0, 20))
        icon_cv.create_oval(2, 2, 53, 53, fill="#ECEFF1", outline="")
        icon_cv.create_text(28, 28, text=icon_char, font=("Segoe UI", 20, "bold"), fill="#B0BEC5")
        
        # 2. Info Stack (Right)
        info = tk.Frame(inner, bg="#FAFAFA")
        info.pack(side="left", fill="both", expand=True)
        
        # Top Row: Label + Serial
        top_row = tk.Frame(info, bg="#FAFAFA")
        top_row.pack(fill="x")
        tk.Label(top_row, text=label_text, font=("Segoe UI", 10, "bold"), fg="#90A4AE", bg="#FAFAFA").pack(side="left")
        
        sn = tk.Label(top_row, text="--", font=("Consolas", 10), fg="#CFD8DC", bg="#FAFAFA")
        sn.pack(side="right")
        
        # Bottom Row: Marquee (Model)
        # Increased height and Font Size (16 bold)
        mq = MarqueeLabel(info, text="Empty", width=280, height=30, font=("Segoe UI", 16, "bold"), fg="#CFD8DC", bg="#FAFAFA")
        mq.pack(anchor="w", pady=(2,0))
        
        # Save refs
        container.marquee = mq
        container.lbl_sn = sn
        container.canvas = icon_cv
        container.inner = inner
        container.info = info
        container.top_row = top_row
        container.default_char = icon_char
        
        return container

    def update_view(self, state):
        pips = state.get("pipettes", {})
        
        self.update_slot(self.slot1, pips.get("left", {}))
        self.update_slot(self.slot2, pips.get("right", {}))
        
        # Connection Status
        if self.c.backend.server_connected:
            self.lbl_status.config(text="● Remote Connected", fg=CLR_SUCCESS)
        else:
            self.lbl_status.config(text="● Remote Disconnected", fg=CLR_DANGER)

    def update_slot(self, widget, data):
        found = data.get("found", False)
        
        if found:
            # ACTIVE STYLE
            bg_col = "white"
            border_col = CLR_SUCCESS
            
            icon_bg = "#E8F5E9"
            icon_fg = CLR_SUCCESS
            icon_char = "✔"
            
            text_model_col = CLR_PRIMARY
            text_sn_col = "#546E7A"
        else:
            # EMPTY STYLE
            bg_col = "#FAFAFA"
            border_col = "#ECEFF1"
            
            icon_bg = "#ECEFF1"
            icon_fg = "#B0BEC5"
            icon_char = widget.default_char
            
            text_model_col = "#CFD8DC"
            text_sn_col = "#CFD8DC"

        # Apply Colors
        if widget.cget("bg") != bg_col or widget.cget("highlightbackground") != border_col:
            widget.config(bg=bg_col, highlightbackground=border_col)
            widget.inner.config(bg=bg_col)
            widget.info.config(bg=bg_col)
            widget.top_row.config(bg=bg_col)
            
            for child in widget.top_row.winfo_children(): child.config(bg=bg_col)
            
            # Update Marquee
            widget.marquee.config(bg=bg_col)
            widget.marquee.itemconfig(widget.marquee.text_id, fill=text_model_col)

            # Update Icon
            widget.canvas.config(bg=bg_col)

        # Update Content
        model_name = data.get("model", "Empty Slot") if found else "Empty Slot"
        widget.marquee.set_text(model_name)
        
        sn_text = data.get("id", "--") if found else "--"
        widget.lbl_sn.config(text=sn_text, fg=text_sn_col)
        
        # Update Icon
        widget.canvas.itemconfig(1, fill=icon_bg)
        widget.canvas.itemconfig(2, text=icon_char, fill=icon_fg)

    def on_calibrate_click(self):
        pips = self.c.backend.state.get("pipettes", {})
        p1 = pips.get("left", {}).get("found", False)
        p2 = pips.get("right", {}).get("found", False)
        
        
        if not p1 and not p2:
            popup = CustomPopup(self.c, "Required", "NO HARDWARE", "No pipettes detected.\nPlease attach a pipette.", CLR_DANGER, "🛑")
            self.c.wait_window(popup); return
        else:
            self.c.show_frame("Calibrate")      
   # Inside your Home class or SettingsTray:
    # def view_logs(self):
    #     LogViewerPopup(self.c)
            
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
        
        # --- DYNAMIC PIPETTE CALIBRATION COMMAND ---
        pips = self.c.backend.state.get("pipettes", {})
        left_attached = pips.get("left", {}).get("found", False)
        right_attached = pips.get("right", {}).get("found", False)
        
        # Priority: Left (P1), then Right (P2)
        if left_attached and right_attached:
            self.c.backend.ui_send_gcode("T00") # Fallback just in case
        elif left_attached:
            self.c.backend.ui_send_gcode("T00 P1")
        elif right_attached:
            self.c.backend.ui_send_gcode("T00 P2")
        else:
            self.c.backend.ui_send_gcode("T00") # Fallback just in case
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

    def on_fan_change(self, val): 
        self.c.backend.state["fan_manual_val"] = int(val)
    
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
