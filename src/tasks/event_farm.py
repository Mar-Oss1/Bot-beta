import time
from core.logger import get_logger
from tasks.base_task import BaseTask

log = get_logger("event_farm")


class EventFarm(BaseTask):
    def __init__(self, device, vision, account=None, db=None):
        super().__init__(device, vision, account, db)
        self._auto_battle_activado = False
        self._speed_activado = False
        self._team_10_verificado = False

    def handle_victory_sequence(self):
        log.info("   [✨] Victoria detectada. Limpiando...")
        for _ in range(3):
            self.device.tap(2200, 500)
            time.sleep(0.45)
        self.wait_for_screen_stable(timeout=4, interval=0.35, stability_threshold=0.98, min_stable_checks=2)

    def ensure_team_10(self) -> bool:
        if self._team_10_verificado:
            return True

        log.info("  [🛡️] Verificando Team 10...")
        for _ in range(10):
            screen_gray = self.vision.to_gray(self.device.screenshot())
            if self.vision.find_template(screen_gray, "templates/label_team_10.png", threshold=0.85, zona="COMPLETA"):
                log.info("  [✓] Team 10 confirmado.")
                self._team_10_verificado = True
                return True

            arrow = self.vision.find_template(screen_gray, "templates/btn_arrow_team.png", threshold=0.8, zona="COMPLETA")
            if arrow:
                self.device.tap(int(arrow[0]), int(arrow[1]))
                time.sleep(0.55)
            else:
                break

        log.warning("  [!] No se pudo llegar a Team 10.")
        return False

    def check_and_recover_mana(self) -> bool:
        pos_insuficiente = self.wait_for_template(
            "templates/mana_insuficiente.png", timeout=2.0, threshold=0.8, interval=0.2, zona="CENTRO"
        )
        if not pos_insuficiente:
            return False

        log.info("  [💧] ¡Aviso de maná detectado! Restaurando...")
        screen = self.device.screenshot()
        pos_ok = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.8, zona="CENTRO")
        target = pos_ok if pos_ok else pos_insuficiente
        self.device.tap(int(target[0]), int(target[1]))

        time.sleep(0.8)
        pos_checkbox = self.vision.find_template(
            self.device.screenshot(), "templates/checkbox_mana.png", threshold=0.8, zona="CENTRO"
        )
        if pos_checkbox:
            self.device.tap(int(pos_checkbox[0]), int(pos_checkbox[1]))
            time.sleep(0.5)

        self.cerrar_ventana()
        return True

    def detectar_costo_y_ejecutar(self):
        # 1 sola conversión a gris para buscar los 5 templates de etapas
        screen_gray = self.vision.to_gray(self.device.screenshot())

        cleared_ys = {
            c[1] for c in self.vision.find_all_templates(
                screen_gray, "templates/cleared.png", threshold=0.8, zona="COMPLETA"
            )
        }
        esta_cleared = lambda y: any(abs(y - cy) < 50 for cy in cleared_ys)

        posiciones_historia = sorted(
            self.vision.find_all_templates(screen_gray, "templates/cost_0.png", threshold=0.8, zona="COMPLETA"),
            key=lambda p: p[1]
        )
        for pos in posiciones_historia:
            if not esta_cleared(pos[1]):
                log.info("  ✅ Etapa de HISTORIA disponible en (%d, %d)", pos[0], pos[1])
                return pos, "cost_0.png"

        for costo_template in ["cost_80.png", "cost_60.png", "cost_50.png"]:
            posiciones = sorted(
                self.vision.find_all_templates(
                    screen_gray, f"templates/{costo_template}", threshold=0.7, zona="COMPLETA"
                ),
                key=lambda p: p[1]
            )
            for pos in posiciones:
                if not esta_cleared(pos[1]):
                    log.info("  ✅ Etapa de BATALLA disponible: %s en (%d, %d)", costo_template, pos[0], pos[1])
                    return pos, costo_template

        return None, None

    def execute(self):
        log.info("\n [🎃] Iniciando farmeo de etapas...")
        max_intentos = 100
        for _ in range(max_intentos):
            pos, tipo_costo = self.detectar_costo_y_ejecutar()
            if not pos:
                log.info("  [✅] No hay más etapas disponibles. Farmeo terminado.")
                break

            if tipo_costo == "cost_0.png":
                self.execute_historia(pos)
            else:
                self.execute_batalla(pos)
            time.sleep(0.8)

    def execute_historia(self, pos):
        log.info("  [📖] Etapa de Historia detectada. Entrando en modo Skip...")
        self.device.tap(int(pos[0]), int(pos[1]))

        inicio = time.monotonic()
        while time.monotonic() - inicio < 20:
            screen_gray = self.vision.to_gray(self.device.screenshot())

            if self.vision.find_template(screen_gray, "templates/victory_banner.png", threshold=0.8, zona="CENTRO"):
                self.handle_victory_sequence()
                return

            p_skip = self.vision.find_template(
                screen_gray, "templates/btn_skip_scene.png", threshold=0.8, zona="MITAD_SUPERIOR"
            )
            if p_skip:
                self.device.tap(int(p_skip[0]), int(p_skip[1]))
                p_ok = self.wait_for_template("templates/btn_skip_ok.png", timeout=3, threshold=0.8, interval=0.15, zona="CENTRO")
                if p_ok:
                    self.device.tap(int(p_ok[0]), int(p_ok[1]))
                    self.wait_for_screen_stable(timeout=6, interval=0.35)
                    return
            time.sleep(0.25)

        self.clear_loot_windows()

    def execute_batalla(self, pos):
        log.info("  [⚔️] Etapa de Batalla detectada. Preparando combate...")
        self.device.tap(int(pos[0]), int(pos[1]))
        time.sleep(0.8)

        if self.check_and_recover_mana():
            self.device.tap(int(pos[0]), int(pos[1]))
            time.sleep(0.8)

        if not self.ensure_team_10():
            log.error("  [❌] No se pudo seleccionar Team 10. Abortando batalla.")
            self.cerrar_ventana()
            return

        if not self._auto_battle_activado:
            pos_cb = self.vision.find_template(
                self.device.screenshot(), "templates/checkbox_mana.png", threshold=0.8, zona="COMPLETA"
            )
            if pos_cb:
                self.device.tap(int(pos_cb[0]), int(pos_cb[1]))
                time.sleep(0.4)
            self._auto_battle_activado = True

        pos_start = self.wait_for_template(
            "templates/btn_start_battle.png", timeout=4, threshold=0.8, interval=0.2, zona="MITAD_INFERIOR"
        )
        if pos_start:
            self.device.tap(int(pos_start[0]), int(pos_start[1]))
            time.sleep(0.6)
            if self.check_and_recover_mana():
                pos_start_again = self.wait_for_template(
                    "templates/btn_start_battle.png", timeout=3, threshold=0.8, interval=0.2, zona="MITAD_INFERIOR"
                )
                if pos_start_again:
                    self.device.tap(int(pos_start_again[0]), int(pos_start_again[1]))
        else:
            self.clear_loot_windows()

        log.info("  [⏳] Esperando fin de batalla...")
        inicio_batalla = time.monotonic()
        timeout_batalla = 300

        while time.monotonic() - inicio_batalla < timeout_batalla:
            screen_gray = self.vision.to_gray(self.device.screenshot())

            if not self._speed_activado:
                p_speed = self.vision.find_template(
                    screen_gray, "templates/btn_battle_speed.png", threshold=0.7, zona="MITAD_DERECHA"
                )
                if p_speed:
                    self.device.tap(int(p_speed[0]), int(p_speed[1]))
                    self._speed_activado = True
                    time.sleep(0.4)
                    continue

            if self.vision.find_template(screen_gray, "templates/victory_banner.png", threshold=0.8, zona="CENTRO"):
                self.handle_victory_sequence()
                return

            if self.vision.find_template(screen_gray, "templates/defeat_banner.png", threshold=0.8, zona="CENTRO"):
                self.device.tap(1000, 1000)
                time.sleep(1.0)
                self.clear_loot_windows()
                return

            p1 = self.vision.find_template(
                screen_gray, "templates/btn_skip_scene.png", threshold=0.8, zona="MITAD_SUPERIOR"
            )
            if p1:
                self.device.tap(int(p1[0]), int(p1[1]))
                ok = self.wait_for_template("templates/btn_skip_ok.png", timeout=2.5, threshold=0.8, interval=0.15, zona="CENTRO")
                if ok:
                    self.device.tap(int(ok[0]), int(ok[1]))
                time.sleep(0.5)
                continue

            time.sleep(0.4)

        self.clear_loot_windows()