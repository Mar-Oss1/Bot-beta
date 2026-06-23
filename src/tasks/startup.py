import time
import os

class Startup:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision
        # Asegurar que exista la carpeta de debug
        self.debug_dir = "screenshots/debug_startup"
        os.makedirs(self.debug_dir, exist_ok=True)

    def execute(self):
        print("\n[🚀] Iniciando secuencia de entrada al juego...")
        max_intentos = 15
        intentos = 0

        while intentos < max_intentos:
            # --- ¡AQUÍ ESTÁ LA MAGIA NUEVA! ---
            # 0. Revisar primero si saltó el evento de regreso
            if self.handle_comeback_bonus():
                # Si lo resolvió, damos una pausa y volvemos a escanear la pantalla limpia
                time.sleep(2)
                continue

            screen = self.device.screenshot()
            algo_encontrado = False

            # 1. ¿Ya estamos a salvo en el menú?
            if self.vision.find_template(screen, "templates/indicador_menu.png", threshold=0.8):
                print("✅ ¡Menú principal detectado! Estamos dentro.")
                return True

            # 2. ¿Salió algún evento o bono que requiere reclamar?
            pos_claim = self.vision.find_template(screen, "templates/btn_claim.png")
            if pos_claim:
                print(" [+] Reclamando botón universal...")
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(2)
                algo_encontrado = True

            # 3. ¿Hay alguna ventana emergente con una 'X'?
            if not algo_encontrado:
                pos_x = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.65)
                if pos_x:
                    print(" [-] Cerrando anuncio/banner...")
                    self.device.tap(pos_x[0], pos_x[1])
                    time.sleep(2)
                    algo_encontrado = True

            # 4. ¿Son las recompensas de Login o la pantalla de título?
            if not algo_encontrado:
                pos_login = self.vision.find_template(screen, "templates/recompensa_login.png")
                pos_titulo = self.vision.find_template(screen, "templates/pantalla_titulo.png")

                if pos_login or pos_titulo:
                    algo_encontrado = True
                    if pos_titulo:
                        print(" [>] Dando Start al juego...")
                        self.device.tap(pos_titulo[0], pos_titulo[1])
                    else:
                        print(" [>] Saltando animación de recompensas...")
                        self.device.tap(100, 800)
                    time.sleep(3)

            # --- LÓGICA DE ESPIONAJE ---
            if not algo_encontrado:
                print(f"⏳ Intento {intentos+1}: No reconozco nada. Guardando evidencia...")
                debug_path = os.path.join(self.debug_dir, f"debug_vuelta_{intentos+1}.png")
                screen.save(debug_path)
                time.sleep(2)
            else:
                intentos = 0 # Reiniciar intentos si encontramos algo, para dar más tiempo

            intentos += 1

        print("❌ No se pudo llegar al menú principal. Atascado.")
        self.device.screenshot("screenshots/error_final.png")
        return False

    def handle_comeback_bonus(self):
        # Tomamos captura para ver si estamos en la pantalla de regreso
        screen = self.device.screenshot()
        pos_claim = self.vision.find_template(screen, "templates/btn_claim_comeback.png", threshold=0.75)

        if pos_claim:
            print(" [🎁] ¡Evento de Regreso detectado! Reclamando recompensas...")

            # Ciclo para reclamar todas las pestañas que tengan puntito rojo
            max_pestanas = 3  # Por si acaso hay más de 2
            for i in range(max_pestanas):
                screen = self.device.screenshot()

                # 1. Buscar si hay una pestaña con puntito rojo sin reclamar
                pos_tab = self.vision.find_template(screen, "templates/tab_comeback_red.png", threshold=0.75)
                if pos_tab:
                    print(f"  [>] Tocando pestaña con recompensa ({i + 1})...")
                    self.device.tap(pos_tab[0], pos_tab[1])
                    time.sleep(1.5)  # Esperar a que cambie la pestaña

                # 2. Buscar y tocar el botón de reclamar
                screen = self.device.screenshot()
                pos_claim_actual = self.vision.find_template(screen, "templates/btn_claim_comeback.png", threshold=0.75)

                if pos_claim_actual:
                    print("  [>] Presionando botón de Reclamar...")
                    self.device.tap(pos_claim_actual[0], pos_claim_actual[1])
                    time.sleep(2)  # Esperar a que salgan los regalos

                    # 3. Hacer taps ciegos en el centro para saltar la animación
                    print("  [>] Saltando animación de regalos...")
                    self.device.tap(500, 500)
                    time.sleep(1)
                    self.device.tap(500, 500)
                    time.sleep(2)
                else:
                    # Si ya no hay botón de reclamar en la pestaña actual, rompemos el ciclo
                    break

            print(" [✓] Evento de Regreso completado. Saliendo del menú...")

            # 4. PASO NUEVO: Salir de la ventana presionando "Back"
            screen = self.device.screenshot()
            pos_back = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.75)
            if pos_back:
                print("  [>] Tocando botón 'Back'...")
                self.device.tap(pos_back[0], pos_back[1])
                time.sleep(3)  # Pausa para que termine la transición a la pantalla de inicio
            else:
                print("  [!] No vi el botón 'Back', intentando un tap en la esquina izquierda...")
                # Coordenadas a ciegas donde suele estar el botón Back (ajústalas si es necesario)
                self.device.tap(150, 950)
                time.sleep(3)

            return True

        return False