"""
core/economia.py
Registro histórico y dashboard contable de gemas por cuenta y servidor.
"""
import json
import os
from datetime import datetime, date
from core.config import LOGS_DIR, ECONOMIA_FILE
from core.logger import get_logger

log = get_logger("economia")


def registrar_economia(cuenta_nombre: str, server_id: str, gemas_inicio: int, gemas_fin: int):
    os.makedirs(LOGS_DIR, exist_ok=True)

    # Protección contra lectura OCR fallida (0) al inicio o al final
    if gemas_inicio <= 0 or gemas_fin <= 0:
        ganancia = 0
        log.warning(
            "⚠️ [%s][%s] Lectura parcial de OCR (Inicio: %d, Fin: %d). Ganancia fijada en 0 para no alterar estadísticas.",
            cuenta_nombre, server_id, gemas_inicio, gemas_fin
        )
    else:
        ganancia = gemas_fin - gemas_inicio

    entry = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cuenta": cuenta_nombre,
        "server_id": server_id,
        "gemas_inicio": gemas_inicio,
        "gemas_fin": max(gemas_inicio, gemas_fin) if gemas_fin == 0 else gemas_fin,
        "ganancia": ganancia,
    }
    try:
        with open(ECONOMIA_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        log.info(
            "💰 [%s][%s] Gemas: %s → %s (%s%d)",
            cuenta_nombre, server_id,
            f"{gemas_inicio:,}", f"{entry['gemas_fin']:,}",
            "+" if ganancia >= 0 else "", ganancia
        )
    except Exception as e:
        log.error("No se pudo guardar el registro de economía: %s", e)


def imprimir_resumen_economico_hoy():
    """Imprime un balance contable consolidado del día y el patrimonio total leído."""
    if not os.path.exists(ECONOMIA_FILE):
        print("📊 Aún no hay registros económicos.")
        return

    hoy_str = str(date.today())
    ganancia_hoy = 0
    ultimas_gemas = {}  # (cuenta, server) -> gemas_fin más reciente

    with open(ECONOMIA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                key = (row["cuenta"], row.get("server_id", "DEFAULT"))
                if row.get("gemas_fin", 0) > 0:
                    ultimas_gemas[key] = row["gemas_fin"]
                if row.get("fecha", "").startswith(hoy_str):
                    ganancia_hoy += row.get("ganancia", 0)
            except Exception:
                continue

    patrimonio_total = sum(ultimas_gemas.values())
    print("\n" + "=" * 70)
    print(f"💎 BALANCE CONTABLE DE GEMAS ({hoy_str})")
    print("-" * 70)
    print(f"  • Ganancia neta hoy     : {'+' if ganancia_hoy >= 0 else ''}{ganancia_hoy:,} gemas")
    print(f"  • Patrimonio registrado : {patrimonio_total:,} gemas ({len(ultimas_gemas)} servidores medidos)")
    print("=" * 70 + "\n")