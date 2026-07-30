# tasks/defense.py
import time
from core.logger import get_logger
from tasks.base_task import BaseTask
from core.utils import es_hora_defensa_alliance_war
from core.utils import es_hora_defensa_war_realms

log = get_logger("defense")

ALLIANCE_TEMPLATES = {
    "Somnia": ["templates/alliance_noterindas.png"],
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

# Patrón de scroll para buscar castillo (optimizado)
SCROLL_PATTERN = [
    # 1. Bajar (swipe hacia arriba: y1 > y2)
    (1400, 590, 1400, 300, 1.0),
    (1400, 300, 1400, 150, 1.0),
    # 2. Izquierda (swipe hacia la derecha: x1 < x2)
    (1400, 200, 1800, 200, 1.0),
    (1800, 200, 1850, 200, 1.0),
    # 3. Arriba (swipe hacia abajo: y1 < y2)
    (1700, 200, 1700, 545, 1.0),
    (1700, 545, 1700, 890, 1.0),
    # 4. Derecha (swipe hacia la izquierda: x1 > x2)
    (1700, 890, 1200, 890, 1.0),
    (1200, 890, 1000, 890, 1.0),
]


class Defense(BaseTask):
    def __init__(self, device, vision, account, db):
        super().__init__(device, vision, account, db)

    def _get_alliance_templates(self) -> list:
        if self.account is None:
            return ALLIANCE_TEMPLATES["default"]
        return ALLIANCE_TEMPLATES.get(self.account.name, ALLIANCE_TEMPLATES["default"])

    def _entrar_evento(self, event: dict) -> bool:
        log.info("Buscando botón de evento: %s", event["name"])
        pos = self.wait_for_template(
            event["template"],
            timeout=5,
            threshold=0.85,
            interval=0.5
        )
        if not pos:
            log.error("No se encontró el botón de %s.", event["name"])
            return False

        self.device.tap(pos[0], pos[1])
        self.wait_for_screen_stable(timeout=5, interval=0.5)
        log.info("Entrado a %s.", event["name"])
        return True

    # ---- Buscar castillo con scroll inteligente ----
    def _buscar_castillo(self) -> tuple | None:
        templates = self._get_alliance_templates()
        log.info("Buscando castillo con templates: %s", templates)

        # Activar mapa (dos toques para asegurar)
        log.info("Activando mapa...")
        self.device.tap(10, 1000)
        time.sleep(1.0)
        self.device.tap(10, 1000)
        time.sleep(1.0)

        # Función auxiliar para verificar si el castillo está visible
        def check(screen):
            for t in templates:
                pos = self.vision.find_template(screen, t, threshold=0.82)
                if pos:
                    log.info("Castillo encontrado con: %s", t)
                    return pos
            return None

        # Primera verificación sin scroll
        pos = check(self.device.screenshot())
        if pos:
            return pos

        # Scroll hasta encontrar el castillo (máximo 8 scrolls)
        for i, (x1, y1, x2, y2, pausa) in enumerate(SCROLL_PATTERN):
            log.info("Scroll %d/%d...", i + 1, len(SCROLL_PATTERN))
            self.device.swipe(x1, y1, x2, y2, duration=0.8)
            time.sleep(pausa)  # mantenemos una pausa fija para que cargue el mapa
            pos = check(self.device.screenshot())
            if pos:
                log.info("Castillo encontrado en scroll %d, pos (%d, %d).", i + 1, pos[0], pos[1])
                return pos

        log.warning("Sin castillo tras %d scrolls.", len(SCROLL_PATTERN))
        return None

    # ---- Abrir menú del castillo ----
    def _tocar_castillo_y_abrir_menu(self, pos: tuple) -> bool:
        log.info("Tocando castillo en (%d, %d)...", pos[0], pos[1])
        self.device.tap(pos[0], pos[1])
        time.sleep(2.5)

        # Esperar a que aparezca el botón de escudo (menú)
        pos_shield = self.wait_for_template(
            "templates/btn_defend_shield.png",
            timeout=3,
            threshold=0.85
        )
        if not pos_shield:
            log.warning("Menú no apareció. Reintentando tocar castillo...")
            self.device.tap(pos[0], pos[1])
            time.sleep(2.5)
            pos_shield = self.wait_for_template(
                "templates/btn_defend_shield.png",
                timeout=3,
                threshold=0.85
            )

        if not pos_shield:
            log.error("No apareció el botón de escudo.")
            return False

        log.info("Menú del castillo abierto.")
        return True

    # ---- Abrir listado de pelotones ----
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

    # ---- Scroll hasta pelotón 20 ----
    def _scrollear_hasta_peloton_20(self):
        log.info("Scrollando listado hasta pelotón 20...")
        for _ in range(4):
            self.device.swipe(840, 832, 840, 255, duration=0.2)
            time.sleep(0.8)  # breve pausa entre scrolls
        time.sleep(1)
        log.info("Scroll completado.")

    # ---- Tocar el botón Defend del último pelotón ----
    def _tocar_defend(self) -> bool:
        screen = self.device.screenshot()
        todos_defend = self.vision.find_all_templates(
            screen,
            "templates/btn_defend_platoon.png",
            threshold=0.85
        )
        if not todos_defend:
            log.error("No se encontró ningún botón Defend.")
            return False

        # Ordenar de abajo a arriba (Y mayor = más abajo)
        todos_defend.sort(key=lambda p: p[1], reverse=True)
        ultimo = todos_defend[0]
        log.info(
            "%d botones Defend. Tocando el último en (%d, %d)...",
            len(todos_defend), int(ultimo[0]), int(ultimo[1])
        )
        self.device.tap(int(ultimo[0]), int(ultimo[1]))
        time.sleep(2)
        log.info("Defensa asignada.")
        return True

    # ---- Salir del evento ----
    def _salir_evento(self, is_last: bool, nivel: int = 2):
        time.sleep(1.5)

        if nivel == 2:
            log.info("Cerrando listado de pelotones...")
            self.cerrar_ventana()
            time.sleep(1.5)
            # Después de cerrar pelotones, ya estamos en el mapa del evento

        if is_last:
            log.info("Último evento. Regresando al Home...")
            self.return_to_home()
            time.sleep(2)
        else:
            log.info("Saliendo del evento al mapa principal...")
            screen = self.device.screenshot()
            pos_back = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.85)
            if pos_back:
                self.device.tap(pos_back[0], pos_back[1])
            else:
                self.device.d.press("back")
            time.sleep(2)
            log.info("Listo para el siguiente evento.")

    # ---- Flujo completo para un evento ----
    def _defender_en_evento(self, event: dict) -> bool:
        log.info("-" * 45)
        log.info("Evento: %s", event["name"])
        log.info("-" * 45)

        if not self._entrar_evento(event):
            return False

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

    # ---- Ejecución principal ----
    def execute(self) -> bool:
        cuenta_label = self.account.name if self.account else "Prueba"
        log.info("=" * 55)
        log.info("Módulo de Defensa - %s", cuenta_label)
        log.info("=" * 55)

        # 1. Verificar si ya estamos en el mapa de warfare
        screen = self.device.screenshot()
        resultado = self.vision.find_any(
            screen,
            ["templates/alliance_war.png", "templates/war_of_the_realms.png"],
            threshold=0.85
        )

        if not resultado:
            # No estamos en warfare, intentar entrar desde home
            log.info("No estamos en el mapa de warfare. Intentando entrar desde Home...")
            pos_battalion = self.vision.find_template(
                screen,
                "templates/btn_battalion_warfare.png",
                threshold=0.85
            )
            if pos_battalion:
                log.info("Botón Battalion Warfare encontrado en Home. Entrando...")
                self.device.tap(pos_battalion[0], pos_battalion[1])
                self.wait_for_screen_stable(timeout=5, interval=0.5)
                # Verificar que entramos correctamente
                screen = self.device.screenshot()
                resultado = self.vision.find_any(
                    screen,
                    ["templates/alliance_war.png", "templates/war_of_the_realms.png"],
                    threshold=0.85
                )
                if not resultado:
                    log.error("No se pudo entrar al mapa de warfare.")
                    return False
            else:
                log.error("No se encontró btn_battalion_warfare. ¿Estás en el home?")
                return False
        else:
            log.info("Ya estamos en el mapa de warfare (detectado: %s).", resultado[0])

        # 2. Ejecutar la defensa en cada evento (solo si está en horario)
        resultados = {}
        for event in EVENTS:
            # Comprobar horario
            if event["name"] == "Alliance War" and not es_hora_defensa_alliance_war():
                log.info("Alliance War fuera de horario. Saltando.")
                continue
            if event["name"] == "War of the Realms" and not es_hora_defensa_war_realms():
                log.info("War of the Realms fuera de horario. Saltando.")
                continue
            exito = self._defender_en_evento(event)
            resultados[event["name"]] = exito
            time.sleep(3)

        # 3. Resumen
        log.info("--" * 45)
        log.info("Resumen Defensa - %s", cuenta_label)
        for nombre, ok in resultados.items():
            log.info(" %s: %s", nombre, "Asignada" if ok else "Falló")
        log.info("--" * 45)

        return all(resultados.values())