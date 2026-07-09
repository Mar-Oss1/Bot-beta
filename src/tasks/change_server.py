import time
import os
from core.logger import get_logger

log = get_logger("change_server")


class ChangeServer:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def execute(self, server_label_template):
        log.info("\n[] Iniciando cambio/verificación de servidor buscando: %s", server_label_template)

        # 1. Tocar el botón de Servidor en la pantalla de inicio
        screen = self.device.screenshot()
        pos_btn_server = self.vision.find_template(screen, "templates/btn_server_title.png", threshold=0.7)
        if not pos_btn_server:
            log.error("❌ No encontré el botón de Servidor en la pantalla de título.")
            return False

        log.info(" [>] Abriendo menú de servidores...")
        self.device.tap(pos_btn_server[0], pos_btn_server[1])

        # ✅ CORRECCIÓN: Esperar a que el menú cargue antes de buscar la etiqueta
        time.sleep(1.5)

        # ✅ OPTIMIZACIÓN: Esperar a que aparezca la etiqueta del servidor
        log.info(" [⏳] Esperando que cargue el menú de servidores...")
        pos_label = self.vision.wait_for_template(
            self.device.screenshot,
            server_label_template,
            timeout=5,
            threshold=0.8
        )

        if not pos_label:
            log.error("❌ No encontré la etiqueta del servidor destino.")
            return False

        log.info(" [>] Servidor encontrado. Tocando directamente...")
        self.device.tap(pos_label[0], pos_label[1])

        # ✅ Esperar a que aparezca la confirmación
        time.sleep(1)

        # ✅ OPTIMIZACIÓN: Esperar a que aparezca el OK
        log.info(" [>] Buscando confirmación de servidor...")
        pos_ok_1 = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_ok_restore.png",
            timeout=5,
            threshold=0.75
        )

        if pos_ok_1:
            log.info("  [>] Primer 'OK' encontrado. Presionando...")
            self.device.tap(pos_ok_1[0], pos_ok_1[1])

            # ✅ Esperar antes de buscar el segundo OK
            time.sleep(1)

            # ✅ OPTIMIZACIÓN: Esperar segundo OK o back
            log.info(" [>] Buscando segunda confirmación...")
            pos_ok_2 = self.vision.wait_for_template(
                self.device.screenshot,
                "templates/btn_ok_restore.png",
                timeout=3,
                threshold=0.75
            )

            if pos_ok_2:
                log.info("  [>] Segundo 'OK' encontrado. Presionando...")
                self.device.tap(pos_ok_2[0], pos_ok_2[1])
                log.info(" [✅] ¡Cambio de servidor exitoso! Esperando carga...")
                # ✅ SE MANTIENE: 12 segundos para que el juego descargue datos del servidor
                time.sleep(12)
                return True
            else:
                log.info(" [i] Solo apareció un 'OK'. Ya estamos en este servidor.")
                screen = self.device.screenshot()
                pos_back_login = self.vision.find_template(screen, "templates/btn_back_login.png", threshold=0.8)
                if pos_back_login:
                    log.info(" [✅] Cerrando menú de servidores con botón 'Back' rojo...")
                    self.device.tap(pos_back_login[0], pos_back_login[1])
                    time.sleep(2)
                else:
                    log.info(" [✅] El menú se cerró solo o no encontré el back rojo.")
                return True
        else:
            log.info(" [i] No apareció ninguna advertencia. Ya estamos en el servidor correcto.")
            screen = self.device.screenshot()
            pos_back_login = self.vision.find_template(screen, "templates/btn_back_login.png", threshold=0.8)
            if pos_back_login:
                log.info(" [✅] Cerrando menú de servidores con botón 'Back' rojo...")
                self.device.tap(pos_back_login[0], pos_back_login[1])
                time.sleep(2)
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
        plantilla_prueba = "templates/label_sa-6.png"
        cambiador.execute(plantilla_prueba)
    else:
        print(" ❌ Error al conectar con el dispositivo ADB.")