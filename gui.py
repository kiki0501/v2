import tkinter as tk
from tkinter import ttk
import threading
import sys
import json
import time
import ctypes

# Enable High DPI Awareness on Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class StreamRedirector:
    def __init__(self, text_widget, tag="stdout"):
        self.text_widget = text_widget
        self.tag = tag

    def write(self, message):
        def _append():
            try:
                self.text_widget.configure(state="normal")
                self.text_widget.insert("end", message, self.tag)
                self.text_widget.see("end")
                self.text_widget.configure(state="disabled")
            except:
                pass
        try:
            self.text_widget.after(0, _append)
        except:
            pass

    def flush(self):
        pass

    def isatty(self):
        return False

class MacWindow:
    def __init__(self, root, stats_manager):
        self.root = root
        self.stats_manager = stats_manager
        self.root.title("Vertex AI Proxy")
        self.root.geometry("800x500")
        self.root.configure(bg="#1E1E1E")
        self.root.overrideredirect(True)  # Remove native title bar

        # --- Styles ---
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#1E1E1E")
        style.configure("Sidebar.TFrame", background="#252526")
        style.configure("TitleBar.TFrame", background="#323233")
        
        # --- Title Bar ---
        self.title_bar = tk.Frame(self.root, bg="#323233", height=32)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.pack_propagate(False)
        
        # Dragging logic
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<ButtonRelease-1>", self.stop_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)

        # Traffic Lights
        self.btn_frame = tk.Frame(self.title_bar, bg="#323233")
        self.btn_frame.pack(side="left", padx=12)
        
        self.close_btn = self.create_circle_btn("#FF5F57", self.close_app)
        self.min_btn = self.create_circle_btn("#FEBC2E", self.minimize_app)
        self.max_btn = self.create_circle_btn("#28C840", lambda: None)

        # Title
        self.title_label = tk.Label(self.title_bar, text="Vertex AI 代理服务器", bg="#323233", fg="#CCCCCC", font=("Microsoft YaHei UI", 9))
        self.title_label.pack(side="left", padx=10)

        # --- Main Layout ---
        self.content_area = tk.Frame(self.root, bg="#1E1E1E")
        self.content_area.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.content_area, bg="#252526", width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Sidebar Content
        tk.Label(self.sidebar, text="统计信息", bg="#252526", fg="#858585", font=("Microsoft YaHei UI", 9, "bold")).pack(anchor="w", padx=15, pady=(20, 10))
        
        self.stats_labels = {}
        self.create_stat_item("总请求数", "0")
        self.create_stat_item("总 Token 数", "0")
        self.create_stat_item("提示词 Token", "0")
        self.create_stat_item("补全 Token", "0")

        tk.Frame(self.sidebar, bg="#3E3E42", height=1).pack(fill="x", padx=15, pady=20)

        # Actions
        tk.Label(self.sidebar, text="操作", bg="#252526", fg="#858585", font=("Microsoft YaHei UI", 9, "bold")).pack(anchor="w", padx=15, pady=(0, 10))
        
        self.create_action_btn("清空日志", self.clear_logs)
        self.create_action_btn("复制统计", self.copy_stats)

        # Log Area
        self.log_frame = tk.Frame(self.content_area, bg="#1E1E1E")
        self.log_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.log_text = tk.Text(self.log_frame, bg="#1E1E1E", fg="#D4D4D4", font=("Consolas", 10), borderwidth=0, highlightthickness=0, state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=self.scrollbar.set)

        # Redirect stdout/stderr
        sys.stdout = StreamRedirector(self.log_text, "stdout")
        sys.stderr = StreamRedirector(self.log_text, "stderr")

        # Window Dragging State
        self.x = 0
        self.y = 0

        # Fix Taskbar Icon (Windows)
        self.root.after(10, self.set_app_window)

        # Start Stats Polling
        self.update_stats()

    def set_app_window(self):
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_TOOLWINDOW
            style = style | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            # Force re-render of window styles
            self.root.wm_withdraw()
            self.root.wm_deiconify()
        except Exception as e:
            print(f"Warning: Could not set taskbar icon: {e}")

    def create_circle_btn(self, color, command):
        canvas = tk.Canvas(self.btn_frame, width=12, height=12, bg="#323233", highlightthickness=0)
        canvas.pack(side="left", padx=4)
        canvas.create_oval(1, 1, 11, 11, fill=color, outline=color)
        canvas.bind("<Button-1>", lambda e: command())
        return canvas

    def create_stat_item(self, label, value):
        frame = tk.Frame(self.sidebar, bg="#252526")
        frame.pack(fill="x", padx=15, pady=4)
        tk.Label(frame, text=label, bg="#252526", fg="#CCCCCC", font=("Microsoft YaHei UI", 9)).pack(anchor="w")
        val_label = tk.Label(frame, text=value, bg="#252526", fg="#007ACC", font=("Microsoft YaHei UI", 11, "bold"))
        val_label.pack(anchor="w")
        self.stats_labels[label] = val_label

    def create_action_btn(self, text, command):
        btn = tk.Button(self.sidebar, text=text, bg="#3E3E42", fg="#FFFFFF", font=("Microsoft YaHei UI", 9),
                        relief="flat", activebackground="#505050", activeforeground="#FFFFFF",
                        command=command, padx=10, pady=5, borderwidth=0)
        btn.pack(fill="x", padx=15, pady=4)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def close_app(self):
        self.root.destroy()
        sys.exit(0)

    def minimize_app(self):
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.bind("<FocusIn>", self.restore_window)

    def restore_window(self, event):
        if self.root.state() == "normal":
            self.root.overrideredirect(True)
            self.root.unbind("<FocusIn>")

    def clear_logs(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def copy_stats(self):
        stats = self.stats_manager.stats
        text = json.dumps(stats, indent=2)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        print("📋 统计信息已复制到剪贴板")

    def update_stats(self):
        try:
            stats = self.stats_manager.stats
            self.stats_labels["总请求数"].config(text=str(stats.get("total_requests", 0)))
            self.stats_labels["总 Token 数"].config(text=str(stats.get("total_tokens", 0)))
            self.stats_labels["提示词 Token"].config(text=str(stats.get("prompt_tokens", 0)))
            self.stats_labels["补全 Token"].config(text=str(stats.get("completion_tokens", 0)))
        except:
            pass
        self.root.after(1000, self.update_stats)

def run(server_func, stats_manager):
    root = tk.Tk()
    app = MacWindow(root, stats_manager)
    
    # Start server thread
    t = threading.Thread(target=server_func, daemon=True)
    t.start()
    
    root.mainloop()