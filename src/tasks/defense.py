import time
from core.logger import get_logger

log = get_logger("defense")

ALLIANCE_TEMPLATES = {
    "Somnial": ["templates/alliance_noterindas.png"],
    "KuroNeko": ["templates/alliance_noterindas.png"],
    "Diferoku": ["templates/alliance_noterindas.png"],
    "ASRA": ["templates/alliance_noterindas.png"],
    "Mini Beth": ["templates/alliance_sao.png"],
    "BENKEI": ["templates/alliance_sao.png"],
    "Yukimura": ["templates/alliance_sao.png"],
    "Link123": ["templates/alliance_sao.png"],
    "Omega123": ["templates/alliance_sao.png"],
    "Mcbeth/Beth": ["templates/alliance_sao.png", "templates/alliance_mcbeth.png"],
    "Y U M E": ["templates/alliance_sao.png"],
    "アラン": ["templates/alliance_sao.png"],
    "Jiren / sami": ["templates/alliance_sao.png", "templates/alliance_mcbeth.png"],
    "default": ["templates/alliance_noterindas.png"],
}

EVENTS = [
    {"name": "Alliance War", "template": "templates/alliance_war.png", "is_last": False},
    {"name": "War of the Realms", "template": "templates/war_of_the_realms.png", "is_last": True},
]

SCROLL_PATTERN = [
    # 1. Bajar (swipe hacia arriba: y1 > y2)
    # Desde centro (1400,590) hasta borde superior (1400,200)
    (1400, 590, 1400, 395, 1.0),  # Primera mitad
    (1400, 395, 1400, 200, 1.0),  # Segunda mitad

    # 2. Izquierda (swipe hacia la derecha: x1 < x2)
    # Desde (1400,200) hasta borde derecho (1700,200)
    (1400, 200, 1550, 200, 1.0),  # Primera mitad
    (1550, 200, 1700, 200, 1.0),  # Segunda mitad

    # 3. Arriba (swipe hacia abajo: y1 < y2)
    # Desde (1700,200) hasta borde inferior (1700,890)
    (1700, 200, 1700, 545, 1.0),  # Primera mitad
    (1700, 545, 1700, 890, 1.0),  # Segunda mitad

    # 4. Derecha (swipe hacia la izquierda: x1 > x2)
    # Desde (1700,890) hasta borde izquierdo (1000,890)
    (1700, 890, 1350, 890, 1.0),  # Primera mitad
    (1350, 890, 1000, 890, 1.0),  # Segunda mitad
]


class Defense:
    def __init__(self, device, vision, account, db):
        self.device = device
        self.vision = vision
        self.account = account
        self.db = db

    def _get_alliance_templates(self) -> list:
        if self.account is None:
            return ALLIANCE_TEMPLATES["default"]
        return ALLIANCE_TEMPLATES.get(self.account.name, ALLIANCE_TEMPLATES["default"])

    def cerrar_ventana(self, screen=None):
        if screen is None:
            screen = self.device.screenshot()
        pos = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
        if pos:
            log.debug("Cerrando con botón X")
            self.device.tap(pos[0], pos[1])
            time.sleep(2)
            return
        pos = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.85)
        if pos:
            log.debug("Cerrando con btn_back.png")
            self.device.tap(pos[0], pos[1])
            time.sleep(2)
            return
        log.debug("Sin botón de cierre. Usando back de Android.")
        self.device.d.press("back")
        time.sleep(2)

    def return_to_home(self):
        screen = self.device.screenshot()
        pos = self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.85)
        if pos:
            self.device.tap(pos[0], pos[1])
            time.sleep(3)
        else:
            for _ in range(4):
                self.device.d.press("back")
                time.sleep(1.5)
                screen = self.device.screenshot()
                pos = self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.85)
                if pos:
                    self.device.tap(pos[0], pos[1])
                    time.sleep(3)
                    break

        for _ in range(4):
            screen = self.device.screenshot()
            algo = False
            pos_claim = self.vision.find_template(screen, "templates/btn_claim.png", threshold=0.8)
            if pos_claim:
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(2)
                algo = True
            if not algo:
                pos_x = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
                if pos_x:
                    self.device.tap(pos_x[0], pos_x[1])
                    time.sleep(2)
                    algo = True
            if not algo:
                break

    def _entrar_evento(self, event: dict) -> bool:
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
        templates = self._get_alliance_templates()
        log.info("  [🔍] Buscando castillo con templates: %s", templates)
        time.sleep(5)
        log.info("  [👆] Activando mapa...")
        self.device.tap(760, 1200)
        time.sleep(1.0)
        self.device.tap(760, 1200)
        time.sleep(1.0)

        def check(screen):
            for t in templates:
                pos = self.vision.find_template(screen, t, threshold=0.82)
                if pos:
                    log.info("  [✓] Castillo encontrado con: %s", t)
                    return pos
            return None

        pos = check(self.device.screenshot())
        if pos:
            return pos

        for i, (x1, y1, x2, y2, pausa) in enumerate(SCROLL_PATTERN):
            log.info("  [🔄] Scroll %d/%d...", i + 1, len(SCROLL_PATTERN))
            self.device.swipe(x1, y1, x2, y2, duration=0.5)
            time.sleep(pausa)
            pos = check(self.device.screenshot())
            if pos:
                log.info("  [✓] Castillo en scroll %d, pos (%d, %d).", i + 1, pos[0], pos[1])
                return pos

        log.warning("  Sin castillo tras %d scrolls.", len(SCROLL_PATTERN))
        return None

    def _tocar_castillo_y_abrir_menu(self, pos: tuple) -> bool:
        log.info("  [👆] Tocando castillo en (%d, %d)...", pos[0], pos[1])
        self.device.tap(pos[0], pos[1])
        time.sleep(2.5)

        screen = self.device.screenshot()
        pos_shield = self.vision.find_template(screen, "templates/btn_defend_shield.png", threshold=0.85)
        if not pos_shield:
            log.warning("  Menú no apareció. Reintentando...")
            self.device.tap(pos[0], pos[1])
            time.sleep(2.5)
            screen = self.device.screenshot()
            pos_shield = self.vision.find_template(screen, "templates/btn_defend_shield.png", threshold=0.85)

        if not pos_shield:
            log.error("  No apareció el botón de escudo.")
            return False

        log.info("  [✓] Menú del castillo abierto.")
        return True

    def _abrir_listado_pelotones(self) -> bool:
        screen = self.device.screenshot()
        pos_shield = self.vision.find_template(screen, "templates/btn_defend_shield.png", threshold=0.85)
        if not pos_shield:
            log.error("  Botón escudo no encontrado.")
            return False
        log.info("  [🛡️] Abriendo listado de pelotones...")
        self.device.tap(pos_shield[0], pos_shield[1])
        time.sleep(3)
        return True

    def _scrollear_hasta_peloton_20(self):
        log.info("  [⬇️] Scrolleando listado hasta pelotón 20...")
        for _ in range(8):
            self.device.swipe(840, 832, 840, 255, duration=0.2)
            time.sleep(0.8)
        time.sleep(1)
        log.info("  [✓] Scroll completado.")

    def _tocar_defend(self) -> bool:
        screen = self.device.screenshot()
        todos_defend = self.vision.find_all_templates(
            screen, "templates/btn_defend_platoon.png", threshold=0.85
        )
        if not todos_defend:
            log.error("  No se encontró ningún botón Defend.")
            return False

        todos_defend.sort(key=lambda p: p[1], reverse=True)
        ultimo = todos_defend[0]
        log.info(
            "  [✓] %d botones Defend. Tocando el último en (%d, %d)...",
            len(todos_defend), int(ultimo[0]), int(ultimo[1])
        )
        self.device.tap(int(ultimo[0]), int(ultimo[1]))
        time.sleep(2)
        log.info("  [🛡️] Defensa asignada.")
        return True

    def _salir_evento(self, is_last: bool, nivel: int = 2):
        time.sleep(1.5)

        if nivel == 2:
            log.info("  [⬅️] Cerrando listado de pelotones...")
            self.cerrar_ventana()
            time.sleep(1.5)
            # ✅ CORRECCIÓN: Después de cerrar pelotones, ya estamos en el mapa del evento
            # No necesitamos hacer otro back para "salir del menú del castillo"
            # porque el juego ya nos llevó de vuelta al mapa después de tocar Defend

        if is_last:
            log.info("  [🏠] Último evento. Regresando al Home...")
            self.return_to_home()
            time.sleep(2)
        else:
            log.info("  [⬅️] Saliendo del evento al mapa principal...")
            screen = self.device.screenshot()
            pos_back = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.85)
            if pos_back:
                self.device.tap(pos_back[0], pos_back[1])
            else:
                self.device.d.press("back")
            time.sleep(2)
            log.info("  [✓] Listo para el siguiente evento.")

    def _defender_en_evento(self, event: dict) -> bool:
        log.info("━" * 45)
        log.info("🛡️  Evento: %s", event["name"])
        log.info("━" * 45)

        if not self._entrar_evento(event):
            return False

        pos_castillo = self._buscar_castillo()
        if not pos_castillo:
            log.warning("  Sin castillo. Saliendo...")
            self._salir_evento(event["is_last"], nivel=0)
            return False

        if not self._tocar_castillo_y_abrir_menu(pos_castillo):
            log.warning("  Menú no abrió. Saliendo...")
            self._salir_evento(event["is_last"], nivel=0)
            return False

        if not self._abrir_listado_pelotones():
            log.warning("  Pelotones no abrieron. Saliendo...")
            self._salir_evento(event["is_last"], nivel=1)
            return False

        self._scrollear_hasta_peloton_20()
        exito = self._tocar_defend()
        self._salir_evento(event["is_last"], nivel=2)

        return exito

    def execute(self) -> bool:
        cuenta_label = self.account.name if self.account else "Prueba"
        log.info("=" * 55)
        log.info("🛡️  Módulo de Defensa — %s", cuenta_label)
        log.info("=" * 55)

        resultados = {}
        for event in EVENTS:
            exito = self._defender_en_evento(event)
            resultados[event["name"]] = exito
            time.sleep(3)

        log.info("━" * 45)
        log.info("📊 Resumen Defensa — %s", cuenta_label)
        for nombre, ok in resultados.items():
            log.info("  %s: %s", nombre, "✅ Asignada" if ok else "❌ Falló")
        log.info("━" * 45)

        return all(resultados.values())
