import time


class EventFarm:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def handle_victory_sequence(self):
        print("   [✨] Victoria detectada. Limpiando...")
        for _ in range(3):
            self.device.tap(2200, 500)
            time.sleep(1)

    def ensure_team_10(self):
        print("  [🛡️] Verificando Team 10...")
        for _ in range(12):
            screen = self.device.screenshot()
            if self.vision.find_template(screen, "templates/label_team_10.png", threshold=0.85):
                return True
            pos_arrow = self.vision.find_template(screen, "templates/btn_arrow_team.png", threshold=0.8)
            if pos_arrow:
                self.device.tap(pos_arrow[0], pos_arrow[1])
                time.sleep(1.5)
        return False

    def detectar_costo_y_ejecutar(self):
        screen = self.device.screenshot()
        prioridad_costos = ["cost_80.png", "cost_60.png", "cost_50.png", "cost_0.png"]

        for c in prioridad_costos:
            pos = self.vision.find_template(screen, f"templates/{c}", threshold=0.85)
            if pos:
                # Filtrar si la fila ya tiene un 'cleared.png'
                cleared_list = self.vision.find_all_templates(screen, "templates/cleared.png", threshold=0.85)
                esta_cleared = any(abs(pos[1] - c_pos[1]) < 40 for c_pos in cleared_list)

                if esta_cleared:
                    print(f"  [⏩] Etapa {c} está completada. Saltando...")
                    continue
                return pos
        return None

    def execute(self):
        print("\n [🎃] Iniciando farmeo infinito...")
        while True:
            pos = self.detectar_costo_y_ejecutar()
            if pos:
                self.execute_en_posicion(pos)
                time.sleep(3)
            else:
                print("  [✅] No hay más etapas disponibles. Farmeo terminado.")
                break

    def execute_en_posicion(self, pos):
        self.device.tap(pos[0], pos[1])
        time.sleep(3)
        if not self.ensure_team_10(): return

        screen = self.device.screenshot()
        pos_auto = self.vision.find_template(screen, "templates/btn_auto_prebattle.png", threshold=0.7)
        if pos_auto: self.device.tap(pos_auto[0], pos_auto[1])

        pos_start = self.vision.find_template(screen, "templates/btn_start_battle.png", threshold=0.8)
        if pos_start: self.device.tap(pos_start[0], pos_start[1])

        time.sleep(5)
        while True:
            screen = self.device.screenshot()

            # Victoria
            if self.vision.find_template(screen, "templates/victory_banner.png", threshold=0.8):
                self.handle_victory_sequence()
                break

            # Derrota (Seguridad)
            if self.vision.find_template(screen, "templates/defeat_banner.png", threshold=0.8):
                print("  [💀] Batalla perdida. Retirándose...")
                self.device.tap(1000, 1000)
                break

            # Skip historia
            p1 = self.vision.find_template(screen, "templates/btn_skip_scene.png", threshold=0.8)
            p2 = self.vision.find_template(screen, "templates/btn_skip_scene_2.png", threshold=0.8)
            if p1 or p2:
                target = p1 if p1 else p2
                self.device.tap(target[0], target[1])
                time.sleep(1)
                ok = self.vision.find_template(screen, "templates/btn_skip_ok.png", threshold=0.8)
                if ok: self.device.tap(ok[0], ok[1])
            time.sleep(5)