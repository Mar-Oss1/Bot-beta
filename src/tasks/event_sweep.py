import time
from core.logger import get_logger
from tasks.event_farm import EventFarm

log = get_logger("event_sweep")

HOME_EXCLUSIVE_TEMPLATES = [
    "templates/btn_battalion_warfare.png"
]

class EventSweep(EventFarm):
    def __init__(self, device, vision, account=None, db=None):
        super().__init__(device, vision, account, db)

    def _estamos_en_lobby_real(self, screen) -> bool:
        return self.vision.find_any(screen, HOME_EXCLUSIVE_TEMPLATES, threshold=0.80, zona="COMPLETA") is not None

    def _forzar_home(self, max_toques: int = 2) -> None:
        for toque in range(max_toques):
            screen = self.device.screenshot()
            if toque > 0 and self._estamos_en_lobby_real(screen):
                break

            pos = self.vision.find_template(
                screen, "templates/btn_home_nav.png", threshold=0.82, zona="ESQUINA_INF_DER"
            )
            if not pos:
                break

            log.info("  [🏠] Tocando botón Home (toque %d/%d)...", toque + 1, max_toques)
            self.device.tap(pos[0], pos[1])
            self.wait_for_screen_stable(timeout=4, interval=0.35)

        self.limpiar_banners_home()

    def _scannear_eventos(self) -> list:
        """Todos los banners 'Ends in' visibles en el Home, ordenados de arriba a abajo."""
        screen_gray = self.vision.to_gray(self.device.screenshot())
        eventos = self.vision.find_all_templates(
            screen_gray, "templates/label_ends_in.png", threshold=0.75, zona="MITAD_DERECHA"
        ) or []
        eventos.sort(key=lambda p: p[1])
        return eventos

    def execute(self) -> bool:
        log.info("=" * 60)
        log.info("Módulo: Farmeo de Eventos (Sweep Completo)")
        log.info("=" * 60)

        # 1) Garantizar que arrancamos desde el Lobby real
        self._forzar_home()

        # 2) Escanear cuántos eventos hay disponibles
        eventos_iniciales = self._scannear_eventos()
        total_eventos = len(eventos_iniciales)
        if total_eventos == 0:
            log.info("[✅] Sin banners de eventos visibles en el Home.")
            return True

        log.info("[📋] Eventos detectados en pantalla: %d", total_eventos)
        procesados = 0

        for idx in range(total_eventos):
            # Re-escanear en vivo en el Lobby para evitar coordenadas desfasadas
            actuales = self._scannear_eventos()
            if idx >= len(actuales):
                log.info("[>] No hay más banners en el índice #%d. Terminando.", idx + 1)
                break

            pos = actuales[idx]
            log.info("[>] Entrando al evento #%d/%d (Y=%d)...", idx + 1, total_eventos, pos[1])
            self.device.tap(pos[0], pos[1])
            self.wait_for_screen_stable(timeout=5, interval=0.35, stability_threshold=0.95, min_stable_checks=2)

            # 3) Farmear todas las etapas de historia/batalla de este evento
            super().execute()

            # 4) Regreso forzoso al Home mediante el botón inferior derecho antes del siguiente banner
            log.info("  [🔙] Saliendo del evento #%d hacia el Home...", idx + 1)
            self._forzar_home()
            procesados += 1

        log.info("[🏁] Sweep terminado: %d/%d eventos procesados.", procesados, total_eventos)
        return procesados > 0