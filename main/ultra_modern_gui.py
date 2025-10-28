import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import time
from main import th

class UltraModernHologramApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hologram Studio v2.0")
        self.root.geometry("900x700")
        self.root.configure(bg='#0d1117')  # Deep navy background
        
        # Variables
        self.selected_file = None
        self.processing_thread = None
        self.is_processing = False
        self.progress_value = 0
        
        # Modern color palette
        self.colors = {
            'bg_primary': '#0d1117',      # Deep navy
            'bg_secondary': '#161b22',    # Lighter navy
            'bg_tertiary': '#21262d',     # Card background
            'accent_primary': '#00d4aa',  # Electric teal
            'accent_secondary': '#7c3aed', # Purple accent
            'text_primary': '#f0f6fc',    # White text
            'text_secondary': '#8b949e',  # Gray text
            'text_muted': '#6e7681',      # Muted text
            'border': '#30363d',          # Border color
            'success': '#3fb950',         # Success green
            'warning': '#f85149',         # Warning red
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container with padding
        main_frame = tk.Frame(self.root, bg=self.colors['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header section
        self.create_modern_header(main_frame)
        
        # Content grid
        content_frame = tk.Frame(main_frame, bg=self.colors['bg_primary'])
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(30, 0))
        
        # Left column
        left_column = tk.Frame(content_frame, bg=self.colors['bg_primary'])
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # Right column
        right_column = tk.Frame(content_frame, bg=self.colors['bg_primary'])
        right_column.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        
        # File selection card
        self.create_file_selection_card(left_column)
        
        # Settings card
        self.create_settings_card(left_column)
        
        # Progress card
        self.create_progress_card(right_column)
        
        # Action buttons
        self.create_action_buttons(main_frame)
        
    def create_modern_header(self, parent):
        header_frame = tk.Frame(parent, bg=self.colors['bg_secondary'], height=80)
        header_frame.pack(fill=tk.X, pady=(0, 30))
        header_frame.pack_propagate(False)
        
        # Header content
        header_content = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        header_content.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # Title with modern typography
        title_frame = tk.Frame(header_content, bg=self.colors['bg_secondary'])
        title_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        title_label = tk.Label(
            title_frame,
            text="HOLOGRAM STUDIO",
            font=('Inter', 28, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        title_label.pack(anchor=tk.W)
        
        subtitle_label = tk.Label(
            title_frame,
            text="Transform videos into stunning holographic displays",
            font=('Inter', 12),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_secondary']
        )
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Version badge
        version_frame = tk.Frame(header_content, bg=self.colors['accent_primary'])
        version_frame.pack(side=tk.RIGHT, padx=(20, 0))
        
        version_label = tk.Label(
            version_frame,
            text="v2.0",
            font=('Inter', 10, 'bold'),
            fg=self.colors['bg_primary'],
            bg=self.colors['accent_primary'],
            padx=12,
            pady=6
        )
        version_label.pack()
        
    def create_file_selection_card(self, parent):
        # Card container
        card = self.create_card(parent, "VIDEO SOURCE")
        
        # File selection area
        file_area = tk.Frame(card, bg=self.colors['bg_tertiary'])
        file_area.pack(fill=tk.X, padx=25, pady=(0, 25))
        
        # Modern file button
        self.file_button = tk.Button(
            file_area,
            text="📁 SELECT VIDEO FILE",
            font=('Inter', 12, 'bold'),
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
        
        # File status with modern styling
        self.file_status_frame = tk.Frame(file_area, bg=self.colors['bg_tertiary'])
        self.file_status_frame.pack(fill=tk.X)
        
        self.file_status_label = tk.Label(
            self.file_status_frame,
            text="No file selected",
            font=('Inter', 11),
            fg=self.colors['text_muted'],
            bg=self.colors['bg_tertiary']
        )
        self.file_status_label.pack(anchor=tk.W)
        
    def create_settings_card(self, parent):
        # Card container
        card = self.create_card(parent, "PROCESSING SETTINGS")
        
        # Settings content
        settings_area = tk.Frame(card, bg=self.colors['bg_tertiary'])
        settings_area.pack(fill=tk.X, padx=25, pady=(0, 25))
        
        # Multi-threading toggle
        threading_frame = tk.Frame(settings_area, bg=self.colors['bg_tertiary'])
        threading_frame.pack(fill=tk.X, pady=(0, 20))
        
        threading_label = tk.Label(
            threading_frame,
            text="Multi-threading",
            font=('Inter', 11, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary']
        )
        threading_label.pack(side=tk.LEFT)
        
        # Modern toggle switch
        self.threading_var = tk.BooleanVar(value=True)
        self.toggle_switch = self.create_toggle_switch(threading_frame, self.threading_var)
        self.toggle_switch.pack(side=tk.RIGHT)
        
        # Frame width setting
        width_frame = tk.Frame(settings_area, bg=self.colors['bg_tertiary'])
        width_frame.pack(fill=tk.X)
        
        width_label = tk.Label(
            width_frame,
            text="Frame Width",
            font=('Inter', 11, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary']
        )
        width_label.pack(side=tk.LEFT)
        
        # Modern input field
        input_frame = tk.Frame(width_frame, bg=self.colors['bg_secondary'], relief=tk.FLAT, bd=1)
        input_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.width_var = tk.StringVar(value="300")
        self.width_entry = tk.Entry(
            input_frame,
            textvariable=self.width_var,
            font=('Inter', 11),
            width=8,
            bg=self.colors['bg_secondary'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief=tk.FLAT,
            bd=0,
            justify=tk.CENTER
        )
        self.width_entry.pack(padx=10, pady=8)
        
        px_label = tk.Label(
            width_frame,
            text="px",
            font=('Inter', 11),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_tertiary']
        )
        px_label.pack(side=tk.RIGHT, padx=(5, 0))
        
    def create_progress_card(self, parent):
        # Card container
        card = self.create_card(parent, "PROGRESS")
        
        # Progress content
        progress_area = tk.Frame(card, bg=self.colors['bg_tertiary'])
        progress_area.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))
        
        # Progress bar container
        progress_container = tk.Frame(progress_area, bg=self.colors['bg_tertiary'])
        progress_container.pack(fill=tk.X, pady=(0, 20))
        
        # Modern progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = tk.Canvas(
            progress_container,
            height=8,
            bg=self.colors['bg_secondary'],
            highlightthickness=0,
            relief=tk.FLAT
        )
        self.progress_bar.pack(fill=tk.X)
        
        # Progress text
        self.progress_label = tk.Label(
            progress_area,
            text="Ready to process",
            font=('Inter', 11),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_tertiary'],
            wraplength=200
        )
        self.progress_label.pack(anchor=tk.W)
        
        # Status indicator
        self.status_indicator = tk.Label(
            progress_area,
            text="●",
            font=('Inter', 16),
            fg=self.colors['text_muted'],
            bg=self.colors['bg_tertiary']
        )
        self.status_indicator.pack(anchor=tk.W, pady=(10, 0))
        
    def create_action_buttons(self, parent):
        button_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        button_frame.pack(fill=tk.X, pady=(30, 0))
        
        # Primary action button
        self.generate_button = tk.Button(
            button_frame,
            text="🚀 RENDER HOLOGRAM",
            font=('Inter', 14, 'bold'),
            bg=self.colors['accent_secondary'],
            fg=self.colors['text_primary'],
            relief=tk.FLAT,
            padx=40,
            pady=15,
            command=self.generate_hologram,
            cursor='hand2',
            bd=0
        )
        self.generate_button.pack()
        
        # Info text
        info_label = tk.Label(
            button_frame,
            text="Processing time varies based on video length and complexity",
            font=('Inter', 10),
            fg=self.colors['text_muted'],
            bg=self.colors['bg_primary']
        )
        info_label.pack(pady=(10, 0))
        
    def create_card(self, parent, title):
        """Create a modern card container"""
        card_frame = tk.Frame(parent, bg=self.colors['bg_tertiary'], relief=tk.FLAT, bd=1)
        card_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Card header
        header_frame = tk.Frame(card_frame, bg=self.colors['bg_tertiary'])
        header_frame.pack(fill=tk.X, padx=25, pady=(25, 15))
        
        title_label = tk.Label(
            header_frame,
            text=title,
            font=('Inter', 12, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_tertiary']
        )
        title_label.pack(anchor=tk.W)
        
        return card_frame
        
    def create_toggle_switch(self, parent, variable):
        """Create a modern toggle switch"""
        switch_frame = tk.Frame(parent, bg=self.colors['bg_tertiary'])
        
        # Toggle background
        self.toggle_bg = tk.Canvas(
            switch_frame,
            width=50,
            height=24,
            bg=self.colors['bg_secondary'],
            highlightthickness=0,
            relief=tk.FLAT
        )
        self.toggle_bg.pack()
        
        # Toggle button
        self.toggle_button = tk.Canvas(
            switch_frame,
            width=20,
            height=20,
            bg=self.colors['accent_primary'],
            highlightthickness=0,
            relief=tk.FLAT
        )
        
        # Bind click event
        self.toggle_bg.bind("<Button-1>", lambda e: self.toggle_switch_click())
        self.toggle_button.bind("<Button-1>", lambda e: self.toggle_switch_click())
        
        # Initial state
        self.update_toggle_switch()
        
        return switch_frame
        
    def toggle_switch_click(self):
        """Handle toggle switch click"""
        self.threading_var.set(not self.threading_var.get())
        self.update_toggle_switch()
        
    def update_toggle_switch(self):
        """Update toggle switch visual state"""
        if self.threading_var.get():
            # ON state
            self.toggle_bg.configure(bg=self.colors['accent_primary'])
            self.toggle_button.place(x=26, y=2)
        else:
            # OFF state
            self.toggle_bg.configure(bg=self.colors['bg_secondary'])
            self.toggle_button.place(x=2, y=2)
            
    def select_file(self):
        """Handle file selection with modern feedback"""
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
            
            # Update file status with modern styling
            self.file_status_label.config(
                text=f"✓ {filename}",
                fg=self.colors['success']
            )
            
            # Update button state
            self.file_button.config(
                text="📁 CHANGE VIDEO FILE",
                bg=self.colors['accent_secondary']
            )
            
    def generate_hologram(self):
        """Start hologram generation with proper threading"""
        if not self.selected_file:
            self.show_modern_error("Please select a video file first!")
            return
            
        if self.is_processing:
            self.show_modern_warning("Processing is already in progress!")
            return
            
        # Start processing
        self.is_processing = True
        self.generate_button.config(
            text="⏳ PROCESSING...",
            bg=self.colors['text_muted'],
            state='disabled'
        )
        
        # Reset progress
        self.progress_var.set(0)
        self.progress_label.config(text="Initializing...")
        self.status_indicator.config(fg=self.colors['accent_primary'])
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_video_thread)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def process_video_thread(self):
        """Process video in separate thread with progress updates"""
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
        """Update progress with smooth animation"""
        self.progress_label.config(text=text)
        
        # Extract percentage from text if available
        if "%" in text:
            try:
                percent = int(text.split("%")[0].split()[-1])
                self.progress_var.set(percent)
                self.update_progress_bar(percent)
            except:
                pass
                
    def update_progress_bar(self, percent):
        """Update progress bar with smooth animation"""
        self.progress_bar.delete("progress")
        
        # Calculate progress bar width
        canvas_width = self.progress_bar.winfo_width()
        if canvas_width > 1:
            progress_width = (canvas_width * percent) / 100
            
            # Draw progress bar
            self.progress_bar.create_rectangle(
                0, 0, progress_width, 8,
                fill=self.colors['accent_primary'],
                outline="",
                tags="progress"
            )
            
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
        self.status_indicator.config(fg=self.colors['success'])
        self.update_progress_bar(100)
        
        self.show_modern_success("Hologram video has been generated successfully!")
        
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
        self.status_indicator.config(fg=self.colors['warning'])
        
        self.show_modern_error(f"Processing failed: {error_msg}")
        
    def show_modern_error(self, message):
        """Show modern error dialog"""
        messagebox.showerror("Error", message)
        
    def show_modern_warning(self, message):
        """Show modern warning dialog"""
        messagebox.showwarning("Warning", message)
        
    def show_modern_success(self, message):
        """Show modern success dialog"""
        messagebox.showinfo("Success", message)


def main():
    root = tk.Tk()
    app = UltraModernHologramApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
