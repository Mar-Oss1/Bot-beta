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

        for intento in range(max_intentos):
            if self.handle_comeback_bonus():
                time.sleep(1.5)
                continue

            screen = self.device.screenshot()
            algo_encontrado = False

            # Buscar claim, X, login o título en UN screenshot
            result = self.vision.find_any(screen, [
                "templates/btn_claim.png",
                "templates/btn_cerrar_x.png",
                "templates/recompensa_login.png",
                "templates/pantalla_titulo.png",
            ], threshold=0.8)

            if result:
                template, x, y = result
                algo_encontrado = True

                if "claim" in template:
                    log.debug("[+] Reclamando botón universal...")
                    self.device.tap(x, y)
                    time.sleep(1.5)
                elif "cerrar_x" in template:
                    log.debug("[-] Cerrando anuncio/banner...")
                    self.device.tap(x, y)
                    time.sleep(1.5)
                elif "pantalla_titulo" in template:
                    log.debug("[>] Dando Start al juego...")
                    self.device.tap(x, y)
                    time.sleep(2.5)
                else:  # recompensa_login
                    log.debug("[>] Saltando animación de recompensas...")
                    self.device.tap(100, 800)
                    time.sleep(2.5)

            if not algo_encontrado:
                log.debug("[i] Pantalla aparentemente limpia. Verificando...")
                # Espera corta y doble verificación
                time.sleep(1.5)
                screen = self.device.screenshot()
                result = self.vision.find_any(screen, [
                    "templates/btn_cerrar_x.png",
                    "templates/btn_claim.png"
                ], threshold=0.8)

                if result:
                    log.warning("[!] Banner detectado tras 1.5s. Repitiendo...")
                    continue

                time.sleep(1)
                screen = self.device.screenshot()
                result = self.vision.find_any(screen, [
                    "templates/btn_cerrar_x.png",
                    "templates/btn_claim.png"
                ], threshold=0.8)

                if result:
                    log.warning("[!] Banner detectado tras 2.5s. Repitiendo...")
                    continue

                log.info("[✅] Pantalla confirmada limpia. Estamos dentro.")
                return True

        log.error("❌ Startup falló tras %d intentos.", max_intentos)
        return False

    def handle_comeback_bonus(self):
        eventos_reclamados = False
        MAX_SCROLLS = 3

        # ── Página 1: Returner's Bonus ──
        while True:
            screen = self.device.screenshot()
            pos_claim = self.vision.find_template(
                screen, "templates/btn_claim_comeback.png", threshold=0.8
            )
            if pos_claim:
                log.debug("  [🎁] Bonus detectado! Reclamando...")
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(2.5)
                self.device.tap(100, 100)
                time.sleep(1)
                self.device.tap(100, 100)
                time.sleep(1.5)
                eventos_reclamados = True
            else:
                if not eventos_reclamados:
                    break
                scroll_exitoso = False
                for intento_scroll in range(1, MAX_SCROLLS + 1):
                    log.debug("  [🔄] Scroll #%d en Bonus...", intento_scroll)
                    self.device.swipe(1840, 740, 1840, 240, duration=0.4)
                    time.sleep(1.2)
                    screen = self.device.screenshot()
                    pos_claim = self.vision.find_template(
                        screen, "templates/btn_claim_comeback.png", threshold=0.8
                    )
                    if pos_claim:
                        log.debug("  [🎁] Claim tras scroll! Reclamando...")
                        self.device.tap(pos_claim[0], pos_claim[1])
                        time.sleep(2.5)
                        self.device.tap(100, 100)
                        time.sleep(1)
                        self.device.tap(100, 100)
                        time.sleep(1.5)
                        eventos_reclamados = True
                        scroll_exitoso = True
                        break
                if not scroll_exitoso:
                    log.debug("  [i] Bonus agotado tras %d scrolls.", MAX_SCROLLS)
                    break

        # ── Página 2: Returner's Pass ──
        if eventos_reclamados:
            log.debug("  [📋] Navegando a Returner's Pass...")
            screen = self.device.screenshot()
            pos_pass = self.vision.find_template(
                screen, "templates/btn_returner_pass.png", threshold=0.8
            )
            if pos_pass:
                self.device.tap(pos_pass[0], pos_pass[1])
                time.sleep(1.5)
                for intento_scroll in range(MAX_SCROLLS + 1):
                    screen = self.device.screenshot()
                    pos_claim = self.vision.find_template(
                        screen, "templates/btn_claim_comeback.png", threshold=0.8
                    )
                    if pos_claim:
                        log.debug("  [🎁] Pass: Claim encontrado! Reclamando...")
                        self.device.tap(pos_claim[0], pos_claim[1])
                        time.sleep(2.5)
                        self.device.tap(100, 100)
                        time.sleep(1)
                        self.device.tap(100, 100)
                        time.sleep(1.5)
                        intento_scroll = 0
                    else:
                        if intento_scroll < MAX_SCROLLS:
                            log.debug("  [🔄] Scroll #%d en Pass...", intento_scroll + 1)
                            self.device.swipe(1840, 740, 1840, 240, duration=0.4)
                            time.sleep(1.2)
                        else:
                            log.debug("  [i] Pass agotado.")
                            break
            else:
                log.warning("  [!] No se encontró Returner's Pass.")

        # ── Salir del menú comeback ──
        if eventos_reclamados:
            log.debug("  [] Saliendo del menú comeback...")
            self.device.d.press("back")
            time.sleep(2.5)
            return True
        return False