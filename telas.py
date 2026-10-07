import cv2
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.utils import platform
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.graphics import Rotate, PushMatrix, PopMatrix, Scale
from kivy.clock import Clock
import numpy as np
from numpy.ma.core import size
import plyer
from plyer import camera
from plyer import accelerometer
import os
from analise import AnaliseFruto
from datetime import datetime


class HomePage(Screen):            
    def iniciar_nova_coleta(self):
        box = BoxLayout(orientation='vertical', padding=10, spacing=10)
        box.add_widget(Label(text="A planilha atual do aplicativo será apagada.\nDeseja iniciar uma nova coleta?", halign="center"))
        
        botoes = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.4)
        btn_sim = Button(text="Sim, apagar", background_color=(1, 0, 0, 1))
        btn_nao = Button(text="Cancelar", background_color=(0.5, 0.5, 0.5, 1))
        
        botoes.add_widget(btn_sim)
        botoes.add_widget(btn_nao)
        box.add_widget(botoes)
        
        popup = Popup(title="Iniciar Nova Coleta", content=box, size_hint=(0.8, 0.4))
        
        def apagar_planilha(instance):
            path = App.get_running_app().user_data_dir
            arquivo_csv = os.path.join(path, "resultados_analise.csv")
            if os.path.exists(arquivo_csv):
                os.remove(arquivo_csv)
                print("Planilha resetada com sucesso.")
            popup.dismiss()
            
        btn_sim.bind(on_release=apagar_planilha)
        btn_nao.bind(on_release=popup.dismiss)
        
        popup.open()
    
class InstrucoesPage(Screen):
    pass

class CalibracaoPage(Screen):
    def salvar_calibracao(self, valor_texto):
        try:
            valor_formatado = valor_texto.replace(',', '.')
            valor_float = float(valor_formatado)
            
            App.get_running_app().tamanho_referencia = valor_float
            print(f"Objeto de referência atualizado para: {valor_float} mm")
            
            self.manager.current = "homepage"
        except ValueError:
            print("Erro: Digite apenas números.")
        

class CameraPage(Screen):
    # Inicializar uma variável para guardar a câmera
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera_widget = None
        self.sensor_event = None # Guarda o evento do relógio do sensor
        self.tolerancia_x = 1.0
        self.tolerancia_y = 1.0              

    def testar_camera_fisica(self):
        try:
            # O OpenCV tenta acessar a webcam primária
            cap = cv2.VideoCapture(0)
            if cap is None or not cap.isOpened():
                return False
            else:
                cap.release()
                return True
        except Exception:
            return False

    def exibir_erro_camera(self):
        box = BoxLayout(orientation='vertical', padding=10, spacing=10)
        box.add_widget(Label(text="Nenhuma câmera física detectada."))

        btn_fechar = Button(text="Entendi", size_hint_y=0.3, background_color=(1, 0, 0, 1))
        box.add_widget(btn_fechar)

        popup = Popup(title="Erro de Hardware", content=box, size_hint=(0.8, 0.4))
        btn_fechar.bind(on_release=popup.dismiss)

        # Assim que o popup fechar, o usuário é direcionado para para a homepage
        btn_fechar.bind(on_release=lambda x: self.voltar_para_home())

        popup.open()

    def voltar_para_home(self):
        from kivy.uix.screenmanager import SlideTransition
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = "homepage"

    def on_enter(self):
        # Verificar se a câmera existe
        try:
            # Se a câmera física existe e ainda não foi criada no app
            if self.camera_widget is None:
                print("Hardware detectado. Criando a câmera na tela.")
                self.camera_widget = Camera(resolution=(640, 480), play=True, allow_stretch=True, keep_ratio=True, size_hint = (1, 1))
                
                with self.camera_widget.canvas.before:
                    PushMatrix()
                    self.rot = Rotate(angle=-90, origin=self.camera_widget.center)
                    self.scale = Scale(1, 1, 1, origin=self.camera_widget.center) # controlador de zoom visual
                with self.camera_widget.canvas.after:
                    PopMatrix()
                    
                self.camera_widget.bind(center=self.atualizar_transformacoes, texture=self.atualizar_transformacoes)
                
                if 'camera_container' in self.ids:
                    self.ids.camera_container.add_widget(self.camera_widget)
                else:
                    print("ERRO CRÍTICO: ID 'camera_container' não encontrado no camerapage.kv")
                    
            self.camera_widget.play = False
            Clock.schedule_once(self._ligar_camera, 0.2)

        except Exception as e:
        #else:
            print(f"Erro ao acessar a câmera: {e}")
            self.exibir_erro_camera()
            
        try:
            accelerometer.enable()
            # Chama o método checar_inclinacao a cada 0.1 segundos
            self.sensor_event = Clock.schedule_interval(self.checar_inclinacao, 0.1)
        except Exception as e:
            print(f"Acelerômetro não suportado ou erro ao ativar: {e}")
            
    def checar_inclinacao(self, dt):
        # Lê o acelerômetro e atualiza o estado do botão de captura
        try:
            # accelerometer.acceleration retorna (x, y, z) em m/s2
            val = accelerometer.acceleration
            if val is not None and val != (None, None, None):
                ax, ay, az = val
                
            esta_inclinado = abs(ax) > self.tolerancia_x or abs(ay) > self.tolerancia_y
            
            if 'btn_analisar' in self.ids:
                if esta_inclinado:
                    self.ids.btn_analisar.disabled = True
                    if 'label_aviso_sensor' in self.ids:
                        self.ids.label_aviso_sensor.text = f"Inclinado. X: {ax:.1f} (Lim:{self.tolerancia_x}) | Y: {ay:.1f} (Lim: {self.tolerancia_y})"
                        self.ids.label_aviso_sensor.color = (1, 0, 0, 1)
                else:
                    self.ids.btn_analisar.disabled = False
                    if 'label_aviso_sensor' in self.ids:
                        self.ids.label_aviso_sensor.text = f"Nivelado (X:{ax:.1f}, Y:{ay:.1f})"
                        self.ids.label_aviso_sensor.color = (0, 1, 0, 1)
        except Exception as e:
            print(f"Erro ao ler acelerômetro: {e}")        
            
    def _ligar_camera(self, dt):
        if self.camera_widget:
            self.camera_widget.play = True
            print("Câmera reiniciada com sucesso!")
            
    def atualizar_transformacoes(self, instance, *args):
        # Mantém o centro de rotação alinhado
        if hasattr(self, 'rot'):
            self.rot.origin = instance.center
            
        # Calcula e aplica o zoom
        if hasattr(self, 'scale') and instance.texture:
            cw, ch = instance.size # Tamanho do espaço disponível na tela
            tw, th = instance.texture.size # Tamanho do sensor da câmera
            
            if tw == 0 or th == 0 or cw == 0 or ch == 0:
                return
                
            proporcao_kivy = min(cw / tw, ch / th)
            largura_desenhada = tw * proporcao_kivy
            altura_desenhada = th * proporcao_kivy
            
            largura_visual = altura_desenhada
            altura_visual = largura_desenhada
            
            zoom_x = cw / largura_visual
            zoom_y = ch / altura_visual
            zoom_final = max(zoom_x, zoom_y)
            
            self.scale.origin = instance.center
            self.scale.x = zoom_final
            self.scale.y = zoom_final
    	    
    def on_pre_leave(self):
        # Pausar a câmera antes de mudar de tela para não travar
        if self.camera_widget:
            self.camera_widget.play = False
            print("Câmera pausada para liberar memória")
            
        try:
            if self.sensor_event:
                self.sensor_event.cancel()
                self.sensor_event = None
            accelerometer.disable()
        except Exception:
            pass

    def on_leave(self):
        # Garante que vai tentar desligar só se estiver ligada
        if self.camera_widget is not None:
            self.camera_widget.play = False
            
        try:
            accelerometer.disable()
        except Exception:
            pass

    def capturar_e_analisar(self):
        camera = self.camera_widget

        if camera is None or camera.texture is None:
            print("Erro: Câmera não está enviando imagens.")
            return

        print("Procesando a imagem do fruto...")



        # Conversão Kivy (RGBA) -> OpenCV (BGR)
        size = camera.texture.size
        pixels = camera.texture.pixels
        img_flat = np.frombuffer(pixels, dtype=np.uint8)
        img_rgba = img_flat.reshape(size[1], size[0], 4)
        img_bgr = cv2.cvtColor(img_rgba, cv2.COLOR_RGBA2BGR)
        img_bgr = cv2.flip(img_bgr, 0)
        img_bgr = cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)

        # Analisar Fruto
        analise = AnaliseFruto()

        try:
            # Segmentacao
            mascara = analise.segmentacao(img_bgr)

            # Busca e classificacao dos contornos
            maior_contorno, referencia_contorno, x, y, h_box, img_com_contorno = analise.buscarContornos(img_bgr, mascara)
            
            if maior_contorno is None or referencia_contorno is None:
                print("Erro: Nao foi possivel identificar o fruto e o OR.")
                return
            
            # Diâmetro real dinâmico    
            app = App.get_running_app()
            # Se não houver valor configurado, o padrão será 27.0
            diametro_real_referencia_mm = getattr(app, 'tamanho_referencia', 27.0)
            
            # Calibracao Espacial Dinamica (PPM)
            ppm = analise.calibracao(diametro_real_referencia_mm, referencia_contorno)
            print(f"PPM calculado dinamicamente: {ppm:.2f} px/mm")
            
            # Calculo dos Parametros Fisicos e Agronomicos
            dados_calculados = analise.propFisicas(mascara, maior_contorno, x, y, h_box, ppm)
            
            
            # Ajuste de resolucao maxima para renderizacao no Android
            max_largura = 1920
            max_altura = 1080
            altura_original, largura_original = img_com_contorno.shape[:2]
            
            if largura_original > max_largura or altura_original > max_altura:
                ratio = min(max_largura / largura_original, max_altura / altura_original)
                nova_resolucao = (int(largura_original * ratio), int(altura_original * ratio))
                img_final_para_tela = cv2.resize(img_com_contorno, nova_resolucao, interpolation=cv2.INTER_AREA)
            else:
                img_final_para_tela = img_com_contorno
                
            # Salvamento em diretorio seguro e privado da aplicacao
            pasta_privada = App.get_running_app().user_data_dir
            caminho_temp = os.path.join(pasta_privada, "temp_resultado.jpg")
            cv2.imwrite(caminho_temp, img_final_para_tela)
            
            # Transicao para a tela de resultados
            try:
                tela_res = self.manager.get_screen("resultadospage")
                tela_res.atualizar_dados(dados_calculados, caminho_temp)
                
                from kivy.uix.screenmanager import SlideTransition
                self.manager.transition = SlideTransition(direction='left')
                
                self.manager.current = "resultadospage"
            except Exception as e:
                print(f"Erro ao mudar para tela de resultados: {e}")
                
        except Exception as e:
            print(f"Erro durante a analise do fruto: {e}")
            
    
            

class ResultadosPage(Screen):
    # Variável para guardar temporariamente os dados antes de salvar no CSV
    dados_atuais = {}

    def atualizar_dados(self, dados_analise, caminho_imagem_processada):
        self.dados_atuais = dados_analise

        # Atualizando os Labels do Kivy (resultados.kv)
        if 'label_area' in self.ids:
            self.ids.label_area.text = f"{dados_analise.get('Area_Superficial', 0):.2f} cm²"
        if 'label_esfericidade' in self.ids:
            self.ids.label_esfericidade.text = f"{dados_analise.get('Esfericidade', 0):.2f}"
        if 'label_volume' in self.ids:
            self.ids.label_volume.text = f"{dados_analise.get('Volume_cm3', 0):.2f} cm³"

        # Atualizando a imagem com o contorno verde
        if 'img_resultado_final' in self.ids:
            self.ids.img_resultado_final.source = caminho_imagem_processada
            self.ids.img_resultado_final.reload() # Força o Kivy a ler o arquivo novo

    def salvar_csv(self):
        # Verificar se realmente há dados para salvar
        if not self.dados_atuais:
            print("Erro: Nenhum dado disponível para salvar.")
            return
        # Definir o nome do arquivo
        path = App.get_running_app().user_data_dir
        arquivo_csv = os.path.join(path, "resultados_analise.csv")

        # Verificar se o arquivo já existe para saber se precisa criar o cabeçalho
        verificacao_cabecalho = not os.path.exists(arquivo_csv)

        try:
            # Abrir o arquivo no modo 'a' (append_ que adiciona linhas no final sem apagar as antigas
            with open(arquivo_csv, "a", encoding="utf-8") as f:
                # Escrever o cabeçalho na primeira vez que o arquivo foi criado
                if verificacao_cabecalho:
                    f.write("Data;Hora;Largura_cm;Altura_cm;Dg_cm;Esfericidade;As_cm2;Vol_cm3\n")

                # Pegar a data e hora no momento da captura
                data_hora = datetime.now()
                data_str = data_hora.strftime("%d/%m/%Y")
                hora_str = data_hora.strftime("%H:%M:%S")

                # Extrair os dados do dicionário (usando o .get para evitar erros caso falte alguma chave)
                d = self.dados_atuais
                linha = f"{data_str};{hora_str};{d.get('Largura_cm', 0):.2f};{d.get('Altura_cm', 0):.2f};{d.get('Diam_Geometrico', 0):.2f};{d.get('Esfericidade', 0):.2f};{d.get('Area_Superficial', 0):.2f};{d.get('Volume_cm3', 0):.2f}\n"

                # Trocar ponto por vírgula para evitar problemas com o Excel
                linha_br = linha.replace('.', ',')

                # Gravar no arquivo
                f.write(linha_br)

            print(f"Dados salvos na planilha {arquivo_csv}.")

            # Voltar para a Tela da Câmera
            from kivy.uix.screenmanager import SlideTransition
            self.manager.transition = SlideTransition(direction='right')
            self.manager.current = "camerapage"

            # Limpar dados atuais da memória
            self.dados_atuais = {}

        except Exception as e:
            print(f"Erro ao tentar salvar o arquivo CSV: {e}")
            
class DownloadPage(Screen):
    def on_pre_enter(self, *args):
        self.atualizar_status()
        
    def atualizar_status(self):
        path_privado = App.get_running_app().user_data_dir
        arquivo_csv = os.path.join(path_privado, "resultados_analise.csv")
        
        if not os.path.exists(arquivo_csv):
            self.ids.label_status.text = "A planilha ainda não foi iniciada.\nRealize uma análise para começar a coleta."
            self.ids.btn_baixar.disabled = True
            self.ids.btn_baixar.background_color = (0.5, 0.5, 0.5, 1)
        else:
            try:
                with open(arquivo_csv, "r", encoding="utf-8") as f:
                    linhas = f.readlines()
                    registros = len(linhas) - 1 if len(linhas) > 0 else 0 # desconsidera a primeira linha (cabeçalho)    
                
                if registros > 0:
                    self.ids.label_status.text = f"{registros} análise(s) registrada(s)"
                    self.ids.btn_baixar.disabled = False
                    self.ids.btn_baixar.background_color = (0.18, 0.49, 0.19, 1)
                else:
                    self.ids.label_status.text = "A planilha foi criada, mas ainda não possui registros."
                    self.ids.btn_baixar.disabled = True
                    self.ids.btn_baixar.background_color = (0.5, 0.5, 0.5, 1)
            except Exception as e:
                self.ids.label_status.text = f"Erro ao ler o arquivo: {e}"
                self.ids.btn_baixar.disabled = True  
                    
                    
    def baixar_csv(self):
        path_privado = App.get_running_app().user_data_dir
        origem = os.path.join(path_privado, "resultados_analise.csv")
        
        if platform == 'android':
            try:
                from jnius import autoclass, cast
                
                # Classes do Android para gerenciar o armazenamento
                ContentValues = autoclass('android.content.ContentValues')
                MediaStore = autoclass('android.provider.MediaStore$Downloads')
                Environment = autoclass('android.os.Environment')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                FileInputStream = autoclass('java.io.FileInputStream')
                
                # Define as propriedades do arquivo "Download"
                values = ContentValues()
                values.put("_display_name", "resultados_analise.csv")
                values.put("mime_type", "text/csv")
                values.put("relative_path", Environment.DIRECTORY_DOWNLOADS)
                
                # Insere o arquivo no banco de dados do Android
                resolver = PythonActivity.mActivity.getContentResolver()
                uri = resolver.insert(MediaStore.EXTERNAL_CONTENT_URI, values)
                
                # Copia os bits da pasta interna para a pasta pública
                out_stream = resolver.openOutputStream(uri)
                in_stream = FileInputStream(origem)
                
                buffer = bytearray(1024)
                while True:
                    num_read = in_stream.read(buffer)
                    if num_read <= 0:
                        break
                    out_stream.write(buffer, 0, num_read)
                    
                out_stream.close()
                in_stream.close()
                
                self.ids.label_status.text += "\n\nDownload concluído com sucesso.\nVerifique a pasta 'Downloads' do seu celular."
                
            except Exception as e:
                print(f"Erro ao baixar arquivo: {e}")
                
        else:
            # Caminho para teste no computador
            print(f"No Desktop, o arquivo está em: {origem}")

