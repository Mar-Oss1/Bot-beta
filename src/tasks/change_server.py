import time
import os

class ChangeServer:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def execute(self, server_label_template):
        """
        Ejecuta la secuencia para cambiar de servidor desde la pantalla de título.
        :param server_label_template: Ruta a la imagen de la etiqueta del server (ej. "templates/label_sa6.png")
        """
        print(f"\n[🌐] Iniciando cambio de servidor buscando: {server_label_template}")

        # 1. Tocar el botón de Servidor en la pantalla de inicio
        screen = self.device.screenshot()
        pos_btn_server = self.vision.find_template(screen, "templates/btn_server_title.png", threshold=0.7)
        if not pos_btn_server:
            print(" ❌ No encontré el botón de Servidor en la pantalla de título.")
            return False

        print(" [>] Abriendo menú de servidores...")
        self.device.tap(pos_btn_server[0], pos_btn_server[1])
        time.sleep(2)

        # 2. Ir a la pestaña 'Recent'
        screen = self.device.screenshot()
        pos_recent = self.vision.find_template(screen, "templates/tab_recent.png", threshold=0.75)
        if pos_recent:
            print(" [>] Cambiando a la pestaña 'Recent'...")
            self.device.tap(pos_recent[0], pos_recent[1])
            time.sleep(1.5)
        else:
            print(" ⚠️ No vi la pestaña 'Recent', asumiendo que ya estamos ahí...")

        # 3. Buscar la etiqueta del servidor destino
        screen = self.device.screenshot()
        pos_label = self.vision.find_template(screen, server_label_template, threshold=0.8)

        if not pos_label:
            print(f" ❌ No encontré la etiqueta del servidor en la lista de recientes.")
            return False

        # 4. TOCAR DIRECTAMENTE: Clic justo sobre la etiqueta encontrada
        print(" [>] Servidor encontrado. Tocando directamente...")
        self.device.tap(pos_label[0], pos_label[1])
        time.sleep(2)

        # 5. Confirmar el cambio con el botón OK (¡Doble confirmación!)
        print(" [>] Buscando primera confirmación de servidor...")
        screen = self.device.screenshot()
        pos_ok_1 = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.75)

        if pos_ok_1:
            print("  [>] Primer 'OK' encontrado. Presionando...")
            self.device.tap(pos_ok_1[0], pos_ok_1[1])
            time.sleep(2)  # Esperamos a que la segunda ventana de advertencia termine de animarse

            print(" [>] Buscando segunda confirmación...")
            screen = self.device.screenshot()
            pos_ok_2 = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.75)

            if pos_ok_2:
                print("  [>] Segundo 'OK' encontrado. Presionando...")
                self.device.tap(pos_ok_2[0], pos_ok_2[1])
                print(" [✅] ¡Cambio de servidor exitoso! Esperando a que el juego vuelva a la pantalla de título...")
                time.sleep(12)  # Tiempo vital para que el juego haga el "Return to Title"
                return True
            else:
                print(" ❌ Encontré el primer OK, pero el segundo no apareció. Posible atasco.")
                return False
        else:
            print(" ❌ No apareció la primera ventana de confirmación.")
            return False


if __name__ == "__main__":
    import sys

    # Ajustamos la ruta para que encuentre la carpeta 'core'
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from core.device import Device
    from core.vision import Vision

    print("=== PRUEBA DE CAMBIO DE SERVIDOR ===")
    dev = Device()
    vis = Vision()

    if dev.connect():
        print(" [🔌] Dispositivo conectado.")
        cambiador = ChangeServer(dev, vis)

        # OJO: Cambia el nombre de la plantilla por el que quieras probar (label_sa3.png o label_sa6.png)
        plantilla_prueba = "templates/label_sa6.png"

        cambiador.execute(plantilla_prueba)
    else:
        print(" ❌ Error al conectar con el dispositivo ADB.")