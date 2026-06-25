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
            if self.vision.find_template(screen, "templates/label_team_10.png", threshold=0.98):
                return True
            pos_arrow = self.vision.find_template(screen, "templates/btn_arrow_team.png", threshold=0.8)
            if pos_arrow:
                self.device.tap(pos_arrow[0], pos_arrow[1])
                time.sleep(1.5)
        return False

    def check_and_recover_mana(self):
        """Revisa si salió el aviso de sin maná, activa la poción y cierra la ventana."""
        screen = self.device.screenshot()
        pos_insuficiente = self.vision.find_template(screen, "templates/mana_insuficiente.png", threshold=0.8)

        if pos_insuficiente:
            print("  [💧] ¡Maná insuficiente detectado! Abriendo menú de pociones...")
            self.device.tap(pos_insuficiente[0], pos_insuficiente[1])
            time.sleep(2)  # Espera a que se abra la ventana de pociones

            # Buscar el cuadradito de "Auto Use Mana Potion"
            screen_pot = self.device.screenshot()
            pos_checkbox = self.vision.find_template(screen_pot, "templates/checkbox_mana.png", threshold=0.8)

            if pos_checkbox:
                print("   [+] Activando uso automático de pociones (Checkbox)...")
                self.device.tap(pos_checkbox[0], pos_checkbox[1])
                time.sleep(1.5)

            # Tocar el borde de la pantalla (esquina superior izquierda) para cerrar la ventana
            print("   [<] Cerrando ventana de recuperación de maná...")
            self.device.tap(100, 100)
            time.sleep(2)
            return True

        return False

    def detectar_costo_y_ejecutar(self):
        screen = self.device.screenshot()
        prioridad_costos = ["cost_80.png", "cost_60.png", "cost_50.png", "cost_0.png"]
        for c in prioridad_costos:
            pos = self.vision.find_template(screen, f"templates/{c}", threshold=0.98)
            if pos:
                cleared_list = self.vision.find_all_templates(screen, "templates/cleared.png", threshold=0.85)
                esta_cleared = any(abs(pos[1] - c_pos[1]) < 40 for c_pos in cleared_list)
                if esta_cleared:
                    print(f"  [⏩] Etapa {c} está completada. Saltando...")
                    continue
                return pos, c
        return None, None

    def execute(self):
        print("\n [🎃] Iniciando farmeo infinito...")
        while True:
            pos, tipo_costo = self.detectar_costo_y_ejecutar()
            if pos:
                if tipo_costo == "cost_0.png":
                    self.execute_historia(pos)
                else:
                    self.execute_batalla(pos)
                time.sleep(3)
            else:
                print("  [✅] No hay más etapas disponibles. Farmeo terminado.")
                break

    # ==========================================
    # LÓGICA EXCLUSIVA PARA HISTORIA (Costo 0)
    # ==========================================
    def execute_historia(self, pos):
        print("  [📖] Etapa de Historia detectada. Entrando en modo Skip...")
        self.device.tap(pos[0], pos[1])
        time.sleep(5)  # Esperamos a que cargue la escena
        intentos = 0
        while intentos < 15:
            screen = self.device.screenshot()
            # 1. Buscar el botón de Skip ">>"
            p_skip = self.vision.find_template(screen, "templates/btn_skip_scene.png", threshold=0.8)
            if p_skip:
                print("   [⏭️] Botón Skip detectado. Presionando...")
                self.device.tap(p_skip[0], p_skip[1])
                time.sleep(1.5)
                # 2. Confirmar el Skip con el botón OK verde
                screen_ok = self.device.screenshot()
                p_ok = self.vision.find_template(screen_ok, "templates/btn_skip_ok.png", threshold=0.8)
                if p_ok:
                    print("   [✅] Confirmando Skip (OK)...")
                    self.device.tap(p_ok[0], p_ok[1])
                    time.sleep(5)  # Esperar a que regrese al menú
                    break

            # 3. Por si la historia termina sola y lanza un Victory Banner
            if self.vision.find_template(screen, "templates/victory_banner.png", threshold=0.8):
                self.handle_victory_sequence()
                break
            intentos += 1
            time.sleep(2)

    # ==========================================
    # LÓGICA EXCLUSIVA PARA PELEAS (Costo 80, 60, 50)
    # ==========================================
    def execute_batalla(self, pos):
        print("  [⚔️] Etapa de Batalla detectada. Preparando combate...")
        self.device.tap(pos[0], pos[1])
        time.sleep(2)

        if self.check_and_recover_mana():
            self.device.tap(pos[0], pos[1])
            time.sleep(2)

        if not self.ensure_team_10(): return
        screen = self.device.screenshot()

        pos_start = self.vision.find_template(screen, "templates/btn_start_battle.png", threshold=0.8)
        if pos_start:
            self.device.tap(pos_start[0], pos_start[1])
            time.sleep(1.5)  # Espera cortita para que el juego despliegue el aviso si no hay maná

            # --- NUEVA VALIDACIÓN POST-START ---
            if self.check_and_recover_mana():
                # Si recargó maná, volvemos a intentar el START
                screen = self.device.screenshot()
                pos_start_again = self.vision.find_template(screen, "templates/btn_start_battle.png", threshold=0.8)
                if pos_start_again:
                    self.device.tap(pos_start_again[0], pos_start_again[1])

        time.sleep(5)  # Ahora sí, esperamos a que la batalla inicie

        while True:
            screen = self.device.screenshot()
            # Victoria
            if self.vision.find_template(screen, "templates/victory_banner.png", threshold=0.8):
                self.handle_victory_sequence()
                break
            # Derrota
            if self.vision.find_template(screen, "templates/defeat_banner.png", threshold=0.8):
                print("  [💀] Batalla perdida. Retirándose...")
                self.device.tap(1000, 1000)
                break
            # A veces hay mini-diálogos antes del jefe en las batallas, mantenemos el skip por si acaso
            p1 = self.vision.find_template(screen, "templates/btn_skip_scene.png", threshold=0.8)
            if p1:
                self.device.tap(p1[0], p1[1])
                time.sleep(1)
                ok = self.vision.find_template(screen, "templates/btn_skip_ok.png", threshold=0.8)
                if ok: self.device.tap(ok[0], ok[1])
            time.sleep(1)
