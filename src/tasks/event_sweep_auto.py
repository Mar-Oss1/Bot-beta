# tasks/event_sweep_auto.py
import time
from core.logger import get_logger
from core.database import Database
from core.device import Device
from core.vision import Vision
from core.flow_helpers import intentar_login, procesar_servidor
from core.config import APP_PACKAGE
from tasks.event_sweep import EventSweep

log = get_logger("event_sweep_auto")


def ejecutar_eventos_para_cuentas(cuentas, dev: Device, vis: Vision, db: Database):
    """
    Ejecuta sweeps de eventos para una lista específica de cuentas.
    """
    if not cuentas:
        log.info("No se proporcionaron cuentas para eventos.")
        return

    log.info("Iniciando sweeps de eventos para %d cuentas.", len(cuentas))

    for cuenta in cuentas:
        log.info("=" * 50)
        log.info("PROCESANDO EVENTOS: %s (Prioridad: %d)", cuenta.name, cuenta.priority)
        log.info("=" * 50)

        # 1. Login
        if not intentar_login(cuenta, dev, vis):
            log.error("No se pudo entrar a %s tras 3 intentos.", cuenta.name)
            cuenta.mark_login_failed()
            db.save()
            continue

        # 2. Servidores
        servidores = cuenta.servers if cuenta.servers else [{"server_id": "DEFAULT"}]
        for index, servidor in enumerate(servidores):
            server_id = servidor.get("server_id", "DEFAULT")
            log.info("Procesando eventos en servidor %s", server_id)

            es_primer = (index == 0)
            if not procesar_servidor(cuenta, db, dev, vis, server_id, es_primer):
                log.error("Fallo al preparar servidor %s", server_id)
                continue

            # 3. Ejecutar Event Sweep
            event_task = EventSweep(dev, vis, cuenta, db)
            event_task._sid = None if server_id == "DEFAULT" else server_id

            exito = event_task.execute()
            if exito:
                log.info("Eventos completados en servidor %s", server_id)
            else:
                log.error("Eventos fallaron en servidor %s", server_id)

            # Cerrar juego después de cada servidor para preparar el siguiente
            dev.d.app_stop(APP_PACKAGE)
            time.sleep(3)

        log.info("Cuenta %s procesada.", cuenta.name)
        db.save()

    log.info("Sweeps de eventos finalizados.")


def ejecutar_eventos_para_todas(db: Database, dev: Device, vis: Vision, force=False):
    """
    Función de entrada principal para procesar eventos de todas las cuentas.
    """
    if force:
        cuentas = [a for a in db.accounts if a.enabled]
        log.info("Modo forzado: ejecutando eventos para todas las cuentas habilitadas.")
    else:
        cuentas = db.get_pending_accounts()
        if not cuentas:
            log.info("No hay cuentas con tareas pendientes. Saliendo.")
            return

    if not cuentas:
        log.info("No hay cuentas habilitadas para eventos.")
        return

    ejecutar_eventos_para_cuentas(cuentas, dev, vis, db)