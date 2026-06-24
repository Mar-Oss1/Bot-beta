import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import Database
from core.device import Device
from core.vision import Vision
from tasks.startup import Startup
from tasks.daily_missions import DailyMissions
from tasks.change_account import ChangeAccount
from tasks.change_server import ChangeServer
from tasks.event_farm import EventFarm

def ejecutar_flujo_completo(db, dev, vis):
    """Ejecuta la rutina automática para todas las cuentas pendientes."""
    print("\n=== INICIANDO MODO AUTOMÁTICO ===")
    db.print_status()

    cuentas_pendientes = db.get_pending_accounts()
    if not cuentas_pendientes:
        print("\n ✅ Todas las cuentas han terminado sus tareas hoy. ¡A descansar!")
        return

    print("\n[🧹] Limpiando estado inicial...")
    dev.d.app_stop("com.zigzagame.evertale")

    for cuenta in cuentas_pendientes:
        print(f"\n" + "=" * 45)
        print(f" 🚀 PROCESANDO CUENTA: {cuenta.name} (Prioridad {cuenta.priority})")
        print("=" * 45)

        max_reintentos = 3
        exito_cambio = False

        # --- A y B: Reintentos para Abrir y Cambiar Cuenta ---
        for intento in range(max_reintentos):
            print(f" [🔌] Arrancando Evertale (Intento {intento + 1}/{max_reintentos})...")
            dev.open_app()
            time.sleep(14)

            if cuenta.serial:
                cambiador = ChangeAccount(dev, vis)
                exito_cambio = cambiador.execute(cuenta.serial)

                if exito_cambio:
                    print(" [✅] Inyección exitosa. Esperando pantalla de título...")
                    time.sleep(12)
                    break
                else:
                    print(f" [⚠️] Falló el cambio. Limpiando y reiniciando...")
                    dev.d.app_stop("com.zigzagame.evertale")
                    time.sleep(3)
            else:
                print(" [i] La cuenta no tiene serial configurado. Entrando directo...")
                exito_cambio = True
                break

        if not exito_cambio:
            continue

        # --- BUCLE DE SERVIDORES DINÁMICO ---
        servidores = getattr(cuenta, "servers", [])
        if not servidores:
            servidores = [{"server_id": "DEFAULT"}]

        for index, servidor in enumerate(servidores):
            server_id = servidor.get("server_id", "DEFAULT")

            if index > 0:
                print(f"\n [🔌] Reabriendo juego para procesar el servidor {server_id}...")
                dev.open_app()
                time.sleep(14)

            if server_id != "DEFAULT":
                cambiador_serv = ChangeServer(dev, vis)
                if not cambiador_serv.execute(f"templates/label_{server_id.lower()}.png"):
                    dev.d.app_stop("com.zigzagame.evertale")
                    continue

            # --- PASO C: Rompehielos ---
            arranque = Startup(dev, vis)
            if not arranque.execute():
                dev.d.app_stop("com.zigzagame.evertale")
                continue

            # --- PASO D: Misiones Diarias ---
            DailyMissions(dev, vis).execute()

            # --- PASO E: Limpieza ---
            dev.d.app_stop("com.zigzagame.evertale")
            time.sleep(4)

        cuenta.mark_task_done("daily_missions")
        cuenta.mark_task_done("login_bonus")
        db.save()
        print(f" 💾 Progreso guardado: {cuenta.name}.")

def menu_interactivo():
    db = Database()
    dev = Device()
    vis = Vision(threshold=0.8)

    print("\n[🔌] Conectando al dispositivo...")
    if not dev.connect():
        return

    while True:
        print("\n" + "=" * 50)
        print(" 🤖 EVERTALE BOT - MENÚ PRINCIPAL 🤖")
        print("=" * 50)
        print(" 1. 🚀 Ejecutar Flujo Completo")
        print(" 2. 📊 Ver Estado")
        print(" 3. 🔄 Inyección Código")
        print(" 4. 🌐 Cambio Servidor")
        print(" 5. ⚔️ Rompehielos")
        print(" 6. 📜 Misiones Diarias")
        print(" 7. 🎃 Farmeo Evento")
        print(" 8. ❌ Salir")
        print("=" * 50)

        opcion = input(" Selecciona una opción: ")

        if opcion == '1': ejecutar_flujo_completo(db, dev, vis)
        elif opcion == '2': db.print_status()
        elif opcion == '3': ChangeAccount(dev, vis).execute(input(" Código: "))
        elif opcion == '4': ChangeServer(dev, vis).execute(f"templates/label_{input('Servidor: ').lower()}.png")
        elif opcion == '5': Startup(dev, vis).execute()
        elif opcion == '6': DailyMissions(dev, vis).execute()
        elif opcion == '7':
            print("\n--- Modo Farmeo de Evento Inteligente ---")
            input(" Asegúrate de estar en el menú del evento y presiona Enter...")
            EventFarm(dev, vis).execute()
        elif opcion == '8': break

if __name__ == "__main__":
    menu_interactivo()