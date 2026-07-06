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
import time  # ← NUEVO: necesario para wait_for_template
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

    # ──────────────────────────────────────────
    # ⭐ NUEVA FUNCIÓN: ESPERA INTELIGENTE ⭐
    # ──────────────────────────────────────────
    def wait_for_template(
            self,
            screenshot_func,
            template_path: str,
            timeout: int = 10,
            threshold: float = None,
            interval: float = 0.3,
            log_progress: bool = False
    ):
        """
        Espera hasta que aparezca un template en pantalla o se agote el timeout.
        Reemplaza los time.sleep() fijos por una espera inteligente.

        Args:
            screenshot_func: Función que toma screenshots (ej: device.screenshot)
            template_path: Ruta del template a buscar (ej: "templates/btn_ok.png")
            timeout: Segundos máximos de espera (default: 10)
            threshold: Umbral de coincidencia (default: usa self.threshold)
            interval: Segundos entre cada intento (default: 0.3)
            log_progress: Si True, logea cada intento (útil para debug)

        Returns:
            (center_x, center_y) si encuentra el template
            None si se agota el timeout

        Ejemplo de uso:
            pos = vision.wait_for_template(
                device.screenshot,
                "templates/btn_ok.png",
                timeout=10
            )
            if pos:
                device.tap(pos[0], pos[1])
        """
        threshold = threshold if threshold is not None else self.threshold
        inicio = time.time()
        intentos = 0

        if log_progress:
            log.debug("🔍 Esperando template: %s (timeout: %ds)", template_path, timeout)

        while time.time() - inicio < timeout:
            intentos += 1
            try:
                screen = screenshot_func()
                pos = self.find_template(screen, template_path, threshold)

                if pos:
                    elapsed = time.time() - inicio
                    if log_progress:
                        log.debug(
                            "✅ Template encontrado en %.2fs (intento %d): %s",
                            elapsed, intentos, template_path
                        )
                    return pos
            except Exception as e:
                log.warning("Error en wait_for_template (intento %d): %s", intentos, e)

            time.sleep(interval)

        elapsed = time.time() - inicio
        log.warning(
            "⏱️  Timeout esperando %s tras %.2fs (%d intentos)",
            template_path, elapsed, intentos
        )
        return None

    def wait_for_screen_stable(
            self,
            screenshot_func,
            timeout: int = 15,
            interval: float = 0.8,
            stability_threshold: float = 0.98,
            min_stable_checks: int = 2,
            log_progress: bool = False
    ):
        """
        Espera hasta que la pantalla deje de cambiar (todos los banners cargaron).
        Compara screenshots consecutivos y retorna cuando la similitud es alta.

        Args:
            screenshot_func: Función que toma screenshots
            timeout: Segundos máximos de espera (default: 15)
            interval: Segundos entre cada comparación (default: 0.8)
            stability_threshold: Similitud mínima para considerar "estable" (0.0-1.0)
            min_stable_checks: Cuántas comparaciones estables consecutivas necesita
            log_progress: Si True, logea el progreso

        Returns:
            True si la pantalla se estabilizó
            False si se agotó el timeout

        Ejemplo:
            # Después de abrir el juego, esperar a que carguen todos los banners
            dev.open_app()
            vis.wait_for_screen_stable(dev.screenshot, timeout=15)
            # Ahora sí, la pantalla está lista para interactuar
        """
        import time
        from core.logger import get_logger
        log = get_logger("vision.stability")

        inicio = time.time()
        screenshot_anterior = None
        checks_estables = 0

        if log_progress:
            log.debug("🔍 Esperando estabilidad de pantalla (timeout: %ds)...", timeout)

        while time.time() - inicio < timeout:
            try:
                screen_actual = screenshot_func()
                screen_cv = self.pil_to_cv2(screen_actual)
                screen_gray = cv2.cvtColor(screen_cv, cv2.COLOR_BGR2GRAY)

                if screenshot_anterior is not None:
                    # Calcular similitud entre screenshots
                    diff = cv2.absdiff(screenshot_anterior, screen_gray)
                    non_zero = cv2.countNonZero(diff)
                    total_pixels = screen_gray.size
                    similarity = 1.0 - (non_zero / total_pixels)

                    if log_progress:
                        log.debug("  Similitud: %.4f (estable: %d/%d)",
                                  similarity, checks_estables, min_stable_checks)

                    if similarity >= stability_threshold:
                        checks_estables += 1
                        if checks_estables >= min_stable_checks:
                            elapsed = time.time() - inicio
                            if log_progress:
                                log.debug("✅ Pantalla estable tras %.2fs", elapsed)
                            return True
                    else:
                        checks_estables = 0  # Reset si hay cambio

                screenshot_anterior = screen_gray
                time.sleep(interval)

            except Exception as e:
                log.warning("Error en wait_for_screen_stable: %s", e)
                time.sleep(interval)

        elapsed = time.time() - inicio
        log.warning("⏱️  Timeout esperando estabilidad de pantalla tras %.2fs", elapsed)
        return False
    
    # ──────────────────────────────────────────
    # OCR
    # ──────────────────────────────────────────
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
