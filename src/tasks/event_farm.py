import time
from core.logger import get_logger

log = get_logger("event_farm")


class EventFarm:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def handle_victory_sequence(self):
        log.info("   [✨] Victoria detectada. Limpiando...")
        for _ in range(3):
            self.device.tap(2200, 500)
            time.sleep(1)

    def ensure_team_10(self):
        log.info("  [🛡️] Verificando Team 10...")
        for _ in range(12):
            screen = self.device.screenshot()
            if self.vision.find_template(screen, "templates/label_team_10.png", threshold=0.85):  # Reducido de 0.98
                log.info("  [✓] Team 10 detectado.")
                return True
            pos_arrow = self.vision.find_template(screen, "templates/btn_arrow_team.png", threshold=0.8)
            if pos_arrow:
                self.device.tap(int(pos_arrow[0]), int(pos_arrow[1]))
                time.sleep(1.5)
        log.warning("  [!] No se pudo llegar a Team 10.")
        return False

    def check_and_recover_mana(self):
        screen = self.device.screenshot()
        pos_insuficiente = self.vision.find_template(screen, "templates/mana_insuficiente.png", threshold=0.8)
        if pos_insuficiente:
            log.info("  [💧] ¡Aviso de maná detectado! Usando botón de restauración...")
            pos_ok = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.8)
            if pos_ok:
                self.device.tap(int(pos_ok[0]), int(pos_ok[1]))
            else:
                self.device.tap(int(pos_insuficiente[0]), int(pos_insuficiente[1]))
            time.sleep(2)

            screen_pot = self.device.screenshot()
            pos_checkbox = self.vision.find_template(screen_pot, "templates/checkbox_mana.png", threshold=0.8)
            if pos_checkbox:
                log.info("   [+] Activando uso automático de pociones (Checkbox)...")
                self.device.tap(int(pos_checkbox[0]), int(pos_checkbox[1]))
                time.sleep(1.5)

            screen_cerrar = self.device.screenshot()
            pos_x = self.vision.find_template(screen_cerrar, "templates/btn_cerrar_x.png", threshold=0.8)
            if pos_x:
                log.info("   [<] Cerrando ventana con botón X...")
                self.device.tap(int(pos_x[0]), int(pos_x[1]))
            else:
                self.device.tap(100, 100)
            time.sleep(2)
            return True
        return False

    def detectar_costo_y_ejecutar(self):
        screen = self.device.screenshot()
        prioridad_costos = ["cost_80.png", "cost_60.png", "cost_50.png", "cost_0.png"]
        for c in prioridad_costos:
            pos = self.vision.find_template(screen, f"templates/{c}", threshold=0.85)  # Reducido de 0.98
            if pos:
                cleared_list = self.vision.find_all_templates(screen, "templates/cleared.png", threshold=0.85)
                esta_cleared = any(abs(pos[1] - c_pos[1]) < 40 for c_pos in cleared_list)
                if esta_cleared:
                    continue
                return pos, c
        return None, None

    def execute(self):
        log.info("\n [🎃] Iniciando farmeo infinito...")
        max_intentos = 100  # Límite de seguridad para evitar bucle infinito
        intentos = 0

        while intentos < max_intentos:
            pos, tipo_costo = self.detectar_costo_y_ejecutar()
            if pos:
                if tipo_costo == "cost_0.png":
                    self.execute_historia(pos)
                else:
                    self.execute_batalla(pos)
                time.sleep(3)
                intentos += 1
            else:
                log.info("  [✅] No hay más etapas disponibles. Farmeo terminado.")
                break

        if intentos >= max_intentos:
            log.warning("  [⚠️] Límite de %d intentos alcanzado. Deteniendo farmeo.", max_intentos)

    def execute_historia(self, pos):
        log.info("  [📖] Etapa de Historia detectada. Entrando en modo Skip...")
        self.device.tap(int(pos[0]), int(pos[1]))
        time.sleep(5)
        intentos = 0
        while intentos < 15:
            screen = self.device.screenshot()
            p_skip = self.vision.find_template(screen, "templates/btn_skip_scene.png", threshold=0.8)
            if p_skip:
                self.device.tap(int(p_skip[0]), int(p_skip[1]))
                time.sleep(1.5)
                screen_ok = self.device.screenshot()
                p_ok = self.vision.find_template(screen_ok, "templates/btn_skip_ok.png", threshold=0.8)
                if p_ok:
                    self.device.tap(int(p_ok[0]), int(p_ok[1]))
                    time.sleep(5)
                    break
            if self.vision.find_template(screen, "templates/victory_banner.png", threshold=0.8):
                self.handle_victory_sequence()
                break
            intentos += 1
            time.sleep(2)

    def execute_batalla(self, pos):
        log.info("  [⚔️] Etapa de Batalla detectada. Preparando combate...")
        self.device.tap(int(pos[0]), int(pos[1]))
        time.sleep(2)
        if self.check_and_recover_mana():
            self.device.tap(int(pos[0]), int(pos[1]))
            time.sleep(2)
        if not self.ensure_team_10():
            log.error("  [❌] No se pudo seleccionar Team 10. Abortando batalla.")
            return

        screen = self.device.screenshot()
        pos_start = self.vision.find_template(screen, "templates/btn_start_battle.png", threshold=0.8)
        if pos_start:
            self.device.tap(int(pos_start[0]), int(pos_start[1]))
            time.sleep(1.5)
            if self.check_and_recover_mana():
                screen = self.device.screenshot()
                pos_start_again = self.vision.find_template(screen, "templates/btn_start_battle.png", threshold=0.8)
                if pos_start_again:
                    self.device.tap(int(pos_start_again[0]), int(pos_start_again[1]))

        time.sleep(5)

        # ✅ MANTENER while True sin timeout para batallas largas
        while True:
            screen = self.device.screenshot()
            if self.vision.find_template(screen, "templates/victory_banner.png", threshold=0.8):
                self.handle_victory_sequence()
                break
            if self.vision.find_template(screen, "templates/defeat_banner.png", threshold=0.8):
                log.info("  [💀] Derrota detectada. Saliendo...")
                self.device.tap(1000, 1000)
                break
            p1 = self.vision.find_template(screen, "templates/btn_skip_scene.png", threshold=0.8)
            if p1:
                self.device.tap(int(p1[0]), int(p1[1]))
                time.sleep(1)
                ok = self.vision.find_template(screen, "templates/btn_skip_ok.png", threshold=0.8)
                if ok:
                    self.device.tap(int(ok[0]), int(ok[1]))
            time.sleep(1)