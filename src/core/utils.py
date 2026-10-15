# core/utils.py
import datetime
from core.config import ALLIANCE_WAR_WINDOW, WAR_OF_REALMS_WINDOW, RAID_WINDOWS


def hora_actual_en_intervalo(hora_inicio: int, min_inicio: int, hora_fin: int, min_fin: int) -> bool:
    """Retorna True si la hora actual está dentro del intervalo (soporta cruce de medianoche)."""
    ahora = datetime.datetime.now().time()
    inicio = datetime.time(hora_inicio, min_inicio)
    fin = datetime.time(hora_fin, min_fin)
    if inicio <= fin:
        return inicio <= ahora <= fin
    return ahora >= inicio or ahora <= fin


def es_hora_defensa_alliance_war() -> bool:
    return hora_actual_en_intervalo(*ALLIANCE_WAR_WINDOW)


def es_hora_defensa_war_realms() -> bool:
    return hora_actual_en_intervalo(*WAR_OF_REALMS_WINDOW)


def es_hora_raid() -> bool:
    return any(hora_actual_en_intervalo(h1, m1, h2, m2) for h1, m1, h2, m2 in RAID_WINDOWS)


def estado_raids_str() -> str:
    """Devuelve texto útil para el menú indicando si hay Raid activa o cuánto falta."""
    if es_hora_raid():
        return "🔥 ACTIVA AHORA"
    ahora = datetime.datetime.now()
    for h1, m1, _, _ in RAID_WINDOWS:
        inicioHoy = ahora.replace(hour=h1, minute=m1, second=0, microsecond=0)
        if inicioHoy > ahora:
            mins = int((inicioHoy - ahora).total_seconds() // 60)
            return f"⏳ Próxima en {mins // 60}h {mins % 60}m ({h1:02d}:{m1:02d})"
    return "🌙 Finalizadas por hoy"