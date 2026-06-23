import sys
import os
import time

# Asegurar que Python reconozca las carpetas del proyecto
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from core.device import Device


def main():
    print("=== 📸 HERRAMIENTA DE CAPTURA PARA PLANTILLAS ===")
    dev = Device()

    print("[🔌] Conectando al dispositivo...")
    if not dev.connect():
        print("❌ No se pudo conectar al teléfono.")
        return

    # Creamos una carpeta especial para estas capturas crudas
    debug_dir = os.path.join(project_root, "screenshots", "debug_templates")
    os.makedirs(debug_dir, exist_ok=True)

    print("\n⏳ Tienes 1 segundos para acomodar la pantalla del juego...")
    for i in range(1, 0, -1):
        print(f" {i}...")
        time.sleep(1)

    # Generamos un nombre único con la hora actual para no sobreescribir
    nombre_archivo = f"captura_UI_{int(time.time())}.png"
    ruta_guardado = os.path.join(debug_dir, nombre_archivo)

    # Tomar y guardar la captura
    screen = dev.screenshot()
    screen.save(ruta_guardado)

    print(f"\n✅ ¡Captura guardada con éxito!")
    print(f"📂 Revisa la carpeta: screenshots/debug_templates/{nombre_archivo}")
    print("🎨 Ahora abre esa imagen en Paint, haz tus recortes y guárdalos en 'templates/'.")


if __name__ == "__main__":
    main()