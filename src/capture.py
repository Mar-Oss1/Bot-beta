import sys
import os
import time
import cv2

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from core.config import PROJECT_ROOT
from core.device import Device


def main():
    print("=== 📸 HERRAMIENTA DE CAPTURA PARA PLANTILLAS ===")
    dev = Device()

    print("[🔌] Conectando al dispositivo...")
    if not dev.connect():
        print("❌ No se pudo conectar al teléfono.")
        return

    debug_dir = os.path.join(PROJECT_ROOT, "screenshots", "debug_templates")
    os.makedirs(debug_dir, exist_ok=True)

    print("\n⏳ Tienes 1 segundos para acomodar la pantalla del juego...")
    time.sleep(1)

    nombre_archivo = f"captura_UI_{int(time.time())}.png"
    ruta_guardado = os.path.join(debug_dir, nombre_archivo)

    # Tomar y guardar la captura con OpenCV
    screen = dev.screenshot()
    cv2.imwrite(ruta_guardado, screen)

    print(f"\n✅ ¡Captura guardada con éxito! -> {ruta_guardado}")


if __name__ == "__main__":
    main()