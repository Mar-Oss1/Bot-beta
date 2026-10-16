"""
core/vision.py
Motor de visión por computadora optimizado con ROI dinámico (porcentajes) y Fallback.
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
        self._template_cache: dict[str, tuple[np.ndarray, tuple[int, int]]] = {}

    def _load_template(self, template_path: str) -> tuple[np.ndarray, tuple[int, int]] | None:
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
        return self._template_cache[template_path]

    def preload_templates(self, template_dir: str = "templates"):
        """Precarga recursivamente todos los templates."""
        ruta_abs = os.path.join(PROJECT_ROOT, template_dir)
        if not os.path.isdir(ruta_abs):
            return
        cargados = 0
        for root, _, files in os.walk(ruta_abs):
            for fname in files:
                if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                    abs_file = os.path.join(root, fname)
                    rel_path = os.path.relpath(abs_file, PROJECT_ROOT).replace("\\", "/")
                    if self._load_template(rel_path):
                        cargados += 1
        log.info("Precargados %d templates en caché RAM.", cargados)

    def clear_cache(self):
        self._template_cache.clear()

    @staticmethod
    def to_gray(image) -> np.ndarray:
        if isinstance(image, np.ndarray):
            if image.ndim == 2:
                return image
            elif image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            elif image.shape[2] == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        elif isinstance(image, Image.Image):
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        raise TypeError(f"Formato no soportado: {type(image)}")

    @staticmethod
    def _crop_zone(screen_gray: np.ndarray, zona: str) -> tuple[np.ndarray, int, int]:
        h, w = screen_gray.shape[:2]

        zonas_calc = {
            "COMPLETA": (0, h, 0, w),
            "CENTRO": (int(h * 0.15), int(h * 0.85), int(w * 0.2), int(w * 0.8)),
            "MITAD_INFERIOR": (int(h * 0.45), h, 0, w),
            "MITAD_SUPERIOR": (0, int(h * 0.55), 0, w),
            "MITAD_DERECHA": (0, h, int(w * 0.45), w),
            "MITAD_IZQUIERDA": (0, h, 0, int(w * 0.55)),
            "ESQUINA_INF_DER": (int(h * 0.45), h, int(w * 0.45), w),
            "ESQUINA_INF_IZQ": (int(h * 0.45), h, 0, int(w * 0.55)),
            "ESQUINA_SUP_DER": (0, int(h * 0.35), int(w * 0.5), w),
            "ESQUINA_SUP_IZQ": (0, int(h * 0.35), 0, int(w * 0.5)),
            "LISTA_RAIDS": (int(h * 0.15), int(h * 0.9), int(w * 0.35), int(w * 0.9))
        }

        if not zona or zona not in zonas_calc:
            return screen_gray, 0, 0

        y1, y2, x1, x2 = zonas_calc[zona]
        return screen_gray[y1:y2, x1:x2], x1, y1

    def find_template(
            self,
            screenshot,
            template_path: str,
            threshold: float = None,
            zona: str = "COMPLETA"
    ) -> tuple[int, int] | None:
        threshold = threshold if threshold is not None else self.threshold
        cached = self._load_template(template_path)
        if cached is None:
            return None

        template_gray, (h, w) = cached
        screen_gray = self.to_gray(screenshot)

        # 1. Intento ultra rápido en la ZONA indicada
        search_area, offset_x, offset_y = self._crop_zone(screen_gray, zona)

        if search_area.shape[0] >= h and search_area.shape[1] >= w:
            res = cv2.matchTemplate(search_area, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val >= threshold:
                cx = max_loc[0] + offset_x + w // 2
                cy = max_loc[1] + offset_y + h // 2
                return (cx, cy)

        # 2. Fallback seguro en pantalla completa si falló la zona o quedó fuera
        if zona and zona != "COMPLETA":
            res_full = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res_full)

            if max_val >= threshold:
                cx = max_loc[0] + w // 2
                cy = max_loc[1] + h // 2
                return (cx, cy)

        return None

    def find_all_templates(
            self,
            screenshot,
            template_path: str,
            threshold: float = 0.8,
            zona: str = "COMPLETA"
    ) -> list[tuple[int, int]]:
        cached = self._load_template(template_path)
        if cached is None:
            return []

        template_gray, (h, w) = cached
        screen_gray = self.to_gray(screenshot)
        search_area, offset_x, offset_y = self._crop_zone(screen_gray, zona)

        if search_area.shape[0] < h or search_area.shape[1] < w:
            return []

        res = cv2.matchTemplate(search_area, template_gray, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        rects = [[int(pt[0]), int(pt[1]), w, h] for pt in zip(*loc[::-1])]

        if not rects:
            return []
        rects, _ = cv2.groupRectangles(rects, groupThreshold=1, eps=0.2)
        return [(x + offset_x + w // 2, y + offset_y + h // 2) for (x, y, w, h) in rects]

    def find_any(
            self,
            screenshot,
            template_paths: list[str],
            threshold: float = None,
            zona: str = "COMPLETA"
    ):
        threshold = threshold if threshold is not None else self.threshold
        screen_gray = self.to_gray(screenshot)

        for path in template_paths:
            pos = self.find_template(screen_gray, path, threshold=threshold, zona=zona)
            if pos:
                return (path, pos[0], pos[1])
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
            interval: float = 0.15,
            log_progress: bool = False,
            zona: str = "COMPLETA"
    ) -> tuple[int, int] | None:
        threshold = threshold if threshold is not None else self.threshold
        inicio = time.monotonic()
        intentos = 0

        while time.monotonic() - inicio < timeout:
            intentos += 1
            try:
                screen = screenshot_func()
                pos = self.find_template(screen, template_path, threshold, zona=zona)
                if pos:
                    if log_progress:
                        log.debug("✅ Encontrado en %.2fs (%d intentos): %s",
                                  time.monotonic() - inicio, intentos, template_path)
                    return pos
            except Exception as e:
                log.warning("Error en wait_for_template (intento %d): %s", intentos, e)
            time.sleep(interval)

        log.warning("⏱️ Timeout: %s tras %.2fs (%d intentos)",
                    template_path, time.monotonic() - inicio, intentos)
        return None

    def wait_for_screen_stable(
            self,
            screenshot_func,
            timeout: int = 15,
            interval: float = 0.4,
            stability_threshold: float = 0.98,
            min_stable_checks: int = 2,
            log_progress: bool = False
    ) -> bool:
        inicio = time.monotonic()
        small_prev = None
        checks_estables = 0

        while time.monotonic() - inicio < timeout:
            try:
                screen_gray = self.to_gray(screenshot_func())
                small_curr = cv2.resize(screen_gray, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)

                if small_prev is not None:
                    diff = cv2.absdiff(small_curr, small_prev)
                    # Corregido el signo de resta que faltaba
                    similarity = 1.0 - (cv2.countNonZero(diff) / small_curr.size)

                    if similarity >= stability_threshold:
                        checks_estables += 1
                        if checks_estables >= min_stable_checks:
                            return True
                    else:
                        checks_estables = 0

                small_prev = small_curr
                time.sleep(interval)
            except Exception as e:
                log.warning("Error en wait_for_screen_stable: %s", e)
                time.sleep(interval)

        return False

    # ──────────────────────────────────────────
    # OCR (Compatible con NumPy y PIL)
    # ──────────────────────────────────────────
    def read_text(self, screenshot, region=None) -> str:
        gray = self.to_gray(screenshot)
        if region:
            x, y, w, h = region
            gray = gray[y:y + h, x:x + w]
        return pytesseract.image_to_string(gray).strip()

    def detect_screen(self, screenshot, screen_templates: dict) -> str:
        screen_gray = self.to_gray(screenshot)
        for screen_name, template_path in screen_templates.items():
            if self.find_template(screen_gray, template_path, threshold=0.75):
                return screen_name
        return "unknown"