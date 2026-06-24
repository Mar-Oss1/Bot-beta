import json
import os
import subprocess

# Configuración
PACKAGE_NAME = "com.zigzagame.evertale"
BACKUP_DIR = "./archivos_modificados"
TARGET_DIR = f"/storage/emulated/0/Android/data/{PACKAGE_NAME}/files"
TEMP_SDCARD_DIR = "/sdcard"

ARCHIVOS_A_PROCESAR = [
    "Ability.json",
    "Equipment.json",
    "Monster.json"
]


def cerrar_juego():
    print("\n[1] Asegurando que el juego esté cerrado...")
    try:
        subprocess.run(["adb", "shell", f"am force-stop {PACKAGE_NAME}"], check=True)
        print(" [+] Evertale cerrado exitosamente (o ya estaba cerrado).")
    except subprocess.CalledProcessError as e:
        print(f" [X] Error al intentar cerrar el juego: {e}")


def patch_evertale_files():
    print("\n[2] Parcheando archivos JSON locales...")

    # 1. Modificar Ability.json
    ability_path = os.path.join(BACKUP_DIR, "Ability.json")
    if os.path.exists(ability_path):
        with open(ability_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for ability in data.get("Ability", []):
            if ability.get("name") == "SakuraSweepAKojiroRegular":
                ability["tuCost"] = 0
                ability["spiritCost"] = 0
                ability["useLimit"] = 0
                ability["blockTargetManipulation"] = 0
                ability["showConfirmation"] = 0
                print(" [+] Habilidad 'SakuraSweepAKojiroRegular' modificada a coste 0.")
                break

        with open(ability_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    # 2. Modificar Monster.json
    monster_path = os.path.join(BACKUP_DIR, "Monster.json")
    if os.path.exists(monster_path):
        with open(monster_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for monster in data.get("Monster", []):
            if monster.get("name") == "Hero01":
                monster["activeSkills"] = {"0": "SakuraSweepAKojiroRegular"}

                # Agregando las pasivas solicitadas: anti-stun, anti-burn y contraataque
                monster["passives"] = {
                    "0": "RegenerationOnMyTurnGetTurnSkinA",
                    "1": "PoisonTrapEnemies"
                }
                print(" [+] Monstruo 'Hero01' modificado (Ataque a 0 y nuevas pasivas inyectadas).")
                break

        with open(monster_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    # 3. Modificar Equipment.json
    equip_path = os.path.join(BACKUP_DIR, "Equipment.json")
    if os.path.exists(equip_path):
        with open(equip_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        equipos_a_chetar = [
            "Armor01", "Pickaxe01", "KukuriKnife01", "CobraRod01",
            "HawkCoin01", "Bracelet01", "Gauntlet01", "AlchemyFlask01", "GreenRing01"
        ]

        for equip in data.get("Equipment", []):
            if equip.get("name") in equipos_a_chetar:
                equip["flatAttack"] = 999999
                equip["flatMaxHp"] = 999999

        print(" [+] Equipo inicial bufado a 999999 de ATK/HP.")
        with open(equip_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)


def inyectar_archivos():
    print("\n[3] Inyectando archivos modificados al teléfono...")

    for archivo in ARCHIVOS_A_PROCESAR:
        ruta_local = os.path.join(BACKUP_DIR, archivo)
        ruta_temp = f"{TEMP_SDCARD_DIR}/{archivo}_inyect.json"
        ruta_final = f"{TARGET_DIR}/{archivo}"

        if not os.path.exists(ruta_local):
            print(f" [-] Omitiendo {archivo} (No existe en la carpeta local).")
            continue

        try:
            print(f" Subiendo: {archivo}...")
            subprocess.run(["adb", "push", ruta_local, ruta_temp], check=True, capture_output=True)
            comando_cp = f"su -c 'cp {ruta_temp} {ruta_final}'"
            subprocess.run(["adb", "shell", comando_cp], check=True)
            subprocess.run(["adb", "shell", f"rm {ruta_temp}"], check=True)
            print(f"  -> ¡{archivo} reemplazado con éxito!")

        except subprocess.CalledProcessError as e:
            print(f" [X] Error al inyectar {archivo}. Detalle: {e}")


def abrir_juego():
    print("\n[4] Iniciando Evertale...")
    try:
        # Usamos monkey para lanzar la aplicación de forma segura
        subprocess.run(["adb", "shell", f"monkey -p {PACKAGE_NAME} -c android.intent.category.LAUNCHER 1"], check=True,
                       capture_output=True)
        print(" [+] ¡Juego abierto y listo para farmear!")
    except subprocess.CalledProcessError as e:
        print(f" [X] Error al intentar abrir el juego: {e}")


if __name__ == "__main__":
    print("=== SCRIPT DE MODIFICACIÓN E INYECCIÓN ===")
    cerrar_juego()
    patch_evertale_files()
    inyectar_archivos()
    abrir_juego()
    print("\n¡Proceso 100% automatizado completado!")