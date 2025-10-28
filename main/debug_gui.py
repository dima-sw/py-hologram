import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import time
import subprocess
import platform
import traceback
from main import th

class DebugHologramApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hologram Studio v2.0 - Debug Version")
        self.root.geometry("1000x800")
        self.root.configure(bg='#0d1117')
        
        # Variables
        self.selected_file = None
        self.processing_thread = None
        self.is_processing = False
        self.progress_value = 0
        self.output_path = None
        self.debug_log = []
        
        # Modern color palette
        self.colors = {
            'bg_primary': '#0d1117',
            'bg_secondary': '#161b22',
            'bg_tertiary': '#21262d',
            'accent_primary': '#00d4aa',
            'accent_secondary': '#7c3aed',
            'text_primary': '#f0f6fc',
            'text_secondary': '#8b949e',
            'text_muted': '#6e7681',
            'border': '#30363d',
            'success': '#3fb950',
            'warning': '#f85149',
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self.create_header(main_frame)
        
        # Content with debug panel
        content_frame = tk.Frame(main_frame, bg=self.colors['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Left panel
        left_panel = tk.Frame(content_frame, bg=self.colors['bg_primary'])
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Right panel (debug)
        right_panel = tk.Frame(content_frame, bg=self.colors['bg_primary'])
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # Cards
        self.create_file_card(left_panel)
        self.create_settings_card(left_panel)
        self.create_progress_card(left_panel)
        self.create_action_buttons(left_panel)
        
        # Debug panel
        self.create_debug_panel(right_panel)
        
    def create_header(self, parent):
        header_frame = tk.Frame(parent, bg=self.colors['bg_secondary'], height=60)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)
        
        header_content = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        header_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        title_label = tk.Label(
            header_content,
            text="HOLOGRAM STUDIO - DEBUG",
            font=('Arial', 20, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        title_label.pack(side=tk.LEFT)
        
        version_label = tk.Label(
            header_content,
            text="v2.0",
            font=('Arial', 12, 'bold'),
            fg=self.colors['accent_primary'],
            bg=self.colors['bg_secondary']
        )
        version_label.pack(side=tk.RIGHT)
        
    def create_file_card(self, parent):
        card = self.create_card(parent, "VIDEO SOURCE")
        
        file_area = tk.Frame(card, bg=self.colors['bg_tertiary'])
        file_area.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.file_button = tk.Button(
            file_area,
            text="📁 SELECT VIDEO FILE",
            font=('Arial', 11, 'bold'),
            bg=self.colors['accent_primary'],
            fg=self.colors['bg_primary'],
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=self.select_file,
            cursor='hand2',
            bd=0
        )
        self.file_button.pack(fill=tk.X, pady=(0, 10))
        
        self.file_status_label = tk.Label(
            file_area,
            text="No file selected",
            font=('Arial', 10),
            fg=self.colors['text_muted'],
            bg=self.colors['bg_tertiary']
        )
        self.file_status_label.pack(anchor=tk.W)
        
    def create_settings_card(self, parent):
        card = self.create_card(parent, "PROCESSING SETTINGS")
        
        settings_area = tk.Frame(card, bg=self.colors['bg_tertiary'])
        settings_area.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Multi-threading
        threading_frame = tk.Frame(settings_area, bg=self.colors['bg_tertiary'])
        threading_frame.pack(fill=tk.X, pady=(0, 15))
        
        threading_label = tk.Label(
            threading_frame,
            text="Multi-threading",
            font=('Arial', 10, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary']
        )
        threading_label.pack(side=tk.LEFT)
        
        self.threading_var = tk.BooleanVar(value=True)
        threading_check = tk.Checkbutton(
            threading_frame,
            variable=self.threading_var,
            bg=self.colors['bg_tertiary'],
            fg=self.colors['text_primary'],
            selectcolor=self.colors['accent_primary'],
            activebackground=self.colors['bg_tertiary'],
            activeforeground=self.colors['text_primary']
        )
        threading_check.pack(side=tk.RIGHT)
        
        # Frame width
        width_frame = tk.Frame(settings_area, bg=self.colors['bg_tertiary'])
        width_frame.pack(fill=tk.X)
        
        width_label = tk.Label(
            width_frame,
            text="Frame Width",
            font=('Arial', 10, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary']
        )
        width_label.pack(side=tk.LEFT)
        
        self.width_var = tk.StringVar(value="300")
        width_entry = tk.Entry(
            width_frame,
            textvariable=self.width_var,
            font=('Arial', 10),
            width=8,
            bg=self.colors['bg_secondary'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief=tk.FLAT,
            bd=1
        )
        width_entry.pack(side=tk.RIGHT, padx=(10, 0))
        
    def create_progress_card(self, parent):
        card = self.create_card(parent, "PROGRESS")
        
        progress_area = tk.Frame(card, bg=self.colors['bg_tertiary'])
        progress_area.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_area,
            variable=self.progress_var,
            maximum=100,
            length=200,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Progress text
        self.progress_label = tk.Label(
            progress_area,
            text="Ready to process",
            font=('Arial', 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_tertiary'],
            wraplength=200
        )
        self.progress_label.pack(anchor=tk.W)
        
        # Status
        self.status_label = tk.Label(
            progress_area,
            text="● Ready",
            font=('Arial', 10),
            fg=self.colors['text_muted'],
            bg=self.colors['bg_tertiary']
        )
        self.status_label.pack(anchor=tk.W, pady=(5, 0))
        
    def create_action_buttons(self, parent):
        button_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Button container
        btn_container = tk.Frame(button_frame, bg=self.colors['bg_primary'])
        btn_container.pack()
        
        self.generate_button = tk.Button(
            btn_container,
            text="🚀 RENDER HOLOGRAM",
            font=('Arial', 12, 'bold'),
            bg=self.colors['accent_secondary'],
            fg=self.colors['text_primary'],
            relief=tk.FLAT,
            padx=30,
            pady=12,
            command=self.generate_hologram,
            cursor='hand2',
            bd=0
        )
        self.generate_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.open_folder_button = tk.Button(
            btn_container,
            text="📂 OPEN FOLDER",
            font=('Arial', 10, 'bold'),
            bg=self.colors['accent_primary'],
            fg=self.colors['bg_primary'],
            relief=tk.FLAT,
            padx=15,
            pady=12,
            command=self.open_output_folder,
            cursor='hand2',
            bd=0
        )
        self.open_folder_button.pack(side=tk.LEFT)
        
    def create_debug_panel(self, parent):
        debug_card = self.create_card(parent, "DEBUG LOG")
        
        debug_area = tk.Frame(debug_card, bg=self.colors['bg_tertiary'])
        debug_area.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Debug text area
        self.debug_text = tk.Text(
            debug_area,
            height=20,
            width=40,
            bg=self.colors['bg_secondary'],
            fg=self.colors['text_primary'],
            font=('Consolas', 9),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.debug_text.pack(fill=tk.BOTH, expand=True)
        
        # Clear button
        clear_button = tk.Button(
            debug_area,
            text="Clear Log",
            font=('Arial', 9),
            bg=self.colors['text_muted'],
            fg=self.colors['text_primary'],
            relief=tk.FLAT,
            padx=10,
            pady=5,
            command=self.clear_debug_log,
            cursor='hand2',
            bd=0
        )
        clear_button.pack(pady=(10, 0))
        
    def create_card(self, parent, title):
        card_frame = tk.Frame(parent, bg=self.colors['bg_tertiary'], relief=tk.FLAT, bd=1)
        card_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        header_frame = tk.Frame(card_frame, bg=self.colors['bg_tertiary'])
        header_frame.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        title_label = tk.Label(
            header_frame,
            text=title,
            font=('Arial', 11, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary']
        )
        title_label.pack(anchor=tk.W)
        
        return card_frame
        
    def log_debug(self, message):
        """Add message to debug log"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.debug_log.append(log_message)
        
        # Update debug text
        self.debug_text.config(state=tk.NORMAL)
        self.debug_text.insert(tk.END, log_message)
        self.debug_text.see(tk.END)
        self.debug_text.config(state=tk.DISABLED)
        
    def clear_debug_log(self):
        """Clear debug log"""
        self.debug_text.config(state=tk.NORMAL)
        self.debug_text.delete(1.0, tk.END)
        self.debug_text.config(state=tk.DISABLED)
        self.debug_log.clear()
        
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
                fg=self.colors['success']
            )
            self.log_debug(f"Selected file: {filename}")
            
    def generate_hologram(self):
        if not self.selected_file:
            messagebox.showerror("Error", "Please select a video file first!")
            return
            
        if self.is_processing:
            messagebox.showwarning("Warning", "Processing is already in progress!")
            return
            
        # Clear debug log
        self.clear_debug_log()
        self.log_debug("Starting hologram generation...")
        
        # Ensure output directory exists
        output_dir = "holograms"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            self.log_debug(f"Created output directory: {output_dir}")
        else:
            self.log_debug(f"Output directory exists: {output_dir}")
            
        # Start processing
        self.is_processing = True
        self.generate_button.config(
            text="⏳ PROCESSING...",
            bg=self.colors['text_muted'],
            state='disabled'
        )
        
        # Reset progress
        self.progress_var.set(0)
        self.progress_label.config(text="Starting processing...")
        self.status_label.config(text="● Processing", fg=self.colors['accent_primary'])
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_video_thread)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Start progress simulation
        self.simulate_progress()
        
    def simulate_progress(self):
        """Simulate progress updates"""
        if not self.is_processing:
            return
            
        current_progress = self.progress_var.get()
        
        if current_progress < 20:
            self.progress_label.config(text="Loading video...")
            self.progress_var.set(20)
            self.log_debug("Loading video...")
        elif current_progress < 40:
            self.progress_label.config(text="Processing frames...")
            self.progress_var.set(40)
            self.log_debug("Processing frames...")
        elif current_progress < 60:
            self.progress_label.config(text="Creating hologram layout...")
            self.progress_var.set(60)
            self.log_debug("Creating hologram layout...")
        elif current_progress < 80:
            self.progress_label.config(text="Generating hologram frames...")
            self.progress_var.set(80)
            self.log_debug("Generating hologram frames...")
        elif current_progress < 95:
            self.progress_label.config(text="Saving video...")
            self.progress_var.set(95)
            self.log_debug("Saving video...")
        else:
            self.progress_var.set(100)
            self.progress_label.config(text="✅ Complete!")
            self.status_label.config(text="● Complete", fg=self.colors['success'])
            self.processing_complete()
            return
            
        # Continue simulation
        self.root.after(2000, self.simulate_progress)
        
    def process_video_thread(self):
        """Process video in separate thread with detailed error handling"""
        try:
            self.log_debug(f"Processing file: {self.selected_file}")
            self.log_debug(f"Threading enabled: {self.threading_var.get()}")
            self.log_debug(f"Frame width: {self.width_var.get()}")
            
            # Create a progress callback
            class ProgressCallback:
                def __init__(self, app):
                    self.app = app
                    
                def update_progress(self, text):
                    self.app.root.after(0, lambda: self.app.log_debug(f"Progress: {text}"))
            
            callback = ProgressCallback(self)
            
            # Start hologram processing
            self.log_debug("Starting hologram processing thread...")
            processing_thread = th(
                self.selected_file,
                callback,
                threading=self.threading_var.get()
            )
            processing_thread.start()
            self.log_debug("Hologram processing thread started")
            
            processing_thread.join()
            self.log_debug("Hologram processing thread completed")
            
            # Complete
            self.root.after(0, self.processing_complete)
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            self.log_debug(error_msg)
            self.log_debug(f"Traceback: {traceback.format_exc()}")
            self.root.after(0, lambda: self.processing_error(str(e)))
            
    def processing_complete(self):
        """Handle processing completion with detailed checks"""
        self.is_processing = False
        self.generate_button.config(
            text="🚀 RENDER HOLOGRAM",
            bg=self.colors['accent_secondary'],
            state='normal'
        )
        self.progress_var.set(100)
        self.progress_label.config(
            text="✅ Processing completed!",
            fg=self.colors['success']
        )
        self.status_label.config(text="● Complete", fg=self.colors['success'])
        
        # Check if file was created
        output_file = "holograms/rar.avi"
        self.log_debug(f"Checking for output file: {output_file}")
        
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            self.log_debug(f"✅ Output file found! Size: {file_size} bytes")
            self.log_debug(f"Full path: {os.path.abspath(output_file)}")
            messagebox.showinfo("Success", f"Hologram video has been generated successfully!\n\nSaved to: {os.path.abspath(output_file)}\nSize: {file_size} bytes")
        else:
            self.log_debug("❌ Output file not found!")
            self.log_debug("Checking holograms directory contents:")
            
            # List contents of holograms directory
            try:
                holograms_dir = "holograms"
                if os.path.exists(holograms_dir):
                    files = os.listdir(holograms_dir)
                    self.log_debug(f"Files in holograms directory: {files}")
                else:
                    self.log_debug("Holograms directory does not exist!")
            except Exception as e:
                self.log_debug(f"Error listing directory: {str(e)}")
                
            messagebox.showerror("Error", "Processing completed but output file was not created!\nCheck the debug log for details.")
        
    def processing_error(self, error_msg):
        """Handle processing error"""
        self.is_processing = False
        self.generate_button.config(
            text="🚀 RENDER HOLOGRAM",
            bg=self.colors['accent_secondary'],
            state='normal'
        )
        self.progress_label.config(
            text="❌ Processing failed",
            fg=self.colors['warning']
        )
        self.status_label.config(text="● Error", fg=self.colors['warning'])
        
        self.log_debug(f"❌ Processing failed: {error_msg}")
        messagebox.showerror("Error", f"Processing failed: {error_msg}\nCheck the debug log for details.")
        
    def open_output_folder(self):
        """Open the output folder in file explorer"""
        output_dir = os.path.abspath("holograms")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        try:
            if platform.system() == "Windows":
                os.startfile(output_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", output_dir])
            else:  # Linux
                subprocess.run(["xdg-open", output_dir])
            self.log_debug(f"Opened output folder: {output_dir}")
        except Exception as e:
            self.log_debug(f"Error opening folder: {str(e)}")
            messagebox.showerror("Error", f"Could not open folder: {str(e)}")


def main():
    root = tk.Tk()
    app = DebugHologramApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
