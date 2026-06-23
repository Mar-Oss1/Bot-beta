import time


class ChangeAccount:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    def execute(self, serial_cuenta):
        print(f"\n[🔄] Iniciando cambio a la cuenta con código: {serial_cuenta}")
        max_intentos = 15
        intentos = 0

        while intentos < max_intentos:
            screen = self.device.screenshot()

            # 1. Buscar la nube en la pantalla de inicio
            pos_nube = self.vision.find_template(screen, "templates/btn_nube.png", threshold=0.75)

            if pos_nube:
                print(" [>] Ícono de nube detectado. Abriendo menú de restauración...")
                self.device.tap(pos_nube[0], pos_nube[1])
                time.sleep(3)  # Esperar a que se anime y abra la ventana

                # 2. Buscar el cuadro de texto y el botón verde
                screen = self.device.screenshot()
                pos_input = self.vision.find_template(screen, "templates/input_restore.png", threshold=0.75)
                pos_use = self.vision.find_template(screen, "templates/btn_use_code.png", threshold=0.75)

                if pos_input and pos_use:
                    print(" [>] Menú detectado. Activando teclado...")
                    self.device.tap(pos_input[0], pos_input[1])
                    time.sleep(1)  # Pequeña pausa para que el sistema abra su teclado

                    print(f" [>] Inyectando código: {serial_cuenta} ...")
                    self.device.d.send_keys(serial_cuenta)
                    time.sleep(1.5)

                    print(" [>] Código pegado. Confirmando (Use Code)...")
                    self.device.tap(pos_use[0], pos_use[1])
                    time.sleep(3)  # Esperamos al primer pop-up

                    # --- Confirmación 1: Restore Anyway (Opcional) ---
                    screen = self.device.screenshot()
                    pos_restore_anyway = self.vision.find_template(screen, "templates/btn_restore_anyway.png",
                                                                   threshold=0.75)
                    if pos_restore_anyway:
                        print(" [!] Pop-up de advertencia detectado. Dando a 'Restore Anyway'...")
                        self.device.tap(pos_restore_anyway[0], pos_restore_anyway[1])
                        time.sleep(3)  # Esperar a que salga el OK de éxito
                    else:
                        print(" [i] No salió 'Restore Anyway'.")

                    # --- Confirmación 2: Botón OK de éxito ---
                    screen = self.device.screenshot()
                    pos_ok = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.75)
                    if pos_ok:
                        print(" [!] Pop-up de éxito detectado. Dando a 'OK'...")
                        self.device.tap(pos_ok[0], pos_ok[1])
                    else:
                        print(" [i] No salió botón 'OK'.")

                    print(" [✓] Secuencia de cambio enviada. Esperando reinicio de Evertale (20 seg)...")
                    # Damos 20 segundos para que el juego descargue datos si es necesario y reinicie
                    time.sleep(20)
                    return True
                else:
                    print(" [!] No se encontró el cuadro de texto o el botón verde. Reintentando...")
                    time.sleep(2)
                    continue

            print("⏳ Esperando la pantalla de inicio con la nube...")
            time.sleep(2)
            intentos += 1

        print("❌ Atasco en el cambio de cuenta. Guardando evidencia...")
        self.device.screenshot("screenshots/error_cambio_cuenta.png")
        return False

