import time
import datetime
import json
import os
import cv2
import pytesseract
import numpy as np

# Configura aquí la ruta de tu Tesseract si no está en las variables de entorno de Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class DailyMissions:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision
        self.estado_file = "estado_diario.json"
        self.cuenta_actual = "Default"
        self.estado_hoy = self.cargar_estado()

    # ==========================================
    # SISTEMA DE LOGS Y ESTADO JSON
    # ==========================================
    def cargar_estado(self):
        hoy = datetime.datetime.now().strftime("%Y-%m-%d")
        if os.path.exists(self.estado_file):
            try:
                with open(self.estado_file, "r") as f:
                    data = json.load(f)
                    if data.get("fecha") == hoy:
                        return data
            except Exception:
                pass
        return {"fecha": hoy, "cuentas": {}}

    def guardar_estado(self):
        with open(self.estado_file, "w") as f:
            json.dump(self.estado_hoy, f, indent=4)

    def actualizar_modulo(self, modulo, completado=True):
        if self.cuenta_actual not in self.estado_hoy["cuentas"]:
            self.estado_hoy["cuentas"][self.cuenta_actual] = {}
        self.estado_hoy["cuentas"][self.cuenta_actual][modulo] = completado
        self.guardar_estado()

    def modulo_completado(self, modulo):
        return self.estado_hoy["cuentas"].get(self.cuenta_actual, {}).get(modulo, False)

    # ==========================================
    # SISTEMA OCR (CONTADOR DE GEMAS)
    # ==========================================
    def leer_gemas(self):
        """
        Lee el contador de gemas mediante un recorte fijo de pantalla (ROI),
        en vez de depender de detección de template. Coordenadas calibradas
        para la posición del contador de gemas en la barra superior.
        """
        print("  [👁️] Escaneando contador de gemas (OCR)...")
        try:
            # Coordenadas ajustadas para la zona de gemas en pantalla (2400x1080)
            X, Y, W, H = 2060, 35, 210, 50

            screen_path = "temp_gems_ocr.png"
            # Aseguramos que la captura sea reciente
            self.device.d.screenshot(screen_path)
            img = cv2.imread(screen_path)

            if img is None:
                print("  [!] No se pudo leer la captura de pantalla para OCR.")
                return 0

            # Recortamos la zona donde están los números
            roi = img[Y:Y + H, X:X + W]

            # Procesamiento para OCR: mejora contraste y escala para lectura precisa
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            # Threshold: letras blancas (números) sobre fondo oscuro
            _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)

            # Leer números (whitelist fuerza a que solo busque dígitos)
            texto = pytesseract.image_to_string(
                thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789'
            )
            numeros = ''.join(filter(str.isdigit, texto))

            if os.path.exists(screen_path):
                os.remove(screen_path)

            valor = int(numeros) if numeros else 0
            print(f"  [💎] Gemas leídas: {valor}")
            return valor

        except Exception as e:
            print(f"  [!] Error de OCR. ¿Instalaste Tesseract en tu PC?: {e}")
            return 0

    # ==========================================
    # FUNCIONES BASE DE INTERACCIÓN
    # ==========================================
    def cerrar_ventana(self, screen=None):
        """
        Función unificada de cierre: intenta botón X, si no existe intenta
        btn_back.png, y como última opción presiona el botón 'back' de Android.
        """
        if screen is None:
            screen = self.device.screenshot()

        pos_close = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
        if pos_close:
            print("   [<] Cerrando con botón X...")
            self.device.tap(int(pos_close[0]), int(pos_close[1]))
            time.sleep(2)
            return

        pos_back = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.9)
        if pos_back:
            print("   [<] Cerrando con btn_back.png...")
            self.device.tap(int(pos_back[0]), int(pos_back[1]))
            time.sleep(2)
            return

        print("   [<] No se detectó X ni btn_back. Usando botón físico/virtual 'back' de Android...")
        self.device.d.press("back")
        time.sleep(2)

    def clear_loot_windows(self):
        intentos = 0
        while intentos < 5:
            screen = self.device.screenshot()
            pos_loot = self.vision.find_template(screen, "templates/pantalla_loot.png", threshold=0.9)
            pos_nivel = self.vision.find_template(screen, "templates/level_up.png", threshold=0.9)
            pos_rewards = self.vision.find_template(screen, "templates/rewards.png", threshold=0.9)
            pos_victory = self.vision.find_template(screen, "templates/victory_banner.png", threshold=0.9)
            pos_defeat = self.vision.find_template(screen, "templates/defeat_banner.png", threshold=0.9)

            if pos_loot or pos_nivel or pos_rewards or pos_victory or pos_defeat:
                print("   [+] Pantalla de fin de batalla/botín detectada. Cerrando...")
                self.device.tap(100, 100)
                time.sleep(1.5)
                intentos += 1
            else:
                break

    def _limpiar_invocacion(self):
        print("   [>>] Esperando animación para saltar (Skip)...")
        intentos_skip = 0
        animacion_saltada = False
        while intentos_skip < 8:
            screen = self.device.screenshot()
            pos_skip = self.vision.find_template(screen, "templates/btn_skip_summon.png", threshold=0.75)

            if pos_skip:
                self.device.tap(int(pos_skip[0]), int(pos_skip[1]))
                print("   [>>] Animación saltada exitosamente.")
                animacion_saltada = True
                time.sleep(2)
                break

            time.sleep(1)
            intentos_skip += 1

        if not animacion_saltada:
            print("   [!] No se vio el botón Skip, esperando que termine la animación natural...")
            time.sleep(5)

        print("   [>] Recogiendo personajes y limpiando pantallas...")
        intentos_limpieza = 0
        while intentos_limpieza < 6:
            screen = self.device.screenshot()
            pos_result_ok = self.vision.find_template(screen, "templates/btn_result_ok.png", threshold=0.8)
            pos_rewards = self.vision.find_template(screen, "templates/rewards.png", threshold=0.8)

            if pos_result_ok:
                print("   [+] Pantalla de resultados detectada. Dando OK...")
                self.device.tap(int(pos_result_ok[0]), int(pos_result_ok[1]))
                time.sleep(1.5)
                intentos_limpieza = 0

            elif pos_rewards:
                print("   [+] Pantalla de auto-forge/rewards detectada. Cerrando...")
                self.device.tap(100, 100)
                time.sleep(1.5)
                intentos_limpieza = 0

            else:
                intentos_limpieza += 1
                time.sleep(1)

    def return_to_home(self):
        screen = self.device.screenshot()
        pos_home = self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.9)
        if pos_home:
            self.device.tap(int(pos_home[0]), int(pos_home[1]))
            time.sleep(3)

    def handle_battle_sequence(self):
        """
        Maneja el flujo de una batalla. Si detecta un empate (Draw.png), confirma
        con btn_draw_ok.png y devuelve "draw" para que el llamador decida reintentar
        (hasta 3 veces según la lógica de cada módulo).
        """
        time.sleep(2)
        screen = self.device.screenshot()
        pos_draw = self.vision.find_template(screen, "templates/Draw.png", threshold=0.9)

        if pos_draw:
            print("   [⚖️] Se detectó un EMPATE (Draw) instantáneo.")
            pos_ok = self.vision.find_template(screen, "templates/btn_draw_ok.png", threshold=0.9)
            if pos_ok:
                self.device.tap(int(pos_ok[0]), int(pos_ok[1]))
            time.sleep(2)
            return "draw"

        print("   [⚔️] Intentando saltar/acelerar batalla...")
        time.sleep(2)

        for _ in range(3):
            screen = self.device.screenshot()
            pos_skip = self.vision.find_template(screen, "templates/btn_battle_skip.png", threshold=0.9)
            pos_speed = self.vision.find_template(screen, "templates/btn_battle_speed.png", threshold=0.9)

            if pos_skip:
                self.device.tap(int(pos_skip[0]), int(pos_skip[1]))
                print("   [>] Batalla saltada.")
                time.sleep(4)
                break
            elif pos_speed:
                self.device.tap(int(pos_speed[0]), int(pos_speed[1]))
                time.sleep(1)

        print("   [>] Limpiando pantallas de victoria/derrota/loot...")
        self.clear_loot_windows()
        return "finished"

    def check_and_recover_mana(self):
        screen = self.device.screenshot()
        pos_insuficiente = self.vision.find_template(screen, "templates/mana_insuficiente.png", threshold=0.9)

        if pos_insuficiente:
            print("  [💧] ¡Aviso de maná detectado! Usando botón de restauración...")
            pos_ok = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.9)
            if pos_ok:
                self.device.tap(int(pos_ok[0]), int(pos_ok[1]))
            else:
                self.device.tap(int(pos_insuficiente[0]), int(pos_insuficiente[1]))

            time.sleep(2)

            screen_pot = self.device.screenshot()
            pos_checkbox = self.vision.find_template(screen_pot, "templates/checkbox_mana.png", threshold=0.9)
            if pos_checkbox:
                print("   [+] Activando uso automático de pociones (Checkbox)...")
                self.device.tap(int(pos_checkbox[0]), int(pos_checkbox[1]))
                time.sleep(1.5)

            screen_cerrar = self.device.screenshot()
            self.cerrar_ventana(screen_cerrar)

            time.sleep(2)
            return True
        return False

    # ==========================================
    # CEREBRO PRINCIPAL (ORQUESTADOR)
    # ==========================================
    def execute(self, cuenta_name="Default"):
        self.cuenta_actual = cuenta_name
        print(f"\n [📜] Iniciando Rutina Diaria para: {self.cuenta_actual}")

        # OCR: Lectura inicial
        gemas_inicio = self.leer_gemas()
        print(f" [💎] Gemas al empezar: {gemas_inicio}")

        # === VALIDACIÓN FUENTE ===
        dia_actual = datetime.datetime.now().day
        if dia_actual in [14, 15, 30, 31]:
            if not self.modulo_completado("fountain"):
                print(f"  [📅] Día {dia_actual}. Activando Lucky Fountain!")
                self.do_lucky_fountain()
            else:
                print(f"  [📅] Lucky Fountain ya fue completada hoy para esta cuenta.")

        # === EJECUCIÓN DINÁMICA POR ESTADO ===
        modulos = [
            ("tower", self.do_tower_of_trials, "Tower of Trials"),
            ("alliance", self.do_alliance_quest, "Misiones de Gremio"),
            ("arena", self.do_arena, "Arena"),
            ("summons", self.do_summons, "Invocaciones"),
            ("mana", self.do_spend_mana, "Gasto de Maná"),
            ("rewards", self.claim_all_rewards, "Reclamo de Recompensas"),
        ]

        for key, func, label in modulos:
            if not self.modulo_completado(key):
                func()
                self.actualizar_modulo(key)
            else:
                print(f" [⏭️] Saltando {label} (Ya completado).")

        # OCR: Lectura final y balance
        gemas_fin = self.leer_gemas()
        diferencia = gemas_fin - gemas_inicio

        print("\n" + "=" * 40)
        print(f" 📊 REPORTE CONTABLE - {self.cuenta_actual}")
        print("=" * 40)
        print(f"  💎 Gemas iniciales : {gemas_inicio}")
        print(f"  💎 Gemas finales   : {gemas_fin}")
        print(f"  📈 Ganancia Neta   : {'+' if diferencia >= 0 else ''}{diferencia} gemas")
        print("=" * 40)

        print(f" [✅] Rutina Diaria completada para {self.cuenta_actual}!")
        return True

    # ==========================================
    # MÓDULOS DE JUEGO
    # ==========================================
    def do_lucky_fountain(self):
        print("\n [⛲] Modulo: Lucky Fountain")
        screen = self.device.screenshot()
        pos_fountain_home = self.vision.find_template(screen, "templates/btn_fountain_home.png", threshold=0.95)
        if pos_fountain_home:
            self.device.tap(int(pos_fountain_home[0]), int(pos_fountain_home[1]))
            time.sleep(3)

        for fase in range(1, 5):
            screen = self.device.screenshot()
            pos_offer = self.vision.find_template(screen, "templates/btn_fountain_offer.png", threshold=0.8)
            if pos_offer:
                print(f"   [+] Tirando en la fase {fase}/4...")
                self.device.tap(int(pos_offer[0]), int(pos_offer[1]))
                time.sleep(4)
                self.clear_loot_windows()
                time.sleep(1)
            else:
                print("   [!] No se puede tirar más (Botón no detectado o gemas insuficientes).")
                break

        print("   [<] Cerrando Lucky Fountain...")
        self.cerrar_ventana()

        self.return_to_home()
        self.actualizar_modulo("fountain")

    def do_premium_summons(self):
        print("\n [🌠] Modulo: Invocación de Personajes (Premium)")
        screen = self.device.screenshot()
        pos_x10 = self.vision.find_template(screen, "templates/btn_summon_x10.png", threshold=0.8)

        if not pos_x10:
            print("  ❌ No se encontró el botón de Invocación x10. ¿Estás en el banner correcto?")
            return

        self.device.tap(int(pos_x10[0]), int(pos_x10[1]))
        time.sleep(1.5)

        screen = self.device.screenshot()
        pos_confirm = self.vision.find_template(screen, "templates/btn_confirm_summon.png", threshold=0.8)
        if pos_confirm:
            print("   [+] Confirmando gasto de gemas...")
            self.device.tap(int(pos_confirm[0]), int(pos_confirm[1]))
            self._limpiar_invocacion()
        else:
            print("  ❌ No apareció la ventana de confirmación.")
            return
        print("  [✅] Invocación completada.")

    def do_tower_of_trials(self):
        print("\n [🗼] Modulo: Tower of Trials")
        screen = self.device.screenshot()
        pos_tot = self.vision.find_template(screen, "templates/btn_tot_home.png", threshold=0.9)
        if not pos_tot:
            print("  ❌ No se encontró el botón de Tower of Trials.")
            return

        self.device.tap(int(pos_tot[0]), int(pos_tot[1]))
        time.sleep(5)

        print("  [🎁] Reclamando cofre...")
        screen = self.device.screenshot()
        pos_chest = self.vision.find_template(screen, "templates/btn_tot_chest.png", threshold=0.9)
        if pos_chest:
            self.device.tap(int(pos_chest[0]), int(pos_chest[1] - 45))
            time.sleep(2)
            self.clear_loot_windows()

        print("  [⏩] Acelerando (Fast Forward)...")
        screen = self.device.screenshot()
        pos_ff_menu = self.vision.find_template(screen, "templates/btn_fast_forward_menu.png", threshold=0.9)
        if pos_ff_menu:
            self.device.tap(int(pos_ff_menu[0]), int(pos_ff_menu[1]))
            time.sleep(3)

            acels = 0
            intentos_flecha = 0
            while acels < 2 and intentos_flecha < 3:
                screen = self.device.screenshot()
                pos_green = self.vision.find_template(screen, "templates/btn_ff_green.png", threshold=0.9)
                if pos_green:
                    self.device.tap(int(pos_green[0]), int(pos_green[1]))
                    time.sleep(2)
                    self.clear_loot_windows()
                    acels += 1
                else:
                    pos_arrow = self.vision.find_template(screen, "templates/btn_ff_arrow.png", threshold=0.9)
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
            self.clear_loot_windows()
            screen = self.device.screenshot()
            pos_explore = self.vision.find_template(screen, "templates/btn_explore.png", threshold=0.9)
            if pos_explore:
                self.device.tap(int(pos_explore[0]), int(pos_explore[1]))
                time.sleep(3)
                self.clear_loot_windows()
            else:
                break

        print("  [⚔️] Desafiando Jefe...")
        reintentos = 0
        while reintentos < 3:
            screen = self.device.screenshot()
            pos_boss = self.vision.find_template(screen, "templates/btn_challenge_boss.png", threshold=0.9)
            if pos_boss:
                self.device.tap(int(pos_boss[0]), int(pos_boss[1]))
                resultado = self.handle_battle_sequence()
                if resultado == "draw":
                    reintentos += 1
                    print(f"   [🔄] Reintentando Jefe Torre por empate ({reintentos}/3)...")
                    time.sleep(2)
                else:
                    break
            else:
                break

        if reintentos == 3:
            print("   [⚠️] Límite de empates alcanzado en la Torre.")

        self.return_to_home()

    def do_alliance_quest(self):
        print("\n [🛡️] Modulo: Misiones de Gremio")
        screen = self.device.screenshot()
        pos_bw = self.vision.find_template(screen, "templates/btn_battalion_warfare.png", threshold=0.9)
        if not pos_bw:
            return
        self.device.tap(int(pos_bw[0]), int(pos_bw[1]))
        time.sleep(2)

        screen = self.device.screenshot()
        pos_aq = self.vision.find_template(screen, "templates/btn_alliance_quest.png", threshold=0.9)
        if pos_aq:
            self.device.tap(int(pos_aq[0]), int(pos_aq[1]))
            time.sleep(2)

        screen = self.device.screenshot()
        print("  [🗡️] F2P: Usando Challenge Boss individual.")
        pos_challenge = self.vision.find_template(screen, "templates/btn_challenge_boss_2.png", threshold=0.9)
        if pos_challenge:
            self.device.tap(int(pos_challenge[0]), int(pos_challenge[1]))
            self.handle_battle_sequence()

            print("  [>] Limpiando pantallas post-batalla a la derecha...")
            for _ in range(3):
                self.device.tap(2200, 500)
                time.sleep(1)

        print("  [🔙] Volviendo atrás para Arena...")
        self.cerrar_ventana()

    def do_arena(self):
        print("\n [🏟️] Modulo: Arena (5 Batallas)")
        screen = self.device.screenshot()
        pos_arena = self.vision.find_template(screen, "templates/arena.png", threshold=0.9)
        if not pos_arena:
            print("  ❌ No se encontró el ícono de Arena en el Home.")
            return

        self.device.tap(int(pos_arena[0]), int(pos_arena[1]))
        time.sleep(4)

        screen = self.device.screenshot()
        arenas = self.vision.find_all_templates(screen, "templates/btn_arena.png", threshold=0.9)
        if not arenas:
            print("  ❌ No se encontraron los modos de Arena.")
            self.return_to_home()
            return

        arenas.sort(key=lambda pos: pos[0])
        desplazamiento_y = 190

        print("  [>] Gema detectada. Dando clic al botón de Arena inferior...")
        self.device.tap(int(arenas[0][0]), int(arenas[0][1] + desplazamiento_y))
        time.sleep(3)

        print("  [⚔️] Iniciando los 5 combates diarios...")
        for i in range(5):
            print(f"   [🥊] Combate {i + 1}/5...")
            reintentos = 0
            while reintentos < 3:
                screen = self.device.screenshot()
                oponentes = self.vision.find_all_templates(screen, "templates/challenge_area.png", threshold=0.9)
                if not oponentes:
                    print("   [!] No se encontraron oponentes o botón de desafío.")
                    break

                oponentes.sort(key=lambda pos: pos[1])
                self.device.tap(int(oponentes[0][0]), int(oponentes[0][1]))

                resultado = self.handle_battle_sequence()
                if resultado == "draw":
                    reintentos += 1
                    print(f"   [🔄] Reintentando por empate ({reintentos}/3)...")
                    time.sleep(2)
                else:
                    break

            if reintentos == 3:
                print("   [⚠️] Límite de empates alcanzado. Avanzando al siguiente.")
            time.sleep(2)

        print("  [✅] Rutina de Arena finalizada.")
        self.return_to_home()

    def do_summons(self):
        print("\n [🌟] Modulo: Invocaciones")
        screen = self.device.screenshot()
        pos_nav = self.vision.find_template(screen, "templates/btn_summon_nav.png", threshold=0.9)
        if not pos_nav:
            return
        self.device.tap(int(pos_nav[0]), int(pos_nav[1]))
        time.sleep(3)

        encontrado = False
        intentos = 0
        while not encontrado and intentos < 5:
            screen = self.device.screenshot()
            pos_x1_free = self.vision.find_template(screen, "templates/btn_summon_x1_free.png", threshold=0.9)

            if pos_x1_free:
                encontrado = True
            else:
                pos_arrow = self.vision.find_template(screen, "templates/btn_summon_arrow_left.png", threshold=0.9)
                if pos_arrow:
                    self.device.tap(int(pos_arrow[0]), int(pos_arrow[1]))
                    time.sleep(1.5)
                intentos += 1

        if encontrado:
            print("  [>] Tirando summons gratis...")
            screen = self.device.screenshot()
            pos_chest = self.vision.find_template(screen, "templates/btn_friend_chest.png", threshold=0.9)
            if pos_chest:
                print("   [+] Cofre detectado.")
                self.device.tap(int(pos_chest[0]), int(pos_chest[1]))
                time.sleep(1)
                self.clear_loot_windows()

            screen = self.device.screenshot()
            pos_x1 = self.vision.find_template(screen, "templates/btn_summon_x1_free.png", threshold=0.9)
            if pos_x1:
                print("   [+] Lanzando Invocación x1...")
                self.device.tap(int(pos_x1[0]), int(pos_x1[1]))
                self._limpiar_invocacion()

            screen = self.device.screenshot()
            pos_x10 = self.vision.find_template(screen, "templates/btn_summon_x10_free.png", threshold=0.9)
            if pos_x10:
                print("   [+] Lanzando Invocación x10...")
                self.device.tap(int(pos_x10[0]), int(pos_x10[1]))
                self._limpiar_invocacion()

        screen = self.device.screenshot()
        pos_back_summon = self.vision.find_template(screen, "templates/btn_back_summon.png", threshold=0.9)
        if pos_back_summon:
            print("  [🏠] Saliendo del menú de invocaciones...")
            self.device.tap(int(pos_back_summon[0]), int(pos_back_summon[1]))
            time.sleep(3)
        else:
            self.cerrar_ventana(screen)

        self.return_to_home()

    def do_spend_mana(self):
        print("\n [💧] Modulo: Gastar Maná (Sweep Dinámico de Eventos)")

        # Leemos la pantalla principal en busca de todos los eventos activos
        screen = self.device.screenshot()
        eventos = self.vision.find_all_templates(screen, "templates/label_ends_in.png", threshold=0.8)

        if not eventos:
            print("  ❌ No se encontraron banners de eventos activos bajo Battalion Warfare.")
            return

        # Ordenar los eventos detectados de arriba hacia abajo
        eventos.sort(key=lambda pos: pos[1])
        mana_agotado = False

        for idx, pos_evento in enumerate(eventos):
            if mana_agotado:
                print("  [💧] El maná se agotó. Deteniendo barrido en otros eventos.")
                break

            print(f"\n  [>] Entrando al evento activo #{idx + 1} de la lista...")
            self.device.tap(int(pos_evento[0]), int(pos_evento[1]))
            time.sleep(4)

            etapas = ["stage_ex_10.png", "stage_ex_9.png", "stage_ex_8.png"]
            etapa_encontrada = False

            for etapa in etapas:
                screen_evento = self.device.screenshot()
                pos_stage = self.vision.find_template(screen_evento, f"templates/{etapa}", threshold=0.95)
                if pos_stage:
                    print(f"  [🔍] Etapa de mayor nivel detectada: {etapa.replace('.png', '')}")
                    self.device.tap(int(pos_stage[0]), int(pos_stage[1]))
                    time.sleep(3)
                    etapa_encontrada = True
                    break

            if not etapa_encontrada:
                print("  [i] No hay etapas EX configuradas en este evento o no están desbloqueadas. Saliendo...")
                self.return_to_home()
                time.sleep(2)
                continue

            print("  [⏩] Ejecutando Sweeps en bucle hasta que no se pueda más...")
            for i in range(3):
                screen_sweep = self.device.screenshot()
                pos_sweep = self.vision.find_template(screen_sweep, "templates/btn_sweep.png", threshold=0.9)

                if pos_sweep:
                    self.device.tap(int(pos_sweep[0]), int(pos_sweep[1]))
                    time.sleep(1.5)

                    if self.check_and_recover_mana():
                        self.device.tap(int(pos_sweep[0]), int(pos_sweep[1]))
                        time.sleep(1.5)

                    print(f"   [+] Sweep múltiple completado (Set #{i + 1}).")
                    time.sleep(2)
                    self.clear_loot_windows()
                else:
                    print("   [!] Botón Sweep no detectado. Probablemente te quedaste sin maná.")
                    mana_agotado = True
                    break

            print(f"  [🏠] Saliendo del evento #{idx + 1}...")
            for _ in range(2):
                self.cerrar_ventana()

            self.return_to_home()
            time.sleep(2)

    def claim_all_rewards(self):
        print("\n [🎁] Modulo: Reclamar Recompensas")
        screen = self.device.screenshot()
        pos_arrow_down = self.vision.find_template(screen, "templates/btn_menu_arrow_down.png", threshold=0.9)
        if pos_arrow_down:
            self.device.tap(int(pos_arrow_down[0]), int(pos_arrow_down[1]))
            time.sleep(1.5)

        screen = self.device.screenshot()
        pos_mail = self.vision.find_template(screen, "templates/btn_mailbox_icon.png", threshold=0.9)
        if pos_mail:
            self.device.tap(int(pos_mail[0]), int(pos_mail[1]))
            time.sleep(2)

            screen = self.device.screenshot()
            pos_claim = self.vision.find_template(screen, "templates/btn_claim_all.png", threshold=0.9)
            if pos_claim:
                self.device.tap(int(pos_claim[0]), int(pos_claim[1]))
                time.sleep(2)
                self.clear_loot_windows()

            self.cerrar_ventana()

        screen = self.device.screenshot()
        pos_arrow_down = self.vision.find_template(screen, "templates/btn_menu_arrow_down.png", threshold=0.9)
        if pos_arrow_down:
            self.device.tap(int(pos_arrow_down[0]), int(pos_arrow_down[1]))
            time.sleep(1.5)

        screen = self.device.screenshot()
        pos_missions = self.vision.find_template(screen, "templates/btn_missions_icon.png", threshold=0.9)
        if pos_missions:
            self.device.tap(int(pos_missions[0]), int(pos_missions[1]))
            time.sleep(2)

            screen = self.device.screenshot()
            pos_tab_daily = self.vision.find_template(screen, "templates/tab_daily.png", threshold=0.9)
            if pos_tab_daily:
                self.device.tap(int(pos_tab_daily[0]), int(pos_tab_daily[1]))
                time.sleep(1.5)

            print("  [>] Iniciando barrido total de misiones y cofres...")
            intentos_vacios = 0
            while intentos_vacios < 2:
                algo_reclamado = False
                screen = self.device.screenshot()

                pos_claim = self.vision.find_template(screen, "templates/btn_claim_all.png", threshold=0.9)
                if pos_claim:
                    print("   [+] Misiones listas. Reclamando...")
                    self.device.tap(int(pos_claim[0]), int(pos_claim[1]))
                    time.sleep(2)
                    self.clear_loot_windows()
                    algo_reclamado = True

                if not algo_reclamado:
                    pos_chest = self.vision.find_template(screen, "templates/chest_ready.png", threshold=0.9)
                    if pos_chest:
                        print("   [+] Cofre listo. Reclamando...")
                        self.device.tap(int(pos_chest[0]), int(pos_chest[1]))
                        time.sleep(2)
                        self.clear_loot_windows()
                        algo_reclamado = True

                if algo_reclamado:
                    intentos_vacios = 0
                else:
                    intentos_vacios += 1
                    time.sleep(1.5)

            print("  [✅] Barrido completado. No se quedó nada atrás.")

        self.return_to_home()