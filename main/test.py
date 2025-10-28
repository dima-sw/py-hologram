from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.factory import Factory
from kivy.properties import ObjectProperty
from kivy.uix.popup import Popup
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.button import Button
from main import th
import os


class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


class Root(FloatLayout):
    loadfile = ObjectProperty(None)
    savefile = ObjectProperty(None)
    text_input = ObjectProperty(None)
    labelName = ObjectProperty(None)
    pathInputVideo = None
    processing_thread = None

    def __init__(self, **kwargs):
        super(Root, self).__init__(**kwargs)
        self.processing_thread = None

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self):
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="", content=content, size_hint=(0.8, 0.8))
        self._popup.open()

    def show_save(self):
        if not self.pathInputVideo:
            self.show_error_popup("Please select a video file first!")
            return
            
        if self.processing_thread and self.processing_thread.is_alive():
            self.show_error_popup("Processing is already in progress!")
            return
            
        # Reset progress
        self.ids.progress_label.text = "Starting processing..."
        self.update_progress_bar(0)
        
        # Start processing thread
        self.processing_thread = th(
            self.pathInputVideo, 
            self.ids.progress_label, 
            threading=self.ids.threading_check.active
        )
        self.processing_thread.start()
        
        # Update UI to show processing state
        self.ids.file_status_label.text = "Processing..."
        self.ids.file_status_label.color = (0.2, 0.8, 0.4, 1)

    def load(self, path, filename):
        if filename:
            self.pathInputVideo = os.path.join(path, filename[0])
            filename_only = os.path.basename(filename[0])
            self.ids.file_status_label.text = f"✓ {filename_only}"
            self.ids.file_status_label.color = (0.2, 0.8, 0.4, 1)
            
            # Animate the file selection
            anim = Animation(opacity=0.7, duration=0.1) + Animation(opacity=1, duration=0.1)
            anim.start(self.ids.file_status_label)
        else:
            self.show_error_popup("No file selected!")
            
        self.dismiss_popup()

    def update_progress_bar(self, progress):
        """Update the progress bar with animation"""
        if hasattr(self, 'ids') and 'progress_bar' in self.ids:
            # Animate the progress bar
            anim = Animation(progress=progress, duration=0.3)
            anim.start(self.ids.progress_bar)

    def show_error_popup(self, message):
        """Show an error popup with modern styling"""
        content = FloatLayout()
        
        # Error message label
        error_label = Label(
            text=message,
            font_name='Roboto',
            font_size='16sp',
            color=(0.8, 0.2, 0.2, 1),
            size_hint=(0.8, 0.3),
            pos_hint={'center_x': 0.5, 'center_y': 0.6},
            halign='center'
        )
        content.add_widget(error_label)
        
        # OK button
        ok_button = Button(
            text='OK',
            font_name='Roboto',
            font_size='14sp',
            size_hint=(0.3, 0.2),
            pos_hint={'center_x': 0.5, 'center_y': 0.3},
            background_normal='',
            background_color=(0.2, 0.6, 0.8, 1),
            color=(1, 1, 1, 1)
        )
        ok_button.bind(on_release=lambda x: self._popup.dismiss())
        content.add_widget(ok_button)
        
        self._popup = Popup(
            title="",
            content=content,
            size_hint=(0.6, 0.4),
            auto_dismiss=True
        )
        self._popup.open()

    def on_processing_complete(self):
        """Called when processing is complete"""
        self.ids.file_status_label.text = "Processing complete!"
        self.ids.file_status_label.color = (0.2, 0.8, 0.4, 1)
        self.ids.progress_label.text = "Hologram video generated successfully!"
        self.update_progress_bar(100)


class Editor(App):
    def build(self):
        return Root()


Factory.register('Root', cls=Root)
Factory.register('LoadDialog', cls=LoadDialog)


if __name__ == '__main__':
    Editor().run()