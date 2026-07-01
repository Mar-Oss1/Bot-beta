"""
core/logger.py
Configura el sistema de logging del bot.
Llama setup_logger() UNA VEZ en main.py al arrancar.
Después cada módulo hace: log = get_logger(__name__)
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler

_LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")


def setup_logger(level_console=logging.INFO, level_file=logging.DEBUG) -> logging.Logger:
    """
    Inicializa el logger raíz 'evertale'.
    - Consola: INFO  (lo que ves corriendo el bot)
    - Archivo : DEBUG (todo, incluyendo detalle de visión)
    Rota a medianoche y guarda los últimos 14 días.
    """
    os.makedirs(_LOGS_DIR, exist_ok=True)

    logger = logging.getLogger("evertale")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger  # Evita agregar handlers duplicados si se llama dos veces

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Consola
    ch = logging.StreamHandler()
    ch.setLevel(level_console)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Archivo rotativo diario
    log_path = os.path.join(_LOGS_DIR, "bot_execution.log")
    fh = TimedRotatingFileHandler(
        log_path, when="midnight", backupCount=14, encoding="utf-8"
    )
    fh.setLevel(level_file)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logger.info("=" * 60)
    logger.info("Logger inicializado. Archivo: %s", log_path)
    logger.info("=" * 60)
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Retorna un logger hijo del logger raíz 'evertale'.
    Uso: log = get_logger(__name__)
    """
    return logging.getLogger(f"evertale.{name}")
