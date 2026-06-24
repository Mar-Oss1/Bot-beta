import uiautomator2 as u2
import subprocess
import time
import random
from PIL import Image

class Device:
    def __init__(self, serial=None):
        # El 'serial' ahora puede ser un ID de USB o una IP (ej: "192.168.1.15:5555")
        self.serial = serial
        self.d = None

    def connect(self):
        """Conecta al dispositivo Android (Vía USB o Inalámbrico)"""
        # Si no le pasamos IP al iniciar, busca lo que esté conectado
        if not self.serial:
            self.serial = self.get_serial()

        # Si después de buscar sigue sin haber nada, lanzamos alerta
        if not self.serial:
            print(" ❌ No se detectó dispositivo. ¿Estás conectado al Wi-Fi e hiciste 'adb connect IP'?")
            return False

        try:
            print(f" [🔌] Intentando conectar a: {self.serial}...")
            self.d = u2.connect(self.serial)
            info = self.d.device_info
            # uiautomator2 a veces devuelve 'marketName' o 'model'
            nombre_tel = info.get('marketName', info.get('model', 'Desconocido'))
            print(f" [✅] Conectado: {nombre_tel} | Resolución: {self.d.window_size()}")
            return True
        except Exception as e:
            print(f" ❌ Error conectando: {e}")
            return False

    def screenshot(self, save_path=None):
        """Toma screenshot y lo retorna como imagen"""
        screen = self.d.screenshot()
        if save_path:
            screen.save(save_path)
        return screen

    def tap(self, x, y, variance=10):
        """Tap con variación aleatoria para no ser tan predecible"""
        rx = x + random.randint(-variance, variance)
        ry = y + random.randint(-variance, variance)
        self.d.click(rx, ry)
        time.sleep(random.uniform(0.3, 0.8))

    def swipe(self, x1, y1, x2, y2, duration=0.5):
        """Swipe entre dos puntos"""
        self.d.swipe(x1, y1, x2, y2, duration)
        time.sleep(random.uniform(0.3, 0.6))

    def is_app_running(self, package="com.zigzagame.evertale"):
        """Verifica si Evertale está abierto"""
        current = self.d.app_current()
        return current['package'] == package

    def open_app(self, package="com.zigzagame.evertale"):
        """Abre Evertale si no está abierto"""
        if not self.is_app_running(package):
            print(" [📱] Abriendo Evertale...")
            self.d.app_start(package)
            time.sleep(5)

    def get_serial(self):
        """Obtiene el serial del dispositivo conectado por adb"""
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n")[1:]
        devices = [l.split("\t")[0] for l in lines if "device" in l]
        return devices[0] if devices else None