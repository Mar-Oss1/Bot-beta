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
            timeout=20,  # máximo 20s (por si el device es lento)
            threshold=0.75,
            interval=0.5  # poll cada 0.5s
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


def ejecutar_tarea_en_cuentas(task_class, cuentas, dev, vis, db, nombre_tarea="Tarea"):
    """
    Despachador genérico para ejecutar una tarea (clase) en una lista de cuentas.
    Elimina el boilerplate duplicado en los ejecutores por lotes (*_auto.py).
    """
    if not cuentas:
        log.info("No se proporcionaron cuentas para %s.", nombre_tarea)
        return

    log.info("Iniciando %s para %d cuentas.", nombre_tarea, len(cuentas))

    for cuenta in cuentas:
        log.info("=" * 50)
        log.info("PROCESANDO %s: %s (Prioridad: %d)", nombre_tarea.upper(), cuenta.name, cuenta.priority)
        log.info("=" * 50)

        # 1. Login
        if not intentar_login(cuenta, dev, vis):
            log.error("No se pudo entrar a %s tras 3 intentos.", cuenta.name)
            cuenta.mark_login_failed()
            db.commit()
            continue

        # 2. Servidores
        servidores = cuenta.servers if cuenta.servers else [{"server_id": "DEFAULT"}]
        for index, servidor in enumerate(servidores):
            server_id = servidor.get("server_id", "DEFAULT")
            log.info("Procesando %s en servidor %s", nombre_tarea, server_id)

            es_primer = (index == 0)
            if not procesar_servidor(cuenta, db, dev, vis, server_id, es_primer):
                log.error("Fallo al preparar servidor %s", server_id)
                continue

            # 3. Instanciar y Ejecutar Tarea
            # Instanciamos la clase de la tarea dinámicamente
            tarea_instance = task_class(dev, vis, cuenta, db)

            # Si la clase requiere el server_id como atributo (ej: EventSweep, Raid)
            if hasattr(tarea_instance, '_sid'):
                tarea_instance._sid = None if server_id == "DEFAULT" else server_id

            try:
                exito = tarea_instance.execute()
                if exito:
                    log.info("%s completado en servidor %s", nombre_tarea, server_id)
                else:
                    log.warning("%s incompleto/fallido en servidor %s", nombre_tarea, server_id)
            except Exception as e:
                log.error("Error crítico ejecutando %s en servidor %s: %s", nombre_tarea, server_id, e)

            # Cerrar juego después de cada servidor para preparar el siguiente
            dev.d.app_stop(APP_PACKAGE)
            time.sleep(3)

        log.info("Cuenta %s procesada.", cuenta.name)
        db.commit()

    log.info("Ejecución de %s finalizada.", nombre_tarea)
