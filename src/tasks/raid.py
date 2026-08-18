# tasks/raid.py  (coordenadas unificadas con test_raid_coords.py)

import time
import re
import cv2
import pytesseract
import os
import numpy as np
from PIL import Image
from core.config import TESSERACT_CMD, PROJECT_ROOT
from core.logger import get_logger
from tasks.base_task import BaseTask

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
log = get_logger("raid")

MONSTER_TYPES = {
    "brown":     {"template": "templates/raid_monster_brown.png",     "priority": 1, "resource": "Green Potions",      "name": "Café"},
    "purple":    {"template": "templates/raid_monster_purple.png",    "priority": 2, "resource": "Minerals + Fruit",   "name": "Morado"},
    "yellow":    {"template": "templates/raid_monster_yellow.png",    "priority": 3, "resource": "Blue Potions",       "name": "Amarillo"},
    "turquoise": {"template": "templates/raid_monster_turquoise.png", "priority": 4, "resource": "Minerals",           "name": "Turquesa"},
    "blue":      {"template": "templates/raid_monster_blue.png",      "priority": 5, "resource": "Minerals",           "name": "Azul"},
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

    # ── cerrar_ventana optimizado ──
    def cerrar_ventana(self, screen=None):
        if screen is None:
            screen = self.device.screenshot()
        result = self.vision.find_any(screen, [
            "templates/btn_cerrar_x.png",
            "templates/btn_back.png"
        ], threshold=0.8)
        if result:
            self.device.tap(result[1], result[2])
            time.sleep(0.8)
            return
        self.device.d.press("back")
        time.sleep(0.8)

    # ── clear_loot_windows optimizado ──
    def clear_loot_windows(self):
        acciones = {
            "templates/victory_banner.png": lambda: self.device.tap(300, 100),
            "templates/defeat_banner.png": lambda: self.device.tap(300, 100),
            "templates/raid_rewards.png": self._cerrar_rewards,
            "templates/rewards.png": self._cerrar_rewards,
            "templates/pantalla_loot.png": lambda: self.device.tap(300, 100),
        }
        for _ in range(6):
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, list(acciones.keys()), threshold=0.80)
            if result:
                template, x, y = result
                log.debug("Ventana detectada: %s", template)
                acciones[template]()
                time.sleep(0.8)
            else:
                break

    def _cerrar_rewards(self):
        screen = self.device.screenshot()
        pos_x = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
        if pos_x:
            self.device.tap(pos_x[0], pos_x[1])
        else:
            self.device.tap(2400, 200)
        time.sleep(0.8)

    # ── OCR de poder ──
    def _leer_poder(self, screen_bgr, x: int, y: int) -> int:
        try:
            h, w = screen_bgr.shape[:2]
            x1 = max(0, x - POWER_HALF_W_LEFT)
            x2 = min(w, x + POWER_HALF_W_RIGHT)
            y1 = max(0, y - POWER_HALF_H)
            y2 = min(h, y + POWER_HALF_H)
            roi_cv = screen_bgr[y1:y2, x1:x2]
            escala = 3
            roi_esc = cv2.resize(roi_cv, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(roi_esc, cv2.COLOR_BGR2GRAY)

            def _ocr(thresh_img):
                return pytesseract.image_to_string(
                    thresh_img, config="--psm 7 -c tessedit_char_whitelist=0123456789.,KMkm"
                ).strip()

            def _parsear(texto_limpio):
                if not texto_limpio:
                    return 0
                if "M" in texto_limpio or "m" in texto_limpio:
                    nums = re.findall(r"[\d.]+", texto_limpio)
                    return int(float(nums[0]) * 1_000_000) if nums else 0
                elif "K" in texto_limpio or "k" in texto_limpio:
                    nums = re.findall(r"[\d.]+", texto_limpio)
                    return int(float(nums[0]) * 1_000) if nums else 0
                else:
                    nums = re.sub(r"[^\d]", "", texto_limpio)
                    return int(nums) if nums and len(nums) <= 9 else 0

            _, thresh_normal = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            texto = _ocr(thresh_normal)
            texto_limpio = re.sub(r"[^\d.,KMkm]", "", texto)
            poder = _parsear(texto_limpio)

            if poder == 0:
                _, thresh_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                texto2 = _ocr(thresh_inv)
                texto_limpio2 = re.sub(r"[^\d.,KMkm]", "", texto2)
                poder2 = _parsear(texto_limpio2)
                if poder2 > 0:
                    return poder2

            return poder
        except Exception as e:
            log.error("Error leyendo poder: %s", e)
            return 0

    # ── Detección de tipo ──
    def _detectar_tipo_monstruo(self, screen_gray, y: int, icon_x: int) -> tuple:
        h, w = screen_gray.shape
        icon_y = y
        x1 = max(0, icon_x - ICON_HALF_W)
        x2 = min(w, icon_x + ICON_HALF_W)
        y1 = max(0, icon_y - ICON_HALF_H)
        y2 = min(h, icon_y + ICON_HALF_H)
        roi_gray = screen_gray[y1:y2, x1:x2]

        mejor_tipo = None
        mejor_confidence = 0

        for tipo, config in MONSTER_TYPES.items():
            pos = self.vision.find_template(roi_gray, config["template"], threshold=0.65)
            if pos:
                conf = 0.7
                if conf > mejor_confidence:
                    mejor_confidence = conf
                    mejor_tipo = tipo

        if mejor_tipo:
            log.info("  ✓ Tipo: %s", MONSTER_TYPES[mejor_tipo]["name"])
            return (mejor_tipo, mejor_confidence)

        log.warning("  ✗ No detectado y=%d", y)
        return (None, 0)

    # ── Análisis de monstruos ──
    def _analizar_monstruos(self) -> list:
        screen = self.device.screenshot()
        screen_gray = self.vision.to_gray(screen)
        screen_bgr = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)

        monstruos = []
        for i, pos in enumerate(MONSTER_POSITIONS):
            log.info("  Analizando monstruo %d...", i + 1)
            tipo, confidence = self._detectar_tipo_monstruo(
                screen_gray, pos["y"], pos["icon_x"]
            )
            if not tipo:
                log.warning("  ✗ No se detectó tipo del monstruo %d", i + 1)
                continue

            poder = self._leer_poder(screen_bgr, pos["power_x"], pos["y"])
            if poder == 0:
                log.warning("  ✗ No se pudo leer poder del monstruo %d", i + 1)
                continue

            monstruos.append({
                "index": i,
                "tipo": tipo,
                "priority": MONSTER_TYPES[tipo]["priority"],
                "power": poder,
                "y": pos["y"],
                "enter_x": pos["enter_x"]
            })

        if not monstruos:
            log.error("No se detectaron monstruos válidos")
            return []

        monstruos.sort(key=lambda m: (m["priority"], -m["power"]))
        return monstruos

    def _generar_plan_batallas(self, monstruos: list) -> list:
        if not monstruos:
            return []
        max_priority = monstruos[0]["priority"]
        mismos_tipo = [m for m in monstruos if m["priority"] == max_priority]

        log.info("Monstruos de máxima prioridad: %d", len(mismos_tipo))

        if len(mismos_tipo) >= 3:
            return mismos_tipo[:3]
        elif len(mismos_tipo) == 2:
            return [mismos_tipo[0], mismos_tipo[0], mismos_tipo[1]]
        else:
            return [mismos_tipo[0]] * 3

    # ── Navegación ──
    def _ir_al_mapa_guerra(self) -> bool:
        log.info("  [→] Navegando al mapa de Battalion Warfare...")
        screen = self.device.screenshot()
        resultado = self.vision.find_any(screen, [
            "templates/alliance_war.png",
            "templates/war_of_the_realms.png",
            "templates/btn_raid_map.png",
        ], threshold=0.85)

        if resultado:
            log.info("[✓] Ya estamos en el mapa.")
            return True

        pos_battalion = self.vision.find_template(screen, "templates/btn_battalion_warfare.png", threshold=0.85)
        if not pos_battalion:
            log.error("No se encontró btn_battalion_warfare.")
            return False

        self.device.tap(pos_battalion[0], pos_battalion[1])
        self.wait_for_screen_stable(timeout=6, interval=0.5)

        screen = self.device.screenshot()
        resultado = self.vision.find_any(screen, [
            "templates/alliance_war.png",
            "templates/war_of_the_realms.png",
            "templates/btn_raid_map.png",
        ], threshold=0.85)

        if resultado:
            log.info("[✓] Entrada exitosa al mapa.")
            return True

        log.error("No se pudo entrar al mapa.")
        return False

    def _entrar_raid(self) -> bool:
        log.info("[→] Buscando botón de raids...")
        if not self._ir_al_mapa_guerra():
            return False

        screen = self.device.screenshot()
        pos_raid = self.vision.find_any(screen, [
            "templates/btn_raid_map.png",
            "templates/btn_siege.png",
            "templates/btn_raid.png",
        ], threshold=0.85)

        if not pos_raid:
            log.error("No se encontró el botón de raids.")
            return False

        self.device.tap(pos_raid[1], pos_raid[2])
        self.wait_for_screen_stable(timeout=5, interval=0.5)
        log.info("[✓] Entrando a raids...")
        return True

    # ── Crear party ──
    def _crear_party(self) -> bool:
        log.info("[→] Creando party...")

        pos_create = self.wait_for_template(
            "templates/btn_siege_create.png",
            timeout=10,
            threshold=0.85,
            interval=0.5
        )
        if not pos_create:
            log.error("No se encontró botón Create tras 10s.")
            return False

        self.device.tap(pos_create[0], pos_create[1])

        pos_confirm = self.wait_for_template(
            "templates/btn_siege_create_confirm.png",
            timeout=6,
            threshold=0.85,
            interval=0.3
        )
        if not pos_confirm:
            log.error("No se encontró confirmación de Create.")
            return False

        self.device.tap(pos_confirm[0], pos_confirm[1])

        pos_start_check = self.wait_for_template(
            "templates/btn_siege_start.png",
            timeout=8,
            threshold=0.85,
            interval=0.5
        )
        if pos_start_check:
            log.info("[✓] Party creada (botón Start visible).")
        else:
            log.warning("[!] No se confirmó visualmente la creación de party. Continuando...")

        return True

    # ── Iniciar raid ──
    def _iniciar_raid(self) -> bool:
        log.info("[→] Iniciando raid...")

        pos_start = self.wait_for_template(
            "templates/btn_siege_start.png",
            timeout=8,
            threshold=0.85,
            interval=0.5
        )
        if not pos_start:
            log.error("No se encontró botón Start Raid tras 8s.")
            return False

        self.device.tap(pos_start[0], pos_start[1])

        log.info("[⏳] Esperando inicio de batalla...")
        inicio = time.time()
        while time.time() - inicio < 15:
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, [
                "templates/btn_battle_skip.png",
                "templates/btn_battle_speed.png",
                "templates/victory_banner.png",
            ], threshold=0.75)
            if result:
                log.info("[✓] Batalla iniciada (elemento de combate detectado).")
                return True
            time.sleep(0.5)

        log.warning("[!] No se detectó inicio de batalla visualmente. Continuando...")
        return True

    # ── Esperar batalla ──
    def _esperar_batalla(self):
        log.info("[⏳] Esperando batalla...")
        timeout = 90
        inicio = time.time()

        while time.time() - inicio < timeout:
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, [
                "templates/btn_battle_skip.png",
                "templates/victory_banner.png",
                "templates/defeat_banner.png",
            ], threshold=0.80)

            if result:
                template, x, y = result

                if "skip" in template:
                    log.info("[→] Skip detectado")
                    self.device.tap(x, y)
                    time.sleep(0.8)
                    pos_ok = self.vision.find_template(
                        self.device.screenshot(), "templates/btn_skip_ok.png", threshold=0.80
                    )
                    if pos_ok:
                        log.info("[✓] Confirmando skip")
                        self.device.tap(pos_ok[0], pos_ok[1])
                    continue

                if "victory" in template:
                    log.info("[✓] Victoria detectada")
                    w, h = screen.size
                    self.device.tap(w // 2, h // 2)
                    time.sleep(0.8)

                    pos_rewards = self.wait_for_template(
                        "templates/raid_rewards.png", timeout=8, threshold=0.75, interval=0.5
                    )
                    if pos_rewards:
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

    # ── Volver a lista ──
    def _volver_a_lista(self):
        log.debug("[←] Volviendo a la lista...")
        self.cerrar_ventana()

        inicio = time.time()
        while time.time() - inicio < 8:
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, [
                "templates/raid_monster_brown.png",
                "templates/raid_monster_purple.png",
                "templates/raid_monster_yellow.png",
                "templates/raid_monster_turquoise.png",
                "templates/raid_monster_blue.png",
            ], threshold=0.6)
            if result:
                log.debug("[✓] Lista de raids visible.")
                return
            time.sleep(0.5)

        log.warning("[!] No se confirmó visualmente la lista. Continuando...")

    # ═══════════════════════════════════════════════════════════
    # EJECUCIÓN PRINCIPAL - CON OPTIMIZACIÓN DE REPETICIÓN
    # ═══════════════════════════════════════════════════════════
    def execute(self) -> bool:
        self._sid = getattr(self, "_sid", None)
        cuenta_label = self.account.name if self.account else "Prueba"

        log.info("=" * 55)
        log.info("  Módulo de Asedios/Raids - %s", cuenta_label)
        log.info("=" * 55)

        if not self._entrar_raid():
            return False

        time.sleep(1.5)
        monstruos = self._analizar_monstruos()

        if not monstruos:
            log.error("No se detectaron monstruos válidos")
            return False

        plan = self._generar_plan_batallas(monstruos)
        if not plan:
            log.error("No se pudo generar plan de batallas")
            return False

        log.info("=" * 45)
        log.info("Plan: %d batallas", len(plan))
        for i, m in enumerate(plan):
            log.info("  Batalla %d: %s (Poder: %d)", i + 1, MONSTER_TYPES[m["tipo"]]["name"], m["power"])
        log.info("=" * 45)

        for i, monstruo in enumerate(plan):
            log.info("=" * 45)
            log.info("  Batalla %d/%d", i + 1, len(plan))
            log.info("=" * 45)

            # ═══════════════════════════════════════════════════
            # OPTIMIZACIÓN: ¿El anterior era del mismo tipo?
            # Si sí → intentar repetir directo sin volver a lista
            # Si no → navegación normal desde la lista
            # ═══════════════════════════════════════════════════
            es_mismo_tipo_que_anterior = (
                i > 0 and plan[i - 1]["tipo"] == monstruo["tipo"]
            )

            if es_mismo_tipo_que_anterior:
                # ── INTENTO RÁPIDO: Create ya visible ──
                log.info("[⚡] Mismo tipo que anterior. Buscando Create directo...")
                pos_create_wait = self.wait_for_template(
                    "templates/btn_siege_create.png",
                    timeout=5,       # Solo 5s: si no está, algo salió mal
                    threshold=0.80,
                    interval=0.4
                )
                if pos_create_wait:
                    log.info("[✓] Create encontrado directo. Repitiendo raid...")
                else:
                    # ── FALLBACK: Navegar desde lista ──
                    log.info("[!] Create no visible. Navegando desde lista...")
                    self._volver_a_lista()
                    self.device.tap(monstruo["enter_x"], monstruo["y"])
                    pos_create_wait = self.wait_for_template(
                        "templates/btn_siege_create.png",
                        timeout=12,
                        threshold=0.80,
                        interval=0.5
                    )
                    if not pos_create_wait:
                        log.error("No apareció pantalla de party para batalla %d.", i + 1)
                        self.cerrar_ventana()
                        time.sleep(2)
                        self._volver_a_lista()
                        continue
            else:
                # ── NAVEGACIÓN NORMAL: Primera batalla o tipo diferente ──
                self.device.tap(monstruo["enter_x"], monstruo["y"])
                log.info("[⏳] Esperando pantalla de creación de party...")
                pos_create_wait = self.wait_for_template(
                    "templates/btn_siege_create.png",
                    timeout=12,
                    threshold=0.80,
                    interval=0.5
                )
                if not pos_create_wait:
                    log.error("No apareció pantalla de party para batalla %d.", i + 1)
                    self.cerrar_ventana()
                    time.sleep(2)
                    self._volver_a_lista()
                    continue

            # ── CREAR + INICIAR + ESPERAR (igual para todos) ──
            if not self._crear_party():
                log.error("Fallo creando party en batalla %d.", i + 1)
                self.cerrar_ventana()
                self._volver_a_lista()
                continue

            if not self._iniciar_raid():
                log.error("Fallo iniciando raid en batalla %d.", i + 1)
                self.cerrar_ventana()
                self._volver_a_lista()
                continue

            self._esperar_batalla()

            # ═══════════════════════════════════════════════════
            # DECISIÓN: ¿Volver a lista o no?
            # Solo volver si el SIGUIENTE es de tipo DIFERENTE
            # Si es mismo tipo, quedarse para repetir directo
            # ═══════════════════════════════════════════════════
            if i < len(plan) - 1:
                siguiente_tipo = plan[i + 1]["tipo"]
                if siguiente_tipo != monstruo["tipo"]:
                    log.info("[←] Siguiente es tipo diferente. Volviendo a lista...")
                    self._volver_a_lista()
                else:
                    log.info("[⚡] Siguiente es mismo tipo (%s). No retrocedemos.",
                             MONSTER_TYPES[siguiente_tipo]["name"])
                    # No hacemos nada: la próxima iteración buscará Create directo

        log.info("[←] Volviendo al home...")
        self.cerrar_ventana()
        time.sleep(1.5)
        log.info("  Módulo de raids completado")
        return True