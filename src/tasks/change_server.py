import time
import os
from core.logger import get_logger

log = get_logger("change_server")


class ChangeServer:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def execute(self, server_label_template):
        log.info("\n[] Iniciando cambio/verificación de servidor: %s", server_label_template)

        # 1. Buscar botón de Servidor
        pos_btn_server = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_server_title.png",
            timeout=8,
            threshold=0.7,
            interval=0.5
        )
        if not pos_btn_server:
            log.error("❌ No encontré el botón de Servidor.")
            return False

        log.info(" [>] Abriendo menú de servidores...")
        self.device.tap(pos_btn_server[0], pos_btn_server[1])

        # 2. Esperar a que cargue el menú y aparezca la etiqueta del servidor
        log.info(" [⏳] Esperando menú de servidores...")
        pos_label = self.vision.wait_for_template(
            self.device.screenshot,
            server_label_template,
            timeout=6,
            threshold=0.8,
            interval=0.4
        )

        if not pos_label:
            log.error("❌ No encontré la etiqueta del servidor destino.")
            return False

        log.info(" [>] Servidor encontrado. Tocando...")
        self.device.tap(pos_label[0], pos_label[1])
        time.sleep(1)

        # 3. Esperar confirmación (OK o back)
        log.info(" [>] Buscando confirmación...")
        inicio = time.time()
        while time.time() - inicio < 6:
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, [
                "templates/btn_ok_restore.png",
                "templates/btn_back_login.png"
            ], threshold=0.75)

            if result:
                template, x, y = result
                if "ok" in template.lower():
                    log.info("  [>] Primer 'OK' encontrado. Presionando...")
                    self.device.tap(x, y)
                    time.sleep(1)

                    # Segundo OK
                    log.info(" [>] Buscando segunda confirmación...")
                    pos_ok2 = self.vision.wait_for_template(
                        self.device.screenshot,
                        "templates/btn_ok_restore.png",
                        timeout=3, threshold=0.75, interval=0.3
                    )
                    if pos_ok2:
                        log.info("  [>] Segundo 'OK' encontrado. Presionando...")
                        self.device.tap(pos_ok2[0], pos_ok2[1])
                        log.info(" [✅] ¡Cambio de servidor exitoso! Esperando carga...")
                        time.sleep(12)
                        return True
                    else:
                        log.info(" [i] Solo apareció un 'OK'. Ya estamos en este servidor.")
                        return True
                else:
                    # Es btn_back_login → ya estamos en el servidor
                    log.info(" [✅] Menú de servidores abierto con back. Ya estamos en el servidor correcto.")
                    self.device.tap(x, y)
                    time.sleep(1.5)
                    return True

            time.sleep(0.5)

        log.info(" [i] No apareció advertencia. Probablemente ya estamos en el servidor.")
        screen = self.device.screenshot()
        pos_back = self.vision.find_template(screen, "templates/btn_back_login.png", threshold=0.8)
        if pos_back:
            self.device.tap(pos_back[0], pos_back[1])
            time.sleep(1.5)
        return True


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.device import Device
    from core.vision import Vision

    print("=== PRUEBA DE CAMBIO DE SERVIDOR ===")
    dev = Device()
    vis = Vision()
    if dev.connect():
        print(" [] Dispositivo conectado.")
        cambiador = ChangeServer(dev, vis)
        cambiador.execute("templates/label_sa-6.png")
    else:
        print(" ❌ Error al conectar.")