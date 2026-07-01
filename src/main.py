"""
main.py
Punto de entrada del bot Evertale.

CAMBIOS VS VERSIÓN ANTERIOR:
- ejecutar_flujo_completo() descompuesta en helpers:
    _intentar_login()    → reintento de cambio de cuenta (aislado y testeable)
    _procesar_servidor() → lógica de un servidor completo
- DailyMissions recibe el objeto Account y la Database para persistir
  el estado módulo a módulo directamente en accounts.json.
- Logging centralizado: todos los print() → log.info/warning/error.
"""
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import setup_logger, get_logger
from core.database import Database
from core.device import Device
from core.vision import Vision
from tasks.startup import Startup
from tasks.daily_missions import DailyMissions
from tasks.change_account import ChangeAccount
from tasks.change_server import ChangeServer
from tasks.event_farm import EventFarm

# Inicializar logging UNA VEZ al arrancar
setup_logger()
log = get_logger("main")


# ══════════════════════════════════════════════════════════════
# HELPERS DEL FLUJO PRINCIPAL
# ══════════════════════════════════════════════════════════════

def _intentar_login(cuenta, dev: Device, vis: Vision, max_reintentos: int = 3) -> bool:
    """
    Abre Evertale y cambia a la cuenta indicada con hasta max_reintentos intentos.

    Retorna True si el login fue exitoso, False si se agotaron los reintentos.
    Extraído de ejecutar_flujo_completo para facilitar lectura y testing.
    """
    from core.config import APP_PACKAGE

    for intento in range(1, max_reintentos + 1):
        log.info("🔌 Arrancando Evertale — intento %d/%d...", intento, max_reintentos)
        dev.open_app()
        time.sleep(14)

        if not cuenta.serial:
            log.info("  [i] Sin serial configurado. Entrando directo.")
            return True

        exito = ChangeAccount(dev, vis).execute(cuenta.serial)
        if exito:
            log.info("✅ Inyección exitosa. Esperando pantalla de título...")
            time.sleep(12)
            return True

        log.warning("⚠️  Falló el cambio. Limpiando y reiniciando...")
        dev.d.app_stop(APP_PACKAGE)
        time.sleep(3)

    return False


def _procesar_servidor(
    cuenta, db: Database, dev: Device, vis: Vision,
    server_id: str, es_primer_servidor: bool
):
    """
    Maneja el ciclo completo para un servidor específico:
    1. Reabre el juego si no es el primer servidor de la cuenta.
    2. Cambia al servidor si no es DEFAULT.
    3. Corre el Startup (rompehielos).
    4. Corre DailyMissions, pasando Account y Database.
    5. Cierra el juego.

    Retorna True si el servidor se procesó correctamente.
    """
    from core.config import APP_PACKAGE

    if not es_primer_servidor:
        log.info("🔌 Reabriendo juego para servidor %s...", server_id)
        dev.open_app()
        time.sleep(14)

    if server_id != "DEFAULT":
        cambiador = ChangeServer(dev, vis)
        if not cambiador.execute(f"templates/label_{server_id.lower()}.png"):
            log.error("❌ No se pudo cambiar al servidor %s. Saltando.", server_id)
            dev.d.app_stop(APP_PACKAGE)
            return False

    if not Startup(dev, vis).execute():
        log.error("❌ Startup falló en servidor %s. Saltando.", server_id)
        dev.d.app_stop(APP_PACKAGE)
        return False

    # DailyMissions ya sabe en qué servidor está y guarda módulo a módulo
    DailyMissions(dev, vis, cuenta, db).execute(server_id=server_id)

    dev.d.app_stop(APP_PACKAGE)
    time.sleep(4)
    return True


# ══════════════════════════════════════════════════════════════
# FLUJO COMPLETO
# ══════════════════════════════════════════════════════════════

def ejecutar_flujo_completo(db: Database, dev: Device, vis: Vision):
    """Ejecuta la rutina automática para todas las cuentas pendientes."""
    from core.config import APP_PACKAGE

    log.info("=== INICIANDO MODO AUTOMÁTICO ===")
    db.print_status()

    cuentas_pendientes = db.get_pending_accounts()
    if not cuentas_pendientes:
        log.info("✅ Todas las cuentas terminaron sus tareas hoy. ¡A descansar!")
        return

    log.info("🧹 Limpiando estado inicial...")
    dev.d.app_stop(APP_PACKAGE)

    for cuenta in cuentas_pendientes:
        log.info("=" * 50)
        log.info("🚀 PROCESANDO: %s (Prioridad %d)", cuenta.name, cuenta.priority)
        log.info("=" * 50)

        # ── LOGIN ──────────────────────────────────────────
        if not _intentar_login(cuenta, dev, vis):
            log.error("❌ No se pudo entrar a %s tras 3 intentos.", cuenta.name)
            cuenta.mark_login_failed()
            db.save()
            continue

        # ── SERVIDORES ─────────────────────────────────────
        servidores = cuenta.servers if cuenta.servers else [{"server_id": "DEFAULT"}]

        for index, servidor in enumerate(servidores):
            server_id = servidor.get("server_id", "DEFAULT")

            # Saltar si este servidor ya está completo (recuperación tras crash)
            if cuenta.is_task_done("daily_missions", None if server_id == "DEFAULT" else server_id):
                log.info("⏭️  Servidor %s ya completado hoy. Saltando.", server_id)
                continue

            _procesar_servidor(
                cuenta, db, dev, vis,
                server_id=server_id,
                es_primer_servidor=(index == 0),
            )

        # db.save() ya fue llamado por DailyMissions después de cada módulo.
        # Este save final asegura que last_run quede actualizado.
        db.save()
        log.info("💾 Progreso final guardado: %s.", cuenta.name)


# ══════════════════════════════════════════════════════════════
# MENÚ INTERACTIVO
# ══════════════════════════════════════════════════════════════

def menu_interactivo():
    db = Database()
    dev = Device()
    vis = Vision(threshold=0.8)

    log.info("🔌 Conectando al dispositivo...")
    if not dev.connect():
        log.critical("No se pudo conectar al dispositivo. Saliendo.")
        return

    while True:
        print("\n" + "=" * 50)
        print(" 🤖 EVERTALE BOT - MENÚ PRINCIPAL 🤖")
        print("=" * 50)
        print(" 1. 🚀 Ejecutar Flujo Completo")
        print(" 2. 📊 Ver Estado")
        print(" 3. 🔄 Inyección Código")
        print(" 4. 🌐 Cambio Servidor")
        print(" 5. ⚔️  Rompehielos")
        print(" 6. 📜 Misiones Diarias (Modo Prueba — sin guardar estado)")
        print(" 7. 🎃 Farmeo Evento")
        print(" 8. ❌ Salir")
        print("=" * 50)

        opcion = input(" Selecciona una opción: ").strip()

        if opcion == "1":
            ejecutar_flujo_completo(db, dev, vis)

        elif opcion == "2":
            db.print_status()

        elif opcion == "3":
            ChangeAccount(dev, vis).execute(input(" Código: ").strip())

        elif opcion == "4":
            servidor = input(" Servidor (ej. SA-3): ").strip().lower()
            ChangeServer(dev, vis).execute(f"templates/label_{servidor}.png")

        elif opcion == "5":
            Startup(dev, vis).execute()

        elif opcion == "6":
            # Modo prueba: account=None, db=None → no guarda en accounts.json
            log.info("Modo Prueba activado (sin persistencia de estado).")
            DailyMissions(dev, vis, account=None, db=None).execute(server_id="DEFAULT")

        elif opcion == "7":
            print("\n--- Modo Farmeo de Evento Inteligente ---")
            input(" Asegúrate de estar en el menú del evento y presiona Enter...")
            EventFarm(dev, vis).execute()

        elif opcion == "8":
            log.info("Saliendo del bot.")
            break


if __name__ == "__main__":
    menu_interactivo()
