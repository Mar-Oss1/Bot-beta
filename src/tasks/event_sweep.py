# tasks/event_sweep.py
import time
from core.logger import get_logger
from tasks.event_farm import EventFarm

log = get_logger("event_sweep")


class EventSweep(EventFarm):
    def __init__(self, device, vision, account=None, db=None):
        # EventFarm solo requiere device y vision, pero guardamos account y db por compatibilidad
        super().__init__(device, vision)
        self.account = account
        self.db = db

    def execute(self) -> bool:
        log.info("Módulo: Sweep de Eventos (Procesando TODOS los eventos activos)")
        time.sleep(2)

        # 1. Verificación inicial de banners de eventos activos
        eventos_iniciales = None
        for intento in range(3):
            screen = self.device.screenshot()
            eventos_iniciales = self.vision.find_all_templates(screen, "templates/label_ends_in.png", threshold=0.75)
            if eventos_iniciales:
                break
            if intento < 2:
                log.debug("No se encontraron eventos. Reintentando (%d/3)...", intento + 1)
                time.sleep(1.5)

        if not eventos_iniciales:
            log.warning("No se encontraron banners de eventos activos en la pantalla.")
            return True

        log.info("Se detectaron %d eventos activos inicialmente.", len(eventos_iniciales))

        # 2. Iterar sobre TODOS los eventos uno por uno
        # Re-escaneamos la pantalla en cada iteración para evitar problemas si la lista se desplaza.
        eventos_procesados = 0
        while True:
            screen = self.device.screenshot()
            eventos_actuales = self.vision.find_all_templates(screen, "templates/label_ends_in.png", threshold=0.75)

            if not eventos_actuales:
                log.info("No quedan más eventos en pantalla. Terminado.")
                break

            # Ordenar por Y para tomar el más alto (el primero disponible)
            eventos_actuales.sort(key=lambda p: p[1])
            pos_evento = eventos_actuales[0]

            eventos_procesados += 1
            log.info("[>] Procesando evento #%d (Y=%d)...", eventos_procesados, pos_evento[1])
            self.device.tap(pos_evento[0], pos_evento[1])

            # Esperar a que cargue la pantalla interna del evento
            self.vision.wait_for_screen_stable(
                self.device.screenshot,
                timeout=5,
                interval=0.5,
                stability_threshold=0.98,
                min_stable_checks=2
            )

            # 3. Buscar etapa EX disponible (10 > 9 > 8)
            etapa_encontrada = False
            for etapa in ["stage_ex_10.png", "stage_ex_9.png", "stage_ex_8.png"]:
                screen = self.device.screenshot()
                pos_s = self.vision.find_template(screen, f"templates/{etapa}", threshold=0.85)
                if pos_s:
                    log.info("Etapa encontrada: %s", etapa.replace(".png", ""))
                    self.device.tap(pos_s[0], pos_s[1])
                    self.vision.wait_for_screen_stable(
                        self.device.screenshot,
                        timeout=4,
                        interval=0.5,
                        stability_threshold=0.98,
                        min_stable_checks=2
                    )
                    etapa_encontrada = True
                    break

            if not etapa_encontrada:
                log.info("Sin etapas EX disponibles en este evento. Pasando al siguiente...")
                self._cerrar_ventana()
                time.sleep(1.5)
                continue

            # 4. Realizar sweeps (máximo 3 por evento)
            sweeps_completados = 0
            while sweeps_completados < 3:
                screen = self.device.screenshot()
                pos_sweep = self.vision.find_template(screen, "templates/btn_sweep.png", threshold=0.85)
                if not pos_sweep:
                    log.warning("Botón Sweep no detectado. Saliendo del loop de sweeps.")
                    break

                self.device.tap(pos_sweep[0], pos_sweep[1])
                time.sleep(1.5)

                # Llamada a la función de recuperación de maná heredada de EventFarm
                if self.check_and_recover_mana():
                    log.info("Maná insuficiente detectado y recuperado. Reintentando sweep...")
                    continue

                log.info("Sweep #%d completado.", sweeps_completados + 1)
                time.sleep(1.5)
                self._clear_loot_windows()
                sweeps_completados += 1

            # 5. Cerrar ventanas de resultados y volver a la lista de eventos
            # Presionamos back/cerrar un par de veces para asegurar que volvemos a la lista
            for _ in range(2):
                self._cerrar_ventana()

            time.sleep(1.5)

        log.info("Sweep de todos los eventos completado. Total procesados: %d", eventos_procesados)

        self.device.d.press("back")
        time.sleep(1)

        return True