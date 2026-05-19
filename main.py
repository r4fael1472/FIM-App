import os

os.environ['KIVY_CAMERA'] = 'android'
os.environ['KIVY_AUDIO'] = 'android'

from kivy.utils import platform

if platform == 'android':
	os.environ['KIVY_CAMERA'] = 'android'

from kivy.app import App
from kivy.lang import Builder
from telas import *
from botoes import *
from plyer import filechooser, camera
from kivy.clock import Clock
import cv2
from analise import AnaliseTomate
import csv
import threading


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
            
            # Pedimos permissão para Câmera e Armazenamento (essencial para o CSV)
            request_permissions([
                Permission.CAMERA,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ], callback)
    def build(self):
        return GUI

    def selecionar_arquivos(self):
        print("Abrindo seletor de arquivos...")
        # Abre a janela nativa para selecionar múltiplos arquivos (funciona no PC e Android)
        filechooser.open_file(
            title="Selecione as fotos dos tomates",
            filters=[("Imagens", "*.jpg", "*.jpeg", "*.png")],
            multiple=True,
            on_selection=self.callback_arquivos
        )

    def callback_arquivos(self, selection):
        if not selection:
            return

        print(f"{len(selection)} arquivo(s) selecionado(s). Iniciando lote em segundo plano...")

        threading.Thread(target=self.processar_arquivos, args=(selection,)).start()

    def processar_arquivos(self, lista_caminhos):
        ppm = 3.0
        pasta_privada = App.get_running_app().user_data_dir
        caminho_calibracao = os.path.join(pasta_privada, "calibracao.txt")
        if os.path.exists(caminho_calibracao):
            with open(caminho_calibracao, "r") as f:
                try:
                    ppm = float(f.read().strip())
                except ValueError:
                    print("Erro ao ler calibracao.txt. Usando PPM padrão = 3.0")
        else:
            print("Aviso: calibracao.txt não encontrado. Usando PPM = 3.0.")

        analise = AnaliseTomate()
        sucessos = 0


        caminho_csv = os.path.join(pasta_privada, "resultado_lote.csv")
        with open(caminho_csv, "w", encoding="utf-8") as f:
            # Cabeçalho do CSV configurado para relatórios da UFRRJ
            f.write("Arquivo;Largura_cm;Altura_cm;Diam_Geometrico_cm;Esfericidade;Area_Superficial_cm2;Volume_cm3\n")

            for caminho in lista_caminhos:
                nome_arquivo = os.path.basename(caminho)
                img_bgr = cv2.imread(caminho)

                if img_bgr is None:
                    print(f"Erro ao ler: {nome_arquivo} (Arquivo corrompido ou formato não suportado)")
                    continue

                try:
                    # Aplica o fluxo exato de Integração por Discos
                    mascara = analise.segmentacao(img_bgr)
                    maior_contorno, x, y, w_px, h_px = analise.buscarContornos(img_bgr, mascara)
                    dados = analise.propFisicas(mascara, x, y, w_px, h_px, ppm)
                    # Formata a linha. Trocar '.' por ',' ajuda ao abrir no Excel em PT-BR
                    linha = f"{nome_arquivo};{dados['Largura_cm']:.2f};{dados['Altura_cm']:.2f};{dados['Diam_Geometrico']:.2f};{dados['Esfericidade']:.2f};{dados['Area_Superficial']:.2f};{dados['Volume_cm3']:.2f}\n"
                    f.write(linha.replace('.', ','))

                    sucessos += 1
                    print(f"Processado: {nome_arquivo} | Volume: {dados['Volume_cm3']:.2f} cm³")

                except Exception as e:
                    print(f"Falha ao analisar o tomate em {nome_arquivo}: {e}")

        # 4. Retorna para a interface principal através do Clock
        Clock.schedule_once(lambda dt: self.aviso_conclusao(sucessos, total=len(lista_caminhos), caminho=caminho_csv), 0)

    def aviso_conclusao(self, sucessos, total, caminho):
        # Esta função roda de volta na "Thread principal" do Kivy
        print("\n" + "=" * 40)
        print(f"LOTE FINALIZADO: {sucessos} de {total} tomates analisados com sucesso!")
        print(f"Relatório salvo em: {caminho}")
        print("=" * 40 + "\n")

    def mudar_tela(self, id_tela):
        gerenciador_telas = self.root.ids["screen_manager"] #ARQUIVO CARREGADO NA VARIÁVEL GUI
        gerenciador_telas.current = id_tela


MainApp().run()
