from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.factory import Factory
from kivy.properties import ObjectProperty
from kivy.uix.popup import Popup
from main import th


import os


class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)





class Root(FloatLayout):
    loadfile = ObjectProperty(None)
    savefile = ObjectProperty(None)
    text_input = ObjectProperty(None)
    labelName=ObjectProperty(None)

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self):
        content = LoadDialog(load=self.load, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def show_save(self):
        cl= th(self.pathInputVideo,self.ids.text_input, threading=self.ids.thredingCheck.active)

        cl.start()
        print("principale")

    def load(self, path, filename):
        self.pathInputVideo= os.path.join(path, filename[0])

        """with open(os.path.join(path, filename[0])) as stream:"""
        self.ids.labelLoad.text = "Video selected"

        self.dismiss_popup()






class Editor(App):
    pass


Factory.register('Root', cls=Root)
Factory.register('LoadDialog', cls=LoadDialog)



if __name__ == '__main__':
    Editor().run()