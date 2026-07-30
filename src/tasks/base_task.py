# tasks/base_task.py
import time
from core.logger import get_logger

log = get_logger("base_task")

class BaseTask:
    def __init__(self, device, vision, account=None, db=None):
        self.device = device
        self.vision = vision
        self.account = account
        self.db = db

    # ---- Métodos de espera inteligente (delegados a vision) ----
    def wait_for_template(self, template_path, timeout=10, threshold=None, interval=0.3, log_progress=False):
        """Espera a que aparezca un template en pantalla."""
        return self.vision.wait_for_template(
            self.device.screenshot,
            template_path,
            timeout=timeout,
            threshold=threshold,
            interval=interval,
            log_progress=log_progress
        )

    def wait_for_screen_stable(self, timeout=15, interval=0.8, stability_threshold=0.98, min_stable_checks=2):
        """Espera a que la pantalla deje de cambiar (carga completa)."""
        return self.vision.wait_for_screen_stable(
            self.device.screenshot,
            timeout=timeout,
            interval=interval,
            stability_threshold=stability_threshold,
            min_stable_checks=min_stable_checks
        )

    # ---- Funciones auxiliares comunes ----
    def cerrar_ventana(self, screen=None):
        """Intenta cerrar una ventana emergente usando X, back o botón físico."""
        if screen is None:
            screen = self.device.screenshot()

        pos = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
        if pos:
            log.debug("Cerrando con botón X")
            self.device.tap(pos[0], pos[1])
            time.sleep(2)
            return

        pos = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.85)
        if pos:
            log.debug("Cerrando con btn_back.png")
            self.device.tap(pos[0], pos[1])
            time.sleep(2)
            return

        log.debug("Sin botón de cierre. Usando back de Android.")
        self.device.d.press("back")
        time.sleep(2)

    def return_to_home(self):
        """Vuelve a la pantalla principal del juego (Home)."""
        screen = self.device.screenshot()
        pos = self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.85)
        if pos:
            self.device.tap(pos[0], pos[1])
            time.sleep(3)
        else:
            # Intentar con varias pulsaciones de back
            for _ in range(4):
                self.device.d.press("back")
                time.sleep(1.5)
                screen = self.device.screenshot()
                pos = self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.85)
                if pos:
                    self.device.tap(pos[0], pos[1])
                    time.sleep(3)
                    break

        # Limpiar posibles banners que aparezcan en el home
        self.limpiar_banners_home()

    def limpiar_banners_home(self):
        """Cierra popups y reclama botones que aparecen en el home."""
        for _ in range(4):
            screen = self.device.screenshot()
            # Buscar botón Claim o X
            pos_claim = self.vision.find_template(screen, "templates/btn_claim.png", threshold=0.8)
            if pos_claim:
                log.debug("Reclamando banner...")
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(2)
                continue

            pos_x = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
            if pos_x:
                log.debug("Cerrando popup con X...")
                self.device.tap(pos_x[0], pos_x[1])
                time.sleep(2)
                continue

            # Si no hay nada, esperar un segundo y verificar de nuevo
            time.sleep(1)
            screen2 = self.device.screenshot()
            if not (self.vision.find_template(screen2, "templates/btn_claim.png", 0.8) or
                    self.vision.find_template(screen2, "templates/btn_cerrar_x.png", 0.8)):
                log.debug("Home limpio.")
                break

    def clear_loot_windows(self):
        """Cierra ventanas de loot, victoria, derrota, etc."""
        templates = [
            "templates/pantalla_loot.png",
            "templates/level_up.png",
            "templates/rewards.png",
            "templates/victory_banner.png",
            "templates/defeat_banner.png",
            "templates/summon_chest_loot.png",
        ]
        for _ in range(6):
            screen = self.device.screenshot()
            if any(self.vision.find_template(screen, t, threshold=0.85) for t in templates):
                log.debug("Ventana de loot/victoria detectada. Cerrando...")
                self.device.tap(300, 100)  # Toca en un punto genérico para cerrar
                time.sleep(1.5)
            else:
                break