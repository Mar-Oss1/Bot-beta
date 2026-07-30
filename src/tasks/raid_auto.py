# tasks/raid_auto.py
import time
from core.logger import get_logger
from core.database import Database
from core.device import Device
from core.vision import Vision
from core.flow_helpers import intentar_login, procesar_servidor
from core.config import APP_PACKAGE
from tasks.raid import Raid

log = get_logger("raid_auto")

def ejecutar_raids_para_cuentas(cuentas, dev: Device, vis: Vision, db: Database):
    """
    Ejecuta raids para una lista específica de cuentas (ya procesadas o no).
    """
    if not cuentas:
        log.info("No se proporcionaron cuentas para raids.")
        return

    log.info("Iniciando raids para %d cuentas.", len(cuentas))
    for cuenta in cuentas:
        log.info("=" * 50)
        log.info("PROCESANDO RAIDS: %s (Prioridad %d)", cuenta.name, cuenta.priority)
        log.info("=" * 50)

        # Login
        if not intentar_login(cuenta, dev, vis):
            log.error("No se pudo entrar a %s tras 3 intentos.", cuenta.name)
            cuenta.mark_login_failed()
            db.save()
            continue

        # Servidores
        servidores = cuenta.servers if cuenta.servers else [{"server_id": "DEFAULT"}]
        for index, servidor in enumerate(servidores):
            server_id = servidor.get("server_id", "DEFAULT")
            log.info("Procesando raids en servidor %s...", server_id)

            es_primer = (index == 0)
            if not procesar_servidor(cuenta, db, dev, vis, server_id, es_primer):
                log.error("Fallo al preparar servidor %s", server_id)
                continue

            # Ejecutar Raid
            raid = Raid(dev, vis, cuenta, db)
            raid._sid = None if server_id == "DEFAULT" else server_id
            exito = raid.execute()
            if exito:
                log.info("Raids completados en servidor %s", server_id)
            else:
                log.error("Raids fallaron en servidor %s", server_id)

            # Cerrar juego después de cada servidor
            dev.d.app_stop(APP_PACKAGE)
            time.sleep(3)

        log.info("Cuenta %s procesada.", cuenta.name)
        db.save()

    log.info("Raids finalizados.")


def ejecutar_raids_para_todas(db: Database, dev: Device, vis: Vision, force=False):

    if force:
        cuentas = [a for a in db.accounts if a.enabled]
        log.info("Modo forzado: ejecutando raids para todas las cuentas habilitadas.")
    else:
        cuentas = db.get_pending_accounts()
        if not cuentas:
            log.info("No hay cuentas con tareas pendientes. Saliendo.")
            return

    if not cuentas:
        log.info("No hay cuentas habilitadas para raids.")
        return

    ejecutar_raids_para_cuentas(cuentas, dev, vis, db)