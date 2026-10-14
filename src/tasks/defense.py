import time
from core.logger import get_logger
from tasks.base_task import BaseTask
from core.utils import es_hora_defensa_alliance_war, es_hora_defensa_war_realms

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
    "Jiren / sami": ["templates/alliance_sao.png", "templates/alliance_mcbeth.png"],
    "default": ["templates/alliance_noterindas.png"],
}

EVENTS = [
    {"name": "Alliance War", "template": "templates/alliance_war.png", "is_last": False},
    {"name": "War of the Realms", "template": "templates/war_of_the_realms.png", "is_last": True},
]


class Defense(BaseTask):
    def __init__(self, device, vision, account, db):
        super().__init__(device, vision, account, db)

    def _generar_espiral_scroll(self, cx=1200, cy=540, paso=350, max_vueltas=2):
        """
        Genera dinámicamente las coordenadas de swipe en una espiral cuadrada.
        cx, cy: Centro de tu pantalla (POCO X5 Pro horizontal es ~1200, 540)
        paso: Distancia del arrastre en píxeles.
        """
        movimientos = []
        x, y = cx, cy
        direcciones = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # Arriba, Derecha, Abajo, Izquierda
        longitud = 1
        idx = 0

        for _ in range(max_vueltas * 2):
            for _ in range(2):
                dx, dy = direcciones[idx]
                nx = x + (dx * paso * longitud)
                ny = y + (dy * paso * longitud)

                # Mantenemos las coordenadas de swipe dentro de los márgenes físicos seguros del celular
                nx = max(100, min(2300, nx))
                ny = max(100, min(980, ny))

                movimientos.append((x, y, nx, ny, 0.8))
                x, y = nx, ny
                idx = (idx + 1) % 4
            longitud += 1

        return movimientos

    def _get_alliance_templates(self) -> list:
        if self.account is None:
            return ALLIANCE_TEMPLATES["default"]
        return ALLIANCE_TEMPLATES.get(self.account.name, ALLIANCE_TEMPLATES["default"])

    def _entrar_evento(self, event: dict) -> bool:
        log.info("Buscando botón de evento: %s", event["name"])
        pos = self.wait_for_template(event["template"], timeout=5, threshold=0.85, interval=0.5)
        if not pos:
            log.error("No se encontró el botón de %s.", event["name"])
            return False
        self.device.tap(pos[0], pos[1])
        self.wait_for_screen_stable(timeout=5, interval=0.5)
        log.info("Entrado a %s.", event["name"])
        return True

    def _buscar_castillo(self) -> tuple | None:
        templates = self._get_alliance_templates()
        log.info("Buscando castillo con templates: %s", templates)

        log.info("Activando mapa...")
        self.device.tap(10, 1000)
        time.sleep(0.8)
        self.device.tap(10, 1000)
        time.sleep(0.8)

        # Primera verificación
        screen = self.device.screenshot()
        result = self.vision.find_any(screen, templates, threshold=0.82)
        if result:
            log.info("Castillo encontrado sin necesidad de scroll: %s", result[0])
            return (result[1], result[2])

        # Generar movimientos matemáticos
        patron_espiral = self._generar_espiral_scroll()

        for i, (x1, y1, x2, y2, duracion) in enumerate(patron_espiral):
            log.info("Scroll %d/%d (espiral)...", i + 1, len(patron_espiral))
            self.device.swipe(x1, y1, x2, y2, duration=duracion)
            time.sleep(1.0)  # Estabilización tras el swipe

            screen = self.device.screenshot()
            result = self.vision.find_any(screen, templates, threshold=0.82)
            if result:
                log.info("Castillo encontrado en scroll %d.", i + 1)
                return (result[1], result[2])

        log.warning("Sin castillo tras %d barridos en espiral.", len(patron_espiral))
        return None

    def _tocar_castillo_y_abrir_menu(self, pos: tuple) -> bool:
        log.info("Tocando castillo en (%d, %d)...", pos[0], pos[1])
        self.device.tap(pos[0], pos[1])
        time.sleep(2)

        pos_shield = self.wait_for_template("templates/btn_defend_shield.png", timeout=3, threshold=0.85)
        if not pos_shield:
            log.warning("Menú no apareció. Reintentando...")
            self.device.tap(pos[0], pos[1])
            time.sleep(2)
            pos_shield = self.wait_for_template("templates/btn_defend_shield.png", timeout=3, threshold=0.85)

        if not pos_shield:
            log.error("No apareció el botón de escudo.")
            return False
        log.info("Menú del castillo abierto.")
        return True

    def _abrir_listado_pelotones(self) -> bool:
        screen = self.device.screenshot()
        pos_shield = self.vision.find_template(screen, "templates/btn_defend_shield.png", threshold=0.85)
        if not pos_shield:
            log.error("Botón escudo no encontrado.")
            return False
        log.info("Abriendo listado de pelotones...")
        self.device.tap(pos_shield[0], pos_shield[1])
        self.wait_for_screen_stable(timeout=4, interval=0.5)
        return True

    def _scrollear_hasta_peloton_20(self):
        log.info("Scrollando hasta pelotón 20...")
        for _ in range(4):
            self.device.swipe(840, 832, 840, 255, duration=0.2)
            time.sleep(0.6)
        time.sleep(0.8)
        log.info("Scroll completado.")

    def _tocar_defend(self) -> bool:
        screen = self.device.screenshot()
        todos_defend = self.vision.find_all_templates(
            screen, "templates/btn_defend_platoon.png", threshold=0.85
        )
        if not todos_defend:
            log.error("No se encontró ningún botón Defend.")
            return False
        todos_defend.sort(key=lambda p: p[1], reverse=True)
        ultimo = todos_defend[0]
        log.info("%d botones Defend. Tocando el último en (%d, %d)...",
                 len(todos_defend), int(ultimo[0]), int(ultimo[1]))
        self.device.tap(int(ultimo[0]), int(ultimo[1]))
        time.sleep(1.5)
        log.info("Defensa asignada.")
        return True

    def _salir_evento(self, is_last: bool, nivel: int = 2):
        time.sleep(1)
        if nivel == 2:
            log.info("Cerrando listado de pelotones...")
            self.cerrar_ventana()
            time.sleep(1)

        if is_last:
            log.info("Último evento. Regresando al Home...")
            self.return_to_home()
            time.sleep(1.5)
        else:
            log.info("Saliendo del evento al mapa principal...")
            screen = self.device.screenshot()
            pos_back = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.85)
            if pos_back:
                self.device.tap(pos_back[0], pos_back[1])
            else:
                self.device.d.press("back")
            time.sleep(1.5)
            log.info("Listo para el siguiente evento.")

    def _defender_en_evento(self, event: dict) -> bool:
        log.info("-" * 45)
        log.info("Evento: %s", event["name"])
        log.info("-" * 45)

        if not self._entrar_evento(event): return False

        pos_castillo = self._buscar_castillo()
        if not pos_castillo:
            log.warning("Sin castillo. Saliendo...")
            self._salir_evento(event["is_last"], nivel=0)
            return False

        if not self._tocar_castillo_y_abrir_menu(pos_castillo):
            log.warning("Menú no abrió. Saliendo...")
            self._salir_evento(event["is_last"], nivel=0)
            return False

        if not self._abrir_listado_pelotones():
            log.warning("Pelotones no abrieron. Saliendo...")
            self._salir_evento(event["is_last"], nivel=1)
            return False

        self._scrollear_hasta_peloton_20()
        exito = self._tocar_defend()
        self._salir_evento(event["is_last"], nivel=2)
        return exito

    def execute(self) -> bool:
        cuenta_label = self.account.name if self.account else "Prueba"
        log.info("=" * 55)
        log.info("Módulo de Defensa - %s", cuenta_label)
        log.info("=" * 55)

        screen = self.device.screenshot()
        resultado = self.vision.find_any(screen, [
            "templates/alliance_war.png",
            "templates/war_of_the_realms.png"
        ], threshold=0.85)

        if not resultado:
            log.info("No estamos en el mapa de warfare. Intentando entrar desde Home...")
            pos_battalion = self.vision.find_template(
                screen, "templates/btn_battalion_warfare.png", threshold=0.85
            )
            if pos_battalion:
                log.info("Entrando a Battalion Warfare...")
                self.device.tap(pos_battalion[0], pos_battalion[1])
                self.wait_for_screen_stable(timeout=5, interval=0.5)
                screen = self.device.screenshot()
                resultado = self.vision.find_any(screen, [
                    "templates/alliance_war.png",
                    "templates/war_of_the_realms.png"
                ], threshold=0.85)
                if not resultado:
                    log.error("No se pudo entrar al mapa.")
                    return False
            else:
                log.error("No se encontró btn_battalion_warfare.")
                return False
        else:
            log.info("Ya estamos en el mapa de warfare.")

        resultados = {}
        for event in EVENTS:
            if event["name"] == "Alliance War" and not es_hora_defensa_alliance_war():
                log.info("Alliance War fuera de horario. Saltando.")
                continue
            if event["name"] == "War of the Realms" and not es_hora_defensa_war_realms():
                log.info("War of the Realms fuera de horario. Saltando.")
                continue

            exito = self._defender_en_evento(event)
            resultados[event["name"]] = exito
            time.sleep(2)

        log.info("--" * 45)
        log.info("Resumen Defensa - %s", cuenta_label)
        for nombre, ok in resultados.items():
            log.info("%s: %s", nombre, "Asignada" if ok else "Fallo")
        log.info("--" * 45)

        if not resultados:
            log.warning("Defensa: nada ejecutado (fuera de horario). No se marcará como completada.")
            return False

        return all(resultados.values())