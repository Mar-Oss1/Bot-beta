# core/flow_helpers.py

import time
from core.logger import get_logger
from core.config import APP_PACKAGE
from tasks.change_account import ChangeAccount
from tasks.change_server import ChangeServer
from tasks.startup import Startup

log = get_logger("flow_helpers")


def intentar_login(cuenta, dev, vis, max_reintentos=3):
    """Intenta abrir el juego e inyectar el serial de la cuenta."""
    for intento in range(1, max_reintentos + 1):
        log.info("Abriendo Evertale - intento %d/%d...", intento, max_reintentos)
        dev.open_app()

        # ═══ FIX: En vez de sleep(14) fijo, esperar la nube visualmente ═══
        pos_nube = vis.wait_for_template(
            dev.screenshot,
            "templates/btn_nube.png",
            timeout=20,      # máximo 20s (por si el device es lento)
            threshold=0.75,
            interval=0.5     # poll cada 0.5s
        )
        if not pos_nube:
            log.warning("No apareció la nube. Reintentando...")
            dev.d.app_stop(APP_PACKAGE)
            time.sleep(2)
            continue

        if not cuenta.serial:
            log.info("Sin serial configurado. Entrando directo.")
            return True

        exito = ChangeAccount(dev, vis).execute(cuenta.serial)
        if exito:
            # ═══ FIX: En vez de sleep(12) fijo, esperar pantalla de título ═══
            log.info("Inyección exitosa. Esperando pantalla de título...")
            pos_titulo = vis.wait_for_template(
                dev.screenshot,
                "templates/pantalla_titulo.png",
                timeout=25,
                threshold=0.8,
                interval=0.8
            )
            if pos_titulo:
                log.info("Pantalla de título detectada.")
            return True

        log.warning("Fallo el cambio. Limpiando y reiniciando...")
        dev.d.app_stop(APP_PACKAGE)
        time.sleep(2)  # ← reducido de 3 a 2

    return False


def procesar_servidor(cuenta, db, dev, vis, server_id, es_primer_servidor):
    if not es_primer_servidor:
        log.info("Reabriendo juego para servidor %s...", server_id)
        dev.open_app()
        # ═══ FIX: Esperar visual en vez de sleep(14) ═══
        vis.wait_for_template(
            dev.screenshot,
            "templates/btn_server_title.png",  # o btn_nube si aplica
            timeout=20,
            threshold=0.75,
            interval=0.5
        )

    if server_id != "DEFAULT":
        template_path = f"templates/label_{server_id.lower()}.png"
        if not ChangeServer(dev, vis).execute(template_path):
            log.error("No se pudo cambiar al servidor %s", server_id)
            return False

    if not Startup(dev, vis).execute():
        log.error("Startup falló para servidor %s", server_id)
        return False

    return True