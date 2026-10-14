# tasks/event_sweep_auto.py
from core.logger import get_logger
from core.database import Database
from core.device import Device
from core.vision import Vision
from core.flow_helpers import ejecutar_tarea_en_cuentas
from tasks.event_sweep import EventSweep

log = get_logger("event_sweep_auto")

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

    ejecutar_tarea_en_cuentas(
        task_class=EventSweep,
        cuentas=cuentas,
        dev=dev,
        vis=vis,
        db=db,
        nombre_tarea="Sweep de Eventos"
    )