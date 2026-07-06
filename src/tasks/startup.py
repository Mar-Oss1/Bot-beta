import time
import os
from core.logger import get_logger

log = get_logger("startup")


class Startup:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision
        self.debug_dir = "screenshots/debug_startup"
        os.makedirs(self.debug_dir, exist_ok=True)

    def execute(self):
        log.info("🚀 Iniciando secuencia de entrada...")
        max_intentos = 15
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
                log.debug("[+] Reclamando botón universal...")
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(2)
                algo_encontrado = True

            # 2. ¿Hay ventana emergente con 'X'?
            if not algo_encontrado:
                pos_x = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
                if pos_x:
                    log.debug("[-] Cerrando anuncio/banner...")
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
                        log.debug("[>] Dando Start al juego...")
                        self.device.tap(pos_titulo[0], pos_titulo[1])
                    else:
                        log.debug("[>] Saltando animación de recompensas...")
                        self.device.tap(100, 800)
                    time.sleep(3)

            # --- PAUSA DE SEGURIDAD OPTIMIZADA ---
            if not algo_encontrado:
                log.debug("[i] Pantalla aparentemente limpia. Verificando banners tardíos...")

                # Esperar solo 2 segundos en lugar de 6
                time.sleep(2)

                # Verificación 1
                screen_final = self.device.screenshot()
                banner_tardio = (
                        self.vision.find_template(screen_final, "templates/btn_cerrar_x.png", threshold=0.8) or
                        self.vision.find_template(screen_final, "templates/btn_claim.png", threshold=0.8)
                )

                if banner_tardio:
                    log.warning("[!] ¡Detecté un banner tras 2s! Repitiendo ciclo...")
                    continue

                # Verificación 2 (solo si la primera pasó)
                time.sleep(1)
                screen_final_2 = self.device.screenshot()
                banner_tardio_2 = (
                        self.vision.find_template(screen_final_2, "templates/btn_cerrar_x.png", threshold=0.8) or
                        self.vision.find_template(screen_final_2, "templates/btn_claim.png", threshold=0.8)
                )

                if banner_tardio_2:
                    log.warning("[!] ¡Detecté un banner tras 3s! Repitiendo ciclo...")
                    continue

                log.info("[✅] Pantalla confirmada limpia. Estamos dentro.")
                return True

            intentos += 1

        log.error("❌ Startup falló tras %d intentos.", max_intentos)
        return False

    def handle_comeback_bonus(self):
        eventos_reclamados = False
        MAX_SCROLLS = 5

        # ── Página 1: Returner's Bonus ────────────────────────────────────
        while True:
            screen = self.device.screenshot()
            pos_claim = self.vision.find_template(screen, "templates/btn_claim_comeback.png", threshold=0.8)
            if pos_claim:
                log.debug("  [🎁] Bonus detectado! Reclamando...")
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(3)
                log.debug("  [🎁] Cerrando loot...")
                self.device.tap(100, 100)
                time.sleep(1.5)
                self.device.tap(100, 100)
                time.sleep(2)
                eventos_reclamados = True
            else:
                if not eventos_reclamados:
                    break
                scroll_exitoso = False
                for intento_scroll in range(1, MAX_SCROLLS + 1):
                    log.debug("  [🔄] Scroll #%d buscando más en Bonus...", intento_scroll)
                    self.device.swipe(1840, 740, 1840, 240, duration=0.4)
                    time.sleep(1.5)
                    screen = self.device.screenshot()
                    pos_claim = self.vision.find_template(
                        screen, "templates/btn_claim_comeback.png", threshold=0.8
                    )
                    if pos_claim:
                        log.debug("  [🎁] Claim encontrado tras scroll! Reclamando...")
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
                    log.debug("  [i] Bonus agotado tras %d scrolls.", MAX_SCROLLS)
                    break

        # ── Página 2: Returner's Pass ──────────────────────────────────────
        if eventos_reclamados:
            log.debug("  [📋] Navegando a Returner's Pass...")
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
                        log.debug("  [🎁] Pass: Claim encontrado! Reclamando...")
                        self.device.tap(pos_claim[0], pos_claim[1])
                        time.sleep(3)
                        self.device.tap(100, 100)
                        time.sleep(1.5)
                        self.device.tap(100, 100)
                        time.sleep(2)
                        intento_scroll = 0
                    else:
                        if intento_scroll < MAX_SCROLLS:
                            log.debug("  [🔄] Scroll #%d en Pass...", intento_scroll + 1)
                            self.device.swipe(1840, 740, 1840, 240, duration=0.4)
                            time.sleep(1.5)
                        else:
                            log.debug("  [i] Pass agotado.")
                            break
            else:
                log.warning("  [!] No se encontró Returner's Pass en el menú. Saltando.")

        # ── Salir del menú comeback ────────────────────────────────────────
        if eventos_reclamados:
            log.debug("  [] Todas las recompensas reclamadas. Saliendo del menú...")
            self.device.d.press("back")
            time.sleep(3)
            return True
        return False