"""
tasks/defense.py

Módulo de defensa automática para Alliance War y War of the Realms.
Flujo:
  1. Entrar al evento (Alliance War o War of the Realms)
  2. Scrollear el mapa buscando un castillo de la alianza correcta
  3. Tocar el castillo → aparece botón escudo + exclamación
  4. Tocar el escudo → aparece listado de pelotones
  5. Scrollear hasta el pelotón 20
  6. Tocar Defend → se asigna directo sin confirmación
  7. Salir y repetir para el segundo evento
"""

import time
import random
from core.logger import get_logger

log = get_logger("defense")

# Mapeo de cuenta → nombre de alianza (template a usar)
# Basado en accounts.json
ALLIANCE_TEMPLATES = {
    # SA-9
    "Somnial":   "templates/alliance_noterindas.png",
    "KuroNeko":  "templates/alliance_noterindas.png",
    "Diferoku":  "templates/alliance_noterindas.png",
    "ASRA":      "templates/alliance_noterindas.png",
    # SA-3
    "Mini Beth": "templates/alliance_sao.png",
    "BENKEI":    "templates/alliance_sao.png",
    "Yukimura":  "templates/alliance_sao.png",
    # SA-6
    "Mcbeth/Beth": "templates/alliance_mcbeth.png",
    # Default fallback
    "default":   "templates/alliance_noterindas.png",
}

# Eventos a defender
EVENTS = [
    {
        "name":     "Alliance War",
        "template": "templates/alliance_war.png",
    },
    {
        "name":     "War of the Realms",
        "template": "templates/war_of_the_realms.png",
    },
]

# Parámetros de scroll del mapa
# El mapa es extenso y el scroll es manual en todas direcciones
SCROLL_PATTERN = [
    # (x1, y1, x2, y2, pausa) — patrón en espiral desde el centro
    (760, 1200, 760,  400, 1.5),   # arriba
    (760,  400, 760, 1200, 1.5),   # abajo
    (760, 1200, 200, 1200, 1.5),   # izquierda
    (200, 1200, 760, 1200, 1.5),   # derecha
    (760, 1200, 400,  600, 1.5),   # diagonal arriba-izq
    (400,  600, 760, 1200, 1.5),   # diagonal abajo-der
    (760, 1200, 1200, 600, 1.5),   # diagonal arriba-der
    (1200, 600, 760, 1200, 1.5),   # diagonal abajo-izq
    (760, 1200, 760,  300, 2.0),   # arriba extendido
    (760,  300, 200,  300, 2.0),   # izquierda extendido
    (200,  300, 200, 1400, 2.0),   # abajo izquierda
    (200, 1400, 1300, 1400, 2.0),  # derecha abajo
    (1300, 1400, 1300, 300, 2.0),  # arriba derecha
]

MAX_SCROLL_INTENTOS = len(SCROLL_PATTERN)


class Defense:
    def __init__(self, device, vision, account, db):
        self.device  = device
        self.vision  = vision
        self.account = account
        self.db      = db

    def _get_alliance_template(self) -> str:
        """Retorna el template de alianza correspondiente a esta cuenta."""
        if self.account is None:
            return ALLIANCE_TEMPLATES["default"]
        return ALLIANCE_TEMPLATES.get(self.account.name, ALLIANCE_TEMPLATES["default"])

    def _entrar_evento(self, event: dict) -> bool:
        """
        Busca y toca el botón del evento en el mapa principal.
        Retorna True si entró correctamente.
        """
        log.info("  [🗺️] Buscando botón de evento: %s", event["name"])
        screen = self.device.screenshot()
        pos = self.vision.find_template(screen, event["template"], threshold=0.85)
        if not pos:
            log.error("  No se encontró el botón de %s.", event["name"])
            return False

        self.device.tap(pos[0], pos[1])
        time.sleep(4)
        log.info("  [✓] Entrado a %s.", event["name"])
        return True

    def _buscar_castillo(self) -> tuple | None:
        """
        Scrollea el mapa en patrón de búsqueda buscando un castillo
        de la alianza. Retorna (x, y) del castillo o None.
        """
        alliance_template = self._get_alliance_template()
        log.info("  [🔍] Buscando castillo de alianza con: %s", alliance_template)

        # Primero buscar sin scrollear (puede estar visible al entrar)
        screen = self.device.screenshot()
        pos = self.vision.find_template(screen, alliance_template, threshold=0.82)
        if pos:
            log.info("  [✓] Castillo encontrado sin scroll en (%d, %d).", pos[0], pos[1])
            return pos

        # Scrollear en patrón
        for i, (x1, y1, x2, y2, pausa) in enumerate(SCROLL_PATTERN):
            log.info("  [🔄] Scroll %d/%d buscando castillo...", i + 1, MAX_SCROLL_INTENTOS)
            self.device.swipe(x1, y1, x2, y2, duration=0.6)
            time.sleep(pausa)

            screen = self.device.screenshot()
            pos = self.vision.find_template(screen, alliance_template, threshold=0.82)
            if pos:
                log.info("  [✓] Castillo encontrado en scroll %d, pos (%d, %d).", i + 1, pos[0], pos[1])
                return pos

        log.warning("  No se encontró castillo tras %d scrolls.", MAX_SCROLL_INTENTOS)
        return None

    def _tocar_castillo_y_abrir_menu(self, pos: tuple) -> bool:
        """
        Toca el castillo y espera que aparezca el menú con
        el botón de escudo y exclamación.
        """
        log.info("  [👆] Tocando castillo en (%d, %d)...", pos[0], pos[1])
        self.device.tap(pos[0], pos[1])
        time.sleep(2.5)

        # Verificar que apareció el menú con el escudo
        screen = self.device.screenshot()
        pos_shield = self.vision.find_template(
            screen, "templates/btn_defend_shield.png", threshold=0.85
        )
        if not pos_shield:
            log.warning("  Menú de castillo no apareció. Reintentando tap...")
            self.device.tap(pos[0], pos[1])
            time.sleep(2.5)
            screen = self.device.screenshot()
            pos_shield = self.vision.find_template(
                screen, "templates/btn_defend_shield.png", threshold=0.85
            )

        if not pos_shield:
            log.error("  No apareció el botón de escudo.")
            return False

        log.info("  [✓] Menú del castillo abierto.")
        return True

    def _abrir_listado_pelotones(self) -> bool:
        """Toca el botón escudo para abrir el listado de pelotones."""
        screen = self.device.screenshot()
        pos_shield = self.vision.find_template(
            screen, "templates/btn_defend_shield.png", threshold=0.85
        )
        if not pos_shield:
            log.error("  Botón escudo no encontrado para abrir pelotones.")
            return False

        log.info("  [🛡️] Tocando botón escudo...")
        self.device.tap(pos_shield[0], pos_shield[1])
        time.sleep(3)
        return True

    def _scrollear_hasta_peloton_20(self):
        """
        Scrollea el listado de pelotones hacia abajo hasta llegar
        al pelotón 20. Scroll agresivo hacia abajo.
        """
        log.info("  [⬇️] Scrolleando hasta el pelotón 20...")
        # Scrollear varias veces hacia abajo para asegurar llegar al final
        for i in range(8):
            self.device.swipe(760, 1400, 760, 400, duration=0.4)
            time.sleep(0.8)
        log.info("  [✓] Scroll hasta el fondo completado.")
        time.sleep(1)

    def _tocar_defend(self) -> bool:
        """
        Busca y toca el botón Defend en el listado de pelotones.
        Como puede haber varios Defend visibles, toca el último visible
        (el más abajo en pantalla = el de mayor número de pelotón).
        """
        screen = self.device.screenshot()
        todos_defend = self.vision.find_all_templates(
            screen, "templates/btn_defend_platoon.png", threshold=0.85
        )

        if not todos_defend:
            log.error("  No se encontró ningún botón Defend.")
            return False

        # Ordenar por Y descendente → el más abajo es el pelotón de mayor número
        todos_defend.sort(key=lambda p: p[1], reverse=True)
        ultimo = todos_defend[0]

        log.info(
            "  [✓] %d botones Defend encontrados. Tocando el último en (%d, %d)...",
            len(todos_defend), int(ultimo[0]), int(ultimo[1])
        )
        self.device.tap(int(ultimo[0]), int(ultimo[1]))
        time.sleep(2)
        log.info("  [🛡️] Defensa asignada.")
        return True

    def _defender_en_evento(self, event: dict) -> bool:
        """
        Flujo completo de defensa para un evento.
        Retorna True si se asignó defensa correctamente.
        """
        log.info("━" * 45)
        log.info("🛡️  Evento: %s", event["name"])
        log.info("━" * 45)

        # 1. Entrar al evento
        if not self._entrar_evento(event):
            return False

        # 2. Buscar castillo de la alianza
        pos_castillo = self._buscar_castillo()
        if not pos_castillo:
            log.warning("  Sin castillo encontrado en %s. Saltando.", event["name"])
            self.device.d.press("back")
            time.sleep(2)
            return False

        # 3. Tocar castillo y verificar menú
        if not self._tocar_castillo_y_abrir_menu(pos_castillo):
            self.device.d.press("back")
            time.sleep(2)
            return False

        # 4. Abrir listado de pelotones
        if not self._abrir_listado_pelotones():
            self.device.d.press("back")
            time.sleep(2)
            return False

        # 5. Scrollear hasta pelotón 20
        self._scrollear_hasta_peloton_20()

        # 6. Tocar Defend
        exito = self._tocar_defend()

        # 7. Salir del evento
        time.sleep(1.5)
        self.device.d.press("back")
        time.sleep(2)
        self.device.d.press("back")
        time.sleep(2)

        return exito

    def execute(self) -> bool:
        """
        Ejecuta la defensa en Alliance War y War of the Realms.
        Ambos eventos en una sola llamada.
        """
        cuenta_label = self.account.name if self.account else "Prueba"
        log.info("=" * 55)
        log.info("🛡️  Módulo de Defensa — %s", cuenta_label)
        log.info("=" * 55)

        resultados = {}

        for event in EVENTS:
            exito = self._defender_en_evento(event)
            resultados[event["name"]] = exito
            # Pausa entre eventos para que el juego cargue
            time.sleep(3)

        # Reporte final
        log.info("━" * 45)
        log.info("📊 Resumen de Defensa — %s", cuenta_label)
        for nombre, ok in resultados.items():
            log.info("  %s: %s", nombre, "✅ Asignada" if ok else "❌ Falló")
        log.info("━" * 45)

        return all(resultados.values())
