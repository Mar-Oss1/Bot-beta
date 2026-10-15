# tasks/change_server.py

import time
import os
from core.logger import get_logger

log = get_logger("change_server")


class ChangeServer:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def execute(self, server_label_template: str) -> bool:
        log.info("\n[→] Iniciando cambio/verificación de servidor: %s", server_label_template)

        pos_btn_server = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_server_title.png",
            timeout=10,
            threshold=0.7,
            interval=0.25,
            zona="MITAD_INFERIOR"
        )
        if not pos_btn_server:
            log.error("❌ No encontré el botón de Servidor.")
            return False

        self.device.tap(pos_btn_server[0], pos_btn_server[1])

        pos_label = self.vision.wait_for_template(
            self.device.screenshot,
            server_label_template,
            timeout=8,
            threshold=0.8,
            interval=0.2,
            zona="COMPLETA"
        )
        if not pos_label:
            log.error("❌ No encontré la etiqueta del servidor destino.")
            self._salir_menu_servidores()
            return False

        self.device.tap(pos_label[0], pos_label[1])

        pos_ok = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_ok_restore.png",
            timeout=3.5,
            threshold=0.75,
            interval=0.2,
            zona="CENTRO"
        )
        if pos_ok:
            self.device.tap(pos_ok[0], pos_ok[1])
            time.sleep(1.0)

        return self._llegar_a_titulo(timeout=35)

    def _llegar_a_titulo(self, timeout: float = 20) -> bool:
        log.info("[⏳] Esperando pantalla de título...")
        inicio = time.monotonic()

        while time.monotonic() - inicio < timeout:
            screen_gray = self.vision.to_gray(self.device.screenshot())

            # ✅ ÉXITO: START GAME visible en MITAD_INFERIOR
            if self.vision.find_template(
                screen_gray, "templates/pantalla_titulo.png", threshold=0.8, zona="MITAD_INFERIOR"
            ):
                log.info("[✓] Pantalla de título detectada. Servidor listo.")
                return True

            pos_ok = self.vision.find_template(
                screen_gray, "templates/btn_ok_restore.png", threshold=0.75, zona="CENTRO"
            )
            if pos_ok:
                self.device.tap(pos_ok[0], pos_ok[1])
                time.sleep(0.5)
                continue

            pos_back = self.vision.find_template(
                screen_gray, "templates/btn_back_login.png", threshold=0.8, zona="MITAD_INFERIOR"
            )
            if pos_back:
                self.device.tap(pos_back[0], pos_back[1])
                time.sleep(0.8)
                continue

            time.sleep(0.4)

        log.warning("[!] Timeout (%ds) esperando pantalla de título. Continuando...", timeout)
        return True

    def _salir_menu_servidores(self):
        screen = self.device.screenshot()
        pos_back = self.vision.find_template(
            screen, "templates/btn_back_login.png", threshold=0.75, zona="MITAD_INFERIOR"
        )
        if pos_back:
            self.device.tap(pos_back[0], pos_back[1])
        else:
            self.device.d.press("back")
        time.sleep(0.6)