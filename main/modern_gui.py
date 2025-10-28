import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from main import th
import time

class ModernHologramApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hologram Studio v2.0")
        self.root.geometry("800x600")
        self.root.configure(bg='#1a1a1a')
        
        # Variables
        self.selected_file = None
        self.processing_thread = None
        self.is_processing = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self.create_header(main_frame)
        
        # Content area
        content_frame = tk.Frame(main_frame, bg='#1a1a1a')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # File selection card
        self.create_file_selection_card(content_frame)
        
        # Settings card
        self.create_settings_card(content_frame)
        
        # Generate button
        self.create_generate_button(content_frame)
        
        # Progress section
        self.create_progress_section(content_frame)
        
    def create_header(self, parent):
        header_frame = tk.Frame(parent, bg='#2d2d2d', height=80)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="🎬 HOLOGRAM STUDIO",
            font=('Segoe UI', 24, 'bold'),
            fg='#ffffff',
            bg='#2d2d2d'
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=20)
        
        # Version
        version_label = tk.Label(
            header_frame,
            text="v2.0",
            font=('Segoe UI', 12),
            fg='#888888',
            bg='#2d2d2d'
        )
        version_label.pack(side=tk.RIGHT, padx=20, pady=20)
        
    def create_file_selection_card(self, parent):
        # Card frame
        card_frame = tk.Frame(parent, bg='#2d2d2d', relief=tk.RAISED, bd=1)
        card_frame.pack(fill=tk.X, pady=10)
        
        # Card title
        title_label = tk.Label(
            card_frame,
            text="SELECT VIDEO FILE",
            font=('Segoe UI', 14, 'bold'),
            fg='#ffffff',
            bg='#2d2d2d'
        )
        title_label.pack(anchor=tk.W, padx=20, pady=(20, 10))
        
        # File selection area
        file_frame = tk.Frame(card_frame, bg='#2d2d2d')
        file_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Select button
        select_btn = tk.Button(
            file_frame,
            text="📁 Choose Video File",
            font=('Segoe UI', 12, 'bold'),
            bg='#0078d4',
            fg='#ffffff',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=self.select_file,
            cursor='hand2'
        )
        select_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # File status
        self.file_status_label = tk.Label(
            file_frame,
            text="No file selected",
            font=('Segoe UI', 11),
            fg='#888888',
            bg='#2d2d2d',
            anchor=tk.W
        )
        self.file_status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
    def create_settings_card(self, parent):
        # Card frame
        card_frame = tk.Frame(parent, bg='#2d2d2d', relief=tk.RAISED, bd=1)
        card_frame.pack(fill=tk.X, pady=10)
        
        # Card title
        title_label = tk.Label(
            card_frame,
            text="PROCESSING SETTINGS",
            font=('Segoe UI', 14, 'bold'),
            fg='#ffffff',
            bg='#2d2d2d'
        )
        title_label.pack(anchor=tk.W, padx=20, pady=(20, 10))
        
        # Settings area
        settings_frame = tk.Frame(card_frame, bg='#2d2d2d')
        settings_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Multi-threading checkbox
        threading_frame = tk.Frame(settings_frame, bg='#2d2d2d')
        threading_frame.pack(fill=tk.X, pady=5)
        
        self.threading_var = tk.BooleanVar(value=True)
        threading_check = tk.Checkbutton(
            threading_frame,
            text="Multi-threading (Recommended)",
            font=('Segoe UI', 11),
            fg='#ffffff',
            bg='#2d2d2d',
            selectcolor='#0078d4',
            variable=self.threading_var,
            activebackground='#2d2d2d',
            activeforeground='#ffffff'
        )
        threading_check.pack(side=tk.LEFT)
        
        # Frame width setting
        width_frame = tk.Frame(settings_frame, bg='#2d2d2d')
        width_frame.pack(fill=tk.X, pady=5)
        
        width_label = tk.Label(
            width_frame,
            text="Frame Width:",
            font=('Segoe UI', 11),
            fg='#ffffff',
            bg='#2d2d2d'
        )
        width_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.width_var = tk.StringVar(value="300")
        width_entry = tk.Entry(
            width_frame,
            textvariable=self.width_var,
            font=('Segoe UI', 11),
            width=10,
            bg='#404040',
            fg='#ffffff',
            insertbackground='#ffffff',
            relief=tk.FLAT
        )
        width_entry.pack(side=tk.LEFT)
        
        px_label = tk.Label(
            width_frame,
            text="px",
            font=('Segoe UI', 11),
            fg='#888888',
            bg='#2d2d2d'
        )
        px_label.pack(side=tk.LEFT, padx=(5, 0))
        
    def create_generate_button(self, parent):
        button_frame = tk.Frame(parent, bg='#1a1a1a')
        button_frame.pack(fill=tk.X, pady=20)
        
        self.generate_btn = tk.Button(
            button_frame,
            text="🚀 GENERATE HOLOGRAM VIDEO",
            font=('Segoe UI', 16, 'bold'),
            bg='#00a86b',
            fg='#ffffff',
            relief=tk.FLAT,
            padx=30,
            pady=15,
            command=self.generate_hologram,
            cursor='hand2'
        )
        self.generate_btn.pack()
        
        # Info label
        info_label = tk.Label(
            button_frame,
            text="This may take several minutes depending on video length",
            font=('Segoe UI', 10),
            fg='#888888',
            bg='#1a1a1a'
        )
        info_label.pack(pady=(10, 0))
        
    def create_progress_section(self, parent):
        # Progress frame
        progress_frame = tk.Frame(parent, bg='#2d2d2d', relief=tk.RAISED, bd=1)
        progress_frame.pack(fill=tk.X, pady=10)
        
        # Progress title
        title_label = tk.Label(
            progress_frame,
            text="PROGRESS",
            font=('Segoe UI', 14, 'bold'),
            fg='#ffffff',
            bg='#2d2d2d'
        )
        title_label.pack(anchor=tk.W, padx=20, pady=(20, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(padx=20, pady=(0, 10))
        
        # Progress label
        self.progress_label = tk.Label(
            progress_frame,
            text="Ready to process",
            font=('Segoe UI', 11),
            fg='#888888',
            bg='#2d2d2d'
        )
        self.progress_label.pack(padx=20, pady=(0, 20))
        
    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.selected_file = file_path
            filename = os.path.basename(file_path)
            self.file_status_label.config(
                text=f"✓ {filename}",
                fg='#00a86b'
            )
            
    def generate_hologram(self):
        if not self.selected_file:
            messagebox.showerror("Error", "Please select a video file first!")
            return
            
        if self.is_processing:
            messagebox.showwarning("Warning", "Processing is already in progress!")
            return
            
        # Start processing
        self.is_processing = True
        self.generate_btn.config(
            text="⏳ PROCESSING...",
            bg='#666666',
            state='disabled'
        )
        
        # Reset progress
        self.progress_var.set(0)
        self.progress_label.config(text="Starting processing...")
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_video)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def process_video(self):
        try:
            # Create a custom progress callback
            class ProgressCallback:
                def __init__(self, app):
                    self.app = app
                    
                def update_progress(self, text):
                    self.app.root.after(0, lambda: self.app.update_progress(text))
            
            callback = ProgressCallback(self)
            
            # Start hologram processing
            processing_thread = th(
                self.selected_file,
                callback,
                threading=self.threading_var.get()
            )
            processing_thread.start()
            processing_thread.join()
            
            # Complete
            self.root.after(0, self.processing_complete)
            
        except Exception as e:
            self.root.after(0, lambda: self.processing_error(str(e)))
            
    def update_progress(self, text):
        self.progress_label.config(text=text)
        
        # Extract percentage from text if available
        if "%" in text:
            try:
                percent = int(text.split("%")[0].split()[-1])
                self.progress_var.set(percent)
            except:
                pass
                
    def processing_complete(self):
        self.is_processing = False
        self.generate_btn.config(
            text="🚀 GENERATE HOLOGRAM VIDEO",
            bg='#00a86b',
            state='normal'
        )
        self.progress_var.set(100)
        self.progress_label.config(
            text="✅ Hologram video generated successfully!",
            fg='#00a86b'
        )
        messagebox.showinfo("Success", "Hologram video has been generated successfully!")
        
    def processing_error(self, error_msg):
        self.is_processing = False
        self.generate_btn.config(
            text="🚀 GENERATE HOLOGRAM VIDEO",
            bg='#00a86b',
            state='normal'
        )
        self.progress_label.config(
            text="❌ Processing failed",
            fg='#ff4444'
        )
        messagebox.showerror("Error", f"Processing failed: {error_msg}")


def main():
    root = tk.Tk()
    app = ModernHologramApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
