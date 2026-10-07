import os

os.environ['KIVY_CAMERA'] = 'android'
os.environ['KIVY_AUDIO'] = 'android'

from kivy.utils import platform

if platform == 'android':
	os.environ['KIVY_CAMERA'] = 'android'

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import NoTransition, SlideTransition
from telas import *
from botoes import *


GUI = Builder.load_file("main.kv")

class MainApp(App):
    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            
            def callback(permissions, results):
            	if all(results):
            		print("Todas as permissões concedidas")
            	else:
            		print("Algumas permissões foram negadas")
            
            # Pedir permissão para Câmera e Armazenamento
            request_permissions([
                Permission.CAMERA,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ], callback)
    def build(self):
        return GUI

    def mudar_tela(self, id_tela, animacao=False):
        gerenciador_telas = self.root.ids["screen_manager"] #ARQUIVO CARREGADO NA VARIÁVEL GUI
        
        if animacao:
            gerenciador_telas.transition = SlideTransition(direction='left')
        else:
            gerenciador_telas.transition = NoTransition()
            
        gerenciador_telas.current = id_tela

if __name__ == "__main__":
    MainApp().run()
