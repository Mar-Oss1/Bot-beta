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

    # ---- Métodos de espera (delegados a vision con soporte de ZONA) ----
    def wait_for_template(
        self,
        template_path: str,
        timeout: float = 10,
        threshold: float = None,
        interval: float = 0.15,
        log_progress: bool = False,
        zona: str = "COMPLETA"
    ):
        return self.vision.wait_for_template(
            self.device.screenshot,
            template_path,
            timeout=timeout,
            threshold=threshold,
            interval=interval,
            log_progress=log_progress,
            zona=zona
        )

    def wait_for_screen_stable(
        self,
        timeout: float = 6,
        interval: float = 0.35,
        stability_threshold: float = 0.98,
        min_stable_checks: int = 2
    ):
        return self.vision.wait_for_screen_stable(
            self.device.screenshot,
            timeout=timeout,
            interval=interval,
            stability_threshold=stability_threshold,
            min_stable_checks=min_stable_checks
        )

    def wait_for_disappearance(
        self,
        template_path: str,
        timeout: float = 5,
        threshold: float = None,
        interval: float = 0.2,
        zona: str = "COMPLETA"
    ) -> bool:
        """Espera a que un template desaparezca de la zona indicada."""
        threshold = threshold if threshold is not None else self.vision.threshold
        inicio = time.monotonic()
        while time.monotonic() - inicio < timeout:
            screen = self.device.screenshot()
            if self.vision.find_template(screen, template_path, threshold, zona=zona) is None:
                return True
            time.sleep(interval)
        return False

    # ---- Funciones auxiliares genéricas optimizadas ----
    def cerrar_ventana(self, screen=None) -> bool:
        if screen is None:
            screen = self.device.screenshot()

        # Los botones de cerrar/atrás suelen estar en la mitad superior
        result = self.vision.find_any(
            screen,
            ["templates/btn_cerrar_x.png", "templates/btn_back.png"],
            threshold=0.8,
            zona="COMPLETA"
        )

        if result:
            _, x, y = result
            self.device.tap(x, y)
            time.sleep(0.4)
            return True

        self.device.d.press("back")
        time.sleep(0.4)
        return False

    def clear_loot_windows(self, max_taps: int = 6, extra_templates: list[str] = None):
        """
        Cierra ventanas comunes de loot, victoria, derrota, etc.
        Reutiliza la captura en memoria y recorta al CENTRO cuando es posible.
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
            found = self.vision.find_any(screen, loot_templates, threshold=0.85, zona="CENTRO")

            # Fallback a pantalla completa solo si hay extra_templates fuera del centro
            if not found and extra_templates:
                found = self.vision.find_any(screen, extra_templates, threshold=0.85, zona="COMPLETA")

            if found:
                template, _, _ = found
                log.debug("Ventana detectada: %s. Cerrando...", os.path.basename(template))

                if "raid_rewards" in template or "rewards.png" in template:
                    self._cerrar_recompensa_especifica(screen)
                else:
                    self._tap_generico_para_cerrar()

                time.sleep(0.6)
            else:
                break

    def _tap_generico_para_cerrar(self):
        self.device.tap(300, 100)

    def _cerrar_recompensa_especifica(self, screen=None):
        """Reutiliza el screenshot actual sin volver a pedirlo por ADB."""
        if screen is None:
            screen = self.device.screenshot()
        pos_x = self.vision.find_template(
            screen, "templates/btn_cerrar_x.png", threshold=0.8, zona="COMPLETA"
        )
        if pos_x:
            self.device.tap(pos_x[0], pos_x[1])
        else:
            self._tap_generico_para_cerrar()

    def return_to_home(self):
        """Regresa al Home asegurando que la transición posbatalla haya terminado."""
        for intento in range(5):
            screen = self.device.screenshot()

            # 1. Verificar si YA estamos en la portada principal (Home real)
            if self.vision.find_any(
                    screen,
                    ["templates/btn_battalion_warfare.png", "templates/btn_tot_home.png"],
                    threshold=0.82,
                    zona="MITAD_DERECHA"
            ):
                self.limpiar_banners_home(screen_inicial=screen)
                return

            # 2. Buscar el botón Home en la barra inferior (esperando hasta 2.5s en el primer intento por si sale de batalla)
            pos_home = (
                self.wait_for_template("templates/btn_home_nav.png", timeout=2.5, threshold=0.82, interval=0.25,
                                       zona="ESQUINA_INF_DER")
                if intento == 0
                else self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.82,
                                               zona="ESQUINA_INF_DER")
            )

            if pos_home:
                log.debug("Tocando btn_home_nav en (%d, %d)...", pos_home[0], pos_home[1])
                self.device.tap(pos_home[0], pos_home[1])
                time.sleep(1.2)
                self.wait_for_screen_stable(timeout=4, interval=0.35)
                continue

            # 3. Si estamos en una subventana sin barra inferior, presionar Back
            self.device.d.press("back")
            time.sleep(0.8)

        self.limpiar_banners_home()

    def limpiar_banners_home(self, max_iter: int = 6, screen_inicial=None):
        banner_templates = [
            "templates/btn_claim.png",
            "templates/btn_cerrar_x.png"
        ]
        alguno_cerrado = False

        for i in range(max_iter):
            screen = screen_inicial if (i == 0 and screen_inicial is not None) else self.device.screenshot()
            result = self.vision.find_any(screen, banner_templates, threshold=0.8, zona="COMPLETA")

            if result:
                template, x, y = result
                log.debug("Banner detectado: %s. Procesando...", os.path.basename(template))
                self.device.tap(x, y)
                alguno_cerrado = True
                time.sleep(0.9)
                continue

            # Si hubo al menos un banner cerrado, hacemos 1 espera corta por si se encadena otro
            if alguno_cerrado:
                time.sleep(0.35)
                alguno_cerrado = False
                continue

            # Si desde el primer chequeo estaba limpio, salimos al instante sin doble screenshot
            log.debug("Home limpio.")
            break