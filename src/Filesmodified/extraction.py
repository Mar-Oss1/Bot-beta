import subprocess
import os

# Directorios corregidos
PACKAGE_NAME = "com.zigzagame.evertale"
SOURCE_DIR = f"/storage/emulated/0/Android/data/{PACKAGE_NAME}/files"
BACKUP_DIR = "./archivos_modificados"
TEMP_SDCARD_DIR = "/sdcard"

ARCHIVOS_A_EXTRAER = [
    "Ability.json",
    "Equipment.json",
    "Monster.json"
]


def extraer_archivos():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"Carpeta creada: {BACKUP_DIR}\n")

    print("Iniciando extracción de archivos del juego...\n")

    for archivo in ARCHIVOS_A_EXTRAER:
        ruta_origen = f"{SOURCE_DIR}/{archivo}"
        # Le añadimos un sufijo temporal para evitar cualquier conflicto de nombres
        ruta_temp = f"{TEMP_SDCARD_DIR}/{archivo}_temp.json"
        ruta_destino = os.path.join(BACKUP_DIR, archivo)

        try:
            print(f"Procesando: {archivo}...")

            # 1. Usar root para sacar el archivo de Android/data y ponerlo en la raíz pública
            comando_cp = f"su -c 'cp {ruta_origen} {ruta_temp}'"
            subprocess.run(["adb", "shell", comando_cp], check=True)

            # 2. Extraerlo a tu PC
            subprocess.run(["adb", "pull", ruta_temp, ruta_destino], check=True, capture_output=True)

            # 3. Borrar el archivo temporal
            subprocess.run(["adb", "shell", f"rm {ruta_temp}"], check=True)

            print(f"  -> Guardado exitosamente en: {ruta_destino}")

        except subprocess.CalledProcessError as e:
            print(f"  [X] Error al procesar {archivo}. Detalle: {e}")


if __name__ == "__main__":
    extraer_archivos()