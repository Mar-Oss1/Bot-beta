# tasks/base_task.py
import time
import os
from core.logger import get_logger

log = get_logger("base_task")


class BaseTask:
    def __init__(self, device, vision, account=None, db=None):
        self.device = device
        self.vision = vision
        self.account = account
        self.db = db

    # ---- Métodos de espera (delegados a vision) ----
    def wait_for_template(self, template_path, timeout=10, threshold=None, interval=0.25, log_progress=False):
        return self.vision.wait_for_template(
            self.device.screenshot, template_path, timeout=timeout,
            threshold=threshold, interval=interval, log_progress=log_progress
        )

    def wait_for_screen_stable(self, timeout=7, interval=0.5, stability_threshold=0.98, min_stable_checks=2):
        return self.vision.wait_for_screen_stable(
            self.device.screenshot,
            timeout=timeout,
            interval=interval,
            stability_threshold=stability_threshold,
            min_stable_checks=min_stable_checks
        )

    def wait_for_disappearance(self, template_path, timeout=5, threshold=None, interval=0.3) -> bool:
        """Espera a que un template desaparezca de la pantalla."""
        threshold = threshold if threshold is not None else self.vision.threshold
        inicio = time.time()
        while time.time() - inicio < timeout:
            screen = self.device.screenshot()
            if self.vision.find_template(screen, template_path, threshold) is None:
                return True
            time.sleep(interval)
        return False

    # ---- Funciones auxiliares genéricas optimizadas ----
    def cerrar_ventana(self, screen=None):
        if screen is None:
            screen = self.device.screenshot()
        result = self.vision.find_any(screen, [
            "templates/btn_cerrar_x.png",
            "templates/btn_back.png"
        ], threshold=0.8)

        if result:
            template, x, y = result
            self.device.tap(x, y)
            time.sleep(0.6)
            return True

        self.device.d.press("back")
        time.sleep(0.6)
        return False  # Fallback executed

    def clear_loot_windows(self, max_taps=6, extra_templates=None):
        """
        Cierra ventanas comunes de loot, victoria, derrota, etc.
        Permite extender las plantillas a buscar pasándolas en extra_templates.
        """
        loot_templates = [
            "templates/pantalla_loot.png",
            "templates/rewards.png",
            "templates/victory_banner.png",
            "templates/level_up.png",
            "templates/defeat_banner.png",
            "templates/summon_chest_loot.png",
        ]

        if extra_templates:
            loot_templates.extend(extra_templates)

        for _ in range(max_taps):
            screen = self.device.screenshot()
            found = self.vision.find_any(screen, loot_templates, threshold=0.85)

            if found:
                template, x, y = found
                log.debug("Ventana detectada: %s. Cerrando...", os.path.basename(template))

                # Caso especial: algunos menús de recompensas necesitan cerrarse en la X en lugar de un tap genérico
                if "raid_rewards" in template or "rewards.png" in template:
                    self._cerrar_recompensa_especifica()
                else:
                    self._tap_generico_para_cerrar()

                time.sleep(1)  # Esperar a que la animación termine y desaparezca
            else:
                break

    def _tap_generico_para_cerrar(self):
        """Intenta cerrar un pop-up con un tap en un área segura de la pantalla."""
        # Idealmente obtener las dimensiones para no hardcodear el (300, 100)
        # Por simplicidad, mantenemos la lógica actual pero la encapsulamos
        self.device.tap(300, 100)

    def _cerrar_recompensa_especifica(self):
        """Lógica especializada para cerrar menús de recompensas que requieren tocar la 'X'."""
        screen = self.device.screenshot()
        pos_x = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
        if pos_x:
            self.device.tap(pos_x[0], pos_x[1])
        else:
            self._tap_generico_para_cerrar()

    def return_to_home(self):
        pos = self.vision.find_template(
            self.device.screenshot(), "templates/btn_home_nav.png", threshold=0.85
        )
        if pos:
            self.device.tap(pos[0], pos[1])
            time.sleep(1.0)
            self.limpiar_banners_home()
            return

        for _ in range(5):
            self.device.d.press("back")
            time.sleep(0.8)
            screen = self.device.screenshot()
            pos = self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.85)
            if pos:
                self.device.tap(pos[0], pos[1])
                time.sleep(1.5)
                break

        self.limpiar_banners_home()

    def limpiar_banners_home(self, max_iter=6):
        banner_templates = [
            "templates/btn_claim.png",
            "templates/btn_cerrar_x.png"
        ]
        for _ in range(max_iter):
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, banner_templates, threshold=0.8)

            if result:
                template, x, y = result
                log.debug("Banner detectado: %s. Procesando...", os.path.basename(template))
                self.device.tap(x, y)
                time.sleep(1.5)
                continue

            time.sleep(0.5)
            screen = self.device.screenshot()
            if not self.vision.find_any(screen, banner_templates, threshold=0.8):
                log.debug("Home limpio.")
                break