"""
core/vision.py
Motor de visión por computadora del bot.
Cambios clave:
  - Templates cacheados en memoria (lazy + preload)
  - Conversión PIL→Gray inteligente (sin duplicar)
  - find_any optimizado (1 screenshot, N templates)
  - wait_for_screen_stable usa resize 25% para comparación rápida
"""
import cv2
import numpy as np
import pytesseract
import os
import time
from PIL import Image

from core.config import TESSERACT_CMD, PROJECT_ROOT
from core.logger import get_logger

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
log = get_logger("vision")


class Vision:
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        # Cache: ruta_relativa -> (template_gray, (h, w))
        self._template_cache: dict[str, tuple[np.ndarray, tuple[int, int]]] = {}

    # ──────────────────────────────────────────
    # CACHEO DE TEMPLATES
    # ──────────────────────────────────────────
    def _load_template(self, template_path: str) -> tuple[np.ndarray, tuple[int, int]] | None:
        """Carga template en caché. Clave = ruta relativa."""
        if template_path in self._template_cache:
            return self._template_cache[template_path]

        ruta_absoluta = os.path.join(PROJECT_ROOT, template_path)
        if not os.path.exists(ruta_absoluta):
            log.debug("Template no encontrado: %s", ruta_absoluta)
            return None

        template = cv2.imread(ruta_absoluta, cv2.IMREAD_GRAYSCALE)
        if template is None:
            log.debug("No se pudo decodificar: %s", ruta_absoluta)
            return None

        h, w = template.shape
        self._template_cache[template_path] = (template, (h, w))
        log.debug("Template cacheado: %s (%dx%d)", template_path, w, h)
        return self._template_cache[template_path]

    def preload_templates(self, template_dir: str = "templates"):
        """Precarga TODOS los templates al iniciar. Llama en main.py"""
        ruta_abs = os.path.join(PROJECT_ROOT, template_dir)
        if not os.path.isdir(ruta_abs):
            return
        cargados = 0
        for fname in os.listdir(ruta_abs):
            if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                rel_path = os.path.join(template_dir, fname).replace("\\", "/")
                if self._load_template(rel_path):
                    cargados += 1
        log.info("Precargados %d templates en caché.", cargados)

    def clear_cache(self):
        self._template_cache.clear()

    # ──────────────────────────────────────────
    # CONVERSIÓN INTELIGENTE
    # ──────────────────────────────────────────
    @staticmethod
    def to_gray(image) -> np.ndarray:
        """Convierte PIL.Image o np.ndarray (BGR/Gray/BGRA) a grayscale."""
        if isinstance(image, Image.Image):
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        elif isinstance(image, np.ndarray):
            if len(image.shape) == 2:
                return image
            elif image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif image.shape[2] == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        raise TypeError(f"Formato no soportado: {type(image)}")

    # ──────────────────────────────────────────
    # BÚSQUEDA DE TEMPLATES
    # ──────────────────────────────────────────
    def find_template(self, screenshot, template_path: str, threshold: float = None) -> tuple[int, int] | None:
        threshold = threshold if threshold is not None else self.threshold
        cached = self._load_template(template_path)
        if cached is None:
            return None

        template_gray, (h, w) = cached
        screen_gray = self.to_gray(screenshot)

        result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            cx = max_loc[0] + w // 2
            cy = max_loc[1] + h // 2
            log.debug("✅ [%.2f] %s en (%d, %d)", max_val, os.path.basename(template_path), cx, cy)
            return (cx, cy)
        return None

    def find_all_templates(self, screenshot, template_path: str, threshold: float = 0.8) -> list[tuple[int, int]]:
        cached = self._load_template(template_path)
        if cached is None:
            return []

        template_gray, (h, w) = cached
        screen_gray = self.to_gray(screenshot)

        res = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        rects = [[int(pt[0]), int(pt[1]), w, h] for pt in zip(*loc[::-1])]

        if not rects:
            return []
        rects, _ = cv2.groupRectangles(rects, groupThreshold=1, eps=0.2)
        return [(x + w // 2, y + h // 2) for (x, y, w, h) in rects]

    def find_any(self, screenshot, template_paths: list[str], threshold: float = None):
        """
        Prueba múltiples templates sobre UN screenshot convertido.
        Retorna (template_path, center_x, center_y) o None.
        """
        threshold = threshold if threshold is not None else self.threshold
        screen_gray = self.to_gray(screenshot)  # ← UNA conversión

        for path in template_paths:
            cached = self._load_template(path)
            if cached is None:
                continue

            template_gray, (h, w) = cached
            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= threshold:
                cx = max_loc[0] + w // 2
                cy = max_loc[1] + h // 2
                log.debug("✅ [%.2f] %s en (%d, %d)", max_val, os.path.basename(path), cx, cy)
                return (path, cx, cy)
        return None

    # ──────────────────────────────────────────
    # ESPERA INTELIGENTE
    # ──────────────────────────────────────────
    def wait_for_template(
            self,
            screenshot_func,
            template_path: str,
            timeout: int = 10,
            threshold: float = None,
            interval: float = 0.3,
            log_progress: bool = False
    ) -> tuple[int, int] | None:
        threshold = threshold if threshold is not None else self.threshold
        inicio = time.time()
        intentos = 0

        if log_progress:
            log.debug("🔍 Esperando: %s (timeout: %ds)", template_path, timeout)

        while time.time() - inicio < timeout:
            intentos += 1
            try:
                screen = screenshot_func()
                pos = self.find_template(screen, template_path, threshold)
                if pos:
                    elapsed = time.time() - inicio
                    if log_progress:
                        log.debug("✅ Encontrado en %.2fs (%d intentos): %s", elapsed, intentos, template_path)
                    return pos
            except Exception as e:
                log.warning("Error en wait_for_template (intento %d): %s", intentos, e)
            time.sleep(interval)

        elapsed = time.time() - inicio
        log.warning("⏱️ Timeout: %s tras %.2fs (%d intentos)", template_path, elapsed, intentos)
        return None

    def wait_for_screen_stable(
            self,
            screenshot_func,
            timeout: int = 15,
            interval: float = 0.8,
            stability_threshold: float = 0.98,
            min_stable_checks: int = 2,
            log_progress: bool = False
    ) -> bool:
        inicio = time.time()
        screenshot_anterior = None
        checks_estables = 0

        if log_progress:
            log.debug("🔍 Esperando estabilidad (timeout: %ds)...", timeout)

        while time.time() - inicio < timeout:
            try:
                screen_actual = screenshot_func()
                screen_gray = self.to_gray(screen_actual)

                if screenshot_anterior is not None:
                    # Comparación rápida a 25% de resolución
                    small_curr = cv2.resize(screen_gray, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
                    small_prev = cv2.resize(screenshot_anterior, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
                    diff = cv2.absdiff(small_curr, small_prev)
                    non_zero = cv2.countNonZero(diff)
                    similarity = 1.0 - (non_zero / small_curr.size)

                    if log_progress:
                        log.debug("  Similitud: %.4f (%d/%d)", similarity, checks_estables, min_stable_checks)

                    if similarity >= stability_threshold:
                        checks_estables += 1
                        if checks_estables >= min_stable_checks:
                            if log_progress:
                                log.debug("✅ Pantalla estable tras %.2fs", time.time() - inicio)
                            return True
                    else:
                        checks_estables = 0

                screenshot_anterior = screen_gray
                time.sleep(interval)
            except Exception as e:
                log.warning("Error en wait_for_screen_stable: %s", e)
                time.sleep(interval)

        log.warning("⏱️ Timeout estabilidad tras %.2fs", time.time() - inicio)
        return False

    # ──────────────────────────────────────────
    # OCR
    # ──────────────────────────────────────────
    def read_text(self, screenshot, region=None) -> str:
        if region:
            x, y, w, h = region
            screenshot = screenshot.crop((x, y, x + w, y + h))
        return pytesseract.image_to_string(screenshot).strip()

    def detect_screen(self, screenshot, screen_templates: dict) -> str:
        for screen_name, template_path in screen_templates.items():
            if self.find_template(screenshot, template_path, threshold=0.75):
                log.debug("Pantalla detectada: %s", screen_name)
                return screen_name
        return "unknown"
