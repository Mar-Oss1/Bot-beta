# tasks/event_sweep_auto.py
from core.logger import get_logger
from core.database import Database
from core.device import Device
from core.vision import Vision
from core.flow_helpers import ejecutar_tarea_en_cuentas
from tasks.event_sweep import EventSweep

log = get_logger("event_sweep_auto")


def ejecutar_eventos_para_todas(db: Database, dev: Device, vis: Vision, force: bool = False):
    todas_habilitadas = [a for a in db.accounts if a.enabled]

    if force:
        cuentas = todas_habilitadas
        log.info("Modo forzado: ejecutando eventos para %d cuentas habilitadas.", len(cuentas))
    else:
        cuentas = [
            a for a in todas_habilitadas
            if any(
                not a.is_task_done("event_sweep", None if s.get("server_id", "DEFAULT") == "DEFAULT" else s.get("server_id"))
                for s in (a.servers if a.servers else [{"server_id": "DEFAULT"}])
            )
        ]
        if not cuentas:
            log.info("Todas las cuentas ya completaron el sweep de eventos hoy.")
            return

    ejecutar_tarea_en_cuentas(
        task_class=EventSweep,
        cuentas=cuentas,
        dev=dev,
        vis=vis,
        db=db,
        nombre_tarea="Sweep de Eventos"
    )