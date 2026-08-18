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

        # Bucle principal: mientras haya banners de eventos en la pantalla principal
        while True:
            # 1. Escanear la lista de eventos en la pestaña principal
            screen = self.device.screenshot()
            eventos_actuales = self.vision.find_all_templates(screen, "templates/label_ends_in.png", threshold=0.75)

            if not eventos_actuales:
                if eventos_procesados == 0:
                    log.warning("No se encontraron banners de eventos activos en la pantalla.")
                else:
                    log.info("[✅] No quedan más eventos en pantalla. Terminado.")
                break

            # Ordenar por Y para tomar el más alto (el primero disponible)
            eventos_actuales.sort(key=lambda p: p[1])
            pos_evento = eventos_actuales[0]

            eventos_procesados += 1
            log.info("-" * 60)
            log.info("[>] Entrando al evento #%d (Y=%d)...", eventos_procesados, pos_evento[1])
            self.device.tap(pos_evento[0], pos_evento[1])

            # Esperar a que cargue la pantalla interna del evento
            self.vision.wait_for_screen_stable(
                self.device.screenshot,
                timeout=6, interval=0.5,
                stability_threshold=0.95, min_stable_checks=2
            )

            # 2. Farmear Historia y Batallas Normales (Lógica completa heredada de EventFarm)
            # Esto buscará cost_0, cost_80, cost_60, cost_50.
            # Usará Skips para historia, Team 10 y Start para batallas, manejo de maná, etc.
            # Se detendrá solo cuando no queden etapas sin "Cleared".
            log.info("  [🚜] Iniciando farmeo de historia y batallas en evento #%d...", eventos_procesados)
            super().execute()

            # 3. Salir del evento para volver a la lista de banners
            log.info("  [🔙] Farmeo terminado en este evento. Saliendo a la lista...")
            for _ in range(3):
                self._cerrar_ventana()
                time.sleep(1.0)

            # Pequeña espera para que cargue la lista de banners nuevamente antes del siguiente loop
            self.vision.wait_for_screen_stable(
                self.device.screenshot,
                timeout=4, interval=0.5,
                stability_threshold=0.95, min_stable_checks=2
            )

        log.info("=" * 60)
        log.info("Farmeo de eventos completado.")
        log.info("Total de eventos procesados: %d", eventos_procesados)
        log.info("=" * 60)

        self.device.d.press("back")
        time.sleep(1.5)

        return True