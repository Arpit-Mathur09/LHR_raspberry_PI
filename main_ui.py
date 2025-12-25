""" import tkinter as tk
from tkinter import ttk, messagebox
import os
import time
from datetime import timedelta
import backend 

# --- CONFIGURATION ---
BASE_DIR = "/home/lhr/Robot_Client"
DIR_TEST = os.path.join(BASE_DIR, "test_protocols")
DIR_RECENT = os.path.join(BASE_DIR, "recent_protocols")
DIR_ICONS = os.path.join(BASE_DIR, "icons")

for d in [DIR_TEST, DIR_RECENT, DIR_ICONS]:
    os.makedirs(d, exist_ok=True)

# --- COLORS ---
CLR_BG = "#F0F2F5"
CLR_CARD = "#FFFFFF"
CLR_PRIMARY = "#2196F3"     
CLR_INACTIVE = "#CFD8DC"    
CLR_SUCCESS = "#4CAF50"
CLR_SUCCESS_DARK = "#388E3C"     
CLR_DANGER = "#F44336"  
CLR_WARNING = "#FF9800"
CLR_WARNING_DARK = "#F57C00"    
CLR_TEXT = "#212121"
CLR_INFO_BOX = "#ECEFF1" # Light Grey for Command Box

class KioskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.backend = backend.RobotClient()
        self.backend.start()

        w, h = 800, 480
        self.geometry(f"{w}x{h}")
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.config(bg=CLR_BG)

        # --- STYLES ---
        style = ttk.Style()
        style.theme_use("clam")
        
        # List Style
        style.configure("Treeview", background="white", foreground=CLR_TEXT, 
                        rowheight=50, font=("Arial", 14))
        style.configure("Treeview.Heading", font=('Arial', 14, 'bold'))
        style.map('Treeview', background=[('selected', CLR_PRIMARY)])
        
        # Chunky Progress Bar
        style.layout("Chunky.Horizontal.TProgressbar",
                     [('Horizontal.Progressbar.trough',
                       {'children': [('Horizontal.Progressbar.pbar',
                                      {'side': 'left', 'sticky': 'ns'})],
                        'sticky': 'nswe'})])
        style.configure("Chunky.Horizontal.TProgressbar", thickness=40, troughcolor="#E0E0E0", background=CLR_SUCCESS, borderwidth=0)

        # Variables
        self.offsets = {"X": tk.DoubleVar(value=0.0), "Y": tk.DoubleVar(value=0.0), 
                        "Z1": tk.DoubleVar(value=0.0), "Z2": tk.DoubleVar(value=0.0)}
        self.step_size = tk.DoubleVar(value=1.0)
        self.selected_file = tk.StringVar(value="No File Selected")
        self.current_page_name = "Home"

        # Load Frames
        container = tk.Frame(self, bg=CLR_BG)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (Home, Calibrate, ProtocolList, Running):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("Home")
        self.start_ui_updater()

    def show_frame(self, page_name):
        self.current_page_name = page_name
        frame = self.frames[page_name]
        frame.tkraise()
        if page_name == "ProtocolList":
            frame.refresh_files(frame.current_dir)
        if page_name == "Running":
            frame.reset_run_state() 

    def start_ui_updater(self):
        state = self.backend.state
        if state["status"] in ["Running", "Paused"] and self.current_page_name != "Running":
            self.selected_file.set(state["filename"])
            self.show_frame("Running")
        
        if self.current_page_name == "Running":
            self.frames["Running"].update_view(state)

        if state["status"] == "Done" and self.current_page_name == "Running":
            messagebox.showinfo("Done", "Protocol Finished")
            self.show_frame("Home")
            self.backend.state["status"] = "Idle"

        self.after(200, self.start_ui_updater)

# --- 1. HOME ---
class Home(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        card = tk.Frame(self, bg=CLR_CARD, padx=50, pady=50)
        card.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(card, text="Liquid Handler v1.0", font=("Arial", 22, "bold"), bg=CLR_CARD).pack(pady=(0, 30))
        
        btn_cfg = {"font": ("Arial", 16, "bold"), "width": 22, "height": 3, "relief": "flat", "fg": "white"}
        tk.Button(card, text="CALIBRATION", bg="#FF9800", **btn_cfg,
                  command=lambda: controller.show_frame("Calibrate")).pack(pady=10)
        tk.Button(card, text="RUN PROTOCOL", bg=CLR_PRIMARY, **btn_cfg,
                  command=lambda: controller.show_frame("ProtocolList")).pack(pady=10)

# --- 2. CALIBRATE ---
class Calibrate(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_CARD)
        self.c = controller
        left = tk.Frame(self, bg=CLR_CARD, padx=20, pady=20)
        left.pack(side="left", fill="both", expand=True)
        grid = tk.Frame(left, bg=CLR_CARD)
        grid.pack(pady=20)
        bs = {"font": ("Arial", 14, "bold"), "width": 5, "height": 2, "bg": CLR_INACTIVE, "relief": "flat"}
        
        tk.Button(grid, text="Y+", **bs, command=lambda: self.move("Y", 1)).grid(row=0, column=1, pady=5)
        tk.Button(grid, text="X-", **bs, command=lambda: self.move("X", -1)).grid(row=1, column=0, padx=5)
        tk.Button(grid, text="X+", **bs, command=lambda: self.move("X", 1)).grid(row=1, column=2, padx=5)
        tk.Button(grid, text="Y-", **bs, command=lambda: self.move("Y", -1)).grid(row=2, column=1, pady=5)
        tk.Button(grid, text="Z1+", **bs, command=lambda: self.move("Z1", 1)).grid(row=0, column=4, padx=(40, 5))
        tk.Button(grid, text="Z1-", **bs, command=lambda: self.move("Z1", -1)).grid(row=1, column=4, padx=(40, 5))
        tk.Button(grid, text="Z2+", **bs, command=lambda: self.move("Z2", 1)).grid(row=0, column=5, padx=5)
        tk.Button(grid, text="Z2-", **bs, command=lambda: self.move("Z2", -1)).grid(row=1, column=5, padx=5)

        step_f = tk.Frame(left, bg=CLR_BG, pady=10)
        step_f.pack(fill="x", pady=20)
        tk.Label(step_f, text="Step:", font=("Arial", 12), bg=CLR_BG).pack(side="left")
        for s in [0.1, 1.0, 10.0]:
            tk.Radiobutton(step_f, text=f"{s}mm", variable=self.c.step_size, value=s, indicatoron=0, 
                           width=6, font=("Arial", 14), selectcolor=CLR_PRIMARY, bg=CLR_BG).pack(side="left", padx=5)

        right = tk.Frame(self, bg="#E0E0E0", width=250)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        tk.Label(right, text="Position", font=("Arial", 16, "bold"), bg="#E0E0E0").pack(pady=30)
        for axis in ["X", "Y", "Z1", "Z2"]:
            f = tk.Frame(right, bg="#E0E0E0")
            f.pack(fill="x", padx=20, pady=5)
            tk.Label(f, text=axis, font=("Arial", 14), bg="#E0E0E0", width=4).pack(side="left")
            tk.Label(f, textvariable=self.c.offsets[axis], font=("Arial", 14, "bold"), bg="white", width=8).pack(side="right")
        tk.Button(right, text="EXIT", bg=CLR_DANGER, fg="white", font=("Arial", 14, "bold"), height=2,
                  command=lambda: controller.show_frame("Home")).pack(side="bottom", fill="x", padx=10, pady=20)

    def move(self, axis, direction):
        step = self.c.step_size.get() * direction
        val = self.c.offsets[axis].get() + step
        self.c.offsets[axis].set(round(val, 2))
        dx, dy, dz = 0, 0, 0
        if axis == "X": dx = step
        elif axis == "Y": dy = step
        elif "Z" in axis: dz = step
        self.c.backend.ui_send_gcode(f"C dx={dx}, dy={dy}, dz={dz}")

# --- 3. PROTOCOL LIST ---
class ProtocolList(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        self.current_dir = DIR_TEST
        
        self.icon_file = None
        self.icon_empty = None
        try:
            f_path = os.path.join(DIR_ICONS, "file.png")
            if os.path.exists(f_path): self.icon_file = tk.PhotoImage(file=f_path).subsample(15, 15) 
            e_path = os.path.join(DIR_ICONS, "empty.png")
            if os.path.exists(e_path): self.icon_empty = tk.PhotoImage(file=e_path).subsample(15, 15)
        except: pass

        footer = tk.Frame(self, bg="white", height=80)
        footer.pack(side="bottom", fill="x")
        tk.Button(footer, text="<< BACK", font=("Arial", 14, "bold"), bg=CLR_INACTIVE, fg="black", width=12, height=2,
                  command=lambda: controller.show_frame("Home")).pack(side="left", padx=20, pady=10)
        tk.Button(footer, text="START >>", font=("Arial", 14, "bold"), bg=CLR_SUCCESS, fg="white", width=12, height=2,
                  command=self.load_and_run).pack(side="right", padx=20, pady=10)

        header = tk.Frame(self, bg=CLR_BG)
        header.pack(side="top", fill="x", pady=10, padx=20)
        self.btn_test = tk.Button(header, text="TEST PROTOCOLS", font=("Arial", 13, "bold"), height=2, relief="flat",
                                  command=lambda: self.switch_tab("TEST"))
        self.btn_test.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.btn_recent = tk.Button(header, text="RECENT FILES", font=("Arial", 13, "bold"), height=2, relief="flat",
                                    command=lambda: self.switch_tab("RECENT"))
        self.btn_recent.pack(side="left", fill="x", expand=True, padx=(2, 0))

        list_frame = tk.Frame(self, bg="white")
        list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))
        self.tree = ttk.Treeview(list_frame, columns=("name"), show="tree", selectmode="browse")
        self.tree.column("#0", anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.switch_tab("TEST")

    def switch_tab(self, tab_name):
        if tab_name == "TEST":
            self.current_dir = DIR_TEST
            self.btn_test.config(bg=CLR_PRIMARY, fg="white", activebackground=CLR_PRIMARY, activeforeground="white")
            self.btn_recent.config(bg=CLR_INACTIVE, fg="black", activebackground=CLR_INACTIVE, activeforeground="black")
        else:
            self.current_dir = DIR_RECENT
            self.btn_recent.config(bg=CLR_PRIMARY, fg="white", activebackground=CLR_PRIMARY, activeforeground="white")
            self.btn_test.config(bg=CLR_INACTIVE, fg="black", activebackground=CLR_INACTIVE, activeforeground="black")
        self.refresh_files(self.current_dir)

    def refresh_files(self, folder_path):
        for item in self.tree.get_children(): self.tree.delete(item)
        try:
            files = sorted(os.listdir(folder_path))
            count = 0
            for f in files:
                if f.endswith(('.g', '.nc', '.gc', '.gcode', '.txt', '.py')):
                    if self.icon_file: self.tree.insert("", "end", iid=f, text=f"  {f}", image=self.icon_file)
                    else: self.tree.insert("", "end", iid=f, text=f"  [FILE]  {f}")
                    count += 1
            if count == 0:
                txt = f"  Empty: {os.path.basename(folder_path)}"
                if self.icon_empty: self.tree.insert("", "end", text=txt, image=self.icon_empty)
                else: self.tree.insert("", "end", text=txt)
        except Exception as e: self.tree.insert("", "end", text=f"Error: {str(e)}")

    def load_and_run(self):
        sel = self.tree.selection()
        if not sel: return
        filename = sel[0]
        if " " in filename and not filename.endswith(".g"): return 
        self.c.selected_file.set(filename)
        self.c.backend.ui_load_and_run(filename)
        self.c.show_frame("Running")

# --- 4. RUNNING ---
class Running(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_CARD)
        self.c = controller
        
        self.start_time = None 
        self.smoothed_seconds = 0
        
        # 1. Header
        tk.Label(self, text="RUNNING PROTOCOL", font=("Arial", 12, "bold"), fg=CLR_INACTIVE, bg=CLR_CARD).pack(pady=(20, 0))
        tk.Label(self, textvariable=controller.selected_file, font=("Arial", 18, "bold"), fg=CLR_PRIMARY, bg=CLR_CARD).pack(pady=5)
        
        # 2. BOXED Command Display (Solving Visibility Issue)
        info_box = tk.Frame(self, bg=CLR_INFO_BOX, bd=2, relief="groove")
        info_box.pack(pady=15, fill="x", padx=40)
        
        tk.Label(info_box, text="Current Command:", font=("Arial", 10), bg=CLR_INFO_BOX, fg="gray").pack(pady=(10,0))
        self.cmd_lbl = tk.Label(info_box, text="Waiting for Start...", font=("Courier New", 18, "bold"), bg=CLR_INFO_BOX, fg="black")
        self.cmd_lbl.pack(pady=5)
        
        tk.Label(info_box, text="Description:", font=("Arial", 10), bg=CLR_INFO_BOX, fg="gray").pack(pady=(5,0))
        self.desc_lbl = tk.Label(info_box, text="--", font=("Arial", 14, "italic"), fg="#555", bg=CLR_INFO_BOX)
        self.desc_lbl.pack(pady=(0, 10))

        # 3. Chunky Progress Bar
        prog_frame = tk.Frame(self, bg=CLR_CARD)
        prog_frame.pack(fill="x", padx=50, pady=5)
        
        self.percent_lbl = tk.Label(prog_frame, text="0%", font=("Arial", 14, "bold"), bg=CLR_CARD, fg=CLR_PRIMARY)
        self.percent_lbl.pack(side="left")
        
        self.time_lbl = tk.Label(prog_frame, text="⏳ Est: --:--:--", font=("Arial", 14), bg=CLR_CARD, fg="#777")
        self.time_lbl.pack(side="right")
        
        self.prog = ttk.Progressbar(self, style="Chunky.Horizontal.TProgressbar", length=600, mode="determinate")
        self.prog.pack(pady=(5, 20))

        # 4. Footer with STATUS INDICATION
        footer = tk.Frame(self, bg=CLR_CARD)
        footer.pack(side="bottom", pady=30)
        
        # Pause Button (We save reference to change color/text)
        self.btn_pause = tk.Button(footer, text="⏸ PAUSE", font=("Arial", 14, "bold"), width=16, height=2, 
                                   bg=CLR_WARNING, fg="white", activeforeground="white", activebackground=CLR_WARNING_DARK,
                                   relief="flat",
                                   command=lambda: self.c.backend.ui_pause_resume())
        self.btn_pause.pack(side="left", padx=20)
        
        tk.Button(footer, text="✖ STOP", font=("Arial", 14, "bold"), width=12, height=2, 
                  bg=CLR_DANGER, fg="white", activeforeground="white", activebackground="#D32F2F",
                  relief="flat",
                  command=self.cancel_run).pack(side="left", padx=20)
        
        # Status Text (Debug)
        self.status_debug = tk.Label(self, text="Status: IDLE", font=("Arial", 10), bg=CLR_CARD, fg="gray")
        self.status_debug.place(x=10, y=10) # Top left corner

    def reset_run_state(self):
        self.start_time = time.time()
        self.smoothed_seconds = 0

    def cancel_run(self):
        if messagebox.askyesno("Stop", "Abort current protocol?"):
            self.c.backend.ui_stop()
            self.c.show_frame("Home")

    def update_view(self, state):
        progress = state["progress"]
        status = state["status"] 
        raw_line = state["current_line"]
        
        # Debug Label
        self.status_debug.config(text=f"System Status: {status}")

        # A. Update Progress
        self.prog["value"] = progress
        self.percent_lbl.config(text=f"{progress}%")

        # B. Smooth Time Estimation
        if self.start_time and progress > 1 and status == "Running":
            elapsed = time.time() - self.start_time
            raw_remaining = (elapsed / progress) * (100 - progress)
            if self.smoothed_seconds == 0: self.smoothed_seconds = raw_remaining
            else: self.smoothed_seconds = (0.99 * self.smoothed_seconds) + (0.01 * raw_remaining)
            
            td = timedelta(seconds=int(self.smoothed_seconds))
            self.time_lbl.config(text=f"⏳ Est: {str(td)}")
        elif progress == 0:
            self.time_lbl.config(text="⏳ Est: Calculating...")

        # C. Parse G-Code
        if ";" in raw_line:
            parts = raw_line.split(";", 1)
            cmd_text = parts[0].strip()
            desc_text = parts[1].strip()
        else:
            cmd_text = raw_line
            desc_text = ""
        
        if not cmd_text: cmd_text = "..." # Placeholder if empty

        # D. PAUSE LOGIC
        if status.upper() == "PAUSED":
            self.cmd_lbl.config(text="PAUSED", fg="red")
            self.desc_lbl.config(text="Resume to continue...", fg="red")
            
            # Button -> Green RESUME
            self.btn_pause.config(text="▶ RESUME", bg=CLR_SUCCESS, activebackground=CLR_SUCCESS_DARK)
            
        else:
            self.cmd_lbl.config(text=cmd_text, fg="black")
            self.desc_lbl.config(text=desc_text, fg="#555")
            
            # Button -> Orange PAUSE
            self.btn_pause.config(text="⏸ PAUSE", bg=CLR_WARNING, activebackground=CLR_WARNING_DARK)

if __name__ == "__main__":
    app = KioskApp()
    app.mainloop() """

import tkinter as tk
from tkinter import ttk, messagebox
import os
import backend 

# --- CONFIGURATION ---
BASE_DIR = "/home/lhr/Robot_Client"
DIR_TEST = os.path.join(BASE_DIR, "test_protocols")
DIR_RECENT = os.path.join(BASE_DIR, "recent_protocols")
DIR_ICONS = os.path.join(BASE_DIR, "icons")

for d in [DIR_TEST, DIR_RECENT, DIR_ICONS]:
    os.makedirs(d, exist_ok=True)

# --- COLORS ---
CLR_BG = "#F0F2F5"
CLR_CARD = "#FFFFFF"
CLR_PRIMARY = "#2196F3"     
CLR_INACTIVE = "#CFD8DC"    
CLR_SUCCESS = "#4CAF50"
CLR_SUCCESS_DARK = "#388E3C"     
CLR_DANGER = "#F44336"  
CLR_WARNING = "#FF9800"
CLR_WARNING_DARK = "#F57C00"    
CLR_TEXT = "#212121"
CLR_INFO_BOX = "#ECEFF1" 

class KioskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.backend = backend.RobotClient()
        self.backend.start()

        w, h = 800, 480
        self.geometry(f"{w}x{h}")
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.config(bg=CLR_BG)

        # --- STYLES ---
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="white", foreground=CLR_TEXT, rowheight=50, font=("Arial", 14))
        style.configure("Treeview.Heading", font=('Arial', 14, 'bold'))
        style.map('Treeview', background=[('selected', CLR_PRIMARY)])
        style.layout("Chunky.Horizontal.TProgressbar",
                     [('Horizontal.Progressbar.trough',
                       {'children': [('Horizontal.Progressbar.pbar',
                                      {'side': 'left', 'sticky': 'ns'})],
                        'sticky': 'nswe'})])
        style.configure("Chunky.Horizontal.TProgressbar", thickness=40, troughcolor="#E0E0E0", background=CLR_SUCCESS, borderwidth=0)

        self.offsets = {"X": tk.DoubleVar(value=0.0), "Y": tk.DoubleVar(value=0.0), 
                        "Z1": tk.DoubleVar(value=0.0), "Z2": tk.DoubleVar(value=0.0)}
        self.step_size = tk.DoubleVar(value=1.0)
        self.selected_file = tk.StringVar(value="No File Selected")
        self.current_page_name = "Home"

        container = tk.Frame(self, bg=CLR_BG)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (Home, Calibrate, ProtocolList, Running):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("Home")
        self.start_ui_updater()

    def show_frame(self, page_name):
        self.current_page_name = page_name
        frame = self.frames[page_name]
        frame.tkraise()
        if page_name == "ProtocolList":
            frame.refresh_files(frame.current_dir)

    def start_ui_updater(self):
        state = self.backend.state
        if state["status"] in ["Running", "Paused"] and self.current_page_name != "Running":
            self.selected_file.set(state["filename"])
            self.show_frame("Running")
        
        if self.current_page_name == "Running":
            self.frames["Running"].update_view(state)

        if state["status"] == "Done" and self.current_page_name == "Running":
            messagebox.showinfo("Done", "Protocol Finished")
            self.show_frame("Home")
            self.backend.state["status"] = "Idle"

        self.after(200, self.start_ui_updater)

# --- 1. HOME ---
class Home(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        card = tk.Frame(self, bg=CLR_CARD, padx=50, pady=50)
        card.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(card, text="Liquid Handler v1.0", font=("Arial", 22, "bold"), bg=CLR_CARD).pack(pady=(0, 30))
        btn_cfg = {"font": ("Arial", 16, "bold"), "width": 22, "height": 3, "relief": "flat", "fg": "white"}
        tk.Button(card, text="CALIBRATION", bg="#FF9800", **btn_cfg, command=lambda: controller.show_frame("Calibrate")).pack(pady=10)
        tk.Button(card, text="RUN PROTOCOL", bg=CLR_PRIMARY, **btn_cfg, command=lambda: controller.show_frame("ProtocolList")).pack(pady=10)

# --- 2. CALIBRATE ---
class Calibrate(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_CARD)
        self.c = controller
        left = tk.Frame(self, bg=CLR_CARD, padx=20, pady=20)
        left.pack(side="left", fill="both", expand=True)
        grid = tk.Frame(left, bg=CLR_CARD)
        grid.pack(pady=20)
        bs = {"font": ("Arial", 14, "bold"), "width": 5, "height": 2, "bg": CLR_INACTIVE, "relief": "flat"}
        
        tk.Button(grid, text="Y+", **bs, command=lambda: self.move("Y", 1)).grid(row=0, column=1, pady=5)
        tk.Button(grid, text="X-", **bs, command=lambda: self.move("X", -1)).grid(row=1, column=0, padx=5)
        tk.Button(grid, text="X+", **bs, command=lambda: self.move("X", 1)).grid(row=1, column=2, padx=5)
        tk.Button(grid, text="Y-", **bs, command=lambda: self.move("Y", -1)).grid(row=2, column=1, pady=5)
        tk.Button(grid, text="Z1+", **bs, command=lambda: self.move("Z1", 1)).grid(row=0, column=4, padx=(40, 5))
        tk.Button(grid, text="Z1-", **bs, command=lambda: self.move("Z1", -1)).grid(row=1, column=4, padx=(40, 5))
        tk.Button(grid, text="Z2+", **bs, command=lambda: self.move("Z2", 1)).grid(row=0, column=5, padx=5)
        tk.Button(grid, text="Z2-", **bs, command=lambda: self.move("Z2", -1)).grid(row=1, column=5, padx=5)

        step_f = tk.Frame(left, bg=CLR_BG, pady=10)
        step_f.pack(fill="x", pady=20)
        tk.Label(step_f, text="Step:", font=("Arial", 12), bg=CLR_BG).pack(side="left")
        for s in [0.1, 1.0, 10.0]:
            tk.Radiobutton(step_f, text=f"{s}mm", variable=self.c.step_size, value=s, indicatoron=0, 
                           width=6, font=("Arial", 14), selectcolor=CLR_PRIMARY, bg=CLR_BG).pack(side="left", padx=5)
        right = tk.Frame(self, bg="#E0E0E0", width=250)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        tk.Label(right, text="Position", font=("Arial", 16, "bold"), bg="#E0E0E0").pack(pady=30)
        for axis in ["X", "Y", "Z1", "Z2"]:
            f = tk.Frame(right, bg="#E0E0E0")
            f.pack(fill="x", padx=20, pady=5)
            tk.Label(f, text=axis, font=("Arial", 14), bg="#E0E0E0", width=4).pack(side="left")
            tk.Label(f, textvariable=self.c.offsets[axis], font=("Arial", 14, "bold"), bg="white", width=8).pack(side="right")
        tk.Button(right, text="EXIT", bg=CLR_DANGER, fg="white", font=("Arial", 14, "bold"), height=2,
                  command=lambda: controller.show_frame("Home")).pack(side="bottom", fill="x", padx=10, pady=20)

    def move(self, axis, direction):
        step = self.c.step_size.get() * direction
        val = self.c.offsets[axis].get() + step
        self.c.offsets[axis].set(round(val, 2))
        dx, dy, dz = 0, 0, 0
        if axis == "X": dx = step
        elif axis == "Y": dy = step
        elif "Z" in axis: dz = step
        self.c.backend.ui_send_gcode(f"C dx={dx}, dy={dy}, dz={dz}")

# --- 3. PROTOCOL LIST ---
class ProtocolList(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        self.c = controller
        self.current_dir = DIR_TEST
        self.icon_file = None
        self.icon_empty = None
        try:
            f_path = os.path.join(DIR_ICONS, "file.png")
            if os.path.exists(f_path): self.icon_file = tk.PhotoImage(file=f_path).subsample(15, 15) 
            e_path = os.path.join(DIR_ICONS, "empty.png")
            if os.path.exists(e_path): self.icon_empty = tk.PhotoImage(file=e_path).subsample(15, 15)
        except: pass

        footer = tk.Frame(self, bg="white", height=80)
        footer.pack(side="bottom", fill="x")
        tk.Button(footer, text="<< BACK", font=("Arial", 14, "bold"), bg=CLR_INACTIVE, fg="black", width=12, height=2,
                  command=lambda: controller.show_frame("Home")).pack(side="left", padx=20, pady=10)
        tk.Button(footer, text="START >>", font=("Arial", 14, "bold"), bg=CLR_SUCCESS, fg="white", width=12, height=2,
                  command=self.load_and_run).pack(side="right", padx=20, pady=10)
        header = tk.Frame(self, bg=CLR_BG)
        header.pack(side="top", fill="x", pady=10, padx=20)
        self.btn_test = tk.Button(header, text="TEST PROTOCOLS", font=("Arial", 13, "bold"), height=2, relief="flat",
                                  command=lambda: self.switch_tab("TEST"))
        self.btn_test.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.btn_recent = tk.Button(header, text="RECENT FILES", font=("Arial", 13, "bold"), height=2, relief="flat",
                                    command=lambda: self.switch_tab("RECENT"))
        self.btn_recent.pack(side="left", fill="x", expand=True, padx=(2, 0))
        list_frame = tk.Frame(self, bg="white")
        list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))
        self.tree = ttk.Treeview(list_frame, columns=("name"), show="tree", selectmode="browse")
        self.tree.column("#0", anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.switch_tab("TEST")

    def switch_tab(self, tab_name):
        if tab_name == "TEST":
            self.current_dir = DIR_TEST
            self.btn_test.config(bg=CLR_PRIMARY, fg="white", activebackground=CLR_PRIMARY, activeforeground="white")
            self.btn_recent.config(bg=CLR_INACTIVE, fg="black", activebackground=CLR_INACTIVE, activeforeground="black")
        else:
            self.current_dir = DIR_RECENT
            self.btn_recent.config(bg=CLR_PRIMARY, fg="white", activebackground=CLR_PRIMARY, activeforeground="white")
            self.btn_test.config(bg=CLR_INACTIVE, fg="black", activebackground=CLR_INACTIVE, activeforeground="black")
        self.refresh_files(self.current_dir)

    def refresh_files(self, folder_path):
        for item in self.tree.get_children(): self.tree.delete(item)
        try:
            files = sorted(os.listdir(folder_path))
            count = 0
            for f in files:
                if f.endswith(('.g', '.nc', '.gc', '.gcode', '.txt', '.py')):
                    if self.icon_file: self.tree.insert("", "end", iid=f, text=f"  {f}", image=self.icon_file)
                    else: self.tree.insert("", "end", iid=f, text=f"  [FILE]  {f}")
                    count += 1
            if count == 0:
                txt = f"  Empty: {os.path.basename(folder_path)}"
                if self.icon_empty: self.tree.insert("", "end", text=txt, image=self.icon_empty)
                else: self.tree.insert("", "end", text=txt)
        except Exception as e: self.tree.insert("", "end", text=f"Error: {str(e)}")

    def load_and_run(self):
        sel = self.tree.selection()
        if not sel: return
        filename = sel[0]
        if " " in filename and not filename.endswith(".g"): return 
        self.c.selected_file.set(filename)
        self.c.backend.ui_load_and_run(filename)
        self.c.show_frame("Running")

# --- 4. RUNNING ---
class Running(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_CARD)
        self.c = controller
        
        tk.Label(self, text="RUNNING PROTOCOL", font=("Arial", 12, "bold"), fg=CLR_INACTIVE, bg=CLR_CARD).pack(pady=(20, 0))
        tk.Label(self, textvariable=controller.selected_file, font=("Arial", 18, "bold"), fg=CLR_PRIMARY, bg=CLR_CARD).pack(pady=5)
        
        info_box = tk.Frame(self, bg=CLR_INFO_BOX, bd=2, relief="groove")
        info_box.pack(pady=15, fill="x", padx=40)
        
        tk.Label(info_box, text="Current Command:", font=("Arial", 10), bg=CLR_INFO_BOX, fg="gray").pack(pady=(10,0))
        self.cmd_lbl = tk.Label(info_box, text="Waiting...", font=("Courier New", 18, "bold"), bg=CLR_INFO_BOX, fg="black")
        self.cmd_lbl.pack(pady=5)
        
        tk.Label(info_box, text="Description:", font=("Arial", 10), bg=CLR_INFO_BOX, fg="gray").pack(pady=(5,0))
        self.desc_lbl = tk.Label(info_box, text="--", font=("Arial", 14, "italic"), fg="#37474F", bg=CLR_INFO_BOX)
        self.desc_lbl.pack(pady=(0, 10))

        prog_frame = tk.Frame(self, bg=CLR_CARD)
        prog_frame.pack(fill="x", padx=50, pady=5)
        self.percent_lbl = tk.Label(prog_frame, text="0%", font=("Arial", 14, "bold"), bg=CLR_CARD, fg=CLR_PRIMARY)
        self.percent_lbl.pack(side="left")
        self.time_lbl = tk.Label(prog_frame, text="⏳ Est: --:--:--:--", font=("Arial", 14), bg=CLR_CARD, fg="#777")
        self.time_lbl.pack(side="right")
        self.prog = ttk.Progressbar(self, style="Chunky.Horizontal.TProgressbar", length=600, mode="determinate")
        self.prog.pack(pady=(5, 20))

        footer = tk.Frame(self, bg=CLR_CARD)
        footer.pack(side="bottom", pady=30)
        
        self.btn_pause = tk.Button(footer, text="⏸ PAUSE", font=("Arial", 14, "bold"), width=16, height=2, 
                                   bg=CLR_WARNING, fg="white", activeforeground="white", activebackground=CLR_WARNING_DARK,
                                   relief="flat", command=lambda: self.c.backend.ui_pause_resume())
        self.btn_pause.pack(side="left", padx=20)
        
        tk.Button(footer, text="✖ STOP", font=("Arial", 14, "bold"), width=12, height=2, 
                  bg=CLR_DANGER, fg="white", activeforeground="white", activebackground="#D32F2F",
                  relief="flat", command=self.cancel_run).pack(side="left", padx=20)
        
        self.status_debug = tk.Label(self, text="Status: IDLE", font=("Arial", 10), bg=CLR_CARD, fg="gray")
        self.status_debug.place(x=10, y=10)

    def cancel_run(self):
        if messagebox.askyesno("Stop", "Abort current protocol?"):
            self.c.backend.ui_stop()
            self.c.show_frame("Home")

    def update_view(self, state):
        progress = state["progress"]
        status = state["status"] 
        cmd_text = state["current_line"]
        desc_text = state.get("current_desc", "") 
        est_time = state.get("est", "--:--:--:--")

        self.status_debug.config(text=f"System Status: {status}")
        self.prog["value"] = progress
        self.percent_lbl.config(text=f"{progress}%")
        self.time_lbl.config(text=f"⏳ Est: {est_time}")

        if status.upper() == "PAUSED":
            self.cmd_lbl.config(text="PAUSED", fg="red")
            self.desc_lbl.config(text="Resume to continue...", fg="red")
            self.btn_pause.config(text="▶ RESUME", bg=CLR_SUCCESS, activebackground=CLR_SUCCESS_DARK)
        else:
            self.cmd_lbl.config(text=cmd_text, fg="black")
            self.desc_lbl.config(text=desc_text, fg="#37474F")
            self.btn_pause.config(text="⏸ PAUSE", bg=CLR_WARNING, activebackground=CLR_WARNING_DARK)

if __name__ == "__main__":
    app = KioskApp()
    app.mainloop()
    