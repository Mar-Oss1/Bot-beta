"""
core/logger.py
Configura el sistema de logging del bot con colores ANSI en consola.
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from core.config import LOGS_DIR


class _ColorFormatter(logging.Formatter):
    """Pinta los niveles en la terminal de Windows/PyCharm sin ensuciar el archivo .log."""
    COLORS = {
        logging.DEBUG: "\033[90m",     # Gris
        logging.INFO: "\033[36m",      # Cyan
        logging.WARNING: "\033[93m",   # Amarillo brillante
        logging.ERROR: "\033[91m",     # Rojo brillante
        logging.CRITICAL: "\033[41m",  # Fondo rojo
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        record_copy = logging.makeLogRecord(record.__dict__)
        record_copy.levelname = f"{color}{record_copy.levelname:<8}{self.RESET}"
        return super().format(record_copy)


def setup_logger(level_console=logging.INFO, level_file=logging.DEBUG) -> logging.Logger:
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.system("")  # Activa soporte ANSI nativo en consolas de Windows 10/11

    logger = logging.getLogger("evertale")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    fmt_plain = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fmt_color = _ColorFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"  # En consola solo hora:min:seg para ganar espacio
    )

    ch = logging.StreamHandler()
    ch.setLevel(level_console)
    ch.setFormatter(fmt_color)
    logger.addHandler(ch)

    log_path = os.path.join(LOGS_DIR, "bot_execution.log")
    fh = TimedRotatingFileHandler(
        log_path, when="midnight", backupCount=14, encoding="utf-8"
    )
    fh.setLevel(level_file)
    fh.setFormatter(fmt_plain)
    logger.addHandler(fh)

    logger.info("=" * 60)
    logger.info("Logger inicializado. Archivo: %s", log_path)
    logger.info("=" * 60)
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"evertale.{name}")