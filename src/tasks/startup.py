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
        max_intentos = 18

        for intento in range(max_intentos):
            screen = self.device.screenshot()

            if self.handle_comeback_bonus(screen):
                time.sleep(0.6)
                continue

            # Buscar claim, X, login o título sobre la MISMA captura
            result = self.vision.find_any(screen, [
                "templates/btn_claim.png",
                "templates/btn_cerrar_x.png",
                "templates/recompensa_login.png",
                "templates/pantalla_titulo.png",
            ], threshold=0.8, zona="COMPLETA")

            if result:
                template, x, y = result

                if "claim" in template:
                    log.debug("[+] Reclamando botón universal...")
                    self.device.tap(x, y)
                    time.sleep(0.6)
                elif "cerrar_x" in template:
                    log.debug("[-] Cerrando anuncio/banner...")
                    self.device.tap(x, y)
                    time.sleep(0.6)
                elif "pantalla_titulo" in template:
                    log.debug("[>] Dando Start al juego...")
                    self.device.tap(x, y)
                    time.sleep(1.0)
                else:  # recompensa_login
                    log.debug("[>] Saltando animación de recompensas...")
                    self.device.tap(100, 800)
                    time.sleep(0.8)
                continue

            # Si no hay popups, verificamos si YA estamos en el Home (barra inferior visible)
            en_home = self.vision.find_any(screen, [
                "templates/btn_summon_nav.png",
                "templates/btn_tot_home.png",
                "templates/btn_battalion_warfare.png"
            ], threshold=0.8, zona="MITAD_INFERIOR")

            if en_home:
                # Verificación rápida (0.6s en vez de 2.5s) por si salta un banner tardío
                time.sleep(0.6)
                screen_check = self.device.screenshot()
                popup_tardio = self.vision.find_any(screen_check, [
                    "templates/btn_cerrar_x.png",
                    "templates/btn_claim.png",
                    "templates/btn_claim_comeback.png"
                ], threshold=0.8, zona="COMPLETA")

                if popup_tardio:
                    log.warning("[!] Banner tardío detectado. Limpiando...")
                    continue

                log.info("[✅] Home confirmado y limpio. Estamos dentro.")
                return True

            time.sleep(0.5)

        log.error("❌ Startup falló tras %d intentos.", max_intentos)
        return False

    def handle_comeback_bonus(self, screen=None):
        eventos_reclamados = False
        MAX_SCROLLS = 3

        # ── Página 1: Returner's Bonus ──
        while True:
            if screen is None:
                screen = self.device.screenshot()

            pos_claim = self.vision.find_template(
                screen, "templates/btn_claim_comeback.png", threshold=0.8, zona="MITAD_DERECHA"
            )
            screen = None  # Forzar nueva captura si el bucle se repite

            if pos_claim:
                log.debug("  [🎁] Bonus detectado! Reclamando...")
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(1.5)
                self.device.tap(100, 100)
                time.sleep(0.5)
                self.device.tap(100, 100)
                time.sleep(0.8)
                eventos_reclamados = True
            else:
                if not eventos_reclamados:
                    break
                scroll_exitoso = False
                for intento_scroll in range(1, MAX_SCROLLS + 1):
                    log.debug("  [🔄] Scroll #%d en Bonus...", intento_scroll)
                    self.device.swipe(1840, 740, 1840, 240, duration=0.35)
                    time.sleep(0.8)
                    pos_claim = self.vision.find_template(
                        self.device.screenshot(), "templates/btn_claim_comeback.png",
                        threshold=0.8, zona="MITAD_DERECHA"
                    )
                    if pos_claim:
                        log.debug("  [🎁] Claim tras scroll! Reclamando...")
                        self.device.tap(pos_claim[0], pos_claim[1])
                        time.sleep(1.5)
                        self.device.tap(100, 100)
                        time.sleep(0.5)
                        self.device.tap(100, 100)
                        time.sleep(0.8)
                        eventos_reclamados = True
                        scroll_exitoso = True
                        break
                if not scroll_exitoso:
                    break

        # ── Página 2: Returner's Pass ──
        if eventos_reclamados:
            log.debug("  [📋] Navegando a Returner's Pass...")
            pos_pass = self.vision.find_template(
                self.device.screenshot(), "templates/btn_returner_pass.png",
                threshold=0.8, zona="MITAD_IZQUIERDA"
            )
            if pos_pass:
                self.device.tap(pos_pass[0], pos_pass[1])
                time.sleep(1.0)
                for intento_scroll in range(MAX_SCROLLS + 1):
                    pos_claim = self.vision.find_template(
                        self.device.screenshot(), "templates/btn_claim_comeback.png",
                        threshold=0.8, zona="MITAD_DERECHA"
                    )
                    if pos_claim:
                        self.device.tap(pos_claim[0], pos_claim[1])
                        time.sleep(1.5)
                        self.device.tap(100, 100)
                        time.sleep(0.5)
                        self.device.tap(100, 100)
                        time.sleep(0.8)
                        intento_scroll = 0
                    else:
                        if intento_scroll < MAX_SCROLLS:
                            self.device.swipe(1840, 740, 1840, 240, duration=0.35)
                            time.sleep(0.8)
                        else:
                            break

        if eventos_reclamados:
            self.device.d.press("back")
            time.sleep(1.2)
            return True
        return False