import cv2
import numpy as np
import pytesseract
from PIL import Image
import os

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 1. Calculamos la ruta raíz de tu proyecto
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))


class Vision:
    def __init__(self, threshold=0.8):
        self.threshold = threshold

    def pil_to_cv2(self, pil_image):
        """Convierte imagen PIL a formato OpenCV"""
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def find_template(self, screenshot, template_path, threshold=None):
        """
        Busca una imagen (botón) dentro del screenshot.
        Retorna (x, y) del centro si lo encuentra, None si no.
        """
        threshold = threshold or self.threshold

        # 2. Convertimos la ruta relativa ("templates/imagen.png") a ruta absoluta
        ruta_absoluta = os.path.join(PROJECT_ROOT, template_path)

        screen_cv = self.pil_to_cv2(screenshot)

        # 3. Le pasamos la ruta completa a OpenCV
        template = cv2.imread(ruta_absoluta)

        if template is None:
            print(f"❌ Template no encontrado en disco: {ruta_absoluta}")
            return None

        screen_gray = cv2.cvtColor(screen_cv, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template_gray.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            print(f"✅ Encontrado ({max_val:.2f}): {os.path.basename(template_path)} en ({center_x}, {center_y})")
            return (center_x, center_y)
        else:
            return None
    def find_any(self, screenshot, template_paths):
        """
        Busca cualquiera de una lista de templates.
        Útil para detectar en qué pantalla estás.
        Retorna (template_path, x, y) del primero que encuentre.
        """
        for path in template_paths:
            result = self.find_template(screenshot, path)
            if result:
                return (path, result[0], result[1])
        return None

    def read_text(self, screenshot, region=None):
        """
        Lee texto de la pantalla con OCR.
        region: (x, y, width, height) para leer solo una zona
        """
        if region:
            x, y, w, h = region
            screenshot = screenshot.crop((x, y, x + w, y + h))

        text = pytesseract.image_to_string(screenshot)
        return text.strip()

    def detect_screen(self, screenshot, screen_templates: dict):
        """
        Detecta en qué pantalla del juego estás.
        screen_templates: {'nombre_pantalla': 'ruta/template.png'}
        Retorna el nombre de la pantalla o 'unknown'
        """
        for screen_name, template_path in screen_templates.items():
            result = self.find_template(screenshot, template_path, threshold=0.75)
            if result:
                print(f"📍 Pantalla detectada: {screen_name}")
                return screen_name
        return "unknown"