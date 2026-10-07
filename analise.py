import cv2
import numpy as np
import math


class AnaliseFruto:
    def __init__(self, area_minima_px=300, kernel_blur=(5, 5), kernel_close_tam=15, kernel_dilate_tam=3):

        self.area_minima_px = area_minima_px

        self.kernel_blur = kernel_blur
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_close_tam, kernel_close_tam))
        self.kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_dilate_tam, kernel_dilate_tam))

    def segmentacao(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, self.kernel_blur, 0)

        v = np.median(blur)
        lower_thresh = int(max(0, (1.0 - 0.33) * v))
        upper_thresh = int(min(255, (1.0 + 0.33) * v))
        edges = cv2.Canny(blur, lower_thresh, upper_thresh)

        edges_dilated = cv2.dilate(edges, self.kernel_dilate, iterations=1)
        mascara_fechada = cv2.morphologyEx(edges_dilated, cv2.MORPH_CLOSE, self.kernel_close)

        h, w = mascara_fechada.shape
        mask_floodfill = mascara_fechada.copy()
        mask_padding = np.zeros((h + 2, w + 2), np.uint8)
        cv2.floodFill(mask_floodfill, mask_padding, (0, 0), 255)
        mascara_solida = mascara_fechada | cv2.bitwise_not(mask_floodfill)

        return mascara_solida

    def buscarContornos(self, img, mascara):
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        contornos_validos = [c for c in contornos if cv2.contourArea(c) > self.area_minima_px]

        if len(contornos_validos) < 2:
            print("Erro: Nao foram encontrados pelo menos dois objetos validos")
            return None, None, 0, 0, 0, img.copy()
            
        contornos_ordenados = sorted(contornos_validos, key=cv2.contourArea, reverse=True)
        maior_contorno = contornos_ordenados[0]
        referencia_contorno = contornos_ordenados[1]

        x, y, w_box, h_box = cv2.boundingRect(maior_contorno)

        img_debug = img.copy()
        cv2.drawContours(img_debug, [maior_contorno], -1, (0, 255, 0), 2)
        cv2.drawContours(img_debug, [referencia_contorno], -1, (0, 0, 255), 2)

        return maior_contorno, referencia_contorno, x, y, h_box, img_debug

    def calibracao(self, diametro_real_referencia_mm, referencia_contorno):
        area_px = cv2.contourArea(referencia_contorno)
        
        raio_px = math.sqrt(area_px / math.pi)
        diametro_px = raio_px * 2
        
        if diametro_real_referencia_mm <= 0:
            raise ValueError(
                "diametro_real_referencia_mm deve ser maior que zero "
                f"(recebido: {diametro_real_referencia_mm})."
            )
        if diametro_px <= 0:
            raise ValueError(
                "O contorno de referência produziu diâmetro em pixels <= 0; "
                "a segmentação da referência provavelmente falhou."
            )

        ppm = diametro_px / diametro_real_referencia_mm
        return ppm

    def _alinhar_fruto(self, mascara, maior_contorno):
        (cx, cy), (w_rect, h_rect), angulo = cv2.minAreaRect(maior_contorno)

        correcao = angulo % 90
        if correcao > 45:
            correcao -= 90

        h_img, w_img = mascara.shape
        M = cv2.getRotationMatrix2D((cx, cy), correcao, 1.0)

        mascara_fruto_isolada = np.zeros_like(mascara)
        cv2.drawContours(mascara_fruto_isolada, [maior_contorno], -1, 255, thickness=cv2.FILLED)
        mascara_rotacionada = cv2.warpAffine(mascara_fruto_isolada, M, (w_img, h_img))

        contornos_rot, _ = cv2.findContours(mascara_rotacionada, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos_rot:
            return mascara_fruto_isolada, maior_contorno

        contorno_alinhado = max(contornos_rot, key=cv2.contourArea)
        return mascara_rotacionada, contorno_alinhado

    def propFisicas(self, mascara, maior_contorno, x, y, h_box, ppm):
        if ppm <= 0:
            raise ValueError(f"ppm deve ser maior que zero (recebido: {ppm}).")
            
        rect = cv2.minAreaRect(maior_contorno)
        box = cv2.boxPoints(rect)
        
        p0, p1, p2 = box[0], box[1], box[2]
        
        v1 = p1 - p0
        v2 = p2 - p1
        
        dist1 = math.hypot(v1[0], v1[1])
        dist2 = math.hypot(v2[0], v2[1])
        
        if abs(v1[1]) > abs(v1[0]):
            h_box_subpixel = dist1
            w_box_subpixel = dist2
        else:
            h_box_subpixel = dist2
            w_box_subpixel = dist1
            
        largura_mm = (w_box_subpixel / ppm)
        altura_mm = (h_box_subpixel / ppm)

        largura_cm = largura_mm / 10
        altura_cm = altura_mm / 10

        D = largura_cm
        H = altura_cm

        Dg = (H * (D**2)) ** (1/3)
        Da = (H + D + D) / 3
        
        maior_dimensao = max(H, D)
        Es = Dg / maior_dimensao
        As = math.pi * (Dg**2)

        mascara_fruto, contorno_alinhado = self._alinhar_fruto(mascara, maior_contorno)
        x_rot, y_rot, w_box_int, h_box_int = cv2.boundingRect(contorno_alinhado)       

        # CÁLCULO DO VOLUME
        volume_total_mm3 = 0
        altura_pixel_mm = (1 / ppm)

        for linha in range(y_rot, y_rot + h_box_int - 1):
            idx_atual = np.nonzero(mascara_fruto[linha, :])[0]
            idx_prox = np.nonzero(mascara_fruto[linha + 1, :])[0]

            if idx_atual.size > 0 and idx_prox.size > 0:
                diam_px_atual = idx_atual[-1] - idx_atual[0] + 1
                diam_px_prox = idx_prox[-1] - idx_prox[0] + 1

                diam_mm_atual = diam_px_atual / ppm
                diam_mm_prox = diam_px_prox / ppm

                area1 = math.pi * ((diam_mm_atual / 2) ** 2)
                area2 = math.pi * ((diam_mm_prox / 2) ** 2)

                area_media = (area1 + area2) / 2
                volume_total_mm3 += area_media * altura_pixel_mm

        volume_final_cm3 = volume_total_mm3 / 1000

        return {
            "Largura_cm": largura_cm,
            "Altura_cm": altura_cm,
            "Diam_Geometrico": Dg,
            "Diam_Aritmetico": Da,
            "Esfericidade": Es,
            "Area_Superficial": As,
            "Volume_cm3": volume_final_cm3
        }
