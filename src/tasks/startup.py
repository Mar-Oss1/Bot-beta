import time
import os


class Startup:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision
        self.debug_dir = "screenshots/debug_startup"
        os.makedirs(self.debug_dir, exist_ok=True)

    def execute(self):
        print("\n[🚀] Iniciando secuencia de entrada (con pausa de seguridad)...")
        max_intentos = 10
        intentos = 0

        while intentos < max_intentos:
            if self.handle_comeback_bonus():
                time.sleep(2)
                continue

            screen = self.device.screenshot()
            algo_encontrado = False

            # 1. ¿Salió algún evento o bono?
            pos_claim = self.vision.find_template(screen, "templates/btn_claim.png", threshold=0.8)
            if pos_claim:
                print(" [+] Reclamando botón universal...")
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(2)
                algo_encontrado = True

            # 2. ¿Hay ventana emergente con 'X'?
            if not algo_encontrado:
                pos_x = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
                if pos_x:
                    print(" [-] Cerrando anuncio/banner...")
                    self.device.tap(pos_x[0], pos_x[1])
                    time.sleep(2)
                    algo_encontrado = True

            # 3. ¿Login o Pantalla de inicio?
            if not algo_encontrado:
                pos_login = self.vision.find_template(screen, "templates/recompensa_login.png", threshold=0.8)
                pos_titulo = self.vision.find_template(screen, "templates/pantalla_titulo.png", threshold=0.8)
                if pos_login or pos_titulo:
                    algo_encontrado = True
                    if pos_titulo:
                        print(" [>] Dando Start al juego...")
                        self.device.tap(pos_titulo[0], pos_titulo[1])
                    else:
                        print(" [>] Saltando animación de recompensas...")
                        self.device.tap(100, 800)
                    time.sleep(3)

            # --- LA NUEVA PAUSA DE SEGURIDAD ---
            if not algo_encontrado:
                print(" [i] Pantalla aparentemente limpia. Esperando 3 segundos por banners tardíos...")
                time.sleep(6)

                # Re-escanear después de la pausa para estar 100% seguros
                screen_final = self.device.screenshot()
                if self.vision.find_template(screen_final, "templates/btn_cerrar_x.png", threshold=0.8) or \
                        self.vision.find_template(screen_final, "templates/btn_claim.png", threshold=0.8):
                    print(" [!] ¡Detecté un banner tras la pausa! Repitiendo ciclo...")
                    continue

                print(" [✅] Pantalla confirmada limpia. Estamos dentro.")
                return True

            intentos += 1

        return False

    def handle_comeback_bonus(self):
        eventos_reclamados = False
        MAX_SCROLLS = 5

        # ── Página 1: Returner's Bonus ─────────────────────────────────────
        while True:
            screen = self.device.screenshot()
            pos_claim = self.vision.find_template(screen, "templates/btn_claim_comeback.png", threshold=0.8)

            if pos_claim:
                print("  [🎁] Bonus detectado! Reclamando...")
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(3)

                print("  [🎁] Cerrando loot...")
                self.device.tap(100, 100)
                time.sleep(1.5)
                self.device.tap(100, 100)
                time.sleep(2)

                eventos_reclamados = True

            else:
                # Solo scrolleamos si ya reclamamos algo (estamos dentro del menú)
                if not eventos_reclamados:
                    break

                scroll_exitoso = False
                for intento_scroll in range(1, MAX_SCROLLS + 1):
                    print(f"  [🔄] Scroll #{intento_scroll} buscando más en Bonus...")
                    self.device.swipe(1840, 740, 1840, 240, duration=0.4)
                    time.sleep(1.5)

                    screen = self.device.screenshot()
                    pos_claim = self.vision.find_template(
                        screen, "templates/btn_claim_comeback.png", threshold=0.8
                    )

                    if pos_claim:
                        print("  [🎁] Claim encontrado tras scroll! Reclamando...")
                        self.device.tap(pos_claim[0], pos_claim[1])
                        time.sleep(3)
                        self.device.tap(100, 100)
                        time.sleep(1.5)
                        self.device.tap(100, 100)
                        time.sleep(2)
                        eventos_reclamados = True
                        scroll_exitoso = True
                        break

                if not scroll_exitoso:
                    print(f"  [i] Bonus agotado tras {MAX_SCROLLS} scrolls.")
                    break

        # ── Página 2: Returner's Pass ──────────────────────────────────────
        if eventos_reclamados:
            print("  [📋] Navegando a Returner's Pass...")
            screen = self.device.screenshot()
            pos_pass = self.vision.find_template(
                screen, "templates/btn_returner_pass.png", threshold=0.8
            )

            if pos_pass:
                self.device.tap(pos_pass[0], pos_pass[1])
                time.sleep(2)
                for intento_scroll in range(MAX_SCROLLS + 1):
                    screen = self.device.screenshot()
                    pos_claim = self.vision.find_template(
                        screen, "templates/btn_claim_comeback.png", threshold=0.8
                    )

                    if pos_claim:
                        print("  [🎁] Pass: Claim encontrado! Reclamando...")
                        self.device.tap(pos_claim[0], pos_claim[1])
                        time.sleep(3)
                        self.device.tap(100, 100)
                        time.sleep(1.5)
                        self.device.tap(100, 100)
                        time.sleep(2)
                        # Reset scroll para seguir buscando desde arriba
                        intento_scroll = 0
                    else:
                        if intento_scroll < MAX_SCROLLS:
                            print(f"  [🔄] Scroll #{intento_scroll + 1} en Pass...")
                            self.device.swipe(1840, 740, 1840, 240, duration=0.4)
                            time.sleep(1.5)
                        else:
                            print("  [i] Pass agotado.")
                            break
            else:
                print("  [!] No se encontró Returner's Pass en el menú. Saltando.")

        # ── Salir del menú comeback ────────────────────────────────────────
        if eventos_reclamados:
            print("  [🎁] Todas las recompensas reclamadas. Saliendo del menú...")
            self.device.d.press("back")
            time.sleep(3)
            return True

        return False
