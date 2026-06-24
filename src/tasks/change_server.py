import time
import os

class ChangeServer:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def execute(self, server_label_template):
        print(f"\n[🌐] Iniciando cambio/verificación de servidor buscando: {server_label_template}")

        # 1. Tocar el botón de Servidor en la pantalla de inicio
        screen = self.device.screenshot()
        pos_btn_server = self.vision.find_template(screen, "templates/btn_server_title.png", threshold=0.7)
        if not pos_btn_server:
            print(" ❌ No encontré el botón de Servidor en la pantalla de título.")
            return False

        print(" [>] Abriendo menú de servidores...")
        self.device.tap(pos_btn_server[0], pos_btn_server[1])
        time.sleep(2)

        # 2. Buscar la etiqueta del servidor destino directamente
        screen = self.device.screenshot()
        pos_label = self.vision.find_template(screen, server_label_template, threshold=0.8)

        if not pos_label:
            print(f" ❌ No encontré la etiqueta del servidor destino.")
            return False

        print(" [>] Servidor encontrado. Tocando directamente...")
        self.device.tap(pos_label[0], pos_label[1])
        time.sleep(2)

        # 3. Confirmar el cambio o detectar si YA estamos en el servidor
        print(" [>] Buscando confirmación de servidor...")
        screen = self.device.screenshot()
        pos_ok_1 = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.75)

        if pos_ok_1:
            print("  [>] Primer 'OK' encontrado. Presionando...")
            self.device.tap(pos_ok_1[0], pos_ok_1[1])
            time.sleep(2)

            print(" [>] Buscando segunda confirmación...")
            screen = self.device.screenshot()
            pos_ok_2 = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.75)

            if pos_ok_2:
                print("  [>] Segundo 'OK' encontrado. Presionando...")
                self.device.tap(pos_ok_2[0], pos_ok_2[1])
                print(" [✅] ¡Cambio de servidor exitoso! Esperando carga...")
                time.sleep(12)
                return True
            else:
                print(" [i] Solo apareció un 'OK'. Ya estamos en este servidor.")
                screen = self.device.screenshot()
                # AQUÍ USAMOS TU NUEVO BOTÓN ROJO
                pos_back_login = self.vision.find_template(screen, "templates/btn_back_login.png", threshold=0.8)
                if pos_back_login:
                    print(" [✅] Cerrando menú de servidores con botón 'Back' rojo...")
                    self.device.tap(pos_back_login[0], pos_back_login[1])
                    time.sleep(3)
                else:
                    print(" [✅] El menú se cerró solo o no encontré el back rojo.")
                return True
        else:
            print(" [i] No apareció ninguna advertencia. Ya estamos en el servidor correcto.")
            screen = self.device.screenshot()
            pos_back_login = self.vision.find_template(screen, "templates/btn_back_login.png", threshold=0.8)
            if pos_back_login:
                print(" [✅] Cerrando menú de servidores con botón 'Back' rojo...")
                self.device.tap(pos_back_login[0], pos_back_login[1])
                time.sleep(3)
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
        print(" [🔌] Dispositivo conectado.")
        cambiador = ChangeServer(dev, vis)
        plantilla_prueba = "templates/label_sa-6.png"
        cambiador.execute(plantilla_prueba)
    else:
        print(" ❌ Error al conectar con el dispositivo ADB.")