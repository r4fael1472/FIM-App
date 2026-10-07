# FIM - Fruit Image Metrics

Aplicativo móvel desenvolvido em Python e Kivy para a extração não destrutiva de parâmetros físicos de frutos (esfericidade, área de superfície e volume) utilizando visão computacional (OpenCV).

Este projeto é fruto do Trabalho de Conclusão de Curso (TCC) em Sistemas de Informação pela **Universidade Federal Rural do Rio de Janeiro (UFRRJ)**.

## Funcionalidades
* **Calibração Espacial Dinâmica:** Utilização de um objeto de referência circular para extração da métrica de Pixels por Milímetro (PPM).
* **Controle de Coplanaridade:** Integração com o acelerômetro do smartphone para garantir o paralelismo da captura e evitar distorções de perspetiva.
* **Extração Paramétrica:** Cálculo da área superficial, esfericidade e volume.
* **Exportação de Dados:** Geração automática de relatórios em formato `.csv` guardados no armazenamento local do dispositivo.

## Tecnologias Utilizadas
* **[Python 3](https://www.python.org/)** - Lógica central e cálculos matemáticos.
* **[Kivy](https://kivy.org/)** - Framework para o desenvolvimento da interface gráfica móvel (UI).
* **[OpenCV](https://opencv.org/) & [NumPy](https://numpy.org/)** - Pipeline de visão computacional (Filtro Canny adaptativo, operações morfológicas, trigonometria vetorial).
* **[Buildozer](https://buildozer.readthedocs.io/)** - Compilação e empacotamento para Android (APK).

## Como instalar e testar no Android
Não é necessário compilar o código para testar a aplicação no seu telemóvel.
1. Aceda à secção [Releases](../../releases) deste repositório.
2. Descarregue o ficheiro `FIM-App.apk`.
3. Instale no seu dispositivo Android (poderá ser necessário autorizar a instalação de aplicações de fontes desconhecidas).
