import kivy
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown
import multiprocessing as mp
from kivy.uix.checkbox import CheckBox
from kivy.lang import Builder
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.factory import Factory
from kivy.properties import ObjectProperty
from kivy.uix.popup import Popup

import os

Builder.load_file(r"fileChooser.kv")
class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


class SaveDialog(FloatLayout):
    save = ObjectProperty(None)
    text_input = ObjectProperty(None)
    cancel = ObjectProperty(None)

class searchFIle(App):

    def build(self):
        # print("funzione")
        self.window = GridLayout()


        return self.window

    def slected(self, filename):
        print(filename)

class UIH(App):
    loadfile = ObjectProperty(None)
    def build(self):
        self.window=GridLayout()

        self.window.cols=2
        self.window.rows=5

        self.window.add_widget(Image(source=r"C:\Users\TheDimitri\PycharmProjects\hologram\phototest\test.jpg"))
        self.window.add_widget(Label(text=""))
        self.window.add_widget(Label(text="Select video"))

        self.selectVideo=Button(text="select")
        self.selectVideo.bind(on_press=self.selectFile)
        self.window.add_widget(self.selectVideo)
        self.window.add_widget(Label(text="Use threading: "))
        self.useThreds= CheckBox()
        self.window.add_widget(self.useThreds)

        self.window.add_widget(Label(text="Choose File: "))
        self.useThreds = CheckBox()
        self.window.add_widget(self.useThreds)

        return self.window

    def selectFile(self, value):
        searchFIle().run()

    def slected(self,filename):
        print(filename)

    def load(self, path, filename):
        with open(os.path.join(path, filename[0])) as stream:
            self.text_input.text = stream.read()

        self.dismiss_popup()


Factory.register('LoadDialog', cls=LoadDialog)


if __name__ == "__main__":

    UIH().run()