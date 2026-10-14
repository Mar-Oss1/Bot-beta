import time
import re
import cv2
import pytesseract
import os
import numpy as np
from core.config import TESSERACT_CMD
from core.logger import get_logger
from tasks.base_task import BaseTask

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
log = get_logger("raid")

MONSTER_TYPES = {
    "brown": {"template": "templates/raid_monster_brown.png", "priority": 1, "resource": "Green Potions",
              "name": "Café"},
    "purple": {"template": "templates/raid_monster_purple.png", "priority": 2, "resource": "Minerals + Fruit",
               "name": "Morado"},
    "yellow": {"template": "templates/raid_monster_yellow.png", "priority": 3, "resource": "Blue Potions",
               "name": "Amarillo"},
    "turquoise": {"template": "templates/raid_monster_turquoise.png", "priority": 4, "resource": "Minerals",
                  "name": "Turquesa"},
    "blue": {"template": "templates/raid_monster_blue.png", "priority": 5, "resource": "Minerals", "name": "Azul"},
}

MONSTER_POSITIONS = [
    {"y": 260, "icon_x": 1075, "power_x": 1250, "enter_x": 1775},
    {"y": 410, "icon_x": 1075, "power_x": 1250, "enter_x": 1775},
    {"y": 550, "icon_x": 1075, "power_x": 1250, "enter_x": 1775},
    {"y": 700, "icon_x": 1075, "power_x": 1250, "enter_x": 1775},
    {"y": 850, "icon_x": 1075, "power_x": 1250, "enter_x": 1775},
]

ICON_HALF_W = 70
ICON_HALF_H = 60
POWER_HALF_W_LEFT = 80
POWER_HALF_W_RIGHT = 150
POWER_HALF_H = 20


class Raid(BaseTask):
    def __init__(self, device, vision, account, db):
        super().__init__(device, vision, account, db)
        self._sid = None
        self._debug_dir = "screenshots/debug_raid"
        os.makedirs(self._debug_dir, exist_ok=True)

    def clear_loot_windows(self):
        super().clear_loot_windows(max_taps=6, extra_templates=["templates/raid_rewards.png"])

    def _leer_poder(self, screen_bgr, x: int, y: int) -> int:
        try:
            h, w = screen_bgr.shape[:2]
            roi_esc = cv2.resize(screen_bgr[max(0, y - POWER_HALF_H):min(h, y + POWER_HALF_H), max(0,
                                                                                                   x - POWER_HALF_W_LEFT):min(
                w, x + POWER_HALF_W_RIGHT)], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(roi_esc, cv2.COLOR_BGR2GRAY)

            def _parsear(t):
                if "M" in t or "m" in t: return int(float(re.findall(r"[\d.]+", t)[0]) * 1_000_000) if re.findall(
                    r"[\d.]+", t) else 0
                if "K" in t or "k" in t: return int(float(re.findall(r"[\d.]+", t)[0]) * 1_000) if re.findall(r"[\d.]+",
                                                                                                              t) else 0
                nums = re.sub(r"[^\d]", "", t)
                return int(nums) if nums and len(nums) <= 9 else 0

            _, thresh_normal = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            poder = _parsear(re.sub(r"[^\d.,KMkm]", "", pytesseract.image_to_string(thresh_normal,
                                                                                    config="--psm 7 -c tessedit_char_whitelist=0123456789.,KMkm").strip()))

            if poder == 0:
                _, thresh_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                poder = _parsear(re.sub(r"[^\d.,KMkm]", "", pytesseract.image_to_string(thresh_inv,
                                                                                        config="--psm 7 -c tessedit_char_whitelist=0123456789.,KMkm").strip()))

            return poder
        except Exception as e:
            log.error("Error leyendo poder: %s", e)
            return 0

    def _detectar_tipo_monstruo(self, screen_gray, y: int, icon_x: int) -> tuple:
        h, w = screen_gray.shape
        roi_gray = screen_gray[
            max(0, y - ICON_HALF_H):min(h, y + ICON_HALF_H), max(0, icon_x - ICON_HALF_W):min(w, icon_x + ICON_HALF_W)]

        mejor_tipo, mejor_confidence = None, 0
        for tipo, config in MONSTER_TYPES.items():
            if self.vision.find_template(roi_gray, config["template"], threshold=0.65):
                conf = 0.7
                if conf > mejor_confidence:
                    mejor_confidence, mejor_tipo = conf, tipo

        if mejor_tipo:
            log.info("  ✓ Tipo: %s", MONSTER_TYPES[mejor_tipo]["name"])
            return mejor_tipo, mejor_confidence

        log.warning("  ✗ No detectado y=%d", y)
        return None, 0

    def _analizar_monstruos(self) -> list:
        screen = self.device.screenshot()
        screen_gray, screen_bgr = self.vision.to_gray(screen), cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)

        monstruos = []
        for i, pos in enumerate(MONSTER_POSITIONS):
            log.info("  Analizando monstruo %d...", i + 1)
            tipo, _ = self._detectar_tipo_monstruo(screen_gray, pos["y"], pos["icon_x"])
            if not tipo:
                log.warning("  ✗ No se detectó tipo del monstruo %d", i + 1)
                continue

            poder = self._leer_poder(screen_bgr, pos["power_x"], pos["y"])
            if poder == 0:
                log.warning("  ✗ No se pudo leer poder del monstruo %d", i + 1)
                continue

            monstruos.append(
                {"index": i, "tipo": tipo, "priority": MONSTER_TYPES[tipo]["priority"], "power": poder, "y": pos["y"],
                 "enter_x": pos["enter_x"]})

        if not monstruos:
            log.error("No se detectaron monstruos válidos")
            return []

        return sorted(monstruos, key=lambda m: (m["priority"], -m["power"]))

    def _ir_al_mapa_guerra(self) -> bool:
        log.info("  [→] Navegando al mapa de Battalion Warfare...")
        if self.vision.find_any(self.device.screenshot(),
                                ["templates/alliance_war.png", "templates/war_of_the_realms.png",
                                 "templates/btn_raid_map.png"], threshold=0.85):
            log.info("[✓] Ya estamos en el mapa.")
            return True

        pos_battalion = self.vision.find_template(self.device.screenshot(), "templates/btn_battalion_warfare.png",
                                                  threshold=0.85)
        if not pos_battalion:
            log.error("No se encontró btn_battalion_warfare.")
            return False

        self.device.tap(pos_battalion[0], pos_battalion[1])
        self.wait_for_screen_stable(timeout=6, interval=0.5)

        if self.vision.find_any(self.device.screenshot(),
                                ["templates/alliance_war.png", "templates/war_of_the_realms.png",
                                 "templates/btn_raid_map.png"], threshold=0.85):
            log.info("[✓] Entrada exitosa al mapa.")
            return True

        log.error("No se pudo entrar al mapa.")
        return False

    def _entrar_raid(self) -> bool:
        log.info("[→] Buscando botón de raids...")
        if not self._ir_al_mapa_guerra():
            return False

        pos_raid = self.vision.find_any(self.device.screenshot(),
                                        ["templates/btn_raid_map.png", "templates/btn_siege.png",
                                         "templates/btn_raid.png"], threshold=0.85)
        if not pos_raid:
            log.error("No se encontró el botón de raids.")
            return False

        self.device.tap(pos_raid[1], pos_raid[2])
        self.wait_for_screen_stable(timeout=5, interval=0.5)
        log.info("[✓] Entrando a raids...")
        return True

    def _crear_party(self) -> bool:
        log.info("[→] Creando party...")
        pos_create = self.wait_for_template("templates/btn_siege_create.png", timeout=10, threshold=0.85, interval=0.5)
        if not pos_create:
            log.error("No se encontró botón Create tras 10s.")
            return False

        self.device.tap(pos_create[0], pos_create[1])
        pos_confirm = self.wait_for_template("templates/btn_siege_create_confirm.png", timeout=6, threshold=0.85,
                                             interval=0.3)
        if not pos_confirm:
            log.error("No se encontró confirmación de Create.")
            return False

        self.device.tap(pos_confirm[0], pos_confirm[1])
        if self.wait_for_template("templates/btn_siege_start.png", timeout=8, threshold=0.85, interval=0.5):
            log.info("[✓] Party creada (botón Start visible).")
        else:
            log.warning("[!] No se confirmó visualmente la creación de party. Continuando...")
        return True

    def _iniciar_raid(self) -> bool:
        log.info("[→] Iniciando raid...")
        pos_start = self.wait_for_template("templates/btn_siege_start.png", timeout=8, threshold=0.85, interval=0.5)
        if not pos_start:
            log.error("No se encontró botón Start Raid tras 8s.")
            return False

        self.device.tap(pos_start[0], pos_start[1])
        log.info("[⏳] Esperando inicio de batalla...")

        inicio = time.time()
        while time.time() - inicio < 15:
            if self.vision.find_any(self.device.screenshot(),
                                    ["templates/btn_battle_skip.png", "templates/btn_battle_speed.png",
                                     "templates/victory_banner.png"], threshold=0.75):
                log.info("[✓] Batalla iniciada (elemento de combate detectado).")
                return True
            time.sleep(0.5)

        log.warning("[!] No se detectó inicio de batalla visualmente. Continuando...")
        return True

    def _esperar_batalla(self):
        log.info("[⏳] Esperando batalla...")
        timeout, inicio = 90, time.time()

        while time.time() - inicio < timeout:
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, ["templates/btn_battle_skip.png", "templates/victory_banner.png",
                                                   "templates/defeat_banner.png"], threshold=0.80)

            if result:
                template, x, y = result
                if "skip" in template:
                    log.info("[→] Skip detectado")
                    self.device.tap(x, y)
                    time.sleep(0.8)
                    pos_ok = self.vision.find_template(self.device.screenshot(), "templates/btn_skip_ok.png",
                                                       threshold=0.80)
                    if pos_ok:
                        log.info("[✓] Confirmando skip")
                        self.device.tap(pos_ok[0], pos_ok[1])
                    continue
                if "victory" in template:
                    log.info("[✓] Victoria detectada")
                    self.device.tap(screen.width // 2, screen.height // 2)
                    time.sleep(0.8)
                    if self.wait_for_template("templates/raid_rewards.png", timeout=8, threshold=0.75, interval=0.5):
                        log.info("[✓] Raid Rewards detectado")
                        time.sleep(0.5)
                        self.cerrar_ventana()
                        time.sleep(1.0)
                        self.clear_loot_windows()
                        log.info("[✓] Recompensas cerradas")
                    else:
                        log.warning("[!] No se detectó Raid Rewards. Limpieza forzada.")
                        self.clear_loot_windows()
                    return
                if "defeat" in template:
                    log.info("[✗] Derrota detectada")
                    self.device.tap(300, 100)
                    time.sleep(1.0)
                    self.clear_loot_windows()
                    return
            time.sleep(0.6)

        log.warning("[!] Timeout esperando batalla (%ds)", timeout)
        self.clear_loot_windows()

    def _volver_a_lista(self):
        log.debug("[←] Volviendo a la lista...")
        self.cerrar_ventana()
        inicio = time.time()
        while time.time() - inicio < 8:
            if self.vision.find_any(self.device.screenshot(),
                                    ["templates/raid_monster_brown.png", "templates/raid_monster_purple.png",
                                     "templates/raid_monster_yellow.png", "templates/raid_monster_turquoise.png",
                                     "templates/raid_monster_blue.png"], threshold=0.6):
                log.debug("[✓] Lista de raids visible.")
                return
            time.sleep(0.5)
        log.warning("[!] No se confirmó visualmente la lista. Continuando...")

    def execute(self) -> bool:
        self._sid = getattr(self, "_sid", None)
        log.info("=" * 55)
        log.info("  Módulo de Asedios/Raids - %s", self.account.name if self.account else "Prueba")
        log.info("=" * 55)

        if not self._entrar_raid(): return False
        time.sleep(1.5)
        monstruos = self._analizar_monstruos()

        if not monstruos:
            log.error("No se detectaron monstruos válidos")
            return False

        max_priority = monstruos[0]["priority"]
        mismos_tipo = [m for m in monstruos if m["priority"] == max_priority]
        plan = mismos_tipo[:3] if len(mismos_tipo) >= 3 else (
            [mismos_tipo[0], mismos_tipo[0], mismos_tipo[1]] if len(mismos_tipo) == 2 else [mismos_tipo[0]] * 3)

        log.info("=" * 45)
        log.info("Plan: %d batallas", len(plan))
        for i, m in enumerate(plan): log.info("  Batalla %d: %s (Poder: %d)", i + 1, MONSTER_TYPES[m["tipo"]]["name"],
                                              m["power"])
        log.info("=" * 45)

        for i, monstruo in enumerate(plan):
            log.info("=" * 45)
            log.info("  Batalla %d/%d", i + 1, len(plan))
            log.info("=" * 45)

            if i > 0 and plan[i - 1]["tipo"] == monstruo["tipo"] and plan[i - 1]["power"] == monstruo["power"]:
                log.info("[⚡] Mismo monstruo (tipo y poder) que anterior. Buscando Create directo...")
                if self.wait_for_template("templates/btn_siege_create.png", timeout=5, threshold=0.80, interval=0.4):
                    log.info("[✓] Create encontrado directo. Repitiendo raid...")
                else:
                    log.info("[!] Create no visible. Navegando desde lista...")
                    self._volver_a_lista()
                    self.device.tap(monstruo["enter_x"], monstruo["y"])
                    if not self.wait_for_template("templates/btn_siege_create.png", timeout=12, threshold=0.80,
                                                  interval=0.5):
                        log.error("No apareció pantalla de party para batalla %d.", i + 1)
                        self.cerrar_ventana()
                        time.sleep(2)
                        self._volver_a_lista()
                        continue
            else:
                self.device.tap(monstruo["enter_x"], monstruo["y"])
                log.info("[⏳] Esperando pantalla de creación de party...")
                if not self.wait_for_template("templates/btn_siege_create.png", timeout=12, threshold=0.80,
                                              interval=0.5):
                    log.error("No apareció pantalla de party para batalla %d.", i + 1)
                    self.cerrar_ventana()
                    time.sleep(2)
                    self._volver_a_lista()
                    continue

            if not self._crear_party() or not self._iniciar_raid():
                log.error("Fallo creando o iniciando raid en batalla %d.", i + 1)
                self.cerrar_ventana()
                self._volver_a_lista()
                continue

            self._esperar_batalla()

            if i < len(plan) - 1 and (
                    plan[i + 1]["tipo"] != monstruo["tipo"] or plan[i + 1]["power"] != monstruo["power"]):
                log.info("[←] Siguiente es diferente (tipo o poder). Volviendo a lista...")
                self._volver_a_lista()

        log.info("[←] Volviendo al home...")
        self.cerrar_ventana()
        time.sleep(1.5)
        log.info("  Módulo de raids completado")
        return True