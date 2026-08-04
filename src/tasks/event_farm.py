import time
from core.logger import get_logger

log = get_logger("event_farm")


class EventFarm:
    def __init__(self, device, vision):
        self.device = device
        self.vision = vision

    # ==================== UTILIDADES COMUNES ====================
    def _cerrar_ventana(self, screen=None):
        if screen is None:
            screen = self.device.screenshot()
        pos = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
        if pos:
            self.device.tap(pos[0], pos[1])
            time.sleep(1.5)
            return
        # Si no hay X, intentar back
        self.device.d.press("back")
        time.sleep(1.5)

    def _clear_loot_windows(self):
        templates = [
            "templates/victory_banner.png",
            "templates/defeat_banner.png",
            "templates/rewards.png",
            "templates/level_up.png",
        ]
        for _ in range(5):
            screen = self.device.screenshot()
            found = False
            for t in templates:
                if self.vision.find_template(screen, t, threshold=0.8):
                    found = True
                    break
            if found:
                self.device.tap(300, 100)  # toque genérico para cerrar
                time.sleep(1.5)
            else:
                break

    # ==================== MÉTODOS PRINCIPALES ====================
    def handle_victory_sequence(self):
        """Maneja la secuencia de victoria: taps para limpiar."""
        log.info("   [✨] Victoria detectada. Limpiando...")
        for _ in range(3):
            self.device.tap(2200, 500)
            time.sleep(0.8)
        # Esperar a que la pantalla se estabilice
        self.vision.wait_for_screen_stable(
            self.device.screenshot,
            timeout=5,
            interval=0.5,
            stability_threshold=0.98,
            min_stable_checks=2
        )

    def ensure_team_10(self):
        """
        Verifica y selecciona Team 10.
        Usa wait_for_template para optimizar la espera.
        """
        log.info("  [🛡️] Verificando Team 10...")
        # Intentar detectar team_10 directamente (máximo 2 intentos)
        for _ in range(2):
            screen = self.device.screenshot()
            if self.vision.find_template(screen, "templates/label_team_10.png", threshold=0.85):
                log.info("  [✓] Team 10 detectado.")
                return True
            # Buscar flecha para cambiar
            arrow = self.vision.find_template(screen, "templates/btn_arrow_team.png", threshold=0.8)
            if arrow:
                self.device.tap(int(arrow[0]), int(arrow[1]))
                time.sleep(1.5)

        # Si no, hacer scrolls y esperar a que aparezca team_10
        for _ in range(8):  # máximo 8 scrolls
            arrow = self.vision.find_template(
                self.device.screenshot(),
                "templates/btn_arrow_team.png",
                threshold=0.8
            )
            if arrow:
                self.device.tap(int(arrow[0]), int(arrow[1]))
                # Esperar a que aparezca el label
                pos_label = self.vision.wait_for_template(
                    self.device.screenshot,
                    "templates/label_team_10.png",
                    timeout=2,
                    threshold=0.85,
                    interval=0.3
                )
                if pos_label:
                    log.info("  [✓] Team 10 detectado tras scroll.")
                    return True
            else:
                # No hay más flechas, salir
                break

        log.warning("  [!] No se pudo llegar a Team 10.")
        return False

    def check_and_recover_mana(self):
        """
        Detecta y recupera maná insuficiente.
        Usa wait_for_template para esperar el aviso.
        """
        # Esperar hasta 3 segundos a que aparezca el aviso de maná
        pos_insuficiente = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/mana_insuficiente.png",
            timeout=3,
            threshold=0.8,
            interval=0.5
        )
        if not pos_insuficiente:
            return False

        log.info("  [💧] ¡Aviso de maná detectado! Usando botón de restauración...")
        screen = self.device.screenshot()
        pos_ok = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.8)
        if pos_ok:
            self.device.tap(int(pos_ok[0]), int(pos_ok[1]))
        else:
            self.device.tap(int(pos_insuficiente[0]), int(pos_insuficiente[1]))

        # Esperar a que aparezca la ventana de checkbox
        time.sleep(1.5)
        screen_pot = self.device.screenshot()
        pos_checkbox = self.vision.find_template(screen_pot, "templates/checkbox_mana.png", threshold=0.8)
        if pos_checkbox:
            log.info("   [+] Activando uso automático de pociones (Checkbox)...")
            self.device.tap(int(pos_checkbox[0]), int(pos_checkbox[1]))
            time.sleep(1)

        # Cerrar ventana
        self._cerrar_ventana(self.device.screenshot())
        return True

    def detectar_costo_y_ejecutar(self):
        """
        Detecta etapas disponibles priorizando la historia (cost_0).
        Optimizado: una sola captura y reutilización de resultados.
        """
        screen = self.device.screenshot()
        log.debug("  [DEBUG] Buscando etapas disponibles...")

        # 1. Obtener todas las posiciones "Cleared" de una vez
        cleared_positions = self.vision.find_all_templates(
            screen,
            "templates/cleared.png",
            threshold=0.8
        )
        # Convertir a conjunto de Y para búsqueda rápida
        cleared_ys = {c[1] for c in cleared_positions}
        log.debug("  [DEBUG] Cleared encontrados: %d", len(cleared_ys))

        # Función auxiliar para verificar si una posición está "cleared"
        def esta_cleared(y):
            return any(abs(y - cy) < 50 for cy in cleared_ys)

        # 2. PRIMERO buscar cost_0.png (historia)
        posiciones_historia = self.vision.find_all_templates(
            screen,
            "templates/cost_0.png",
            threshold=0.8
        )
        # Ordenar por Y (de arriba a abajo) para priorizar primeras
        posiciones_historia.sort(key=lambda p: p[1])

        for pos in posiciones_historia:
            if not esta_cleared(pos[1]):
                log.info("  ✅ Etapa de HISTORIA disponible en (%d, %d)", pos[0], pos[1])
                return pos, "cost_0.png"
            else:
                log.debug("  ⏭️ Etapa historia está cleared (Y: %d)", pos[1])

        # 3. Si no hay historia, buscar batallas
        log.debug("  [DEBUG] No hay historia disponible. Buscando batallas...")
        prioridad_costos = ["cost_80.png", "cost_60.png", "cost_50.png"]

        for costo_template in prioridad_costos:
            posiciones = self.vision.find_all_templates(
                screen,
                f"templates/{costo_template}",
                threshold=0.7
            )
            # Ordenar por Y
            posiciones.sort(key=lambda p: p[1])

            log.debug("  [DEBUG] %s encontrados: %d", costo_template, len(posiciones))

            for pos in posiciones:
                if not esta_cleared(pos[1]):
                    log.info("  ✅ Etapa de BATALLA disponible: %s en (%d, %d)",
                             costo_template, pos[0], pos[1])
                    return pos, costo_template
                else:
                    log.debug("  ⏭️ Etapa %s está cleared (Y: %d)",
                              costo_template, pos[1])

        log.debug("  [DEBUG] No se encontraron etapas disponibles")
        return None, None

    def execute(self):
        """
        Bucle principal de farmeo.
        """
        log.info("\n [🎃] Iniciando farmeo infinito...")
        max_intentos = 100
        intentos = 0

        while intentos < max_intentos:
            pos, tipo_costo = self.detectar_costo_y_ejecutar()
            if pos:
                if tipo_costo == "cost_0.png":
                    self.execute_historia(pos)
                else:
                    self.execute_batalla(pos)
                # Pequeña pausa entre etapas
                time.sleep(1.5)
                intentos += 1
            else:
                log.info("  [✅] No hay más etapas disponibles. Farmeo terminado.")
                break

        if intentos >= max_intentos:
            log.warning("  [⚠️] Límite de %d intentos alcanzado. Deteniendo farmeo.", max_intentos)

    def execute_historia(self, pos):
        """
        Ejecuta una etapa de historia usando Skip.
        """
        log.info("  [📖] Etapa de Historia detectada. Entrando en modo Skip...")
        self.device.tap(int(pos[0]), int(pos[1]))

        # Esperar a que aparezca el botón "Skip Scene" o "Victory"
        # Timeout total: hasta 20 segundos
        inicio = time.time()
        while time.time() - inicio < 20:
            screen = self.device.screenshot()

            # Verificar victoria (puede ocurrir sin skip)
            if self.vision.find_template(screen, "templates/victory_banner.png", threshold=0.8):
                self.handle_victory_sequence()
                return

            # Buscar botón skip
            p_skip = self.vision.find_template(screen, "templates/btn_skip_scene.png", threshold=0.8)
            if p_skip:
                self.device.tap(int(p_skip[0]), int(p_skip[1]))
                time.sleep(1)
                # Esperar OK de confirmación
                p_ok = self.vision.wait_for_template(
                    self.device.screenshot,
                    "templates/btn_skip_ok.png",
                    timeout=3,
                    threshold=0.8
                )
                if p_ok:
                    self.device.tap(int(p_ok[0]), int(p_ok[1]))
                    # Esperar a que la pantalla se estabilice (carga)
                    self.vision.wait_for_screen_stable(
                        self.device.screenshot,
                        timeout=8,
                        interval=0.5,
                        stability_threshold=0.98,
                        min_stable_checks=2
                    )
                    return
                # Si no aparece OK, continuar esperando
            time.sleep(0.5)

        log.warning("  [⚠️] Timeout en historia. Forzando limpieza...")
        self._clear_loot_windows()

    def execute_batalla(self, pos):
        """
        Ejecuta una batalla con selección de Team 10 y control de maná.
        """
        log.info("  [⚔️] Etapa de Batalla detectada. Preparando combate...")
        self.device.tap(int(pos[0]), int(pos[1]))
        time.sleep(1.5)

        # Posible aviso de maná
        if self.check_and_recover_mana():
            # Re-tocar la etapa después de recuperar maná
            self.device.tap(int(pos[0]), int(pos[1]))
            time.sleep(1.5)

        # Seleccionar Team 10
        if not self.ensure_team_10():
            log.error("  [❌] No se pudo seleccionar Team 10. Abortando batalla.")
            self._cerrar_ventana()
            return

        # Buscar botón Start
        pos_start = self.vision.wait_for_template(
            self.device.screenshot,
            "templates/btn_start_battle.png",
            timeout=5,
            threshold=0.8,
            interval=0.5
        )
        if pos_start:
            self.device.tap(int(pos_start[0]), int(pos_start[1]))
            time.sleep(1)
            # Verificar maná nuevamente (puede pedir después de start)
            if self.check_and_recover_mana():
                # Reintentar start
                pos_start_again = self.vision.wait_for_template(
                    self.device.screenshot,
                    "templates/btn_start_battle.png",
                    timeout=3,
                    threshold=0.8
                )
                if pos_start_again:
                    self.device.tap(int(pos_start_again[0]), int(pos_start_again[1]))

            # Esperar a que la batalla comience (pantalla estable o botón skip)
            self.vision.wait_for_screen_stable(
                self.device.screenshot,
                timeout=5,
                interval=0.5,
                stability_threshold=0.95,
                min_stable_checks=2
            )
        else:
            log.warning("  [⚠️] No se encontró botón Start. ¿Ya en combate?")
            # Intentar limpiar posibles ventanas
            self._clear_loot_windows()

        log.info("  [⏳] Esperando fin de batalla...")
        inicio_batalla = time.time()
        timeout_batalla = 180  # 3 minutos máximo

        while time.time() - inicio_batalla < timeout_batalla:
            screen = self.device.screenshot()

            # Victoria
            if self.vision.find_template(screen, "templates/victory_banner.png", threshold=0.8):
                self.handle_victory_sequence()
                return

            # Derrota
            if self.vision.find_template(screen, "templates/defeat_banner.png", threshold=0.8):
                log.info("  [💀] Derrota detectada. Saliendo...")
                self.device.tap(1000, 1000)
                time.sleep(2)
                self._clear_loot_windows()
                return

            # Skip scene (si aparece durante la batalla)
            p1 = self.vision.find_template(screen, "templates/btn_skip_scene.png", threshold=0.8)
            if p1:
                self.device.tap(int(p1[0]), int(p1[1]))
                time.sleep(1)
                ok = self.vision.find_template(screen, "templates/btn_skip_ok.png", threshold=0.8)
                if ok:
                    self.device.tap(int(ok[0]), int(ok[1]))
                time.sleep(1)
                continue

            time.sleep(0.8)

        log.warning("  [⚠️] Timeout de batalla (%d segundos). Forzando salida.", timeout_batalla)
        self._clear_loot_windows()