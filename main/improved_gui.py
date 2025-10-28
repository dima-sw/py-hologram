import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import time
import subprocess
import platform
from main import th

class ImprovedHologramApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hologram Studio v2.0")
        self.root.geometry("900x700")
        self.root.configure(bg='#0d1117')
        
        # Variables
        self.selected_file = None
        self.processing_thread = None
        self.is_processing = False
        self.progress_value = 0
        self.output_path = None
        
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
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header
        self.create_header(main_frame)
        
        # Content
        content_frame = tk.Frame(main_frame, bg=self.colors['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(30, 0))
        
        # Left column
        left_column = tk.Frame(content_frame, bg=self.colors['bg_primary'])
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # Right column
        right_column = tk.Frame(content_frame, bg=self.colors['bg_primary'])
        right_column.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        
        # Cards
        self.create_file_card(left_column)
        self.create_settings_card(left_column)
        self.create_progress_card(right_column)
        self.create_action_buttons(main_frame)
        
    def create_header(self, parent):
        header_frame = tk.Frame(parent, bg=self.colors['bg_secondary'], height=80)
        header_frame.pack(fill=tk.X, pady=(0, 30))
        header_frame.pack_propagate(False)
        
        header_content = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        header_content.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        title_label = tk.Label(
            header_content,
            text="HOLOGRAM STUDIO",
            font=('Arial', 28, 'bold'),
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
        file_area.pack(fill=tk.X, padx=25, pady=(0, 25))
        
        self.file_button = tk.Button(
            file_area,
            text="📁 SELECT VIDEO FILE",
            font=('Arial', 12, 'bold'),
            bg=self.colors['accent_primary'],
            fg=self.colors['bg_primary'],
            relief=tk.FLAT,
            padx=25,
            pady=12,
            command=self.select_file,
            cursor='hand2',
            bd=0
        )
        self.file_button.pack(fill=tk.X, pady=(0, 15))
        
        self.file_status_label = tk.Label(
            file_area,
            text="No file selected",
            font=('Arial', 11),
            fg=self.colors['text_muted'],
            bg=self.colors['bg_tertiary']
        )
        self.file_status_label.pack(anchor=tk.W)
        
    def create_settings_card(self, parent):
        card = self.create_card(parent, "PROCESSING SETTINGS")
        
        settings_area = tk.Frame(card, bg=self.colors['bg_tertiary'])
        settings_area.pack(fill=tk.X, padx=25, pady=(0, 25))
        
        # Multi-threading
        threading_frame = tk.Frame(settings_area, bg=self.colors['bg_tertiary'])
        threading_frame.pack(fill=tk.X, pady=(0, 20))
        
        threading_label = tk.Label(
            threading_frame,
            text="Multi-threading",
            font=('Arial', 11, 'bold'),
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
            font=('Arial', 11, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary']
        )
        width_label.pack(side=tk.LEFT)
        
        self.width_var = tk.StringVar(value="300")
        width_entry = tk.Entry(
            width_frame,
            textvariable=self.width_var,
            font=('Arial', 11),
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
        progress_area.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_area,
            variable=self.progress_var,
            maximum=100,
            length=200,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 15))
        
        # Progress text
        self.progress_label = tk.Label(
            progress_area,
            text="Ready to process",
            font=('Arial', 11),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_tertiary'],
            wraplength=200
        )
        self.progress_label.pack(anchor=tk.W)
        
        # Status
        self.status_label = tk.Label(
            progress_area,
            text="● Ready",
            font=('Arial', 11),
            fg=self.colors['text_muted'],
            bg=self.colors['bg_tertiary']
        )
        self.status_label.pack(anchor=tk.W, pady=(10, 0))
        
        # Output path
        self.output_label = tk.Label(
            progress_area,
            text="Output: holograms/rar.avi",
            font=('Arial', 10),
            fg=self.colors['text_muted'],
            bg=self.colors['bg_tertiary'],
            wraplength=200
        )
        self.output_label.pack(anchor=tk.W, pady=(10, 0))
        
    def create_action_buttons(self, parent):
        button_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        button_frame.pack(fill=tk.X, pady=(30, 0))
        
        # Button container
        btn_container = tk.Frame(button_frame, bg=self.colors['bg_primary'])
        btn_container.pack()
        
        self.generate_button = tk.Button(
            btn_container,
            text="🚀 RENDER HOLOGRAM",
            font=('Arial', 14, 'bold'),
            bg=self.colors['accent_secondary'],
            fg=self.colors['text_primary'],
            relief=tk.FLAT,
            padx=40,
            pady=15,
            command=self.generate_hologram,
            cursor='hand2',
            bd=0
        )
        self.generate_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.open_folder_button = tk.Button(
            btn_container,
            text="📂 OPEN OUTPUT FOLDER",
            font=('Arial', 12, 'bold'),
            bg=self.colors['accent_primary'],
            fg=self.colors['bg_primary'],
            relief=tk.FLAT,
            padx=20,
            pady=15,
            command=self.open_output_folder,
            cursor='hand2',
            bd=0
        )
        self.open_folder_button.pack(side=tk.LEFT)
        
    def create_card(self, parent, title):
        card_frame = tk.Frame(parent, bg=self.colors['bg_tertiary'], relief=tk.FLAT, bd=1)
        card_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        header_frame = tk.Frame(card_frame, bg=self.colors['bg_tertiary'])
        header_frame.pack(fill=tk.X, padx=25, pady=(25, 15))
        
        title_label = tk.Label(
            header_frame,
            text=title,
            font=('Arial', 12, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary']
        )
        title_label.pack(anchor=tk.W)
        
        return card_frame
        
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
            
    def generate_hologram(self):
        if not self.selected_file:
            messagebox.showerror("Error", "Please select a video file first!")
            return
            
        if self.is_processing:
            messagebox.showwarning("Warning", "Processing is already in progress!")
            return
            
        # Ensure output directory exists
        output_dir = "holograms"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
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
        elif current_progress < 40:
            self.progress_label.config(text="Processing frames...")
            self.progress_var.set(40)
        elif current_progress < 60:
            self.progress_label.config(text="Creating hologram layout...")
            self.progress_var.set(60)
        elif current_progress < 80:
            self.progress_label.config(text="Generating hologram frames...")
            self.progress_var.set(80)
        elif current_progress < 95:
            self.progress_label.config(text="Saving video...")
            self.progress_var.set(95)
        else:
            self.progress_var.set(100)
            self.progress_label.config(text="✅ Complete!")
            self.status_label.config(text="● Complete", fg=self.colors['success'])
            self.processing_complete()
            return
            
        # Continue simulation
        self.root.after(2000, self.simulate_progress)
        
    def process_video_thread(self):
        """Process video in separate thread"""
        try:
            # Create a simple progress callback
            class ProgressCallback:
                def __init__(self, app):
                    self.app = app
                    
                def update_progress(self, text):
                    # This will be called by the hologram processing
                    pass
            
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
            
    def processing_complete(self):
        """Handle processing completion"""
        self.is_processing = False
        self.generate_button.config(
            text="🚀 RENDER HOLOGRAM",
            bg=self.colors['accent_secondary'],
            state='normal'
        )
        self.progress_var.set(100)
        self.progress_label.config(
            text="✅ Hologram video generated successfully!",
            fg=self.colors['success']
        )
        self.status_label.config(text="● Complete", fg=self.colors['success'])
        
        # Check if file was created
        output_file = "holograms/rar.avi"
        if os.path.exists(output_file):
            self.output_label.config(
                text=f"✅ Output: {os.path.abspath(output_file)}",
                fg=self.colors['success']
            )
            messagebox.showinfo("Success", f"Hologram video has been generated successfully!\n\nSaved to: {os.path.abspath(output_file)}")
        else:
            self.output_label.config(
                text="❌ Output file not found",
                fg=self.colors['warning']
            )
            messagebox.showerror("Error", "Processing completed but output file was not created!")
        
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
        
        messagebox.showerror("Error", f"Processing failed: {error_msg}")
        
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
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {str(e)}")


def main():
    root = tk.Tk()
    app = ImprovedHologramApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
