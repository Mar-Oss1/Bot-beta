import time
from core.logger import get_logger
from tasks.event_farm import EventFarm

log = get_logger("event_sweep")


class EventSweep(EventFarm):
    def __init__(self, device, vision, account=None, db=None):
        super().__init__(device, vision, account, db)

    def _volver_a_home_eventos(self):
        """Regresa al Home deteniéndose apenas ve los banners de evento o el botón Summon."""
        for _ in range(4):
            screen_gray = self.vision.to_gray(self.device.screenshot())
            if self.vision.find_template(
                screen_gray, "templates/label_ends_in.png", threshold=0.75, zona="MITAD_DERECHA"
            ) or self.vision.find_template(
                screen_gray, "templates/btn_summon_nav.png", threshold=0.85, zona="ESQUINA_INF_DER"
            ):
                return
            self.cerrar_ventana(screen=screen_gray)
            time.sleep(0.5)

    def execute(self) -> bool:
        log.info("\n" + "=" * 60)
        log.info("Módulo: Farmeo de Eventos (Historia y Batallas)")
        log.info("=" * 60)
        time.sleep(0.8)

        eventos_procesados = 0
        MAX_EVENTOS = 2
        posiciones_visitadas = []

        while eventos_procesados < MAX_EVENTOS:
            screen = self.device.screenshot()
            # En 1000817284.png todos los eventos están en MITAD_DERECHA
            eventos_actuales = self.vision.find_all_templates(
                screen, "templates/label_ends_in.png", threshold=0.75, zona="MITAD_DERECHA"
            )

            if not eventos_actuales:
                break

            eventos_actuales.sort(key=lambda p: p[1])
            pos_evento = next(
                (ev for ev in eventos_actuales if all(abs(ev[1] - y_vis) >= 20 for y_vis in posiciones_visitadas)),
                None
            )

            if not pos_evento:
                log.info("[✅] Todos los eventos visibles ya fueron procesados.")
                break

            posiciones_visitadas.append(pos_evento[1])
            eventos_procesados += 1

            log.info("[>] Entrando al evento #%d (Y=%d)...", eventos_procesados, pos_evento[1])
            self.device.tap(pos_evento[0], pos_evento[1])
            self.wait_for_screen_stable(timeout=5, interval=0.35, stability_threshold=0.95, min_stable_checks=2)

            super().execute()

            log.info("  [🔙] Saliendo a la lista de eventos...")
            self._volver_a_home_eventos()

        return True