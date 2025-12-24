#home Screen | Calibration Screen |  Run A protocol Screen | Running Screen


import tkinter as tk
from tkinter import ttk, messagebox

# --- STYLE CONSTANTS ---
CLR_BG = "#F0F2F5"
CLR_CARD = "#FFFFFF"
CLR_PRIMARY = "#2196F3"
CLR_SUCCESS = "#4CAF50"
CLR_DANGER = "#F44336"
CLR_NAV = "#E9ECEF"

class KioskApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # 1. Hardware/Display Setup
        self.attributes("-fullscreen", True)
        self.config(cursor="none", bg=CLR_BG)
        self.bind("<Escape>", lambda e: self.destroy())

        # 2. Centralized State Management
        self.offsets = {"X": tk.DoubleVar(value=0.0), "Y": tk.DoubleVar(value=0.0), 
                        "Z1": tk.DoubleVar(value=0.0), "Z2": tk.DoubleVar(value=0.0)}
        self.step_size = tk.DoubleVar(value=1.0) # Default to 1mm
        self.selected_file = tk.StringVar(value="No File Selected")

        # 3. View Management
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

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

# --- 1. HOME SCREEN ---
class Home(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_BG)
        card = tk.Frame(self, bg=CLR_CARD, padx=40, pady=40, relief="flat")
        card.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(card, text="Main Menu", font=("Arial", 20, "bold"), bg=CLR_CARD).pack(pady=20)
        
        btn_cfg = {"font": ("Arial", 16, "bold"), "width": 20, "height": 2, "fg": "white", "relief": "flat"}
        tk.Button(card, text=" 🎯 Calibration", bg=CLR_PRIMARY, **btn_cfg,
                  command=lambda: controller.show_frame("Calibrate")).pack(pady=10)
        tk.Button(card, text="▶  Run Protocol", bg=CLR_PRIMARY, **btn_cfg,
                  command=lambda: controller.show_frame("ProtocolList")).pack(pady=10)

# --- 2. CALIBRATION SCREEN (FIXED OVERLAP & STEP OPTIONS) ---
class Calibrate(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_CARD)
        self.c = controller

        # Layout: Control Panel (Left) | Data Panel (Right)
        left = tk.Frame(self, bg=CLR_CARD, padx=10, pady=10)
        left.pack(side="left", fill="both", expand=True)

        # A. Directional Grid (X/Y)
        grid = tk.Frame(left, bg=CLR_CARD)
        grid.pack(pady=10)
        
        btn_style = {"font": ("Arial", 14, "bold"), "width": 6, "height": 2, "bg": CLR_NAV, "relief": "flat"}
        tk.Button(grid, text="Y ⬆️", **btn_style, command=lambda: self.move("Y", 1)).grid(row=0, column=1, pady=5)
        tk.Button(grid, text="X ⬅️", **btn_style, command=lambda: self.move("X", -1)).grid(row=1, column=0, padx=5)
        tk.Button(grid, text="X ➡️", **btn_style, command=lambda: self.move("X", 1)).grid(row=1, column=2, padx=5)
        tk.Button(grid, text="Y ⬇️", **btn_style, command=lambda: self.move("Y", -1)).grid(row=2, column=1, pady=5)

        # B. Z-Control Grid (Side-by-side to prevent overlap)
        z_grid = tk.Frame(left, bg=CLR_CARD)
        z_grid.pack(pady=10)
        tk.Button(z_grid, text="Z1 ⬆️", **btn_style, command=lambda: self.move("Z1", 1)).grid(row=0, column=0, padx=10)
        tk.Button(z_grid, text="Z1 ⬇️", **btn_style, command=lambda: self.move("Z1", -1)).grid(row=1, column=0, padx=10, pady=5)
        tk.Button(z_grid, text="Z2 ⬆️", **btn_style, command=lambda: self.move("Z2", 1)).grid(row=0, column=1, padx=10)
        tk.Button(z_grid, text="Z2 ⬇️", **btn_style, command=lambda: self.move("Z2", -1)).grid(row=1, column=1, padx=10, pady=5)

        # C. Precision/Step Selector (FIXED: Added 0.1mm)
        step_frame = tk.Frame(left, bg=CLR_NAV, pady=5)
        step_frame.pack(fill="x", pady=10)
        tk.Label(step_frame, text="Step:", font=("Arial", 12, "bold"), bg=CLR_NAV).pack(side="left", padx=10)
        for s in [0.1, 1.0, 10.0]:
            tk.Radiobutton(step_frame, text=f"{s}mm", variable=self.c.step_size, value=s, 
                           indicatoron=0, width=8, font=("Arial", 12), selectcolor=CLR_PRIMARY).pack(side="left", padx=5)

        # D. Right Side: Offset Display
        right = tk.Frame(self, bg=CLR_NAV, width=220)
        right.pack(side="right", fill="y", padx=10, pady=10)
        
        tk.Label(right, text="Current Offsets", font=("Arial", 14, "bold"), bg=CLR_NAV).pack(pady=20)
        for axis in ["X", "Y", "Z1", "Z2"]:
            f = tk.Frame(right, bg=CLR_NAV)
            f.pack(fill="x", padx=15, pady=5)
            tk.Label(f, text=f"{axis}:", font=("Arial", 12), bg=CLR_NAV).pack(side="left")
            tk.Label(f, textvariable=self.c.offsets[axis], font=("Arial", 12, "bold"), bg="white", width=8).pack(side="right")

        tk.Button(right, text="SAVE & BACK", bg=CLR_SUCCESS, fg="white", font=("Arial", 12, "bold"),
                  command=lambda: controller.show_frame("Home")).pack(side="bottom", fill="x", pady=20, padx=10)

    def move(self, axis, direction):
        val = self.c.offsets[axis].get() + (self.c.step_size.get() * direction)
        self.c.offsets[axis].set(round(val, 2))

# --- 3. PROTOCOL LIST (FIXED: Added Tabs & Back Button) ---
class ProtocolList(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_CARD)
        
        # Tabs
        tabs = tk.Frame(self, bg=CLR_NAV)
        tabs.pack(fill="x")
        tk.Button(tabs, text="Inbuilt Protocol", font=("Arial", 12, "bold"), relief="flat", bg=CLR_CARD).pack(side="left", fill="x", expand=True)
        tk.Button(tabs, text="Recent", font=("Arial", 12), relief="flat", bg=CLR_NAV).pack(side="left", fill="x", expand=True)

        # List
        self.lb = tk.Listbox(self, font=("Arial", 16), borderwidth=0, highlightthickness=0)
        self.lb.pack(fill="both", expand=True, padx=20, pady=10)
        for f in ["Plate_A_Rapid.g", "Wash_Cycle.g", "Genetics_Test_V1.g"]: self.lb.insert("end", f)

        # Footer Actions
        footer = tk.Frame(self, bg=CLR_CARD)
        footer.pack(fill="x", side="bottom", pady=10)
        
        tk.Button(footer, text="← BACK", font=("Arial", 14), width=10, 
                  command=lambda: controller.show_frame("Home")).pack(side="left", padx=20)
        
        tk.Button(footer, text="START ▶", bg=CLR_SUCCESS, fg="white", font=("Arial", 14, "bold"), width=15,
                  command=self.load_and_run).pack(side="right", padx=20)

    def load_and_run(self):
        try:
            selection = self.lb.get(self.lb.curselection())
            self.master.master.selected_file.set(selection) # Update global name
            self.master.master.show_frame("Running")
        except:
            messagebox.showwarning("Selection", "Please select a protocol first!")

# --- 4. RUNNING SCREEN (FIXED: Added Filename Label) ---
class Running(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=CLR_CARD)
        
        # Header showing filename
        tk.Label(self, text="Currently Running:", font=("Arial", 12), bg=CLR_CARD).pack(pady=(30,0))
        tk.Label(self, textvariable=controller.selected_file, font=("Arial", 18, "bold"), fg=CLR_PRIMARY, bg=CLR_CARD).pack()

        # Status
        tk.Label(self, text="Current Task:", font=("Arial", 12), bg=CLR_CARD).pack(pady=(40,5))
        self.task = tk.Label(self, text="G28: Home All Axis", font=("Arial", 16, "bold"), bg=CLR_CARD)
        self.task.pack()

        # Progress
        self.prog = ttk.Progressbar(self, length=400, mode="determinate")
        self.prog.pack(pady=40)
        self.prog["value"] = 15

        # Controls
        footer = tk.Frame(self, bg=CLR_CARD)
        footer.pack(side="bottom", pady=40)
        tk.Button(footer, text="⏸ PAUSE", font=("Arial", 14), width=10, command=lambda: messagebox.showinfo("System", "Paused")).pack(side="left", padx=10)
        tk.Button(footer, text="✖ CANCEL", font=("Arial", 14), width=10, bg=CLR_DANGER, fg="white", 
                  command=lambda: controller.show_frame("Home") if messagebox.askyesno("Confirm", "Stop all?") else None).pack(side="left", padx=10)

if __name__ == "__main__":
    app = KioskApp()
    app.mainloop()