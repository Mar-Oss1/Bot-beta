"""
core/vision.py
Motor de visión por computadora del bot.
Usa OpenCV para template matching y Tesseract para OCR.
La ruta de Tesseract se lee desde .env via core/config.py.
"""
import cv2
import numpy as np
import pytesseract
import os

from core.config import TESSERACT_CMD, PROJECT_ROOT
from core.logger import get_logger

# ─── Configuración de Tesseract desde .env (no más rutas hardcodeadas) ───
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

log = get_logger("vision")


class Vision:
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold

    # ──────────────────────────────────────────
    # CONVERSIÓN
    # ──────────────────────────────────────────
    def pil_to_cv2(self, pil_image):
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # ──────────────────────────────────────────
    # BÚSQUEDA DE TEMPLATES
    # ──────────────────────────────────────────
    def find_template(self, screenshot, template_path: str, threshold: float = None):
        """
        Busca un template en el screenshot.
        Retorna (center_x, center_y) si lo encuentra, None si no.
        """
        threshold = threshold if threshold is not None else self.threshold
        ruta_absoluta = os.path.join(PROJECT_ROOT, template_path)
        screen_cv = self.pil_to_cv2(screenshot)
        template = cv2.imread(ruta_absoluta)

        if template is None:
            log.debug("Template no encontrado en disco: %s", ruta_absoluta)
            return None

        screen_gray = cv2.cvtColor(screen_cv, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template_gray.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            log.debug("✅ [%.2f] %s en (%d, %d)", max_val, os.path.basename(template_path), center_x, center_y)
            return (center_x, center_y)

        return None

    def find_all_templates(self, screenshot, template_path: str, threshold: float = 0.8):
        """
        Retorna una lista de centros (x, y) de todas las coincidencias
        del template en el screenshot.
        """
        screen_cv = self.pil_to_cv2(screenshot)
        screen_gray = cv2.cvtColor(screen_cv, cv2.COLOR_BGR2GRAY)

        ruta_absoluta = os.path.join(PROJECT_ROOT, template_path)
        img_template = cv2.imread(ruta_absoluta, 0)

        if img_template is None:
            return []

        w, h = img_template.shape[::-1]
        res = cv2.matchTemplate(screen_gray, img_template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)

        rects = [[int(pt[0]), int(pt[1]), w, h] for pt in zip(*loc[::-1])]
        if not rects:
            return []

        rects, _ = cv2.groupRectangles(rects, groupThreshold=1, eps=0.2)
        return [(x + w // 2, y + h // 2) for (x, y, w, h) in rects]

    def find_any(self, screenshot, template_paths: list):
        """Prueba múltiples templates y retorna el primero que encuentre."""
        for path in template_paths:
            result = self.find_template(screenshot, path)
            if result:
                return (path, result[0], result[1])
        return None

    def read_text(self, screenshot, region=None) -> str:
        """Extrae texto del screenshot (o de una región recortada)."""
        if region:
            x, y, w, h = region
            screenshot = screenshot.crop((x, y, x + w, y + h))
        return pytesseract.image_to_string(screenshot).strip()

    def detect_screen(self, screenshot, screen_templates: dict) -> str:
        """
        Identifica la pantalla actual comparando contra un dict
        {nombre: ruta_template}. Retorna el nombre o "unknown".
        """
        for screen_name, template_path in screen_templates.items():
            if self.find_template(screenshot, template_path, threshold=0.75):
                log.debug("Pantalla detectada: %s", screen_name)
                return screen_name
        return "unknown"
