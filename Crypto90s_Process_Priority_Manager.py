import psutil
import ctypes
import json
import os
import tkinter as tk
from tkinter import ttk
import webbrowser


current_version = "v0.0.2"

CONFIG_FILE = "process_priority_config.json"

PRIORITY_CLASSES = {
    "Idle": 0x00000040,
    "Below Normal": 0x00004000,
    "Normal": 0x00000020,
    "Above Normal": 0x00008000,
    "High": 0x00000080,
    "Realtime": 0x00000100,
}


def set_priority(pid, priority_class):
    try:
        handle = ctypes.windll.kernel32.OpenProcess(0x0200 | 0x0400, False, pid)
        if handle:
            ctypes.windll.kernel32.SetPriorityClass(handle, priority_class)
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    except Exception as e:
        print(f"[-] Could not set priority for PID {pid}: {e}")
    return False


def get_priority_class(pid):
    try:
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            priority = ctypes.windll.kernel32.GetPriorityClass(handle)
            ctypes.windll.kernel32.CloseHandle(handle)
            return priority
    except:
        return None


def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


class ProcessPriorityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto90's Process Priority Manager")

        dark_bg = "#2e2e2e"
        dark_fg = "#ffffff"
        highlight_color = "#3e3e3e"
        entry_bg = "#3a3a3a"
        self.root.configure(bg=dark_bg)

        style = ttk.Style()
        style.theme_use("default")

        style.configure("Treeview",
                        background=dark_bg,
                        foreground=dark_fg,
                        fieldbackground=dark_bg,
                        highlightthickness=0,
                        rowheight=25)

        style.map("Treeview",
                  background=[("selected", "#444444")],
                  foreground=[("selected", "#ffffff")])

        style.configure("TLabel", background=dark_bg, foreground=dark_fg)
        style.configure("TButton", background=highlight_color, foreground=dark_fg)
        style.configure("TCombobox",
                        fieldbackground=entry_bg,
                        background=entry_bg,
                        foreground=dark_fg)

        self.config = load_config()
        self.sort_column = None
        self.sort_reverse = False

        # Search field
        search_frame = tk.Frame(root, bg=dark_bg)
        search_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        tk.Label(search_frame, text="Search:", bg=dark_bg, fg=dark_fg).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: [self.apply_filter(), self.update_clear_button()])

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                     bg=entry_bg, fg=dark_fg, insertbackground=dark_fg)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.clear_search_btn = tk.Button(search_frame, text="Clear", command=self.clear_search,
                                          bg="#444444", fg=dark_fg, activebackground="#666666",
                                          activeforeground="#ffffff", cursor="hand2")
        self.clear_search_btn.pack(side=tk.LEFT, padx=5)
        self.clear_search_btn.pack_forget()  # initially hidden


        frame = tk.Frame(root, bg=dark_bg)
        frame.pack(fill=tk.BOTH, expand=True)

        columns = ("★", "Name", "PID", "Current Priority")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")

        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            if col == "★":
                self.tree.column(col, width=40, minwidth=40, stretch=False)
            elif col == "PID":
                self.tree.column(col, width=80, minwidth=80, stretch=False)
            elif col == "Current Priority":
                self.tree.column(col, width=120, minwidth=100, stretch=False)
            elif col == "Name":
                self.tree.column(col, width=200, minwidth=100, stretch=True)  # stretchable column

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.process_info = {}
        self.selected_priority = tk.StringVar(value="Normal")

        btn_frame = tk.Frame(root, bg=dark_bg)
        btn_frame.pack(pady=5)

        tk.Label(btn_frame, text="New Priority:", bg=dark_bg, fg=dark_fg).pack(side=tk.LEFT, padx=(0, 5))
        style = ttk.Style()
        style.theme_use("default")  # or "clam", "alt", "classic" depending on your platform

        style.configure("Custom.TCombobox",
                        foreground="black",         # text color
                        fieldbackground="white",  # background of the entry field
                        background="white")       # background of the whole widget

        self.priority_dropdown = ttk.Combobox(btn_frame,
                                values=list(PRIORITY_CLASSES.keys()),
                                width=15,
                                textvariable=self.selected_priority,
                                state="readonly",
                                style="Custom.TCombobox")
        self.priority_dropdown.pack(side=tk.LEFT)

        # Bind enter/leave to show hand cursor over Combobox widget
        self.priority_dropdown.bind("<Enter>", lambda e: e.widget.configure(cursor="hand2"))
        self.priority_dropdown.bind("<Leave>", lambda e: e.widget.configure(cursor=""))

        apply_btn = tk.Button(btn_frame, text="Change Priorities", command=self.apply_priorities,
                              bg="#006400", fg=dark_fg,  # dark green
                              activebackground="#004d00",
                              activeforeground="#ffffff", cursor="hand2")
        apply_btn.pack(side=tk.LEFT, padx=5)

        remove_btn = tk.Button(btn_frame, text="Remove Entry", command=self.remove_selected_from_config,
                               bg="#808080", fg=dark_fg,  # grey
                               activebackground="#666666",
                               activeforeground="#ffffff", cursor="hand2")
        remove_btn.pack(side=tk.LEFT, padx=5)

        reload_btn = tk.Button(btn_frame, text="Reload", command=self.load_processes,
                               bg="#2980b9", fg=dark_fg,  # blue
                               activebackground="#1f6391",  # darker shade of #2980b9
                               activeforeground="#ffffff", cursor="hand2")
        reload_btn.pack(side=tk.LEFT, padx=5)

        reset_config_btn = tk.Button(btn_frame, text="Reset Config", command=self.reset_config,
                                     bg="#8b0000", fg=dark_fg,  # dark red
                                     activebackground="#5a0000",
                                     activeforeground="#ffffff", cursor="hand2")
        reset_config_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Buy me a Coffee ☕", 
              bg="#f39c12", fg="black", 
              activebackground="#d68910", activeforeground="black",
              cursor="hand2",
              command=lambda: webbrowser.open("https://ko-fi.com/crypto90")).pack(side="left", padx=5)



        # Console frame at the bottom
        console_frame = tk.Frame(root, bg=dark_bg)
        console_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=(0, 5))

        self.console_text = tk.Text(console_frame, height=8, bg="#1e1e1e", fg="#00ff00", insertbackground="#00ff00",
                                    state=tk.DISABLED, wrap=tk.WORD)
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        console_scroll = ttk.Scrollbar(console_frame, orient="vertical", command=self.console_text.yview)
        console_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.console_text.configure(yscrollcommand=console_scroll.set)

        # Bind Treeview mouse motion for hand cursor on headers and rows
        self.tree.bind("<Motion>", self.on_tree_motion)
        self.tree.bind("<Leave>", lambda e: self.tree.configure(cursor=""))
        
        
        # Adding copyright and thanks message to the log output
        self.log(f"------------------------------------------------")
        self.log(f"Crypto90's Process Priority Manager {current_version}. All rights reserved.")
        self.log(f"Thanks for using! Find the source code here:\nhttps://github.com/Crypto90/ProcessPriorityManager")
        self.log(f"------------------------------------------------")
        
        
        # Initialize
        self.load_processes()
    
    def update_clear_button(self):
        if self.search_var.get().strip():
            self.clear_search_btn.pack(side=tk.LEFT, padx=5)
        else:
            self.clear_search_btn.pack_forget()

    def clear_search(self):
        self.search_var.set("")
        self.apply_filter()

    def reset_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                os.remove(CONFIG_FILE)
                self.log("[*] Config file removed.")
            except Exception as e:
                self.log(f"[-] Failed to remove config file: {e}")
        else:
            self.log("[*] No config file to remove.")
        self.config.clear()
        self.load_processes()
        self.log("[*] Configuration reset and process list reloaded.")

    def on_tree_motion(self, event):
        # Detect if mouse is over header or over a row
        region = self.tree.identify_region(event.x, event.y)
        if region in ("heading", "cell"):
            self.tree.configure(cursor="hand2")
        else:
            self.tree.configure(cursor="")

    def log(self, message):
        self.console_text.configure(state=tk.NORMAL)
        self.console_text.insert(tk.END, message + "\n")
        self.console_text.see(tk.END)
        self.console_text.configure(state=tk.DISABLED)

    def remove_selected_from_config(self):
        updated = False
        for item in self.tree.selection():
            pid = int(item)
            name = self.process_info.get(pid, "")
            if name in self.config:
                del self.config[name]
                updated = True
        if updated:
            save_config(self.config)
            self.log("Selected entries removed from config.")
            self.load_processes()
        else:
            self.log("No matching config entries found to remove.")

    def apply_filter(self):
        self.refresh_treeview()

    def load_processes(self):
        self.tree.delete(*self.tree.get_children())
        self.process_info.clear()
        self.process_data = []

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                priority = get_priority_class(pid)
                if priority is None:
                    continue
                priority_name = next((k for k, v in PRIORITY_CLASSES.items() if v == priority), "Unknown")
                self.process_info[pid] = name
                is_favorite = "★" if name in self.config else ""
                tag = "saved" if is_favorite else ""
                self.process_data.append((is_favorite, name, pid, priority_name, tag))

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.refresh_treeview()
        self.tree.tag_configure("saved", background="#005f00", foreground="#ffffff")  # dark green
        self.log("Process list loaded.")
        self.apply_saved_config()
        if self.sort_column:
            self.sort_by_column(self.sort_column, restore=True)


    def refresh_treeview(self):
        search_text = self.search_var.get().lower().strip()
        self.tree.delete(*self.tree.get_children())
        for favorite, name, pid, priority_name, tag in self.process_data:
            if (search_text in name.lower()
                    or search_text in str(pid)
                    or search_text in priority_name.lower()):
                self.tree.insert("", tk.END, iid=str(pid), values=(favorite, name, pid, priority_name), tags=(tag,))

    def sort_by_column(self, col, restore=False):
        if not restore:
            if self.sort_column == col:
                self.sort_reverse = not self.sort_reverse
            else:
                self.sort_column = col
                self.sort_reverse = False

        reverse = self.sort_reverse

        index = {"★": 0, "Name": 1, "PID": 2, "Current Priority": 3}[col]

        if col == "PID":
            self.process_data.sort(key=lambda x: int(x[index]), reverse=reverse)
        else:
            self.process_data.sort(key=lambda x: str(x[index]).lower(), reverse=reverse)

        # Update header text with arrows
        for heading in self.tree["columns"]:
            arrow = ""
            if heading == self.sort_column:
                arrow = " ▲" if not reverse else " ▼"
            self.tree.heading(heading, text=heading + arrow, command=lambda c=heading: self.sort_by_column(c))

        self.refresh_treeview()



    def apply_priorities(self):
        selected_items = self.tree.selection()
        if not selected_items:
            self.log("No processes selected.")
            return

        new_priority_name = self.selected_priority.get()
        new_priority_value = PRIORITY_CLASSES.get(new_priority_name, PRIORITY_CLASSES["Normal"])

        for item in selected_items:
            pid = int(item)
            name = self.process_info.get(pid, None)
            if name:
                if set_priority(pid, new_priority_value):
                    self.config[name] = new_priority_name
                    self.log(f"[+] Set priority '{new_priority_name}' for {name} (PID {pid})")
                else:
                    self.log(f"[-] Failed to set priority for {name} (PID {pid})")

        save_config(self.config)
        self.load_processes()

    def apply_saved_config(self):
        # Apply saved priority config to running processes on startup
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name']
                pid = proc.info['pid']
                if name in self.config:
                    priority_name = self.config[name]
                    priority_value = PRIORITY_CLASSES.get(priority_name, PRIORITY_CLASSES["Normal"])
                    set_priority(pid, priority_value)
                    self.log(f"Set priority '{priority_name}' for process '{name}' (PID: {pid}).")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue



if __name__ == "__main__":
    root = tk.Tk()
    app = ProcessPriorityApp(root)
    root.mainloop()
