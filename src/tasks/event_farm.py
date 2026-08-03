import time
from core.logger import get_logger

log = get_logger("event_farm")


class EventFarm:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    # ── Utilidades optimizadas ──
    def _cerrar_ventana(self, screen=None):
        if screen is None:
            screen = self.device.screenshot()
        result = self.vision.find_any(screen, [
            "templates/btn_cerrar_x.png",
            "templates/btn_back.png"
        ], threshold=0.8)
        if result:
            self.device.tap(result[1], result[2])
            time.sleep(1)
            return
        self.device.d.press("back")
        time.sleep(1)

    def _clear_loot_windows(self):
        loot_templates = [
            "templates/victory_banner.png",
            "templates/defeat_banner.png",
            "templates/rewards.png",
            "templates/level_up.png",
        ]
        for _ in range(5):
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, loot_templates, threshold=0.8)
            if result:
                self.device.tap(300, 100)
                time.sleep(1)
            else:
                break

    # ── Secuencia de victoria ──
    def handle_victory_sequence(self):
        log.info("   [✨] Victoria detectada. Limpiando...")
        for _ in range(3):
            self.device.tap(2200, 500)
            time.sleep(0.6)
        self.vision.wait_for_screen_stable(
            self.device.screenshot,
            timeout=5, interval=0.5, stability_threshold=0.98, min_stable_checks=2
        )

    def ensure_team_10(self):
        log.info("  [🛡️] Verificando Team 10...")
        for _ in range(2):
            screen = self.device.screenshot()
            if self.vision.find_template(screen, "templates/label_team_10.png", threshold=0.85):
                log.info("  [✓] Team 10 detectado.")
                return True
            arrow = self.vision.find_template(screen, "templates/btn_arrow_team.png", threshold=0.8)
            if arrow:
                self.device.tap(int(arrow[0]), int(arrow[1]))
                time.sleep(1.2)

        for _ in range(8):
            arrow = self.vision.wait_for_template(
                self.device.screenshot,
                "templates/btn_arrow_team.png",
                timeout=2, threshold=0.8, interval=0.3
            )
            if arrow:
                self.device.tap(int(arrow[0]), int(arrow[1]))
                pos_label = self.vision.wait_for_template(
                    self.device.screenshot,
                    "templates/label_team_10.png",
                    timeout=2, threshold=0.85, interval=0.3
                )
                if pos_label:
                    log.info("  [✓] Team 10 detectado tras scroll.")
                    return True
            else:
                break

        log.warning("  [!] No se pudo llegar a Team 10.")
        return False

    def check_and_recover_mana(self):
        pos_insuficiente = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/mana_insuficiente.png",
            timeout=3, threshold=0.8, interval=0.5
        )
        if not pos_insuficiente:
            return False

        log.info("  [💧] ¡Aviso de maná detectado! Usando botón de restauración...")
        screen = self.device.screenshot()
        pos_ok = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.8)
        if pos_ok:
            self.device.tap(int(pos_ok[0]), int(pos_ok[1]))
        else:
            self.device.tap(int(pos_insuficiente[0]), int(pos_insuficiente[1]))

        time.sleep(1.2)
        screen_pot = self.device.screenshot()
        pos_checkbox = self.vision.find_template(screen_pot, "templates/checkbox_mana.png", threshold=0.8)
        if pos_checkbox:
            log.info("   [+] Activando uso automático de pociones...")
            self.device.tap(int(pos_checkbox[0]), int(pos_checkbox[1]))
            time.sleep(0.8)

        self._cerrar_ventana(self.device.screenshot())
        return True

    # ── Detección de etapas (ya estaba bien optimizado) ──
    def detectar_costo_y_ejecutar(self):
        screen = self.device.screenshot()
        log.debug("  [DEBUG] Buscando etapas disponibles...")

        cleared_positions = self.vision.find_all_templates(
            screen, "templates/cleared.png", threshold=0.8
        )
        cleared_ys = {c[1] for c in cleared_positions}
        log.debug("  [DEBUG] Cleared encontrados: %d", len(cleared_ys))

        def esta_cleared(y):
            return any(abs(y - cy) < 50 for cy in cleared_ys)

        # Historia primero
        posiciones_historia = self.vision.find_all_templates(
            screen, "templates/cost_0.png", threshold=0.85
        )
        posiciones_historia.sort(key=lambda p: p[1])
        for pos in posiciones_historia:
            if not esta_cleared(pos[1]):
                log.info("  ✅ Etapa de HISTORIA disponible en (%d, %d)", pos[0], pos[1])
                return pos, "cost_0.png"

        # Batallas
        for costo_template in ["cost_80.png", "cost_60.png", "cost_50.png"]:
            posiciones = self.vision.find_all_templates(
                screen, f"templates/{costo_template}", threshold=0.8
            )
            posiciones.sort(key=lambda p: p[1])
            for pos in posiciones:
                if not esta_cleared(pos[1]):
                    log.info("  ✅ Etapa de BATALLA: %s en (%d, %d)", costo_template, pos[0], pos[1])
                    return pos, costo_template

        log.debug("  [DEBUG] No se encontraron etapas disponibles")
        return None, None

    # ── Bucle principal ──
    def execute(self):
        log.info("\n [🎃] Iniciando farmeo infinito...")
        max_intentos = 100

        for intento in range(max_intentos):
            pos, tipo_costo = self.detectar_costo_y_ejecutar()
            if pos:
                if tipo_costo == "cost_0.png":
                    self.execute_historia(pos)
                else:
                    self.execute_batalla(pos)
                time.sleep(1.2)
            else:
                log.info("  [✅] No hay más etapas disponibles. Farmeo terminado.")
                return

        log.warning("  [⚠️] Límite de %d intentos alcanzado. Deteniendo farmeo.", max_intentos)

    # ── Historia (polling optimizado con find_any) ──
    def execute_historia(self, pos):
        log.info("  [📖] Etapa de Historia detectada. Entrando en modo Skip...")
        self.device.tap(int(pos[0]), int(pos[1]))

        inicio = time.time()
        while time.time() - inicio < 20:
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, [
                "templates/victory_banner.png",
                "templates/btn_skip_scene.png",
            ], threshold=0.8)

            if result:
                template, x, y = result
                if "victory" in template:
                    self.handle_victory_sequence()
                    return
                else:
                    self.device.tap(int(x), int(y))
                    time.sleep(0.8)
                    pos_ok = self.vision.wait_for_template(
                        self.device.screenshot,
                        "templates/btn_skip_ok.png",
                        timeout=3, threshold=0.8, interval=0.3
                    )
                    if pos_ok:
                        self.device.tap(int(pos_ok[0]), int(pos_ok[1]))
                        self.vision.wait_for_screen_stable(
                            self.device.screenshot,
                            timeout=8, interval=0.5, stability_threshold=0.98, min_stable_checks=2
                        )
                        return

            time.sleep(0.5)

        log.warning("  [⚠️] Timeout en historia. Forzando limpieza...")
        self._clear_loot_windows()

    # ── Batalla (polling optimizado con find_any) ──
    def execute_batalla(self, pos):
        log.info("  [⚔️] Etapa de Batalla detectada. Preparando combate...")
        self.device.tap(int(pos[0]), int(pos[1]))
        time.sleep(1.2)

        if self.check_and_recover_mana():
            self.device.tap(int(pos[0]), int(pos[1]))
            time.sleep(1.2)

        if not self.ensure_team_10():
            log.error("  [❌] No se pudo seleccionar Team 10. Abortando.")
            self._cerrar_ventana()
            return

        pos_start = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_start_battle.png",
            timeout=5, threshold=0.8, interval=0.5
        )
        if pos_start:
            self.device.tap(int(pos_start[0]), int(pos_start[1]))
            time.sleep(0.8)
            if self.check_and_recover_mana():
                pos_start_again = self.vision.wait_for_template(
                    self.device.screenshot,
                    "templates/btn_start_battle.png",
                    timeout=3, threshold=0.8
                )
                if pos_start_again:
                    self.device.tap(int(pos_start_again[0]), int(pos_start_again[1]))

            self.vision.wait_for_screen_stable(
                self.device.screenshot,
                timeout=5, interval=0.5, stability_threshold=0.95, min_stable_checks=2
            )
        else:
            log.warning("  [⚠️] No se encontró botón Start.")
            self._clear_loot_windows()
            return

        log.info("  [⏳] Esperando fin de batalla...")
        inicio_batalla = time.time()
        timeout_batalla = 180

        while time.time() - inicio_batalla < timeout_batalla:
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, [
                "templates/victory_banner.png",
                "templates/defeat_banner.png",
                "templates/btn_skip_scene.png",
            ], threshold=0.8)

            if result:
                template, x, y = result
                if "victory" in template:
                    self.handle_victory_sequence()
                    return
                elif "defeat" in template:
                    log.info("  [💀] Derrota detectada. Saliendo...")
                    self.device.tap(1000, 1000)
                    time.sleep(1.5)
                    self._clear_loot_windows()
                    return
                else:  # skip
                    self.device.tap(int(x), int(y))
                    time.sleep(0.8)
                    ok = self.vision.find_template(screen, "templates/btn_skip_ok.png", threshold=0.8)
                    if ok:
                        self.device.tap(int(ok[0]), int(ok[1]))
                    time.sleep(0.8)
                    continue

            time.sleep(0.7)

        log.warning("  [⚠️] Timeout de batalla (%ds). Forzando salida.", timeout_batalla)
        self._clear_loot_windows()