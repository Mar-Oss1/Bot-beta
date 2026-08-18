# tasks/change_server.py

import time
import os
from core.logger import get_logger

log = get_logger("change_server")


class ChangeServer:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def execute(self, server_label_template):
        log.info("\n[→] Iniciando cambio/verificación de servidor: %s", server_label_template)

        # 1. Buscar botón de Servidor en la pantalla de título
        pos_btn_server = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_server_title.png",
            timeout=10,
            threshold=0.7,
            interval=0.5
        )
        if not pos_btn_server:
            log.error("❌ No encontré el botón de Servidor.")
            return False

        log.info("[>] Abriendo menú de servidores...")
        self.device.tap(pos_btn_server[0], pos_btn_server[1])

        # 2. Esperar a que cargue el menú y aparezca la etiqueta del servidor
        log.info("[⏳] Esperando menú de servidores...")
        pos_label = self.vision.wait_for_template(
            self.device.screenshot,
            server_label_template,
            timeout=8,
            threshold=0.8,
            interval=0.4
        )
        if not pos_label:
            log.error("❌ No encontré la etiqueta del servidor destino.")
            self._salir_menu_servidores()
            return False

        log.info("[>] Servidor encontrado. Tocando...")
        self.device.tap(pos_label[0], pos_label[1])

        # 3. Primer OK de confirmación (aparece tanto si hay cambio como si no)
        pos_ok = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_ok_restore.png",
            timeout=4,
            threshold=0.75,
            interval=0.3
        )
        if pos_ok:
            log.info("[>] 'OK' de confirmación encontrado. Presionando...")
            self.device.tap(pos_ok[0], pos_ok[1])
            # Pausa para que un cambio REAL alcance a iniciar el reinicio
            time.sleep(2)
        else:
            log.info("[i] No apareció diálogo de confirmación.")

        # 4. Bucle final robusto: llegar a la pantalla de título sí o sí
        return self._llegar_a_titulo(timeout=45)

    # ═══════════════════════════════════════════════════════════
    # BUCLE FINAL: confirma / sale del menú / espera el título
    # ═══════════════════════════════════════════════════════════
    def _llegar_a_titulo(self, timeout=20) -> bool:
        """
        Cubre los 3 escenarios posibles:
        a) Cambio REAL de servidor → (2º OK) → reinicio → título
        b) YA en el servidor (con diálogo) → OK te devuelve al menú
           → back visible → lo presionamos → título   ← TU CASO DEL LOG
        c) YA en el servidor (sin diálogo) → back directo → título
        """
        log.info("[⏳] Esperando pantalla de título...")
        inicio = time.time()
        oks = 0
        backs = 0

        while time.time() - inicio < timeout:
            screen = self.device.screenshot()

            # ✅ ÉXITO: ya estamos en la pantalla de título
            if self.vision.find_template(screen, "templates/pantalla_titulo.png", threshold=0.8):
                log.info("[✓] Pantalla de título detectada. Servidor listo.")
                return True

            # 🟠 Quedó un diálogo de confirmación pendiente → OK
            pos_ok = self.vision.find_template(
                screen, "templates/btn_ok_restore.png", threshold=0.75
            )
            if pos_ok:
                oks += 1
                log.info("[>] 'OK' #%d encontrado. Presionando...", oks)
                self.device.tap(pos_ok[0], pos_ok[1])
                time.sleep(1)
                continue

            # 🔙 Atrapados en el menú de servidores → back (tu idea)
            pos_back = self.vision.find_template(
                screen, "templates/btn_back_login.png", threshold=0.8
            )
            if pos_back:
                backs += 1
                log.info("[←] Aún en menú de servidores. Back #%d...", backs)
                self.device.tap(pos_back[0], pos_back[1])
                time.sleep(1.5)
                continue

            # Pantalla de carga u otra: esperar
            time.sleep(1)

        log.warning("[!] Timeout (%ds) esperando pantalla de título. Continuando...", timeout)
        return True

    def _salir_menu_servidores(self):
        """Cierra el menú de servidores si algo salió mal."""
        screen = self.device.screenshot()
        pos_back = self.vision.find_template(
            screen, "templates/btn_back_login.png", threshold=0.75
        )
        if pos_back:
            self.device.tap(pos_back[0], pos_back[1])
        else:
            self.device.d.press("back")
        time.sleep(1)


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.device import Device
    from core.vision import Vision

    print("=== PRUEBA DE CAMBIO DE SERVIDOR ===")
    dev = Device()
    vis = Vision()
    if dev.connect():
        print("[✓] Dispositivo conectado.")
        cambiador = ChangeServer(dev, vis)
        cambiador.execute("templates/label_sa-9.png")
    else:
        print("❌ Error al conectar.")