import time
from core.logger import get_logger

log = get_logger("change_account")


class ChangeAccount:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def execute(self, serial_cuenta):
        log.info("\n[🔄] Iniciando cambio a la cuenta con código: %s", serial_cuenta)
        max_intentos = 15
        intentos = 0

        while intentos < max_intentos:
            screen = self.device.screenshot()

            # 1. Buscar la nube en la pantalla de inicio
            pos_nube = self.vision.find_template(screen, "templates/btn_nube.png", threshold=0.75)
            if pos_nube:
                log.info("[>] Ícono de nube detectado. Abriendo menú de restauración...")
                self.device.tap(pos_nube[0], pos_nube[1])

                # ✅ OPTIMIZACIÓN: Esperar a que aparezca el menú de restauración
                log.info("[] Esperando menú de restauración...")
                pos_input = self.vision.wait_for_template(
                    self.device.screenshot,
                    "templates/input_restore.png",
                    timeout=10,
                    threshold=0.75
                )

                if not pos_input:
                    log.warning("[!] No apareció el menú de restauración. Reintentando...")
                    time.sleep(2)
                    continue

                # 2. Buscar el botón verde "Use Code"
                screen = self.device.screenshot()
                pos_use = self.vision.find_template(screen, "templates/btn_use_code.png", threshold=0.75)

                if not pos_use:
                    log.warning("[!] No se encontró el botón 'Use Code'. Reintentando...")
                    time.sleep(2)
                    continue

                log.info("[>] Menú detectado. Activando teclado...")
                self.device.tap(pos_input[0], pos_input[1])
                time.sleep(1)

                log.info("[>] Inyectando código: %s ...", serial_cuenta)
                self.device.d.send_keys(serial_cuenta)
                time.sleep(1.5)

                log.info("[>] Código pegado. Confirmando (Use Code)...")
                self.device.tap(pos_use[0], pos_use[1])
                time.sleep(3)

                # --- Confirmación 1: Restore Anyway (Opcional) ---
                screen = self.device.screenshot()
                pos_restore_anyway = self.vision.find_template(
                    screen, "templates/btn_restore_anyway.png", threshold=0.75
                )
                if pos_restore_anyway:
                    log.warning("[!] Pop-up de advertencia detectado. Dando a 'Restore Anyway'...")
                    self.device.tap(pos_restore_anyway[0], pos_restore_anyway[1])
                    time.sleep(3)
                else:
                    log.info("[i] No salió 'Restore Anyway'.")

                # --- Confirmación 2: Botón OK de éxito ---
                screen = self.device.screenshot()
                pos_ok = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.75)
                if pos_ok:
                    log.warning("[!] Pop-up de éxito detectado. Dando a 'OK'...")
                    self.device.tap(pos_ok[0], pos_ok[1])
                else:
                    log.info("[i] No salió botón 'OK'.")

                log.info("[✓] Secuencia de cambio enviada. Esperando reinicio de Evertale (20 seg)...")
                time.sleep(17)
                return True
            else:
                log.info(" Esperando la pantalla de inicio con la nube...")
                time.sleep(2)
                intentos += 1

        log.error("❌ Atasco en el cambio de cuenta. Guardando evidencia...")
        self.device.screenshot("screenshots/error_cambio_cuenta.png")
        return False
