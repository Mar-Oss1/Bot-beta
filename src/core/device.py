import time
import tempfile
import numpy as np
import uiautomator2 as u2
from PIL import Image

from core.config import DEVICE_SERIAL, APP_PACKAGE
from core.logger import get_logger

log = get_logger("device")

_MAX_RECONNECT = 3
_RECONNECT_WAIT = 6


class Device:
    def __init__(self, serial: str = DEVICE_SERIAL):
        self.serial = serial
        self.d: u2.Device | None = None

    def connect(self) -> bool:
        try:
            log.info("Conectando al dispositivo %s...", self.serial)
            self.d = u2.connect(self.serial)
            self.d.implicitly_wait(5)
            info = self.d.info
            log.info("✅ ADB exitoso. Pantalla: %dx%d",
                     info.get("displayWidth", 0), info.get("displayHeight", 0))
            return True
        except Exception as e:
            log.error("❌ No se pudo conectar: %s", e)
            return False

    def _reconnect(self) -> bool:
        for intento in range(1, _MAX_RECONNECT + 1):
            log.warning("⚡ Reconexión ADB — intento %d/%d...", intento, _MAX_RECONNECT)
            time.sleep(_RECONNECT_WAIT)
            try:
                self.d = u2.connect(self.serial)
                self.d.implicitly_wait(5)
                log.info("✅ Reconexión exitosa en intento %d.", intento)
                return True
            except Exception as e:
                log.error("Reconexión fallida: %s", e)
        log.critical("💀 No se pudo reconectar tras %d intentos.", _MAX_RECONNECT)
        return False

    def screenshot(self, format: str = "opencv") -> np.ndarray | Image.Image:
        for intento in range(_MAX_RECONNECT):
            try:
                return self.d.screenshot(format=format)
            except Exception as e:
                log.warning("Error screenshot (intento %d): %s", intento + 1, e)
                if not self._reconnect():
                    raise RuntimeError("ADB no disponible.") from e
        raise RuntimeError("No se pudo tomar screenshot.")

    def screenshot_to_file(self, path: str | None = None) -> str:
        if path is None:
            fd, path = tempfile.mkstemp(suffix=".png")
            import os
            os.close(fd)
        for intento in range(_MAX_RECONNECT):
            try:
                self.d.screenshot(path)
                return path
            except Exception as e:
                log.warning("Error screenshot_to_file (intento %d): %s", intento + 1, e)
                if not self._reconnect():
                    raise RuntimeError("ADB no disponible.") from e
        raise RuntimeError("No se pudo guardar screenshot.")

    def tap(self, x: int | float, y: int | float):
        for intento in range(_MAX_RECONNECT):
            try:
                self.d.click(int(x), int(y))
                return
            except Exception as e:
                log.warning("Error tap(%s,%s) — intento %d: %s", x, y, intento + 1, e)
                if not self._reconnect():
                    raise RuntimeError("ADB no disponible.") from e

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
        for intento in range(_MAX_RECONNECT):
            try:
                self.d.swipe(int(x1), int(y1), int(x2), int(y2), duration)
                return
            except Exception as e:
                log.warning("Error swipe — intento %d: %s", intento + 1, e)
                if not self._reconnect():
                    raise RuntimeError("ADB no disponible.") from e

    def open_app(self):
        try:
            self.d.app_start(APP_PACKAGE)
            log.debug("App iniciada: %s", APP_PACKAGE)
        except Exception as e:
            log.warning("Error al abrir app: %s. Reconectando...", e)
            if self._reconnect():
                self.d.app_start(APP_PACKAGE)
            else:
                raise RuntimeError("No se pudo abrir la app.") from e