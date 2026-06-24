import time

class DailyMissions:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def clear_loot_windows(self):
        """Clics de seguridad ampliados para limpiar Loot y Level Up."""
        # Damos 4 toques espaciados para atrapar cualquier ventana lenta
        for _ in range(4):
            self.device.tap(100, 100)
            time.sleep(1.5) # 1.5s le da tiempo a las animaciones de nivel para terminar

    def return_to_home(self):
        """Forzar regreso al menú principal."""
        screen = self.device.screenshot()
        pos_home = self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.8)
        if pos_home:
            self.device.tap(pos_home[0], pos_home[1])
            time.sleep(3)

    def handle_battle_sequence(self):
        """Maneja el salto o aceleración de una batalla y limpia el loot final."""
        print("   [⚔️] Intentando saltar/acelerar batalla...")
        time.sleep(3)
        for _ in range(3):
            screen = self.device.screenshot()
            pos_skip = self.vision.find_template(screen, "templates/btn_battle_skip.png", threshold=0.8)
            pos_speed = self.vision.find_template(screen, "templates/btn_battle_speed.png", threshold=0.8)

            if pos_skip:
                self.device.tap(pos_skip[0], pos_skip[1])
                print("   [>] Batalla saltada.")
                time.sleep(4)
                break
            elif pos_speed:
                self.device.tap(pos_speed[0], pos_speed[1])
                time.sleep(1)

        print("   [>] Limpiando pantallas de victoria/loot...")
        for _ in range(3):
            self.clear_loot_windows()

    def execute(self):
        print("\n [📜] Iniciando Rutina de Misiones Diarias...")

        self.do_tower_of_trials()
        self.do_alliance_quest()
        self.do_summons()
        self.do_spend_mana() # <-- NUEVO MÓDULO INTEGRADO AQUÍ
        self.claim_all_rewards()

        print(" [✅] ¡Rutina de Misiones Diarias completada!")
        return True

    # ==========================================
    # 1. TOWER OF TRIALS
    # ==========================================
    def do_tower_of_trials(self):
        print("\n [🗼] Modulo: Tower of Trials")
        screen = self.device.screenshot()
        pos_tot = self.vision.find_template(screen, "templates/btn_tot_home.png", threshold=0.7)
        if not pos_tot:
            print("  ❌ No se encontró el botón de Tower of Trials.")
            return

        self.device.tap(pos_tot[0], pos_tot[1])
        time.sleep(5)

        print("  [🎁] Reclamando cofre...")
        screen = self.device.screenshot()
        pos_chest = self.vision.find_template(screen, "templates/btn_tot_chest.png", threshold=0.8)
        if pos_chest:
            self.device.tap(pos_chest[0], pos_chest[1] - 45)
            time.sleep(2)
            self.clear_loot_windows()

        print("  [⏩] Acelerando (Fast Forward)...")
        screen = self.device.screenshot()
        pos_ff_menu = self.vision.find_template(screen, "templates/btn_fast_forward_menu.png", threshold=0.8)
        if pos_ff_menu:
            self.device.tap(pos_ff_menu[0], pos_ff_menu[1])
            time.sleep(3)

            acels = 0
            intentos_flecha = 0
            while acels < 2 and intentos_flecha < 3:
                screen = self.device.screenshot()
                pos_green = self.vision.find_template(screen, "templates/btn_ff_green.png", threshold=0.8)
                if pos_green:
                    self.device.tap(pos_green[0], pos_green[1])
                    time.sleep(2)
                    self.clear_loot_windows()
                    acels += 1
                else:
                    pos_arrow = self.vision.find_template(screen, "templates/btn_ff_arrow.png", threshold=0.75)
                    if pos_arrow:
                        self.device.tap(pos_arrow[0], pos_arrow[1])
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
                self.device.tap(pos_explore[0], pos_explore[1])
                time.sleep(2)
                self.clear_loot_windows()
            else:
                break

        print("  [⚔️] Desafiando Jefe...")
        screen = self.device.screenshot()
        pos_boss = self.vision.find_template(screen, "templates/btn_challenge_boss.png", threshold=0.8)
        if pos_boss:
            self.device.tap(pos_boss[0], pos_boss[1])
            time.sleep(3)
            self.handle_battle_sequence()

        self.return_to_home()

    # ==========================================
    # 2. BATTALION WARFARE / GREMIO
    # ==========================================
    def do_alliance_quest(self):
        print("\n [🛡️] Modulo: Misiones de Gremio")
        screen = self.device.screenshot()
        pos_bw = self.vision.find_template(screen, "templates/btn_battalion_warfare.png", threshold=0.8)
        if not pos_bw: return
        self.device.tap(pos_bw[0], pos_bw[1])
        time.sleep(2)

        screen = self.device.screenshot()
        pos_aq = self.vision.find_template(screen, "templates/btn_alliance_quest.png", threshold=0.8)
        if pos_aq:
            self.device.tap(pos_aq[0], pos_aq[1])
            time.sleep(2)

        screen = self.device.screenshot()
        print("  [🗡️] F2P: Usando Challenge Boss individual.")
        pos_challenge = self.vision.find_template(screen, "templates/btn_challenge_boss_2.png", threshold=0.8)
        if pos_challenge:
            self.device.tap(pos_challenge[0], pos_challenge[1])
            self.handle_battle_sequence()

            print("  [>] Limpiando pantallas post-batalla a la derecha...")
            for _ in range(3):
                self.device.tap(2200, 500)
                time.sleep(1)

        self.return_to_home()

    # ==========================================
    # 3. FRIEND SUMMON
    # ==========================================
    def do_summons(self):
        print("\n [🌟] Modulo: Invocaciones")
        screen = self.device.screenshot()
        pos_nav = self.vision.find_template(screen, "templates/btn_summon_nav.png", threshold=0.8)
        if not pos_nav: return
        self.device.tap(pos_nav[0], pos_nav[1])
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
                    self.device.tap(pos_arrow[0], pos_arrow[1])
                    time.sleep(1.5)
                intentos += 1

        if encontrado:
            print("  [>] Tirando summons gratis...")

            screen = self.device.screenshot()
            pos_chest = self.vision.find_template(screen, "templates/btn_friend_chest.png", threshold=0.8)
            if pos_chest:
                print("   [+] Cofre detectado.")
                self.device.tap(pos_chest[0], pos_chest[1])
                time.sleep(1)
                self.clear_loot_windows()

            screen = self.device.screenshot()
            pos_x1 = self.vision.find_template(screen, "templates/btn_summon_x1_free.png", threshold=0.8)
            if pos_x1:
                print("   [+] Lanzando Invocación x1...")
                self.device.tap(pos_x1[0], pos_x1[1])
                time.sleep(3)
                self.clear_loot_windows()

            screen = self.device.screenshot()
            pos_x10 = self.vision.find_template(screen, "templates/btn_summon_x10_free.png", threshold=0.8)
            if pos_x10:
                print("   [+] Lanzando Invocación x10...")
                self.device.tap(pos_x10[0], pos_x10[1])
                time.sleep(3)
                self.clear_loot_windows()

        screen = self.device.screenshot()
        pos_back_summon = self.vision.find_template(screen, "templates/btn_back_summon.png", threshold=0.8)
        if pos_back_summon:
            print("  [🏠] Saliendo del menú de invocaciones...")
            self.device.tap(pos_back_summon[0], pos_back_summon[1])
            time.sleep(3)

        self.return_to_home()

    # ==========================================
    # 4. GASTAR MANÁ (EVENTO SWEEP)
    # ==========================================
    def do_spend_mana(self):
        print("\n [💧] Modulo: Gastar Maná (Sweep Evento)")

        # 1. Entrar al Evento desde Home (Asegúrate de tener este recorte)
        screen = self.device.screenshot()
        pos_event = self.vision.find_template(screen, "templates/btn_event_home.png", threshold=0.7)
        if pos_event:
            self.device.tap(pos_event[0], pos_event[1])
            time.sleep(3)
        else:
            print("  ❌ No se encontró el botón del evento en el lobby.")
            return

        # 2. Buscar la etapa más alta disponible (10, 9 u 8)
        etapas = ["stage_ex_10.png", "stage_ex_9.png", "stage_ex_8.png"]
        etapa_encontrada = False

        for etapa in etapas:
            screen = self.device.screenshot()
            pos_stage = self.vision.find_template(screen, f"templates/{etapa}", threshold=0.85)
            if pos_stage:
                print(f"  [🔍] Etapa de mayor nivel detectada: {etapa.replace('.png', '')}")
                self.device.tap(pos_stage[0], pos_stage[1])
                time.sleep(3)
                etapa_encontrada = True
                break

        if not etapa_encontrada:
            print("  ❌ No se detectó ninguna de las etapas EX configuradas.")
            self.return_to_home()
            return

        # 3. Dar clic a Sweep 3 veces
        print("  [⏩] Ejecutando Sweeps...")
        for i in range(3):
            screen = self.device.screenshot()
            pos_sweep = self.vision.find_template(screen, "templates/btn_sweep.png", threshold=0.8)
            if pos_sweep:
                self.device.tap(pos_sweep[0], pos_sweep[1])
                print(f"   [+] Sweep {i+1}/3 completado.")
                time.sleep(2) # Espera a que aparezca la ventana de botín
                self.clear_loot_windows() # Cierra la ventana de botín tocando la esquina
            else:
                print("   [!] Botón Sweep no encontrado. ¿Maná insuficiente?")
                break

        # 4. Dar Back 2 veces
        print("  [🏠] Saliendo del evento (Back x2)...")
        for _ in range(2):
            screen = self.device.screenshot()
            pos_back = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.8)
            if pos_back:
                self.device.tap(pos_back[0], pos_back[1])
            else:
                self.device.d.press("back") # Si no ve el botón, usa el regreso nativo de Android
            time.sleep(2)

        self.return_to_home()

        # ==========================================
        # 5. RECOMPENSAS (Mailbox y Misiones)
        # ==========================================
        def claim_all_rewards(self):
            print("\n [🎁] Modulo: Reclamar Recompensas")

            # 1. MAILBOX (Mantenemos la lógica de navegación igual)
            screen = self.device.screenshot()
            pos_arrow_down = self.vision.find_template(screen, "templates/btn_menu_arrow_down.png", threshold=0.75)
            if pos_arrow_down:
                self.device.tap(pos_arrow_down[0], pos_arrow_down[1])
                time.sleep(1.5)

            screen = self.device.screenshot()
            pos_mail = self.vision.find_template(screen, "templates/btn_mailbox_icon.png", threshold=0.8)
            if pos_mail:
                self.device.tap(pos_mail[0], pos_mail[1])
                time.sleep(2)

                screen = self.device.screenshot()
                pos_claim = self.vision.find_template(screen, "templates/btn_claim_all.png", threshold=0.8)
                if pos_claim:
                    self.device.tap(pos_claim[0], pos_claim[1])
                    time.sleep(2)
                    self.clear_loot_windows()

                screen = self.device.screenshot()
                pos_back = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.8)
                if pos_back: self.device.tap(pos_back[0], pos_back[1])
                time.sleep(1.5)

            # 2. DAILY MISSIONS (Aquí viene la magia)
            screen = self.device.screenshot()
            pos_arrow_down = self.vision.find_template(screen, "templates/btn_menu_arrow_down.png", threshold=0.75)
            if pos_arrow_down:
                self.device.tap(pos_arrow_down[0], pos_arrow_down[1])
                time.sleep(1.5)

            screen = self.device.screenshot()
            pos_missions = self.vision.find_template(screen, "templates/btn_missions_icon.png", threshold=0.7)
            if pos_missions:
                self.device.tap(pos_missions[0], pos_missions[1])
                time.sleep(2)

                screen = self.device.screenshot()
                pos_tab_daily = self.vision.find_template(screen, "templates/tab_daily.png", threshold=0.8)
                if pos_tab_daily:
                    self.device.tap(pos_tab_daily[0], pos_tab_daily[1])
                    time.sleep(1.5)

                print("  [>] Iniciando barrido total de misiones y cofres...")

                # --- BUCLE DE VERIFICACIÓN TOTAL ---
                intentos_vacios = 0
                # Requerimos 2 escaneos limpios consecutivos para asegurar que no hay delay de UI
                while intentos_vacios < 2:
                    algo_reclamado = False
                    screen = self.device.screenshot()

                    # Prioridad 1: Reclamar misiones
                    pos_claim = self.vision.find_template(screen, "templates/btn_claim_all.png", threshold=0.8)
                    if pos_claim:
                        print("   [+] Misiones listas. Reclamando...")
                        self.device.tap(pos_claim[0], pos_claim[1])
                        time.sleep(2)
                        self.clear_loot_windows()
                        algo_reclamado = True

                    # Prioridad 2: Reclamar cofres
                    if not algo_reclamado:  # Solo busca cofres si no acaba de reclamar misiones
                        pos_chest = self.vision.find_template(screen, "templates/chest_ready.png", threshold=0.8)
                        if pos_chest:
                            print("   [+] Cofre listo. Reclamando...")
                            self.device.tap(pos_chest[0], pos_chest[1])
                            time.sleep(2)
                            self.clear_loot_windows()
                            algo_reclamado = True

                    # Lógica de control del bucle
                    if algo_reclamado:
                        intentos_vacios = 0  # Si encontramos algo, reseteamos el contador a 0
                    else:
                        intentos_vacios += 1  # Si no vemos nada, sumamos 1
                        time.sleep(1.5)  # Pausa breve para que el juego actualice la UI

                print("  [✅] Barrido completado. No se quedó nada atrás.")

            self.return_to_home()