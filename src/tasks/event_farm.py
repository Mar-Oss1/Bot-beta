import time
from core.logger import get_logger
from tasks.base_task import BaseTask

log = get_logger("event_farm")


class EventFarm(BaseTask):
    def __init__(self, device, vision, account=None, db=None):
        super().__init__(device, vision, account, db)
        # Banderas para ejecutar clics de auto-batalla y velocidad solo 1 vez por cuenta
        self._auto_battle_activado = False
        self._speed_activado = False

    def handle_victory_sequence(self):
        log.info("   [✨] Victoria detectada. Limpiando...")
        for _ in range(3):
            self.device.tap(2200, 500)
            time.sleep(0.8)
        self.wait_for_screen_stable(timeout=5, interval=0.5, stability_threshold=0.98, min_stable_checks=2)

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
                time.sleep(1.5)

        for _ in range(8):
            arrow = self.vision.find_template(self.device.screenshot(), "templates/btn_arrow_team.png", threshold=0.8)
            if arrow:
                self.device.tap(int(arrow[0]), int(arrow[1]))
                pos_label = self.wait_for_template("templates/label_team_10.png", timeout=2, threshold=0.85,
                                                   interval=0.3)
                if pos_label:
                    log.info("  [✓] Team 10 detectado tras scroll.")
                    return True
            else:
                break

        log.warning("  [!] No se pudo llegar a Team 10.")
        return False

    def check_and_recover_mana(self):
        pos_insuficiente = self.wait_for_template("templates/mana_insuficiente.png", timeout=3, threshold=0.8,
                                                  interval=0.5)
        if not pos_insuficiente:
            return False

        log.info("  [💧] ¡Aviso de maná detectado! Usando botón de restauración...")
        screen = self.device.screenshot()
        pos_ok = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.8)
        self.device.tap(int(pos_ok[0] if pos_ok else pos_insuficiente[0]),
                        int(pos_ok[1] if pos_ok else pos_insuficiente[1]))

        time.sleep(1.5)
        pos_checkbox = self.vision.find_template(self.device.screenshot(), "templates/checkbox_mana.png", threshold=0.8)
        if pos_checkbox:
            log.info("   [+] Activando uso automático de pociones (Checkbox)...")
            self.device.tap(int(pos_checkbox[0]), int(pos_checkbox[1]))
            time.sleep(1)

        self.cerrar_ventana()
        return True

    def detectar_costo_y_ejecutar(self):
        screen = self.device.screenshot()
        log.debug("  [DEBUG] Buscando etapas disponibles...")

        cleared_ys = {c[1] for c in self.vision.find_all_templates(screen, "templates/cleared.png", threshold=0.8)}
        esta_cleared = lambda y: any(abs(y - cy) < 50 for cy in cleared_ys)

        posiciones_historia = sorted(self.vision.find_all_templates(screen, "templates/cost_0.png", threshold=0.8),
                                     key=lambda p: p[1])
        for pos in posiciones_historia:
            if not esta_cleared(pos[1]):
                log.info("  ✅ Etapa de HISTORIA disponible en (%d, %d)", pos[0], pos[1])
                return pos, "cost_0.png"

        for costo_template in ["cost_80.png", "cost_60.png", "cost_50.png"]:
            posiciones = sorted(self.vision.find_all_templates(screen, f"templates/{costo_template}", threshold=0.7),
                                key=lambda p: p[1])
            for pos in posiciones:
                if not esta_cleared(pos[1]):
                    log.info("  ✅ Etapa de BATALLA disponible: %s en (%d, %d)", costo_template, pos[0], pos[1])
                    return pos, costo_template

        return None, None

    def execute(self):
        log.info("\n [🎃] Iniciando farmeo infinito...")
        max_intentos = 100
        for intentos in range(max_intentos):
            pos, tipo_costo = self.detectar_costo_y_ejecutar()
            if not pos:
                log.info("  [✅] No hay más etapas disponibles. Farmeo terminado.")
                break

            self.execute_historia(pos) if tipo_costo == "cost_0.png" else self.execute_batalla(pos)
            time.sleep(1.5)
        else:
            log.warning("  [⚠️] Límite de %d intentos alcanzado. Deteniendo farmeo.", max_intentos)

    def execute_historia(self, pos):
        log.info("  [📖] Etapa de Historia detectada. Entrando en modo Skip...")
        self.device.tap(int(pos[0]), int(pos[1]))

        inicio = time.time()
        while time.time() - inicio < 20:
            screen = self.device.screenshot()
            if self.vision.find_template(screen, "templates/victory_banner.png", threshold=0.8):
                self.handle_victory_sequence()
                return

            p_skip = self.vision.find_template(screen, "templates/btn_skip_scene.png", threshold=0.8)
            if p_skip:
                self.device.tap(int(p_skip[0]), int(p_skip[1]))
                time.sleep(1)
                p_ok = self.wait_for_template("templates/btn_skip_ok.png", timeout=3, threshold=0.8)
                if p_ok:
                    self.device.tap(int(p_ok[0]), int(p_ok[1]))
                    self.wait_for_screen_stable(timeout=8, interval=0.5, stability_threshold=0.98, min_stable_checks=2)
                    return
            time.sleep(0.5)

        log.warning("  [⚠️] Timeout en historia. Forzando limpieza...")
        self.clear_loot_windows()

    def execute_batalla(self, pos):
        log.info("  [⚔️] Etapa de Batalla detectada. Preparando combate...")
        self.device.tap(int(pos[0]), int(pos[1]))
        time.sleep(1.5)

        if self.check_and_recover_mana():
            self.device.tap(int(pos[0]), int(pos[1]))
            time.sleep(1.5)

        if not self.ensure_team_10():
            log.error("  [❌] No se pudo seleccionar Team 10. Abortando batalla.")
            self.cerrar_ventana()
            return

        # NUEVO: Activar Checkbox de Auto-Batalla una sola vez por cuenta
        if not self._auto_battle_activado:
            pos_cb = self.vision.find_template(self.device.screenshot(), "templates/checkbox_mana.png", threshold=0.8)
            if pos_cb:
                log.info("  [+] Activando Checkbox de Batalla por primera vez...")
                self.device.tap(int(pos_cb[0]), int(pos_cb[1]))
                time.sleep(0.8)
            self._auto_battle_activado = True  # Se marca para ignorarlo en el siguiente combate

        pos_start = self.wait_for_template("templates/btn_start_battle.png", timeout=5, threshold=0.8, interval=0.5)
        if pos_start:
            self.device.tap(int(pos_start[0]), int(pos_start[1]))
            time.sleep(1)
            if self.check_and_recover_mana():
                pos_start_again = self.wait_for_template("templates/btn_start_battle.png", timeout=3, threshold=0.8)
                if pos_start_again:
                    self.device.tap(int(pos_start_again[0]), int(pos_start_again[1]))
            self.wait_for_screen_stable(timeout=5, interval=0.5, stability_threshold=0.95, min_stable_checks=2)
        else:
            log.warning("  [⚠️] No se encontró botón Start. ¿Ya en combate?")
            self.clear_loot_windows()

        log.info("  [⏳] Esperando fin de batalla...")
        inicio_batalla = time.time()
        timeout_batalla = 300

        while time.time() - inicio_batalla < timeout_batalla:
            screen = self.device.screenshot()

            # NUEVO: Activar Velocidad una sola vez al inicio del combate
            if not self._speed_activado:
                p_speed = self.vision.find_template(screen, "templates/btn_battle_speed.png", threshold=0.7)
                if p_speed:
                    log.info("  [+] Activando Aceleración de Batalla por primera vez...")
                    self.device.tap(int(p_speed[0]), int(p_speed[1]))
                    self._speed_activado = True
                    time.sleep(0.8)
                    continue

            if self.vision.find_template(screen, "templates/victory_banner.png", threshold=0.8):
                self.handle_victory_sequence()
                return

            if self.vision.find_template(screen, "templates/defeat_banner.png", threshold=0.8):
                log.info("  [💀] Derrota detectada. Saliendo...")
                self.device.tap(1000, 1000)
                time.sleep(2)
                self.clear_loot_windows()
                return

            p1 = self.vision.find_template(screen, "templates/btn_skip_scene.png", threshold=0.8)
            if p1:
                self.device.tap(int(p1[0]), int(p1[1]))
                time.sleep(1)
                ok = self.vision.find_template(screen, "templates/btn_skip_ok.png", threshold=0.8)
                if ok:
                    self.device.tap(int(ok[0]), int(ok[1]))
                time.sleep(1)
                continue

            time.sleep(0.8)

        log.warning("  [⚠️] Timeout de batalla (%d segundos). Forzando salida.", timeout_batalla)
        self.clear_loot_windows()