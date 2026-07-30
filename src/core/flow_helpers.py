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
        time.sleep(14)
        if not cuenta.serial:
            log.info("Sin serial configurado. Entrando directo.")
            return True
        exito = ChangeAccount(dev, vis).execute(cuenta.serial)
        if exito:
            log.info("Inyección exitosa. Esperando pantalla de título...")
            time.sleep(12)
            return True
        log.warning("Falló el cambio. Limpiando y reiniciando...")
        dev.d.app_stop(APP_PACKAGE)
        time.sleep(3)
    return False

def procesar_servidor(cuenta, db, dev, vis, server_id, es_primer_servidor):

    if not es_primer_servidor:
        log.info("Reabriendo juego para servidor %s...", server_id)
        dev.open_app()
        time.sleep(14)
    if server_id != "DEFAULT":
        template_path = f"templates/label_{server_id.lower()}.png"
        if not ChangeServer(dev, vis).execute(template_path):
            log.error("No se pudo cambiar al servidor %s", server_id)
            return False
    if not Startup(dev, vis).execute():
        log.error("Startup falló para servidor %s", server_id)
        return False
    return True