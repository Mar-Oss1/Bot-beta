import time
from core.logger import get_logger

log = get_logger("change_account")


class ChangeAccount:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def execute(self, serial_cuenta):
        log.info("\n[🔄] Iniciando cambio a cuenta: %s", serial_cuenta)
        max_intentos = 15

        # Esperar pantalla de inicio con nube (polling optimizado)
        pos_nube = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_nube.png",
            timeout=30,
            threshold=0.75,
            interval=0.8
        )
        if not pos_nube:
            log.error("❌ No se detectó la pantalla de inicio con nube.")
            self.device.screenshot_to_file("screenshots/error_cambio_cuenta.png")
            return False

        log.info("[>] Ícono de nube detectado. Abriendo menú de restauración...")
        self.device.tap(pos_nube[0], pos_nube[1])

        # Esperar menú de restauración
        pos_input = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/input_restore.png",
            timeout=10,
            threshold=0.75,
            interval=0.4
        )
        if not pos_input:
            log.warning("[!] No apareció el menú de restauración.")
            return False

        # Buscar botón Use Code
        pos_use = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_use_code.png",
            timeout=5,
            threshold=0.75,
            interval=0.3
        )
        if not pos_use:
            log.warning("[!] No se encontró el botón 'Use Code'.")
            return False

        log.info("[>] Menú detectado. Activando teclado...")
        self.device.tap(pos_input[0], pos_input[1])
        time.sleep(0.8)

        log.info("[>] Inyectando código: %s ...", serial_cuenta)
        self.device.d.send_keys(serial_cuenta)
        time.sleep(1)

        log.info("[>] Confirmando (Use Code)...")
        self.device.tap(pos_use[0], pos_use[1])
        time.sleep(2.5)

        # Confirmación 1: Restore Anyway (opcional)
        pos_restore_anyway = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_restore_anyway.png",
            timeout=3,
            threshold=0.75,
            interval=0.3
        )
        if pos_restore_anyway:
            log.warning("[!] Pop-up de advertencia detectado. Dando 'Restore Anyway'...")
            self.device.tap(pos_restore_anyway[0], pos_restore_anyway[1])
            time.sleep(2.5)
        else:
            log.info("[i] No salió 'Restore Anyway'.")

        # Confirmación 2: OK de éxito
        pos_ok = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_ok_restore.png",
            timeout=3,
            threshold=0.75,
            interval=0.3
        )
        if pos_ok:
            log.warning("[!] Pop-up de éxito detectado. Dando 'OK'...")
            self.device.tap(pos_ok[0], pos_ok[1])
            time.sleep(1)
        else:
            log.info("[i] No salió botón 'OK'.")

        log.info("[✓] Secuencia enviada. Esperando reinicio (17s)...")
        time.sleep(17)
        return True