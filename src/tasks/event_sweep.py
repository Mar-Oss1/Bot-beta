# tasks/event_sweep.py
import time
from core.logger import get_logger
from tasks.event_farm import EventFarm

log = get_logger("event_sweep")


class EventSweep(EventFarm):
    def __init__(self, device, vision, account=None, db=None):
        # EventFarm solo requiere device y vision
        super().__init__(device, vision)
        self.account = account
        self.db = db

    def execute(self) -> bool:
        log.info("\n" + "=" * 60)
        log.info("Módulo: Farmeo de Eventos (Historia y Batallas)")
        log.info("=" * 60)
        time.sleep(2)

        eventos_procesados = 0
        MAX_EVENTOS = 2

        while eventos_procesados < MAX_EVENTOS:  # ← CAMBIO AQUÍ
            screen = self.device.screenshot()
            eventos_actuales = self.vision.find_all_templates(
                screen, "templates/label_ends_in.png", threshold=0.75
            )

            if not eventos_actuales:
                if eventos_procesados == 0:
                    log.warning("No se encontraron banners de eventos activos en la pantalla.")
                else:
                    log.info("[✅] No quedan más eventos en pantalla. Terminado.")
                break

            eventos_actuales.sort(key=lambda p: p[1])
            pos_evento = eventos_actuales[0]

            eventos_procesados += 1
            log.info("-" * 60)
            log.info("[>] Entrando al evento #%d (Y=%d)...", eventos_procesados, pos_evento[1])
            self.device.tap(pos_evento[0], pos_evento[1])

            self.vision.wait_for_screen_stable(
                self.device.screenshot,
                timeout=6, interval=0.5,
                stability_threshold=0.95, min_stable_checks=2
            )

            log.info("  [🚜] Iniciando farmeo de historia y batallas en evento #%d...", eventos_procesados)
            super().execute()

            log.info("  [🔙] Farmeo terminado en este evento. Saliendo a la lista...")
            for _ in range(3):
                self._cerrar_ventana()
                time.sleep(1.0)

            self.vision.wait_for_screen_stable(
                self.device.screenshot,
                timeout=4, interval=0.5,
                stability_threshold=0.95, min_stable_checks=2
            )

        log.info("=" * 60)
        log.info("Farmeo de eventos completado.")
        log.info("Total de eventos procesados: %d/%d", eventos_procesados, MAX_EVENTOS)
        log.info("=" * 60)

        self.device.d.press("back")
        time.sleep(1.5)

        return True