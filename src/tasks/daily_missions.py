import time

class DailyMissions:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def clear_loot_windows(self):
        for _ in range(3):
            self.device.tap(100, 100)
            time.sleep(1.5)

    def return_to_home(self):
        screen = self.device.screenshot()
        pos_home = self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.8)
        if pos_home:
            self.device.tap(int(pos_home[0]), int(pos_home[1]))
            time.sleep(3)

    def handle_battle_sequence(self):
        print("   [⚔️] Intentando saltar/acelerar batalla...")
        time.sleep(3)
        for _ in range(3):
            screen = self.device.screenshot()
            pos_skip = self.vision.find_template(screen, "templates/btn_battle_skip.png", threshold=0.8)
            pos_speed = self.vision.find_template(screen, "templates/btn_battle_speed.png", threshold=0.8)

            if pos_skip:
                self.device.tap(int(pos_skip[0]), int(pos_skip[1]))
                print("   [>] Batalla saltada.")
                time.sleep(4)
                break
            elif pos_speed:
                self.device.tap(int(pos_speed[0]), int(pos_speed[1]))
                time.sleep(1)

        print("   [>] Limpiando pantallas de victoria/loot...")
        self.clear_loot_windows()

    def check_and_recover_mana(self):
        screen = self.device.screenshot()
        pos_insuficiente = self.vision.find_template(screen, "templates/mana_insuficiente.png", threshold=0.8)

        if pos_insuficiente:
            print("  [💧] ¡Maná insuficiente detectado! Abriendo menú de pociones...")
            self.device.tap(int(pos_insuficiente[0]), int(pos_insuficiente[1]))
            time.sleep(2)

            screen_pot = self.device.screenshot()
            pos_checkbox = self.vision.find_template(screen_pot, "templates/checkbox_mana.png", threshold=0.8)
            if pos_checkbox:
                print("   [+] Activando uso automático de pociones (Checkbox)...")
                self.device.tap(int(pos_checkbox[0]), int(pos_checkbox[1]))
                time.sleep(1.5)

            print("   [<] Cerrando ventana de recuperación de maná...")
            self.device.tap(100, 100)
            time.sleep(2)
            return True
        return False

    def execute(self):
        print("\n [📜] Iniciando Rutina de Misiones Diarias...")

        self.do_tower_of_trials()
        self.do_alliance_quest()
        self.do_arena()
        self.do_summons()
        self.do_spend_mana()
        self.claim_all_rewards()

        print(" [✅] ¡Rutina de Misiones Diarias completada!")
        return True

    def do_tower_of_trials(self):
        print("\n [🗼] Modulo: Tower of Trials")
        screen = self.device.screenshot()
        pos_tot = self.vision.find_template(screen, "templates/btn_tot_home.png", threshold=0.7)
        if not pos_tot:
            print("  ❌ No se encontró el botón de Tower of Trials.")
            return

        self.device.tap(int(pos_tot[0]), int(pos_tot[1]))
        time.sleep(5)

        print("  [🎁] Reclamando cofre...")
        screen = self.device.screenshot()
        pos_chest = self.vision.find_template(screen, "templates/btn_tot_chest.png", threshold=0.8)
        if pos_chest:
            self.device.tap(int(pos_chest[0]), int(pos_chest[1] - 45))
            time.sleep(2)
            self.clear_loot_windows()

        print("  [⏩] Acelerando (Fast Forward)...")
        screen = self.device.screenshot()
        pos_ff_menu = self.vision.find_template(screen, "templates/btn_fast_forward_menu.png", threshold=0.8)
        if pos_ff_menu:
            self.device.tap(int(pos_ff_menu[0]), int(pos_ff_menu[1]))
            time.sleep(3)

            acels = 0
            intentos_flecha = 0
            while acels < 2 and intentos_flecha < 3:
                screen = self.device.screenshot()
                pos_green = self.vision.find_template(screen, "templates/btn_ff_green.png", threshold=0.8)
                if pos_green:
                    self.device.tap(int(pos_green[0]), int(pos_green[1]))
                    time.sleep(2)
                    self.clear_loot_windows()
                    acels += 1
                else:
                    pos_arrow = self.vision.find_template(screen, "templates/btn_ff_arrow.png", threshold=0.75)
                    if pos_arrow:
                        self.device.tap(int(pos_arrow[0]), int(pos_arrow[1]))
                        time.sleep(1.5)
                        intentos_flecha += 1
                    else:
                        break
            self.device.tap(100, 100)
            time.sleep(1)

        print("  [🔍] Explorando (3x)...")
        for _ in range(3):
            screen = self.device.screenshot()
            pos_explore = self.vision.find_template(screen, "templates/btn_explore.png", threshold=0.8)
            if pos_explore:
                self.device.tap(int(pos_explore[0]), int(pos_explore[1]))
                time.sleep(2)
                self.clear_loot_windows()
            else:
                break

        print("  [⚔️] Desafiando Jefe...")
        screen = self.device.screenshot()
        pos_boss = self.vision.find_template(screen, "templates/btn_challenge_boss.png", threshold=0.8)
        if pos_boss:
            self.device.tap(int(pos_boss[0]), int(pos_boss[1]))
            time.sleep(3)
            self.handle_battle_sequence()

        self.return_to_home()

    def do_alliance_quest(self):
        print("\n [🛡️] Modulo: Misiones de Gremio")
        screen = self.device.screenshot()
        pos_bw = self.vision.find_template(screen, "templates/btn_battalion_warfare.png", threshold=0.8)
        if not pos_bw: return
        self.device.tap(int(pos_bw[0]), int(pos_bw[1]))
        time.sleep(2)

        screen = self.device.screenshot()
        pos_aq = self.vision.find_template(screen, "templates/btn_alliance_quest.png", threshold=0.8)
        if pos_aq:
            self.device.tap(int(pos_aq[0]), int(pos_aq[1]))
            time.sleep(2)

        screen = self.device.screenshot()
        print("  [🗡️] F2P: Usando Challenge Boss individual.")
        pos_challenge = self.vision.find_template(screen, "templates/btn_challenge_boss_2.png", threshold=0.8)
        if pos_challenge:
            self.device.tap(int(pos_challenge[0]), int(pos_challenge[1]))
            self.handle_battle_sequence()

            print("  [>] Limpiando pantallas post-batalla a la derecha...")
            for _ in range(3):
                self.device.tap(2200, 500)
                time.sleep(1)

        self.return_to_home()

    def do_arena(self):
        print("\n [🏟️] Modulo: Arena (5 Batallas)")

        screen = self.device.screenshot()
        pos_arena = self.vision.find_template(screen, "templates/arena.png", threshold=0.7)
        if not pos_arena:
            print("  ❌ No se encontró el ícono de Arena en el Home.")
            return

        self.device.tap(int(pos_arena[0]), int(pos_arena[1]))
        time.sleep(4)

        screen = self.device.screenshot()
        arenas = self.vision.find_all_templates(screen, "templates/btn_arena.png", threshold=0.75)
        if not arenas:
            print("  ❌ No se encontraron los modos de Arena.")
            self.return_to_home()
            return

        arenas.sort(key=lambda pos: pos[0])
        desplazamiento_y = 180

        print("  [>] Gema detectada. Dando clic al botón de Arena inferior...")
        self.device.tap(int(arenas[0][0]), int(arenas[0][1] + desplazamiento_y))
        time.sleep(3)

        print("  [⚔️] Iniciando los 5 combates diarios...")
        for i in range(5):
            print(f"   [🥊] Combate {i + 1}/5...")
            screen = self.device.screenshot()

            oponentes = self.vision.find_all_templates(screen, "templates/challenge_area.png", threshold=0.8)

            if not oponentes:
                print("   [!] No se encontraron oponentes o botón de desafío.")
                break

            oponentes.sort(key=lambda pos: pos[1])
            self.device.tap(int(oponentes[0][0]), int(oponentes[0][1]))

            self.handle_battle_sequence()
            time.sleep(2)

        print("  [✅] Rutina de Arena finalizada.")
        self.return_to_home()

    def do_summons(self):
        print("\n [🌟] Modulo: Invocaciones")
        screen = self.device.screenshot()
        pos_nav = self.vision.find_template(screen, "templates/btn_summon_nav.png", threshold=0.8)
        if not pos_nav: return
        self.device.tap(int(pos_nav[0]), int(pos_nav[1]))
        time.sleep(3)

        encontrado = False
        intentos = 0
        while not encontrado and intentos < 5:
            screen = self.device.screenshot()
            pos_x1_free = self.vision.find_template(screen, "templates/btn_summon_x1_free.png", threshold=0.8)

            if pos_x1_free:
                encontrado = True
            else:
                pos_arrow = self.vision.find_template(screen, "templates/btn_summon_arrow_left.png", threshold=0.65)
                if pos_arrow:
                    self.device.tap(int(pos_arrow[0]), int(pos_arrow[1]))
                    time.sleep(1.5)
                intentos += 1

        if encontrado:
            print("  [>] Tirando summons gratis...")

            screen = self.device.screenshot()
            pos_chest = self.vision.find_template(screen, "templates/btn_friend_chest.png", threshold=0.8)
            if pos_chest:
                print("   [+] Cofre detectado.")
                self.device.tap(int(pos_chest[0]), int(pos_chest[1]))
                time.sleep(1)
                self.clear_loot_windows()

            screen = self.device.screenshot()
            pos_x1 = self.vision.find_template(screen, "templates/btn_summon_x1_free.png", threshold=0.8)
            if pos_x1:
                print("   [+] Lanzando Invocación x1...")
                self.device.tap(int(pos_x1[0]), int(pos_x1[1]))
                time.sleep(3)
                self.clear_loot_windows()

            screen = self.device.screenshot()
            pos_x10 = self.vision.find_template(screen, "templates/btn_summon_x10_free.png", threshold=0.8)
            if pos_x10:
                print("   [+] Lanzando Invocación x10...")
                self.device.tap(int(pos_x10[0]), int(pos_x10[1]))
                time.sleep(3)
                self.clear_loot_windows()

        screen = self.device.screenshot()
        pos_back_summon = self.vision.find_template(screen, "templates/btn_back_summon.png", threshold=0.8)
        if pos_back_summon:
            print("  [🏠] Saliendo del menú de invocaciones...")
            self.device.tap(int(pos_back_summon[0]), int(pos_back_summon[1]))
            time.sleep(3)

        self.return_to_home()

    def do_spend_mana(self):
        print("\n [💧] Modulo: Gastar Maná (Sweep Evento)")

        screen = self.device.screenshot()
        pos_event = self.vision.find_template(screen, "templates/btn_event_home.png", threshold=0.7)
        if pos_event:
            self.device.tap(int(pos_event[0]), int(pos_event[1]))
            time.sleep(3)
        else:
            print("  ❌ No se encontró el botón del evento en el lobby.")
            return

        etapas = ["stage_ex_10.png", "stage_ex_9.png", "stage_ex_8.png"]
        etapa_encontrada = False

        for etapa in etapas:
            screen = self.device.screenshot()
            pos_stage = self.vision.find_template(screen, f"templates/{etapa}", threshold=0.85)
            if pos_stage:
                print(f"  [🔍] Etapa de mayor nivel detectada: {etapa.replace('.png', '')}")
                self.device.tap(int(pos_stage[0]), int(pos_stage[1]))
                time.sleep(3)
                etapa_encontrada = True
                break

        if not etapa_encontrada:
            print("  ❌ No se detectó ninguna de las etapas EX configuradas.")
            self.return_to_home()
            return

        print("  [⏩] Ejecutando Sweeps...")
        for i in range(3):
            screen = self.device.screenshot()
            pos_sweep = self.vision.find_template(screen, "templates/btn_sweep.png", threshold=0.8)
            if pos_sweep:
                self.device.tap(int(pos_sweep[0]), int(pos_sweep[1]))
                time.sleep(1.5)

                if self.check_and_recover_mana():
                    self.device