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

        # Bucle infinito para aspirar TODAS las recompensas de regreso
        while True:
            screen = self.device.screenshot()
            pos_claim = self.vision.find_template(screen, "templates/btn_claim_comeback.png", threshold=0.8)

            if pos_claim:
                print("  [🎁] ¡Evento de Regreso detectado! Dándole clic a Reclamar...")
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(3)  # Esperamos a que salga la pantalla de loot

                # Toques en la esquina superior izquierda (100, 100) para no tocar items
                print("  [🎁] Tocando la esquina para cerrar el loot...")
                self.device.tap(100, 100)
                time.sleep(1.5)
                self.device.tap(100, 100)  # Doble toque por seguridad
                time.sleep(2)

                eventos_reclamados = True
            else:
                # Si ya no hay botones de claim en la pantalla, rompemos el bucle
                break

        # Si logramos reclamar al menos una cosa, salimos del menú de Regreso
        if eventos_reclamados:
            print("  [🎁] Todas las recompensas reclamadas. Saliendo del menú...")
            self.device.d.press("back")
            time.sleep(3)
            return True

        return False