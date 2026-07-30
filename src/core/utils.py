# core/utils.py
import datetime
from core.config import ALLIANCE_WAR_WINDOW, WAR_OF_REALMS_WINDOW, RAID_WINDOWS

def hora_actual_en_intervalo(hora_inicio, min_inicio, hora_fin, min_fin):
    """Retorna True si la hora actual está dentro del intervalo (inclusive)."""
    ahora = datetime.datetime.now().time()
    inicio = datetime.time(hora_inicio, min_inicio)
    fin = datetime.time(hora_fin, min_fin)
    if inicio <= fin:
        return inicio <= ahora <= fin
    else:
        return ahora >= inicio or ahora <= fin

def es_hora_defensa_alliance_war():
    return hora_actual_en_intervalo(*ALLIANCE_WAR_WINDOW)

def es_hora_defensa_war_realms():
    return hora_actual_en_intervalo(*WAR_OF_REALMS_WINDOW)

def es_hora_raid():
    ahora = datetime.datetime.now().time()
    for h1, m1, h2, m2 in RAID_WINDOWS:
        inicio = datetime.time(h1, m1)
        fin = datetime.time(h2, m2)
        if inicio <= ahora <= fin:
            return True
    return False