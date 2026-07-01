"""
core/device.py
Abstracción del dispositivo ADB (POCO X5 Pro / uiautomator2).
Incluye lógica de reconexión automática para cuando ADB se interrumpe
en medio de una rutina (cable suelto, USB sleep, reset del demonio ADB).
"""
import time
import uiautomator2 as u2
from PIL import Image

from core.config import DEVICE_SERIAL, APP_PACKAGE
from core.logger import get_logger

log = get_logger("device")

_MAX_RECONNECT = 3
_RECONNECT_WAIT = 6  # segundos entre reintentos de reconexión


class Device:
    def __init__(self, serial: str = DEVICE_SERIAL):
        self.serial = serial
        self.d: u2.Device | None = None

    # ──────────────────────────────────────────
    # CONEXIÓN Y RECONEXIÓN
    # ──────────────────────────────────────────
    def connect(self) -> bool:
        """Conecta al dispositivo por primera vez. Retorna True si tuvo éxito."""
        try:
            log.info("Conectando al dispositivo %s...", self.serial)
            self.d = u2.connect(self.serial)
            self.d.implicitly_wait(5)
            info = self.d.info
            log.info(
                "✅ Conexión ADB exitosa. Pantalla: %dx%d",
                info.get("displayWidth", 0),
                info.get("displayHeight", 0),
            )
            return True
        except Exception as e:
            log.error("❌ No se pudo conectar al dispositivo: %s", e)
            return False

    def _reconnect(self) -> bool:
        """
        Intenta reconectar al dispositivo hasta _MAX_RECONNECT veces.
        Se llama automáticamente cuando screenshot() o tap() fallan.
        """
        for intento in range(1, _MAX_RECONNECT + 1):
            log.warning(
                "⚡ Reconexión ADB — intento %d/%d...", intento, _MAX_RECONNECT
            )
            time.sleep(_RECONNECT_WAIT)
            try:
                self.d = u2.connect(self.serial)
                self.d.implicitly_wait(5)
                log.info("✅ Reconexión exitosa en el intento %d.", intento)
                return True
            except Exception as e:
                log.error("Reconexión fallida: %s", e)
        log.critical(
            "💀 No se pudo reconectar al dispositivo tras %d intentos.", _MAX_RECONNECT
        )
        return False

    # ──────────────────────────────────────────
    # OPERACIONES CON RETRY AUTOMÁTICO
    # ──────────────────────────────────────────
    def screenshot(self) -> Image.Image:
        """
        Toma un screenshot y lo retorna como imagen PIL.
        Si falla por desconexión ADB, intenta reconectar y reintentar.
        """
        for intento in range(_MAX_RECONNECT):
            try:
                return self.d.screenshot(format="pillow")
            except Exception as e:
                log.warning("Error en screenshot (intento %d): %s", intento + 1, e)
                if not self._reconnect():
                    raise RuntimeError("Dispositivo ADB no disponible tras reconexión.") from e
        raise RuntimeError("No se pudo tomar screenshot.")

    def tap(self, x: int | float, y: int | float):
        """Toca las coordenadas indicadas con retry automático ante desconexión."""
        for intento in range(_MAX_RECONNECT):
            try:
                self.d.click(int(x), int(y))
                return
            except Exception as e:
                log.warning("Error en tap(%s,%s) — intento %d: %s", x, y, intento + 1, e)
                if not self._reconnect():
                    raise RuntimeError("Dispositivo ADB no disponible.") from e

    # ──────────────────────────────────────────
    # APP
    # ──────────────────────────────────────────
    def open_app(self):
        """Abre Evertale. Si falla, intenta reconectar primero."""
        try:
            self.d.app_start(APP_PACKAGE)
            log.debug("App iniciada: %s", APP_PACKAGE)
        except Exception as e:
            log.warning("Error al abrir app: %s. Reconectando...", e)
            if self._reconnect():
                self.d.app_start(APP_PACKAGE)
            else:
                raise RuntimeError("No se pudo abrir la app tras reconexión.") from e
