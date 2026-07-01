"""
core/economia.py
Registro histórico de gemas ganadas por cuenta y servidor.
Usa formato JSONL (una entrada JSON por línea) para que sea
seguro ante cortes de luz y fácil de procesar con pandas.
"""
import json
import os
from datetime import datetime

from core.logger import get_logger

log = get_logger("economia")

_LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
ECONOMIA_FILE = os.path.join(_LOGS_DIR, "economia_log.jsonl")


def registrar_economia(cuenta_nombre: str, server_id: str, gemas_inicio: int, gemas_fin: int):
    """
    Agrega una entrada al log económico con la ganancia neta de gemas
    para la cuenta y servidor indicados.

    Ejemplo de entrada guardada:
    {"fecha": "2026-06-30 12:34:56", "cuenta": "Mini Beth",
     "server_id": "DEFAULT", "gemas_inicio": 1200, "gemas_fin": 1350, "ganancia": 150}
    """
    os.makedirs(_LOGS_DIR, exist_ok=True)
    ganancia = gemas_fin - gemas_inicio
    entry = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cuenta": cuenta_nombre,
        "server_id": server_id,
        "gemas_inicio": gemas_inicio,
        "gemas_fin": gemas_fin,
        "ganancia": ganancia,
    }
    try:
        with open(ECONOMIA_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        log.info(
            "💰 [%s][%s] Gemas: %d → %d (%s%d)",
            cuenta_nombre, server_id,
            gemas_inicio, gemas_fin,
            "+" if ganancia >= 0 else "", ganancia
        )
    except Exception as e:
        log.error("No se pudo guardar el registro de economía: %s", e)
