import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import setup_logger, get_logger
from core.database import Database
from core.device import Device
from core.vision import Vision
from core.config import APP_PACKAGE
from core.utils import es_hora_raid, estado_raids_str
from core.economia import imprimir_resumen_economico_hoy
from tasks.startup import Startup
from tasks.daily_missions import DailyMissions
from tasks.change_account import ChangeAccount
from tasks.change_server import ChangeServer
from tasks.event_farm import EventFarm
from tasks.defense import Defense
from tasks.raid import Raid
from tasks.raid_auto import ejecutar_raids_para_todas
from tasks.event_sweep_auto import ejecutar_eventos_para_todas
from core.flow_helpers import intentar_login, procesar_servidor
from tasks.champions_arena_auto import ejecutar_champions_arena_para_todas

setup_logger()
log = get_logger("main")


# ======================================================
# FLUJO COMPLETO
# ======================================================

def ejecutar_flujo_completo(db: Database, dev: Device, vis: Vision):
    inicio_flujo = time.monotonic()
    log.info("=" * 60)
    log.info("INICIANDO FLUJO COMPLETO DE TAREAS")
    log.info("=" * 60)

    cuentas_pendientes = db.get_pending_accounts()
    if not cuentas_pendientes:
        log.info("Todas las cuentas terminaron sus tareas hoy. ¡A descansar!")
        imprimir_resumen_economico_hoy()
        return

    log.info("Limpiando estado inicial...")
    dev.d.app_stop(APP_PACKAGE)
    time.sleep(2)

    try:
        for idx_c, cuenta in enumerate(cuentas_pendientes, 1):
            inicio_cuenta = time.monotonic()
            log.info("=" * 55)
            log.info("PROCESANDO [%d/%d]: %s (Prioridad %d)",
                     idx_c, len(cuentas_pendientes), cuenta.name, cuenta.priority)
            log.info("=" * 55)

            if not intentar_login(cuenta, dev, vis):
                log.error("No se pudo entrar a %s tras 3 intentos.", cuenta.name)
                cuenta.mark_login_failed()
                db.commit()
                continue

            servidores = cuenta.servers if cuenta.servers else [{"server_id": "DEFAULT"}]

            for index, servidor in enumerate(servidores):
                server_id = servidor.get("server_id", "DEFAULT")

                if cuenta.is_task_done("daily_missions", None if server_id == "DEFAULT" else server_id):
                    log.info("Servidor %s ya completado hoy. Saltando.", server_id)
                    continue

                log.info("Preparando servidor %s...", server_id)
                es_primer_servidor = (index == 0)

                if not procesar_servidor(cuenta, db, dev, vis, server_id, es_primer_servidor):
                    log.warning("Falló la preparación del servidor %s. Continuando con el siguiente.", server_id)
                    continue

                log.info("Ejecutando Misiones Diarias en servidor %s...", server_id)
                misiones = DailyMissions(dev, vis, cuenta, db)
                misiones._server_id = None if server_id == "DEFAULT" else server_id

                if misiones.execute(server_id=server_id):
                    log.info("Servidor %s completado exitosamente.", server_id)
                else:
                    log.warning("Misiones incompletas/fallidas en servidor %s.", server_id)

                dev.d.app_stop(APP_PACKAGE)
                time.sleep(1.5)

            db.commit()
            dur_c = int(time.monotonic() - inicio_cuenta)
            log.info("Cuenta %s procesada en %dm %02ds.", cuenta.name, dur_c // 60, dur_c % 60)
            time.sleep(1.5)

    except KeyboardInterrupt:
        log.warning("Interrupción manual detectada (Ctrl+C). Guardando progreso en disco...")
        db.commit()
        return

    dur_total = int(time.monotonic() - inicio_flujo)
    log.info("=" * 60)
    log.info("FLUJO COMPLETO FINALIZADO EN %dm %02ds", dur_total // 60, dur_total % 60)
    log.info("=" * 60)

    imprimir_resumen_economico_hoy()

    if es_hora_raid():
        log.info("Es horario de raids. Ejecutando raids automáticos...")
        ejecutar_raids_para_todas(db, dev, vis)
    else:
        log.info("No es horario de raids (%s).", estado_raids_str())


# ======================================================
# MENÚ INTERACTIVO
# ======================================================

def menu_interactivo():
    db = Database()
    dev = Device()
    vis = Vision(threshold=0.8)

    vis.preload_templates("templates")

    log.info("Conectando al dispositivo...")
    if not dev.connect():
        log.critical("No se pudo conectar al dispositivo. Saliendo.")
        return

    while True:
        pendientes = len(db.get_pending_accounts())
        total_hab = sum(1 for a in db.accounts if a.enabled)

        print("\n" + "=" * 58)
        print("           EVERTALE BOT - PANEL DE CONTROL")
        print("-" * 58)
        print(f" 📋 Cuentas pendientes hoy : {pendientes}/{total_hab}")
        print(f" ⚔️  Estado de Raids        : {estado_raids_str()}")
        print("=" * 58)
        print("  1. Ejecutar Flujo Completo")
        print("  2. Ver Estado + Balance Contable de Gemas")
        print("  3. Inyección Código")
        print("  4. Cambio Servidor")
        print("  5. Rompehielos (Startup)")
        print("  6. Misiones Diarias (Modo Prueba - sin guardar estado)")
        print("  7. Farmeo Evento (Manual - 1 evento)")
        print("  8. Tiradas Premium")
        print("  9. Asedios/Raids (Todas las cuentas automático)")
        print(" 10. Defensa War (Manual)")
        print(" 11. Sweep de Eventos (Todas las cuentas automático)")
        print(" 12. Arena Champions (Todas las cuentas automático)")
        print(" 13. Salir")
        print("=" * 58)

        try:
            opcion = input("Selecciona una opción: ").strip()
        except KeyboardInterrupt:
            print("\nSaliendo...")
            break

        if opcion == "1":
            ejecutar_flujo_completo(db, dev, vis)

        elif opcion == "2":
            db.print_status()
            imprimir_resumen_economico_hoy()

        elif opcion == "3":
            codigo = input("Código: ").strip()
            if codigo:
                ChangeAccount(dev, vis).execute(codigo)

        elif opcion == "4":
            servidor = input("Servidor (ej. SA-3): ").strip().lower()
            if servidor:
                ChangeServer(dev, vis).execute(f"templates/label_{servidor}.png")

        elif opcion == "5":
            Startup(dev, vis).execute()

        elif opcion == "6":
            log.info("Modo Prueba activado (sin persistencia de estado).")
            DailyMissions(dev, vis, account=None, db=None).execute(server_id="DEFAULT")

        elif opcion == "7":
            print("\n--- Modo Farmeo de Evento Manual (1 evento) ---")
            input("Asegúrate de estar DENTRO del evento y presiona Enter...")
            EventFarm(dev, vis).execute()

        elif opcion == "8":
            print("\n--- Invocación Premium (x10) ---")
            raw_veces = input("¿Cuántas veces ejecutar? (default 1): ").strip() or "1"
            veces = int(raw_veces) if raw_veces.isdigit() else 1
            DailyMissions(dev, vis, account=None, db=None).do_premium_summons(veces=veces)

        elif opcion == "9":
            print("\n--- Asedios/Raids Automáticos para todas las cuentas ---")
            ejecutar_raids_para_todas(db, dev, vis, force=True)

        elif opcion == "10":
            print("\n--- Defensa War (Manual) ---")
            log.info("Ejecutando Defensa en la cuenta actual (sin persistencia).")
            Defense(dev, vis, account=None, db=None).execute()

        elif opcion == "11":
            print("\n--- Sweep de Eventos Automáticos para todas las cuentas ---")
            ejecutar_eventos_para_todas(db, dev, vis, force=True)

        elif opcion == "12":
            ejecutar_champions_arena_para_todas(db, dev, vis, batallas=10)
        elif opcion == "13":
            log.info("Saliendo del bot.")
            break
        else:
            print("Opción no válida. Intenta de nuevo.")



if __name__ == "__main__":
    menu_interactivo()