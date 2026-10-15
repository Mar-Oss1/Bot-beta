import time
from core.config import APP_PACKAGE
from core.logger import get_logger
from core.flow_helpers import intentar_login, procesar_servidor
from tasks.daily_missions import DailyMissions

log = get_logger("champ_arena_auto")


def ejecutar_champions_arena_para_todas(db, dev, vis, batallas: int = 10):
    log.info("=" * 55)
    log.info("INICIANDO ARENA DE CAMPEONES (%d ATAQUES) - TODAS LAS CUENTAS", batallas)
    log.info("=" * 55)

    cuentas = sorted([a for a in db.accounts if a.enabled], key=lambda x: x.priority)
    dev.d.app_stop(APP_PACKAGE)
    time.sleep(2)

    for idx, cuenta in enumerate(cuentas, 1):
        log.info("[%d/%d] Procesando cuenta: %s", idx, len(cuentas), cuenta.name)
        if not intentar_login(cuenta, dev, vis):
            log.error("Fallo login en %s. Saltando.", cuenta.name)
            continue

        servidores = cuenta.servers if cuenta.servers else [{"server_id": "DEFAULT"}]
        for s_idx, srv in enumerate(servidores):
            sid = srv.get("server_id", "DEFAULT")
            if cuenta.is_task_done("champions_arena", None if sid == "DEFAULT" else sid):
                log.info("Arena de Campeones ya hecha hoy en %s [%s].", cuenta.name, sid)
                continue

            if not procesar_servidor(cuenta, db, dev, vis, sid, es_primer_servidor=(s_idx == 0)):
                continue

            dm = DailyMissions(dev, vis, cuenta, db)
            if dm.do_champions_arena(batallas=batallas):
                cuenta.mark_task_done("champions_arena", None if sid == "DEFAULT" else sid)
                db.save()

            dev.d.app_stop(APP_PACKAGE)
            time.sleep(1.5)

        db.commit()