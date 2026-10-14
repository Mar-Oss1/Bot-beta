import time
from core.logger import get_logger
from tasks.event_farm import EventFarm

log = get_logger("event_sweep")


class EventSweep(EventFarm):
    def __init__(self, device, vision, account=None, db=None):
        super().__init__(device, vision, account, db)

    def execute(self) -> bool:
        log.info("\n" + "=" * 60)
        log.info("Módulo: Farmeo de Eventos (Historia y Batallas)")
        log.info("=" * 60)
        time.sleep(2)

        eventos_procesados = 0
        MAX_EVENTOS = 2
        # Lista para guardar las posiciones Y de los eventos ya visitados
        posiciones_visitadas = []

        while eventos_procesados < MAX_EVENTOS:
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

            # Ordenar los eventos de arriba hacia abajo
            eventos_actuales.sort(key=lambda p: p[1])

            pos_evento = None

            # Buscar el primer evento que NO hayamos visitado
            for evento in eventos_actuales:
                ya_visitado = False
                for y_visitada in posiciones_visitadas:
                    # Margen de 20 píxeles por si el scroll se mueve ligeramente
                    if abs(evento[1] - y_visitada) < 20:
                        ya_visitado = True
                        break

                if not ya_visitado:
                    pos_evento = evento
                    break

            # Si todos los eventos en pantalla ya fueron visitados, terminamos
            if not pos_evento:
                log.info("[✅] Todos los eventos visibles ya fueron procesados. Terminado.")
                break

            # Registrar este evento como visitado
            posiciones_visitadas.append(pos_evento[1])
            eventos_procesados += 1

            log.info("-" * 60)
            log.info("[>] Entrando al evento #%d (Y=%d)...", eventos_procesados, pos_evento[1])
            self.device.tap(pos_evento[0], pos_evento[1])

            self.wait_for_screen_stable(timeout=6, interval=0.5, stability_threshold=0.95, min_stable_checks=2)

            log.info("  [🚜] Iniciando farmeo de historia y batallas en evento #%d...", eventos_procesados)
            super().execute()

            log.info("  [🔙] Farmeo terminado en este evento. Saliendo a la lista...")
            for _ in range(3):
                self.cerrar_ventana()
                time.sleep(1.0)

            self.wait_for_screen_stable(timeout=4, interval=0.5, stability_threshold=0.95, min_stable_checks=2)

        log.info("=" * 60)
        log.info("Farmeo de eventos completado.")
        log.info("Total de eventos procesados: %d/%d", eventos_procesados, MAX_EVENTOS)
        log.info("=" * 60)

        self.device.d.press("back")
        time.sleep(1.5)

        return True