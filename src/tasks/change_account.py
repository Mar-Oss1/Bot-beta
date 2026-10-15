import time
from core.logger import get_logger

log = get_logger("change_account")


class ChangeAccount:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def execute(self, serial_cuenta: str, pos_nube_inicial: tuple[int, int] | None = None) -> bool:
        log.info("\n[🔄] Iniciando cambio a cuenta: %s", serial_cuenta)

        pos_nube = pos_nube_inicial or self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_nube.png",
            timeout=25,
            threshold=0.75,
            interval=0.25,
            zona="ESQUINA_INF_IZQ"
        )
        if not pos_nube:
            log.error("❌ No se detectó la pantalla de inicio con nube.")
            self.device.screenshot_to_file("screenshots/error_cambio_cuenta.png")
            return False

        self.device.tap(pos_nube[0], pos_nube[1])

        pos_input = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/input_restore.png",
            timeout=8,
            threshold=0.75,
            interval=0.2,
            zona="CENTRO"
        )
        if not pos_input:
            log.warning("[!] No apareció el menú de restauración.")
            return False

        pos_use = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_use_code.png",
            timeout=3,
            threshold=0.75,
            interval=0.2,
            zona="CENTRO"
        )
        if not pos_use:
            log.warning("[!] No se encontró el botón 'Use Code'.")
            return False

        self.device.tap(pos_input[0], pos_input[1])
        time.sleep(0.5)

        self.device.d.send_keys(serial_cuenta)
        time.sleep(0.6)

        self.device.tap(pos_use[0], pos_use[1])
        time.sleep(1.5)

        # Confirmación 1: Restore Anyway (timeout subido a 5s por si la red tarda en validar el código)
        pos_restore_anyway = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_restore_anyway.png",
            timeout=5.0,
            threshold=0.75,
            interval=0.25,
            zona="CENTRO"
        )
        if pos_restore_anyway:
            log.info("[>] Detectado 'Restore Anyway'. Confirmando...")
            self.device.tap(pos_restore_anyway[0], pos_restore_anyway[1])
            time.sleep(1.5)

        # Confirmación 2: OK de éxito (timeout subido a 6s para esperar respuesta del servidor)
        pos_ok = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_ok_restore.png",
            timeout=6.0,
            threshold=0.75,
            interval=0.25,
            zona="CENTRO"
        )
        if pos_ok:
            log.info("[>] Detectado 'OK' de restauración. Confirmando reinicio...")
            self.device.tap(pos_ok[0], pos_ok[1])

        # ══════════════════════════════════════════════════════════════════
        # FIX DEFINITIVO:
        # 1) Esperar a que la pantalla de título VIEJA desaparezca (pantalla negra de reinicio)
        # 2) Esperar a que cargue la pantalla de título NUEVA
        # ══════════════════════════════════════════════════════════════════
        log.info("[⏳] Esperando a que el juego cierre la sesión anterior...")
        inicio_cierre = time.monotonic()
        while time.monotonic() - inicio_cierre < 8.0:
            screen = self.device.screenshot()
            # Cuando deja de verse tanto el título viejo como el botón de la nube, ya está reiniciando
            if not self.vision.find_template(screen, "templates/pantalla_titulo.png", threshold=0.75, zona="MITAD_INFERIOR") and \
               not self.vision.find_template(screen, "templates/btn_nube.png", threshold=0.75, zona="ESQUINA_INF_IZQ"):
                log.info("[✓] Reinicio en curso detectado (pantalla de carga).")
                break
            time.sleep(0.3)
        else:
            # Fallback de seguridad si por lag aún no se cerraba
            time.sleep(4.0)

        # Pausa base mientras arranca el motor de Unity de Evertale
        time.sleep(5.0)

        log.info("[⏳] Esperando nueva pantalla de título...")
        pos_titulo = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/pantalla_titulo.png",
            timeout=30,
            threshold=0.8,
            interval=0.4,
            zona="MITAD_INFERIOR"
        )
        if pos_titulo:
            log.info("[✓] Nueva pantalla de título lista.")
            return True

        log.error("❌ Timeout esperando nueva pantalla de título tras cambio de cuenta.")
        return False