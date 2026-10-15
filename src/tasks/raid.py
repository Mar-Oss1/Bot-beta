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
    "brown": {"template": "templates/raid_monster_brown.png", "priority": 1, "resource": "Green Potions", "name": "Café"},
    "purple": {"template": "templates/raid_monster_purple.png", "priority": 2, "resource": "Minerals + Fruit", "name": "Morado"},
    "yellow": {"template": "templates/raid_monster_yellow.png", "priority": 3, "resource": "Blue Potions", "name": "Amarillo"},
    "turquoise": {"template": "templates/raid_monster_turquoise.png", "priority": 4, "resource": "Minerals", "name": "Turquesa"},
    "blue": {"template": "templates/raid_monster_blue.png", "priority": 5, "resource": "Minerals", "name": "Azul"},
}

# Dimensiones dinámicas de la caja OCR para el poder
POWER_HALF_W_LEFT = 60
POWER_HALF_W_RIGHT = 150
POWER_HALF_H = 25

_RE_NUM = re.compile(r"[\d.]+")
_RE_CLEAN = re.compile(r"[^\d.,KMkm]")


class Raid(BaseTask):
    def __init__(self, device, vision, account, db):
        super().__init__(device, vision, account, db)
        self._sid = None
        self._debug_dir = "screenshots/debug_raid"
        os.makedirs(self._debug_dir, exist_ok=True)

    def clear_loot_windows(self):
        super().clear_loot_windows(max_taps=6, extra_templates=["templates/raid_rewards.png"])

    def _leer_poder(self, screen_gray: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> int:
        try:
            h, w = screen_gray.shape[:2]
            roi = screen_gray[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
            gray = cv2.resize(roi, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

            def _parsear(t: str) -> int:
                matches = _RE_NUM.findall(t)
                if not matches:
                    return 0
                if "M" in t or "m" in t:
                    return int(float(matches[0]) * 1_000_000)
                if "K" in t or "k" in t:
                    return int(float(matches[0]) * 1_000)
                nums = re.sub(r"[^\d]", "", t)
                return int(nums) if nums and len(nums) <= 9 else 0

            ocr_cfg = "--psm 7 -c tessedit_char_whitelist=0123456789.,KMkm"
            _, thresh_normal = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            raw_txt = pytesseract.image_to_string(thresh_normal, config=ocr_cfg).strip()
            poder = _parsear(_RE_CLEAN.sub("", raw_txt))

            if poder == 0:
                _, thresh_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                raw_txt = pytesseract.image_to_string(thresh_inv, config=ocr_cfg).strip()
                poder = _parsear(_RE_CLEAN.sub("", raw_txt))

            return poder
        except Exception as e:
            log.error("Error leyendo poder: %s", e)
            return 0

    def _detectar_tipo_en_caja(self, roi_gray: np.ndarray) -> tuple[str | None, float]:
        mejor_tipo, mejor_conf = None, 0.0
        for tipo, config in MONSTER_TYPES.items():
            cached = self.vision._load_template(config["template"])
            if cached is None:
                continue
            tmpl_gray, (th, tw) = cached
            if roi_gray.shape[0] < th or roi_gray.shape[1] < tw:
                continue
            res = cv2.matchTemplate(roi_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val >= 0.58 and max_val > mejor_conf:
                mejor_conf = float(max_val)
                mejor_tipo = tipo
        return mejor_tipo, mejor_conf

    def _obtener_slots_escalados(self, h: int, w: int) -> list[dict]:
        """
        Calcula las 5 filas en porcentaje respecto a la pantalla.
        """
        ratios_y = [0.235, 0.375, 0.510, 0.648, 0.785]
        slots = []
        for idx, ry in enumerate(ratios_y):
            cy = int(h * ry)
            slots.append({
                "index": idx,
                "y": cy,
                "icon_box": (int(w * 0.415), int(cy - h * 0.065), int(w * 0.478), int(cy + h * 0.065)),
                # Subido para abrazar los dígitos completos sin cortarlos por arriba
                "power_box": (int(w * 0.480), int(cy - h * 0.022), int(w * 0.610), int(cy + h * 0.032)),
                "enter_x": int(w * 0.735)
            })
        return slots

    def _analizar_monstruos(self) -> list:
        screen_gray = self.vision.to_gray(self.device.screenshot())
        orig_h, orig_w = screen_gray.shape[:2]

        # Si la imagen de prueba viene comprimida (ej. WhatsApp 1600x720),
        # la escalamos a 2400x1080 para que coincida con el tamaño de tus templates
        scale_x, scale_y = 1.0, 1.0
        if orig_w != 2400 or orig_h != 1080:
            scale_x = orig_w / 2400.0
            scale_y = orig_h / 1080.0
            screen_gray = cv2.resize(screen_gray, (2400, 1080), interpolation=cv2.INTER_CUBIC)

        slots = self._obtener_slots_escalados(1080, 2400)
        pre_candidatos = []

        for s in slots:
            ix1, iy1, ix2, iy2 = s["icon_box"]
            roi_icon = screen_gray[iy1:iy2, ix1:ix2]
            tipo, conf = self._detectar_tipo_en_caja(roi_icon)
            if tipo:
                log.info("  ✓ Slot %d -> %s (%.2f)", s["index"] + 1, MONSTER_TYPES[tipo]["name"], conf)
                s["tipo"] = tipo
                s["priority"] = MONSTER_TYPES[tipo]["priority"]
                pre_candidatos.append(s)
            else:
                log.warning("  ✗ Slot %d (y=%d) no reconocido", s["index"] + 1, s["y"])

        if not pre_candidatos:
            log.error("No se detectaron monstruos válidos")
            return []

        # OCR Selectivo: solo leemos poder de los monstruos de la mejor prioridad encontrada
        mejor_prio = min(m["priority"] for m in pre_candidatos)
        finalistas = [m for m in pre_candidatos if m["priority"] == mejor_prio]

        monstruos = []
        for m in finalistas:
            px1, py1, px2, py2 = m["power_box"]
            poder = self._leer_poder(screen_gray, px1, py1, px2, py2)
            if poder == 0 and len(finalistas) == 1:
                poder = 1
            if poder > 0:
                monstruos.append({
                    "index": m["index"],
                    "tipo": m["tipo"],
                    "priority": m["priority"],
                    "power": poder,
                    "y": int(m["y"] * scale_y),
                    "enter_x": int(m["enter_x"] * scale_x)
                })
                log.info("  🔢 Poder leído Slot %d (%s): %d",
                         m["index"] + 1, MONSTER_TYPES[m["tipo"]]["name"], poder)

        return sorted(monstruos, key=lambda m: (m["priority"], -m["power"]))

    def _ir_al_mapa_guerra(self) -> bool:
        log.info("  [→] Navegando al mapa de Battalion Warfare...")
        screen = self.device.screenshot()
        if self.vision.find_any(
            screen,
            ["templates/alliance_war.png", "templates/war_of_the_realms.png", "templates/btn_raid_map.png"],
            threshold=0.85,
            zona="COMPLETA"
        ):
            return True

        pos_battalion = self.vision.find_template(
            screen, "templates/btn_battalion_warfare.png", threshold=0.85, zona="MITAD_DERECHA"
        )
        if not pos_battalion:
            log.error("No se encontró btn_battalion_warfare.")
            return False

        self.device.tap(pos_battalion[0], pos_battalion[1])
        self.wait_for_screen_stable(timeout=5, interval=0.35)

        return self.vision.find_any(
            self.device.screenshot(),
            ["templates/alliance_war.png", "templates/war_of_the_realms.png", "templates/btn_raid_map.png"],
            threshold=0.85,
            zona="COMPLETA"
        ) is not None

    def _entrar_raid(self) -> bool:
        if not self._ir_al_mapa_guerra():
            return False

        pos_raid = self.vision.find_any(
            self.device.screenshot(),
            ["templates/btn_raid_map.png", "templates/btn_siege.png", "templates/btn_raid.png"],
            threshold=0.85,
            zona="MITAD_DERECHA"
        )
        if not pos_raid:
            log.error("No se encontró el botón de raids.")
            return False

        self.device.tap(pos_raid[1], pos_raid[2])
        self.wait_for_screen_stable(timeout=5, interval=0.35)
        return True

    def _crear_party(self) -> bool:
        pos_create = self.wait_for_template(
            "templates/btn_siege_create.png", timeout=10, threshold=0.85, interval=0.2, zona="MITAD_DERECHA"
        )
        if not pos_create:
            return False

        self.device.tap(pos_create[0], pos_create[1])
        pos_confirm = self.wait_for_template(
            "templates/btn_siege_create_confirm.png", timeout=6, threshold=0.85, interval=0.2, zona="CENTRO"
        )
        if not pos_confirm:
            return False

        self.device.tap(pos_confirm[0], pos_confirm[1])
        return True

    def _iniciar_raid(self) -> bool:
        pos_start = self.wait_for_template(
            "templates/btn_siege_start.png", timeout=8, threshold=0.85, interval=0.2, zona="MITAD_DERECHA"
        )
        if not pos_start:
            return False

        self.device.tap(pos_start[0], pos_start[1])
        inicio = time.monotonic()
        while time.monotonic() - inicio < 12:
            if self.vision.find_any(
                self.device.screenshot(),
                ["templates/btn_battle_skip.png", "templates/btn_battle_speed.png", "templates/victory_banner.png"],
                threshold=0.75,
                zona="COMPLETA"
            ):
                return True
            time.sleep(0.25)
        return True

    def _esperar_batalla(self):
        timeout, inicio = 90, time.monotonic()

        while time.monotonic() - inicio < timeout:
            screen = self.device.screenshot()

            # 1. Buscar Skip rápido en esquina
            pos_skip = self.vision.find_template(
                screen, "templates/btn_battle_skip.png", threshold=0.80, zona="ESQUINA_SUP_DER"
            )
            if pos_skip:
                self.device.tap(pos_skip[0], pos_skip[1])
                time.sleep(0.4)
                pos_ok = self.vision.find_template(
                    self.device.screenshot(), "templates/btn_skip_ok.png", threshold=0.80, zona="CENTRO"
                )
                if pos_ok:
                    self.device.tap(pos_ok[0], pos_ok[1])
                continue

            # 2. Buscar Victoria / Derrota en el centro
            result = self.vision.find_any(
                screen,
                ["templates/victory_banner.png", "templates/defeat_banner.png"],
                threshold=0.80,
                zona="CENTRO"
            )
            if result:
                template, _, _ = result
                if "victory" in template:
                    self.device.tap(1200, 540)
                    time.sleep(0.5)
                    if self.wait_for_template("templates/raid_rewards.png", timeout=6, threshold=0.75, interval=0.25, zona="CENTRO"):
                        self.cerrar_ventana()
                        time.sleep(0.5)
                    self.clear_loot_windows()
                    return
                if "defeat" in template:
                    self.device.tap(300, 100)
                    time.sleep(0.6)
                    self.clear_loot_windows()
                    return

            time.sleep(0.3)

        self.clear_loot_windows()

    def _volver_a_lista(self):
        self.cerrar_ventana()
        inicio = time.monotonic()
        templates_monstruos = [cfg["template"] for cfg in MONSTER_TYPES.values()]
        while time.monotonic() - inicio < 6:
            if self.vision.find_any(self.device.screenshot(), templates_monstruos, threshold=0.65, zona="LISTA_RAIDS"):
                return
            time.sleep(0.25)

    def execute(self) -> bool:
        self._sid = getattr(self, "_sid", None)
        log.info("=" * 55)
        log.info("  Módulo de Asedios/Raids - %s", self.account.name if self.account else "Prueba")
        log.info("=" * 55)

        if not self._entrar_raid():
            return False
        time.sleep(0.8)
        monstruos = self._analizar_monstruos()

        if not monstruos:
            return False

        # Preparamos el plan de 3 batallas repitiendo el mejor monstruo encontrado
        plan = [monstruos[0]] * 3

        for i, monstruo in enumerate(plan):
            log.info("  Batalla %d/%d -> %s (Poder: %d)",
                     i + 1, len(plan), MONSTER_TYPES[monstruo["tipo"]]["name"], monstruo["power"])

            if i > 0:
                # Si es la 2da o 3ra batalla contra el mismo tipo, buscamos si salió "Create" directo
                if not self.wait_for_template("templates/btn_siege_create.png", timeout=3.5, threshold=0.80, interval=0.2, zona="MITAD_DERECHA"):
                    self._volver_a_lista()
                    self.device.tap(monstruo["enter_x"], monstruo["y"])
                    if not self.wait_for_template("templates/btn_siege_create.png", timeout=10, threshold=0.80, interval=0.25, zona="MITAD_DERECHA"):
                        self.cerrar_ventana()
                        self._volver_a_lista()
                        continue
            else:
                self.device.tap(monstruo["enter_x"], monstruo["y"])
                if not self.wait_for_template("templates/btn_siege_create.png", timeout=10, threshold=0.80, interval=0.25, zona="MITAD_DERECHA"):
                    self.cerrar_ventana()
                    self._volver_a_lista()
                    continue

            if not self._crear_party() or not self._iniciar_raid():
                self.cerrar_ventana()
                self._volver_a_lista()
                continue

            self._esperar_batalla()

        self.cerrar_ventana()
        self.return_to_home()
        time.sleep(0.8)
        return True