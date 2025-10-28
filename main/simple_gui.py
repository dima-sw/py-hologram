import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from main import th

class SimpleHologramApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hologram Studio v2.0")
        self.root.geometry("700x500")
        self.root.configure(bg='#f0f0f0')
        
        # Variables
        self.selected_file = None
        self.processing_thread = None
        self.is_processing = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self.create_header(main_frame)
        
        # Content area
        content_frame = tk.Frame(main_frame, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # File selection
        self.create_file_selection(content_frame)
        
        # Settings
        self.create_settings(content_frame)
        
        # Generate button
        self.create_generate_button(content_frame)
        
        # Progress section
        self.create_progress_section(content_frame)
        
    def create_header(self, parent):
        header_frame = tk.Frame(parent, bg='#2c3e50', height=60)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="🎬 HOLOGRAM STUDIO v2.0",
            font=('Arial', 20, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(pady=15)
        
    def create_file_selection(self, parent):
        # File selection frame
        file_frame = tk.LabelFrame(
            parent,
            text="Select Video File",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        file_frame.pack(fill=tk.X, pady=10)
        
        # Button and status
        button_frame = tk.Frame(file_frame, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        select_btn = tk.Button(
            button_frame,
            text="📁 Choose Video File",
            font=('Arial', 11, 'bold'),
            bg='#3498db',
            fg='white',
            relief=tk.RAISED,
            padx=20,
            pady=8,
            command=self.select_file,
            cursor='hand2'
        )
        select_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        self.file_status_label = tk.Label(
            button_frame,
            text="No file selected",
            font=('Arial', 11),
            fg='#7f8c8d',
            bg='#f0f0f0',
            anchor=tk.W
        )
        self.file_status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
    def create_settings(self, parent):
        # Settings frame
        settings_frame = tk.LabelFrame(
            parent,
            text="Processing Settings",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        settings_frame.pack(fill=tk.X, pady=10)
        
        # Settings content
        settings_content = tk.Frame(settings_frame, bg='#f0f0f0')
        settings_content.pack(fill=tk.X, padx=10, pady=10)
        
        # Multi-threading
        threading_frame = tk.Frame(settings_content, bg='#f0f0f0')
        threading_frame.pack(fill=tk.X, pady=5)
        
        self.threading_var = tk.BooleanVar(value=True)
        threading_check = tk.Checkbutton(
            threading_frame,
            text="Multi-threading (Recommended for faster processing)",
            font=('Arial', 11),
            fg='#2c3e50',
            bg='#f0f0f0',
            variable=self.threading_var
        )
        threading_check.pack(anchor=tk.W)
        
        # Frame width
        width_frame = tk.Frame(settings_content, bg='#f0f0f0')
        width_frame.pack(fill=tk.X, pady=5)
        
        width_label = tk.Label(
            width_frame,
            text="Frame Width:",
            font=('Arial', 11),
            fg='#2c3e50',
            bg='#f0f0f0'
        )
        width_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.width_var = tk.StringVar(value="300")
        width_entry = tk.Entry(
            width_frame,
            textvariable=self.width_var,
            font=('Arial', 11),
            width=10
        )
        width_entry.pack(side=tk.LEFT)
        
        px_label = tk.Label(
            width_frame,
            text="pixels",
            font=('Arial', 11),
            fg='#7f8c8d',
            bg='#f0f0f0'
        )
        px_label.pack(side=tk.LEFT, padx=(5, 0))
        
    def create_generate_button(self, parent):
        button_frame = tk.Frame(parent, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=20)
        
        self.generate_btn = tk.Button(
            button_frame,
            text="🚀 GENERATE HOLOGRAM VIDEO",
            font=('Arial', 14, 'bold'),
            bg='#27ae60',
            fg='white',
            relief=tk.RAISED,
            padx=30,
            pady=12,
            command=self.generate_hologram,
            cursor='hand2'
        )
        self.generate_btn.pack()
        
        # Info text
        info_label = tk.Label(
            button_frame,
            text="This may take several minutes depending on video length",
            font=('Arial', 10),
            fg='#7f8c8d',
            bg='#f0f0f0'
        )
        info_label.pack(pady=(8, 0))
        
    def create_progress_section(self, parent):
        # Progress frame
        progress_frame = tk.LabelFrame(
            parent,
            text="Progress",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        progress_frame.pack(fill=tk.X, pady=10)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(padx=10, pady=(10, 5))
        
        # Progress label
        self.progress_label = tk.Label(
            progress_frame,
            text="Ready to process",
            font=('Arial', 11),
            fg='#7f8c8d',
            bg='#f0f0f0'
        )
        self.progress_label.pack(padx=10, pady=(0, 10))
        
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
                fg='#27ae60'
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
            bg='#95a5a6',
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
            # Create progress callback
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
            bg='#27ae60',
            state='normal'
        )
        self.progress_var.set(100)
        self.progress_label.config(
            text="✅ Hologram video generated successfully!",
            fg='#27ae60'
        )
        messagebox.showinfo("Success", "Hologram video has been generated successfully!")
        
    def processing_error(self, error_msg):
        self.is_processing = False
        self.generate_btn.config(
            text="🚀 GENERATE HOLOGRAM VIDEO",
            bg='#27ae60',
            state='normal'
        )
        self.progress_label.config(
            text="❌ Processing failed",
            fg='#e74c3c'
        )
        messagebox.showerror("Error", f"Processing failed: {error_msg}")


def main():
    root = tk.Tk()
    app = SimpleHologramApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
