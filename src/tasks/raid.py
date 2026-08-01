# tasks/raid.py
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

# ──────────────────────────────────────────
# CONFIGURACIÓN DE MONSTRUOS
# ──────────────────────────────────────────
MONSTER_TYPES = {
    "brown": {
        "template": "templates/raid_monster_brown.png",
        "priority": 1,
        "resource": "Green Potions (Character)",
        "name": "Café"
    },
    "purple": {
        "template": "templates/raid_monster_purple.png",
        "priority": 2,
        "resource": "Minerals + Fruit",
        "name": "Morado"
    },
    "yellow": {
        "template": "templates/raid_monster_yellow.png",
        "priority": 3,
        "resource": "Blue Potions (Weapon)",
        "name": "Amarillo"
    },
    "turquoise": {
        "template": "templates/raid_monster_turquoise.png",
        "priority": 4,
        "resource": "Minerals",
        "name": "Turquesa"
    },
    "blue": {
        "template": "templates/raid_monster_blue.png",
        "priority": 5,
        "resource": "Minerals",
        "name": "Azul"
    },
}

MONSTER_POSITIONS = [
    {"y": 260, "icon_x": 1075, "power_x": 1250, "enter_x": 1775, "icon_y_offset": 0},
    {"y": 410, "icon_x": 1075, "power_x": 1250, "enter_x": 1775, "icon_y_offset": 0},
    {"y": 550, "icon_x": 1075, "power_x": 1250, "enter_x": 1775, "icon_y_offset": 0},
    {"y": 705, "icon_x": 1075, "power_x": 1250, "enter_x": 1775, "icon_y_offset": 0},
    {"y": 855, "icon_x": 1075, "power_x": 1250, "enter_x": 1775, "icon_y_offset": 0},
]

ICON_HALF_W = 70
ICON_HALF_H = 70

POWER_HALF_W_LEFT = 80
POWER_HALF_W_RIGHT = 150
POWER_HALF_H = 20


class Raid(BaseTask):
    def __init__(self, device, vision, account, db):
        super().__init__(device, vision, account, db)
        self._sid = None

    # ---- Sobrescribimos cerrar_ventana para que solo haga un intento ----
    def cerrar_ventana(self, screen=None):
        """Cierra la ventana actual con un solo intento (X, back o back físico)."""
        if screen is None:
            screen = self.device.screenshot()
        # Primero intentar con X
        pos = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
        if pos:
            self.device.tap(pos[0], pos[1])
            time.sleep(1.5)
            return
        # Si no X, intentar con botón back de la UI
        pos = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.85)
        if pos:
            self.device.tap(pos[0], pos[1])
            time.sleep(1.5)
            return
        # Fallback: back físico
        self.device.d.press("back")
        time.sleep(1.5)

    # ---- clear_loot_windows mejorado para raids (ya no se usa directamente en victoria) ----
    def clear_loot_windows(self):
        """
        Limpia cualquier ventana de loot/recompensa que pueda haber quedado abierta.
        Cada tipo de ventana se maneja con una acción distinta.
        """
        # Mapeo de plantilla -> acción (función lambda o descripción)
        acciones = {
            "templates/victory_banner.png": lambda: self.device.tap(300, 100),
            "templates/defeat_banner.png": lambda: self.device.tap(300, 100),
            "templates/raid_rewards.png": self._cerrar_rewards,
            "templates/rewards.png": self._cerrar_rewards,
            "templates/pantalla_loot.png": lambda: self.device.tap(300, 100),
        }

        for _ in range(6):  # hasta 6 intentos
            screen = self.device.screenshot()
            encontrado = False
            for template, accion in acciones.items():
                pos = self.vision.find_template(screen, template, threshold=0.80)
                if pos:
                    log.debug(f"Ventana de loot detectada: {template}")
                    accion()
                    time.sleep(1.5)
                    encontrado = True
                    break  # salir del for de plantillas para repetir el while
            if not encontrado:
                break  # no hay más ventanas
            time.sleep(0.5)

    def _cerrar_rewards(self):
        """Cierra una ventana de recompensas (raid_rewards o rewards) usando el botón X."""
        screen = self.device.screenshot()
        pos_x = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
        if pos_x:
            self.device.tap(pos_x[0], pos_x[1])
        else:
            # Fallback: tocar esquina superior derecha (para resolución 2560x1440)
            self.device.tap(2400, 200)
        time.sleep(1)

    # ---- Funciones de análisis (igual que la versión que funcionaba) ----
    def _leer_poder(self, screenshot, x: int, y: int, power_y_offset: int = 0) -> int:
        """Extrae el poder del monstruo usando OCR mejorado con ROI dinámico."""
        try:
            screen_cv = self.vision.pil_to_cv2(screenshot)
            h, w = screen_cv.shape[:2]

            # ROI centrado en x, con margen horizontal amplio (200 px a cada lado)
            offset = 200
            x1 = max(0, x - offset + 75)
            x2 = min(w, x + offset)
            y1 = max(0, y - 20)
            y2 = min(h, y + 20)

            roi = screen_cv[y1:y2, x1:x2]

            # Guardar debug
            debug_dir = "screenshots/debug_raid"
            os.makedirs(debug_dir, exist_ok=True)
            cv2.imwrite(f"{debug_dir}/power_y{y}.png", roi)

            # Escalar la imagen para mejorar OCR (factor 2x)
            escala = 2
            roi_escalada = cv2.resize(roi, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)

            gray = cv2.cvtColor(roi_escalada, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            texto = pytesseract.image_to_string(
                thresh,
                config="--psm 7 -c tessedit_char_whitelist=0123456789.,KMkm"
            )

            texto = texto.strip()
            log.debug("  Texto OCR: '%s'", texto)

            texto_limpio = re.sub(r'[^\d.,KMkm]', '', texto)

            if not texto_limpio:
                log.warning("  No se pudo parsear el poder: '%s'", texto)
                return 0

            if 'M' in texto_limpio or 'm' in texto_limpio:
                numeros = re.findall(r'[\d.]+', texto_limpio)
                if numeros:
                    poder = int(float(numeros[0]) * 1_000_000)
                    log.debug("  Poder leído: %d (M)", poder)
                    return poder

            elif 'K' in texto_limpio or 'k' in texto_limpio:
                numeros = re.findall(r'[\d.]+', texto_limpio)
                if numeros:
                    poder = int(float(numeros[0]) * 1_000)
                    log.debug("  Poder leído: %d (K)", poder)
                    return poder

            else:
                numeros = re.sub(r'[^\d]', '', texto_limpio)
                if numeros and len(numeros) <= 9:
                    poder = int(numeros)
                    log.debug("  Poder leído: %d", poder)
                    return poder

            log.warning("  No se pudo parsear el poder: '%s'", texto)
            return 0

        except Exception as e:
            log.error("Error leyendo poder: %s", e)
            return 0

    def _detectar_tipo_monstruo(self, screenshot, y: int, icon_x: int, icon_y_offset: int = 0) -> tuple:
        """Detecta el tipo de monstruo usando template matching, centrado en icon_x real."""
        screen_cv = self.vision.pil_to_cv2(screenshot)
        h, w = screen_cv.shape[:2]

        icon_y = y + icon_y_offset
        x1 = max(0, icon_x - ICON_HALF_W)
        x2 = min(w, icon_x + ICON_HALF_W)
        y1 = max(0, icon_y - ICON_HALF_H)
        y2 = min(h, icon_y + ICON_HALF_H)

        roi_cv = screen_cv[y1:y2, x1:x2]

        debug_dir = "screenshots/debug_raid"
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(f"{debug_dir}/monster_y{y}.png", roi_cv)

        roi_gray = cv2.cvtColor(roi_cv, cv2.COLOR_BGR2GRAY)

        mejor_tipo = None
        mejor_confidence = 0

        for tipo, config in MONSTER_TYPES.items():
            ruta = os.path.join(PROJECT_ROOT, config["template"])
            template = cv2.imread(ruta, cv2.IMREAD_GRAYSCALE)

            if template is None:
                continue
            if template.shape[0] > roi_gray.shape[0] or template.shape[1] > roi_gray.shape[1]:
                continue

            try:
                res = cv2.matchTemplate(roi_gray, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)

                if max_val > 0.65 and max_val > mejor_confidence:
                    mejor_confidence = max_val
                    mejor_tipo = tipo
                    log.debug("    %s: %.2f", config["name"], max_val)
            except cv2.error:
                continue

        if mejor_tipo:
            log.info("  ✓ Tipo: %s (%.2f)", MONSTER_TYPES[mejor_tipo]["name"], mejor_confidence)
            return (mejor_tipo, mejor_confidence)

        log.warning("   No detectado y=%d → ROI: x[%d:%d] y[%d:%d]. Revisa %s",
                    y, x1, x2, y1, y2, debug_dir)
        return (None, 0)

    def _analizar_monstruos(self) -> list:
        """Analiza la lista de monstruos y retorna los detectados con poder."""
        screen = self.device.screenshot()
        monstruos = []

        for i, pos in enumerate(MONSTER_POSITIONS):
            log.info("  Analizando monstruo %d...", i + 1)

            tipo, confidence = self._detectar_tipo_monstruo(
                screen, pos["y"], pos["icon_x"], pos.get("icon_y_offset", 0)
            )

            if not tipo:
                log.warning("  No se pudo detectar el tipo del monstruo %d", i + 1)
                continue

            poder = self._leer_poder(
                screen, pos["power_x"], pos["y"], pos.get("power_y_offset", 0)
            )

            if poder == 0:
                log.warning("  No se pudo leer el poder del monstruo %d", i + 1)
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

        # Ordenar por prioridad (menor número = mayor prioridad) y luego por poder descendente
        monstruos.sort(key=lambda m: (m["priority"], -m["power"]))

        return monstruos

    def _generar_plan_batallas(self, monstruos: list) -> list:
        if not monstruos:
            return []

        monstruos.sort(
            key=lambda m: (m["priority"], -m["power"])
        )

        max_priority = monstruos[0]["priority"]

        mismos_tipo = [
            m for m in monstruos
            if m["priority"] == max_priority
        ]

        log.info("-" * 45)
        log.info(
            "Monstruos de máxima prioridad encontrados: %d",
            len(mismos_tipo)
        )
        log.info("-" * 45)

        plan = []

        # 3 o más monstruos de máxima prioridad
        if len(mismos_tipo) >= 3:

            plan = mismos_tipo[:3]

            log.info(
                "Plan: atacar a los 3 monstruos más fuertes de prioridad %d",
                max_priority
            )

        # 2 monstruos de máxima prioridad
        elif len(mismos_tipo) == 2:

            plan = [
                mismos_tipo[0],
                mismos_tipo[0],
                mismos_tipo[1]
            ]

            log.info(
                "Plan: 2 ataques al más fuerte (%d), 1 ataque al segundo (%d)",
                mismos_tipo[0]["power"],
                mismos_tipo[1]["power"]
            )

        # 1 monstruo de máxima prioridad
        elif len(mismos_tipo) == 1:

            plan = [
                mismos_tipo[0],
                mismos_tipo[0],
                mismos_tipo[0]
            ]

            log.info(
                "Plan: 3 ataques al monstruo de máxima prioridad (%d)",
                mismos_tipo[0]["power"]
            )

        return plan

    # ---- Navegación al mapa de Battalion Warfare ----
    def _ir_al_mapa_guerra(self) -> bool:
        """
        Navega desde el Home al mapa de Battalion Warfare (donde están raids, arena, guerras).
        Si ya está en el mapa, retorna True sin hacer nada.
        """
        log.info("  [🗺️] Navegando al mapa de Battalion Warfare...")

        # Primero verificar si ya estamos en el mapa de warfare
        screen = self.device.screenshot()
        resultado = self.vision.find_any(
            screen,
            [
                "templates/alliance_war.png",
                "templates/war_of_the_realms.png",
                "templates/btn_raid_map.png",  # Si vemos el botón de raids, ya estamos dentro
            ],
            threshold=0.85
        )

        if resultado:
            log.info("  [✓] Ya estamos en el mapa de Battalion Warfare.")
            return True

        # Si no estamos, buscar el botón de entrada en el Home
        pos_battalion = self.vision.find_template(
            screen,
            "templates/btn_battalion_warfare.png",
            threshold=0.85
        )

        if not pos_battalion:
            log.error("No se encontró btn_battalion_warfare en el Home.")
            return False

        log.info("  [▶️] Tocando btn_battalion_warfare para entrar al mapa...")
        self.device.tap(pos_battalion[0], pos_battalion[1])
        self.wait_for_screen_stable(timeout=6, interval=0.5)

        # Verificar que entramos correctamente
        screen = self.device.screenshot()
        resultado = self.vision.find_any(
            screen,
            [
                "templates/alliance_war.png",
                "templates/war_of_the_realms.png",
                "templates/btn_raid_map.png",
            ],
            threshold=0.85
        )

        if resultado:
            log.info("  [✓] Entrada exitosa al mapa de Battalion Warfare.")
            return True
        else:
            log.error("No se pudo entrar al mapa de Battalion Warfare.")
            return False

    # ---- Entrar a raids (ahora con navegación previa) ----
    def _entrar_raid(self) -> bool:
        log.info("  [🗺️] Buscando botón de raids en el mapa...")

        # Primero asegurarnos de estar en el mapa de Battalion Warfare
        if not self._ir_al_mapa_guerra():
            log.error("No se pudo navegar al mapa de Battalion Warfare.")
            return False

        # Ahora buscar el botón de raids
        screen = self.device.screenshot()
        pos_raid = self.vision.find_any(
            screen,
            [
                "templates/btn_raid_map.png",
                "templates/btn_siege.png",
                "templates/btn_raid.png",
            ],
            threshold=0.85
        )

        if not pos_raid:
            log.error("No se encontró el botón de raids en el mapa")
            return False

        self.device.tap(pos_raid[1], pos_raid[2])
        # Esperar a que cargue la pantalla de raids (usamos un sleep fijo porque es carga pesada)
        time.sleep(4)

        log.info("  [✓] Entrando a raids...")
        return True

    def _crear_party(self) -> bool:
        log.info("  [👥] Creando party...")

        # Esperar a que aparezca el botón "Create"
        pos_create = self.wait_for_template(
            "templates/btn_siege_create.png",
            timeout=6,
            threshold=0.85
        )
        if not pos_create:
            log.error("No se encontró botón Create (pantalla principal)")
            return False

        self.device.tap(pos_create[0], pos_create[1])
        time.sleep(2)

        # Esperar a que aparezca el botón de confirmación
        pos_confirm = self.wait_for_template(
            "templates/btn_siege_create_confirm.png",
            timeout=4,
            threshold=0.85
        )
        if not pos_confirm:
            log.error("No se encontró botón Create (popup confirmación)")
            return False

        self.device.tap(pos_confirm[0], pos_confirm[1])
        # Esperar un poco a que se cree la party
        time.sleep(3)

        log.info("  [✓] Party creada")
        return True

    def _iniciar_raid(self) -> bool:
        log.info("  [⚔️] Iniciando raid...")

        # Esperar a que aparezca el botón "Start Raid"
        pos_start = self.wait_for_template(
            "templates/btn_siege_start.png",
            timeout=5,
            threshold=0.85
        )
        if not pos_start:
            log.error("No se encontró botón Start Raid")
            return False

        self.device.tap(pos_start[0], pos_start[1])
        # Pequeña pausa para que empiece la batalla
        time.sleep(2)

        log.info("  [✓] Raid iniciado")
        return True

    # ---- ESPERAR BATALLA (VERSIÓN CORREGIDA) ----
    def _esperar_batalla(self):
        """
        Espera a que termine la batalla.

        Flujo:
        Skip -> Victory/Defeat -> Cerrar banner -> Raid Rewards -> Cerrar reward -> Regresar
        """
        log.info("[ ] Esperando batalla...")

        timeout = 60
        inicio = time.time()

        while time.time() - inicio < timeout:

            screen = self.device.screenshot()

            # ----- SKIP -----
            pos_skip = self.vision.find_template(
                screen,
                "templates/btn_battle_skip.png",
                threshold=0.80
            )
            if pos_skip:
                log.info("[ ] Skip detectado")
                self.device.tap(pos_skip[0], pos_skip[1])
                time.sleep(1)

                screen = self.device.screenshot()
                pos_ok = self.vision.find_template(
                    screen,
                    "templates/btn_skip_ok.png",
                    threshold=0.80
                )
                if pos_ok:
                    log.info("[ ] Confirmando skip")
                    self.device.tap(pos_ok[0], pos_ok[1])

            # ----- VICTORIA -----
            screen = self.device.screenshot()
            if self.vision.find_template(
                    screen,
                    "templates/victory_banner.png",
                    threshold=0.80
            ):
                log.info("[✓] Victoria detectada")

                # Cerrar el banner de victoria tocando el centro de la pantalla
                screen = self.device.screenshot()
                h, w = screen.size[1], screen.size[0]  # PIL: (width, height)
                self.device.tap(w // 2, h // 2)
                time.sleep(1.5)

                log.info("[ ] Esperando Raid Rewards...")
                pos_rewards = self.wait_for_template(
                    "templates/raid_rewards.png",
                    timeout=5,
                    threshold=0.75,
                    interval=0.5,
                    log_progress=True
                )

                if pos_rewards:
                    log.info("[✓] Raid Rewards detectado")
                    time.sleep(1)
                    self.cerrar_ventana()
                    time.sleep(2)
                    self.clear_loot_windows()
                    log.info("[✓] Recompensas cerradas")
                    return
                else:
                    log.warning("[!] No se detectó Raid Rewards. Intentando limpieza forzada...")
                    self.clear_loot_windows()
                    return

            # ----- DERROTA -----
            screen = self.device.screenshot()
            if self.vision.find_template(
                    screen,
                    "templates/defeat_banner.png",
                    threshold=0.80
            ):
                log.info("[X] Derrota detectada")
                # Cerrar el banner de derrota
                self.device.tap(300, 100)
                time.sleep(2)
                self.clear_loot_windows()
                return

            time.sleep(0.5)

        # Timeout
        log.warning("[!] Timeout esperando resultado de batalla")
        self.clear_loot_windows()
        log.info("[✓] Batalla completada")

    # ---- VOLVER A LA LISTA (con espera inteligente) ----
    def _volver_a_lista(self):
        """Vuelve a la lista de monstruos cerrando la ventana actual y esperando a que cargue."""
        log.debug("  [⬅️] Volviendo a la lista...")
        self.cerrar_ventana()
        # Esperar a que la lista de monstruos se estabilice
        self.wait_for_screen_stable(timeout=5, interval=0.5)
        time.sleep(1)

    def execute(self) -> bool:
        self._sid = getattr(self, '_sid', None)
        cuenta_label = self.account.name if self.account else "Prueba"
        log.info("=" * 55)
        log.info("⚔️  Módulo de Asedios/Raids — %s", cuenta_label)
        log.info("=" * 55)

        # Entrar a raids (navega al mapa de Battalion Warfare primero)
        if not self._entrar_raid():
            return False

        # Analizar monstruos
        monstruos = self._analizar_monstruos()
        if not monstruos:
            log.error("No se detectaron monstruos válidos")
            return False

        # Generar plan (siempre 3 batallas)
        plan = self._generar_plan_batallas(monstruos)
        if not plan:
            log.error("No se pudo generar el plan de batallas")
            return False

        log.info("━" * 45)
        log.info(" Plan de batallas generado: %d batallas", len(plan))
        for i, monstruo in enumerate(plan):
            log.info("  Batalla %d: %s (Poder: %d)",
                     i + 1,
                     MONSTER_TYPES[monstruo["tipo"]]["name"],
                     monstruo["power"])
        log.info("━" * 45)

        # Ejecutar batallas
        for i, monstruo in enumerate(plan):
            log.info("━" * 45)
            log.info("⚔️  Batalla %d/%d", i + 1, len(plan))
            log.info("━" * 45)

            # Tocar el monstruo seleccionado
            log.info("  [▶️] Entrando al monstruo...")
            self.device.tap(monstruo["enter_x"], monstruo["y"])
            time.sleep(3)  # Esperar a que cargue la pantalla de preparación

            if not self._crear_party():
                return False

            if not self._iniciar_raid():
                return False

            self._esperar_batalla()

            # Si no es la última batalla, volver a la lista
            if i < len(plan) - 1:
                self._volver_a_lista()

        # Volver al home
        log.info("  [🏠] Volviendo al home...")
        self.cerrar_ventana()
        time.sleep(3)

        log.info("✅ Módulo de raids completado exitosamente")
        return True
