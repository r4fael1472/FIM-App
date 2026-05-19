import cv2
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.utils import platform
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.graphics import Rotate, PushMatrix, PopMatrix
from kivy.clock import Clock
import numpy as np
from numpy.ma.core import size
import plyer
from plyer import camera
import os
from analise import AnaliseTomate
from datetime import datetime
from PIL import Image as PILImage


class HomePage(Screen):
    pass
    
class InstrucoesPage(Screen):
    pass

class CalibracaoPage(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera_widget = None

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
        self.manager.current = "homepage"

    def on_enter(self):
        # Adicionar widget da câmera
        try:
            if self.camera_widget is None:
                self.camera_widget = Camera(resolution=(640, 480), play=True)
                
                with self.camera_widget.canvas.before:
                    PushMatrix()
                    self.rot = Rotate(angle=-90, origin=self.camera_widget.center)
                with self.camera_widget.canvas.after:
                    PopMatrix()
                    
                self.camera_widget.bind(center=self.atualizar_origem_rotacao)

                if 'camera_calibracao_container' in self.ids:
                    self.ids.camera_calibracao_container.add_widget(self.camera_widget)
                else:
                    print("ERRO CRÍTICO: ID 'camera_calibracao_container' não encontrado no calibracaopage.kv")

            else:
                self.camera_widget.play = True
        except Exception as e:
            print("Erro ao acessar a câmera: {e}")
            self.exibir_erro_camera()
            
    def atualizar_origem_rotacao(self, instance, value):
    	if hasattr(self, 'rot'):
    	    self.rot.origin = instance.center

    def on_leave(self):
        # Garante que vai tentar desligar só se estiver ligada
        if self.camera_widget is not None:
            self.camera_widget.play = False
            print("Câmera de calibração desligada com sucesso.")

    def realizar_calibracao(self):
        # Pegar valor que o usuário digitou no aplicativo
        try:
            referencia_mm = float(self.ids.input_referencia.text)
        except:
            print("Erro: Digite um número válido")
            return

        # Buscar o widget da câmera do Kivy
        camera = self.camera_widget
        if camera is None or camera.texture is None:
            print("Aguarde a câmera ligar e tente novamente.")
            return

        print(f"Iniciando calibração com referência de {referencia_mm} mm.")

        # Extrair os pixels brutos e converter para uma matriz BGR do OpenCV
        size = camera.texture.size
        pixels = camera.texture.pixels
        img_flat = np.frombuffer(pixels, dtype=np.uint8)
        img_rgba = img_flat.reshape(size[1], size[0], 4)
        img_bgr = cv2.cvtColor(img_rgba, cv2.COLOR_RGBA2BGR)  # Aqui o OpenCV entende a imagem
        img_bgr = cv2.flip(img_bgr, 0)  # O Kivy costuma entregar a imagem invertida

        # Transforma a foto colorida em tons de cinza
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Aplicar um desfoque leve para ignorar sujeiras ou arranhões na mesa
        blur = cv2.GaussianBlur(gray, (7, 7), 0)

        # Acha as "linhas" e "bordas" da imagem
        bordas = cv2.Canny(blur, 50, 150)

        # OpenCV lista todos os objetos contornados encontrados
        contornos, _ = cv2.findContours(bordas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contornos:
            # Pegar o maior contorno (objeto de referência)
            maior_contorno = max(contornos, key=cv2.contourArea)

            # x, y (posição) | w_px (largura em pixels) | h_px (altura em pixels)
            x, y, w_px, h_px = cv2.boundingRect(maior_contorno)

            # Evitar erro se o OpenCV achar alguma poeira de 10 pixels
            if w_px > 20:
                # Aplicar fórmula de cálculo do PPM
                ppm = w_px / referencia_mm
                path = App.get_running_app().user_data_dir
                caminho_calibracao = os.path.join(path, 'calibracao.txt')
                # Salvar o valor em um arquivo de texto no celular
                with open(caminho_calibracao, "w") as f:
                    f.write(str(ppm))

                print(f"PPM calculado: {ppm:.2f} pixels equivalem a 1 mm.")

                self.manager.current = 'homepage'

            else:
                print("Objeto muito pequeno ou muito longe da câmera.")
        

class CameraPage(Screen):
    # Inicializar uma variável para guardar a câmera
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera_widget = None

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
        self.manager.current = "homepage"

    def on_enter(self):
        # Verificar se a câmera existe
        try:
            # Se a câmera física existe e ainda não foi criada no app
            if self.camera_widget is None:
                print("Hardware detectado. Criando a câmera na tela.")
                self.camera_widget = Camera(resolution=(640, 480), play=True)
                
                with self.camera_widget.canvas.before:
                    PushMatrix()
                    self.rot = Rotate(angle=-90, origin=self.camera_widget.center)
                with self.camera_widget.canvas.after:
                    PopMatrix()
                    
                self.camera_widget.bind(center=self.atualizar_origem_rotacao)
                
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
            
    def _ligar_camera(self, dt):
        if self.camera_widget:
            self.camera_widget.play = True
            print("Câmera reiniciada com sucesso!")
            
    def atualizar_origem_rotacao(self, instance, value):
    	# Atualiza o ponto central da rotação sempre que a câmera se move
    	if hasattr(self, 'rot'):
    	    self.rot.origin = instance.center
    	    
    def on_pre_leave(self):
        # Pausar a câmera antes de mudar de tela para não travar
        if self.camera_widget:
            self.camera_widget.play = False
            print("Câmera pausada para liberar memória")

    def on_leave(self):
        # Garante que vai tentar desligar só se estiver ligada
        if self.camera_widget is not None:
            self.camera_widget.play = False

    def capturar_e_analisar(self):
        # Valor de segurança caso ocorra algum erro
        ppm = 3.0

        if os.path.exists("calibracao.txt"):
            with open("calibracao.txt", "r") as f:
                try:
                    ppm = float(f.read().strip())
                    print(f"Calibração carregada: {ppm:.2f} px/mm")
                except ValueError:
                    print("Aviso: Arquivo de calibração corrompido. Usando PPM padrão.")

        else:
            print("Sistema não calibrado.")

        # Capturar a imagem do tomate
        camera = self.camera_widget

        if camera is None or camera.texture is None:
            print("Erro: Câmera não está enviando imagens.")
            return

        print("Procesando a imagem do tomate")



        # Conversão Kivy (RGBA) -> OpenCV (BGR)
        size = camera.texture.size
        pixels = camera.texture.pixels
        img_flat = np.frombuffer(pixels, dtype=np.uint8)
        img_rgba = img_flat.reshape(size[1], size[0], 4)
        img_bgr = cv2.cvtColor(img_rgba, cv2.COLOR_RGBA2BGR)
        img_bgr = cv2.flip(img_bgr, 0)
        img_bgr = cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)

        # Analisar Tomate
        analise = AnaliseTomate()

        try:
            # Isolar o vermelho (HSV)
            mascara = analise.segmentacao(img_bgr)

            # Achar as coordenadas e recortar o tomate
            maior_contorno, x, y, w_px, h_px = analise.buscarContornos(img_bgr, mascara)

            # Integrar por discos e geração dos dados agronômicos
            dados_calculados = analise.propFisicas(mascara, x, y, w_px, h_px, ppm)

            # Salvar uma imagem temporária para mostrar na tela de resultados
            # O buscarContornos já desenhou um retângulo verde na img_bgr
            img_com_contorno = img_bgr

            # Definir uma resolução máxima aceitável para exibição na tela
            max_largura = 1920
            max_altura = 1080

            # Pegar as dimensões atuais da imagem capturada
            altura_original, largura_original = img_com_contorno.shape[:2]

            # Só redimensionar se a imagem original for maior que o limite
            if largura_original > max_largura or altura_original > max_altura:
                # Calcular a proporção para não distorcer o tomate
                ratio_largura = max_largura / largura_original
                ratio_altura = max_altura / altura_original
                ratio = min(ratio_largura, ratio_altura) # Mantém a menor proporção

                # Nova resolução proporcional
                nova_resolucao = (int(largura_original * ratio), int(altura_original * ratio))

                # Aplica o redimensionamento físico (shrink)
                img_final_para_tela = cv2.resize(img_com_contorno, nova_resolucao, interpolation=cv2.INTER_AREA)
                print(f"Resolução ajustada para Android: {largura_original}x{altura_original} -> {nova_resolucao[0]}x{nova_resolucao[1]}")
            else:
                img_final_para_tela = img_com_contorno

            # Busca a pasta privada e segura do aplicativo no Android
            pasta_privada = App.get_running_app().user_data_dir

            # Cria o caminho completo e absoluto para o arquivo
            caminho_temp = os.path.join(pasta_privada, "temp_resultado.jpg")
            
            # Girar a imagem para visualização
            #img_rotacionada = cv2.rotate(img_final_para_tela, cv2.ROTATE_90_CLOCKWISE)

            # Salva a imagem usando o caminho seguro
            cv2.imwrite(caminho_temp, img_final_para_tela)

            # Passar para a tela de resultados
            try:
                tela_res = self.manager.get_screen("resultadospage")
                tela_res.atualizar_dados(dados_calculados, caminho_temp)

                # Mudar a tela para mostrar o relatório ao usuário
                self.manager.current = "resultadospage"
            except Exception as e:
                print(f"Erro ao mudar para tela de resultados: {e}")
        except Exception as e:
            print(f"Erro durante a análise do tomate: {e}")
            
    def baixar_csv(self):
        path_privado = App.get_running_app().user_data_dir
        origem = os.path.join(path_privado, "resultados_analise.csv")
        
        if not os.path.exists(origem):
            print("Erro: O arquivo ainda não existe. Faça uma análise primeiro.")
            return
        
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
                values.put("_display_name", "relatorio_tomates_ufrrj.csv")
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
                print("O arquivo está na pasta Download.")
                
            except Exception as e:
                print(f"Erro ao baixar arquivo: {e}")
                
        else:
            # Caminho para teste no computador
            print(f"No Desktop, o arquivo está em: {e}")
            

class ResultadosPage(Screen):
    # Variável para guardar temporariamente os dados antes de salvar no CSV
    dados_atuais = {}

    def atualizar_dados(self, dados_analise, caminho_imagem_processada):
        self.dados_atuais = dados_analise

        # Atualizando os Labels do Kivy (resultados.kv)
        if 'label_area' in self.ids:
            self.ids.label_area.text = f"{dados_analise.get('Area_Superficial', 0):.2f} cm2"
        if 'label_diam_geo' in self.ids:
            self.ids.label_diam_geo.text = f"{dados_analise.get('Diam_Geometrico', 0):.2f} cm"
        if 'label_esfericidade' in self.ids:
            self.ids.label_esfericidade.text = f"{dados_analise.get('Esfericidade', 0):.2f}"
        if 'label_volume' in self.ids:
            self.ids.label_volume.text = f"{dados_analise.get('Volume_cm3', 0):.2f} cm3"

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
            self.manager.current = "camerapage"

            # Limpar dados atuais da memória
            self.dados_atuais = {}

        except Exception as e:
            print(f"Erro ao tentar salvar o arquivo CSV: {e}")

