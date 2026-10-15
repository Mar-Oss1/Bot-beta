# tasks/raid_auto.py
from core.logger import get_logger
from core.database import Database
from core.device import Device
from core.vision import Vision
from core.flow_helpers import ejecutar_tarea_en_cuentas
from tasks.raid import Raid

log = get_logger("raid_auto")


def ejecutar_raids_para_todas(db: Database, dev: Device, vis: Vision, force: bool = False):
    todas_habilitadas = [a for a in db.accounts if a.enabled]

    if force:
        cuentas = todas_habilitadas
        log.info("Modo forzado: ejecutando raids para %d cuentas habilitadas.", len(cuentas))
    else:
        # Filtramos cuentas que tengan al menos un servidor sin "raid" hecho hoy
        cuentas = [
            a for a in todas_habilitadas
            if any(
                not a.is_task_done("raid", None if s.get("server_id", "DEFAULT") == "DEFAULT" else s.get("server_id"))
                for s in (a.servers if a.servers else [{"server_id": "DEFAULT"}])
            )
        ]
        if not cuentas:
            log.info("Todas las cuentas habilitadas ya completaron sus raids hoy.")
            return

    ejecutar_tarea_en_cuentas(
        task_class=Raid,
        cuentas=cuentas,
        dev=dev,
        vis=vis,
        db=db,
        nombre_tarea="Raids"
    )