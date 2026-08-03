# tasks/daily_missions.py
import time
import datetime
import cv2
import numpy as np
import pytesseract
import os

from core.config import TESSERACT_CMD
from core.logger import get_logger
from core.economia import registrar_economia
from tasks.base_task import BaseTask
from tasks.defense import Defense

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
log = get_logger("daily_missions")


class DailyMissions(BaseTask):
    def __init__(self, device, vision, account, db):
        super().__init__(device, vision, account, db)
        self._server_id = None

    @property
    def _sid(self):
        return None if self._server_id == "DEFAULT" else self._server_id

    def _modulo_completado(self, modulo: str) -> bool:
        if self.account is None:
            return False
        return self.account.is_task_done(modulo, self._sid)

    def _completar_modulo(self, modulo: str):
        if self.account is None:
            return
        self.account.mark_task_done(modulo, self._sid)
        if self.db is not None:
            self.db.save()
        log.debug("Módulo '%s' guardado [server: %s]", modulo, self._sid or "DEFAULT")

    # ── OCR de gemas (sin escritura a disco) ──
    def leer_gemas(self) -> int:
        log.info("Escaneando contador de gemas...")
        try:
            X, Y, W, H = 1380, 15, 180, 50
            img_pil = self.device.screenshot()
            img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

            if img is None:
                log.warning("No se pudo obtener captura para OCR.")
                return 0

            roi = img[Y:Y + H, X:X + W]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            texto = pytesseract.image_to_string(
                thresh, config="--psm 7 -c tessedit_char_whitelist=0123456789"
            )
            numeros = ''.join(filter(str.isdigit, texto))

            if not numeros:
                debug_path = f"logs/debug_ocr_{datetime.datetime.now().strftime('%H%M%S')}.png"
                os.makedirs("logs", exist_ok=True)
                cv2.imwrite(debug_path, thresh)
                log.warning("OCR vacío. Debug: %s", debug_path)
                return 0

            valor = int(numeros)
            log.info("Gemas leídas: %d", valor)
            return valor

        except Exception as e:
            log.error("Error de OCR: %s", e)
            return 0

    def _limpiar_invocacion(self):
        """Espera y salta la animación de invocación."""
        log.debug("Esperando botón Skip de invocación...")
        pos_skip = self.wait_for_template(
            "templates/btn_skip_scene.png",
            timeout=10, threshold=0.7, interval=0.5
        )
        if pos_skip:
            self.device.tap(pos_skip[0], pos_skip[1])
            log.debug("Animación saltada.")
            time.sleep(2)
        else:
            log.debug("Sin botón Skip. Esperando animación natural...")
            time.sleep(4)

        # Esperar OK o rewards (polling optimizado)
        for _ in range(10):
            screen = self.device.screenshot()
            result = self.vision.find_any(screen, [
                "templates/btn_skip_ok.png",
                "templates/rewards.png"
            ], threshold=0.75)

            if result:
                template, x, y = result
                if "ok" in template.lower():
                    log.info("Botón OK detectado en invocación.")
                    self.device.tap(x, y)
                    time.sleep(1.5)
                    if not self.vision.find_template(
                            self.device.screenshot(), "templates/btn_draw_ok.png", threshold=0.75
                    ):
                        break
                else:
                    log.debug("Ventana de rewards detectada. Limpiando...")
                    self.device.tap(100, 100)
                    time.sleep(1)
            else:
                time.sleep(0.8)

    # ── Gestión de combates ──
    def handle_battle_sequence(self) -> str:
        self.wait_for_screen_stable(timeout=5, interval=0.5)

        screen = self.device.screenshot()
        pos_draw = self.vision.find_template(screen, "templates/Draw.png", threshold=0.85)
        if pos_draw:
            log.info("EMPATE detectado.")
            pos_ok = self.vision.find_template(screen, "templates/btn_draw_ok.png", threshold=0.85)
            tap_x, tap_y = pos_ok if pos_ok else (pos_draw[0], pos_draw[1] + 150)
            self.device.tap(tap_x, tap_y)
            time.sleep(2.5)
            self.clear_loot_windows()
            return "draw"

        # Buscar skip o speed en un solo screenshot
        result = self.vision.find_any(screen, [
            "templates/btn_battle_skip.png",
            "templates/btn_battle_speed.png"
        ], threshold=0.85)

        if result:
            template, x, y = result
            self.device.tap(x, y)
            if "skip" in template:
                log.debug("Batalla saltada.")
                time.sleep(3.5)
            else:
                time.sleep(0.5)

        self.clear_loot_windows()
        return "finished"

    def check_and_recover_mana(self) -> bool:
        pos_insuficiente = self.wait_for_template(
            "templates/mana_insuficiente.png", timeout=3, threshold=0.85
        )
        if not pos_insuficiente:
            return False

        log.info("Aviso de maná detectado. Recuperando...")
        screen = self.device.screenshot()
        pos_ok = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.85)
        self.device.tap((pos_ok or pos_insuficiente)[0], (pos_ok or pos_insuficiente)[1])
        time.sleep(2)

        screen2 = self.device.screenshot()
        pos_cb = self.vision.find_template(screen2, "templates/checkbox_mana.png", threshold=0.85)
        if pos_cb:
            self.device.tap(pos_cb[0], pos_cb[1])
            time.sleep(1.5)

        self.cerrar_ventana()
        return True

    # ── Módulo principal ──
    def execute(self, server_id: str = "DEFAULT") -> bool:
        self._server_id = server_id
        cuenta_label = f"{self.account.name if self.account else 'Prueba'} [{server_id}]"
        log.info("=" * 55)
        log.info("Iniciando Rutina Diaria - %s", cuenta_label)
        log.info("=" * 55)

        self.return_to_home()
        time.sleep(1.5)
        gemas_inicio = self.leer_gemas()
        log.info("Gemas al empezar: %d", gemas_inicio)

        # Lucky Fountain en días específicos
        dia = datetime.datetime.now().day
        if dia in [14, 15, 30, 31]:
            if not self._modulo_completado("fountain"):
                log.info("Día %d → activando Lucky Fountain", dia)
                try:
                    if self.do_lucky_fountain():
                        self._completar_modulo("fountain")
                    else:
                        log.warning("Lucky Fountain falló.")
                except Exception as e:
                    log.error("Error en Lucky Fountain: %s", e)

        modulos = [
            ("tower", self.do_tower_of_trials, "Tower of Trials"),
            ("alliance", self.do_alliance_quest, "Misiones de Gremio"),
            ("arena", self.do_arena, "Arena"),
            ("defense", lambda: Defense(self.device, self.vision, self.account, self.db).execute(), "Defensa War"),
            ("summons", self.do_summons, "Invocaciones"),
            ("mana", self.do_spend_mana, "Gasto de Maná"),
            ("rewards", self.claim_all_rewards, "Reclamo de Recompensas"),
        ]

        rutina_exitosa = True
        for key, func, label in modulos:
            if not self._modulo_completado(key):
                log.info("▶ Ejecutando: %s", label)
                try:
                    exito = func()
                    if exito:
                        self._completar_modulo(key)
                    else:
                        log.warning("Módulo %s falló.", label)
                        rutina_exitosa = False
                except Exception as e:
                    log.error("Error crítico en %s: %s", label, e)
                    rutina_exitosa = False
                    break
            else:
                log.info("✓ %s ya completado.", label)

        if rutina_exitosa:
            self._completar_modulo("daily_missions")
            self._completar_modulo("login_bonus")
            log.info("Rutina diaria completada exitosamente.")
        else:
            log.warning("Rutina diaria incompleta.")

        self.return_to_home()
        time.sleep(2)
        gemas_fin = self.leer_gemas()

        if gemas_fin == 0:
            log.warning("Lectura de gemas cero, reintentando...")
            time.sleep(1.5)
            gemas_fin = self.leer_gemas()

        diferencia = gemas_fin - gemas_inicio
        log.info("--" * 40)
        log.info("REPORTE CONTABLE - %s", cuenta_label)
        log.info("  Gemas inicio : %d", gemas_inicio)
        log.info("  Gemas fin   : %d", gemas_fin)
        log.info("  Ganancia Neta: %s%d gemas", "+" if diferencia >= 0 else "", diferencia)
        log.info("--" * 40)

        registrar_economia(
            cuenta_nombre=self.account.name if self.account else "Prueba",
            server_id=server_id,
            gemas_inicio=gemas_inicio,
            gemas_fin=gemas_fin,
        )

        return rutina_exitosa

    # ── Submódulos ──
    def do_lucky_fountain(self) -> bool:
        log.info("Módulo: Lucky Fountain")
        screen = self.device.screenshot()
        pos = self.vision.find_template(screen, "templates/btn_fountain_home.png", threshold=0.8)
        if not pos:
            log.error("No se encontró btn_fountain_home.")
            return False

        self.device.tap(pos[0], pos[1])
        self.wait_for_screen_stable(timeout=5, interval=0.5)

        for fase in range(1, 5):
            screen = self.device.screenshot()
            pos_offer = self.vision.find_template(screen, "templates/btn_fountain_offer.png", threshold=0.8)
            if pos_offer:
                log.info("Tirando fase %d/4 ...", fase)
                self.device.tap(pos_offer[0], pos_offer[1])
                self.wait_for_screen_stable(timeout=6, interval=0.5)
                self.clear_loot_windows()
                time.sleep(0.8)
            else:
                log.warning("No se puede tirar más.")
                break

        self.cerrar_ventana()
        self.return_to_home()
        self.limpiar_banners_home()
        return True

    # ── Detección de SSR ──
    def _detectar_ssr(self) -> bool:
        screen = self.device.screenshot()
        img = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brillo_promedio = float(np.mean(gray))
        UMBRAL_SSR = 10.0
        es_ssr = brillo_promedio < UMBRAL_SSR

        if es_ssr:
            log.info("SSR detectado! Brillo: %.1f (umbral: %.1f)", brillo_promedio, UMBRAL_SSR)
        else:
            log.debug("Brillo: %.1f - sin SSR.", brillo_promedio)
        return es_ssr

    def _manejar_animacion_ssr(self):
        log.info("Manejando animación SSR...")
        self.device.tap(760, 1200)
        time.sleep(1.5)
        pos_skip = self.wait_for_template(
            "templates/btn_skip_summon.png", timeout=5, threshold=0.7, interval=0.4
        )
        if pos_skip:
            log.info("Skip encontrado tras animación SSR.")
            self.device.tap(pos_skip[0], pos_skip[1])
            time.sleep(2)

    def do_premium_summons(self, veces: int = 1, parar_sin_ssr: int = 0):
        """
        Módulo de invocación premium con manejo robusto de animaciones.
        El juego tiene múltiples estados post-skip que deben manejarse secuencialmente.
        """
        log.info("Módulo: Invocación Premium (%d vez/veces | parar sin SSR: %s)",
                 veces, f"cada {parar_sin_ssr}" if parar_sin_ssr > 0 else "desactivado")

        rondas_sin_ssr = 0
        ssr_total = 0
        ronda = 0

        for ronda in range(1, veces + 1):
            log.info(" — Ronda %d/%d | SSR: %d | Sin SSR: %d —",
                     ronda, veces, ssr_total, rondas_sin_ssr)

            if parar_sin_ssr > 0 and rondas_sin_ssr >= parar_sin_ssr:
                log.info("%d rondas sin SSR. Deteniendo.", rondas_sin_ssr)
                break

            # Buscar botón x10
            pos_x10 = self.wait_for_template(
                "templates/btn_summon_x10.png", timeout=5, threshold=0.8, interval=0.5
            )
            if not pos_x10:
                log.error("No se encontró btn_summon_x10. Abortando.")
                return

            self.device.tap(pos_x10[0], pos_x10[1])
            time.sleep(1)

            # Confirmar
            pos_confirm = self.wait_for_template(
                "templates/btn_confirm_summon.png", timeout=4, threshold=0.8, interval=0.3
            )
            if not pos_confirm:
                log.error("No apareció confirmación. Saltando ronda %d.", ronda)
                continue

            log.info("Confirmando invocación...")
            self.device.tap(pos_confirm[0], pos_confirm[1])
            time.sleep(1.5)

            # ═══════════════════════════════════════════════════════════════════
            #  STATE MACHINE DE ANIMACIÓN DE INVOCACIÓN
            # ═══════════════════════════════════════════════════════════════════
            log.info("Acelerando animación...")
            ssr_en_esta_ronda = False
            inicio_anim = time.time()
            MAX_ANIM_TIME = 15  # 15 segundos máximo para toda la animación
            POLL_INTERVAL = 0.4
            skip_ya_tocado = False
            ssr_ya_manejado = False

            while time.time() - inicio_anim < MAX_ANIM_TIME:
                screen = self.device.screenshot()

                # ── ESTADO 1: SSR detectado (prioridad máxima) ──
                if not ssr_ya_manejado and self._detectar_ssr():
                    ssr_en_esta_ronda = True
                    ssr_total += 1
                    ssr_ya_manejado = True
                    log.info("🌟 SSR DETECTADO! Manejando animación...")
                    self._manejar_animacion_ssr()
                    # Después de manejar SSR, resetear flags para seguir buscando OK/x10
                    skip_ya_tocado = False
                    inicio_anim = time.time()  # Resetear timer
                    continue

                # ── ESTADO 2: Skip disponible (tocar si no lo hemos tocado recientemente) ──
                if not skip_ya_tocado:
                    pos_skip = self.vision.find_template(
                        screen, "templates/btn_skip_summon.png", threshold=0.7
                    )
                    if pos_skip:
                        log.info("Skip encontrado. Saltando...")
                        self.device.tap(pos_skip[0], pos_skip[1])
                        skip_ya_tocado = True
                        time.sleep(0.8)  # Breve para que el juego procese
                        continue

                # ── ESTADO 3: OK disponible (fin de animación) ──
                pos_ok = self.vision.find_template(
                    screen, "templates/btn_skip_ok.png", threshold=0.75
                )
                if pos_ok:
                    log.info("OK encontrado. Cerrando ronda...")
                    self.device.tap(pos_ok[0], pos_ok[1])
                    time.sleep(1)
                    break

                # ── ESTADO 4: Ya estamos de vuelta en el menú de invocaciones ──
                pos_x10_check = self.vision.find_template(
                    screen, "templates/btn_summon_x10.png", threshold=0.8
                )
                if pos_x10_check:
                    log.info("De vuelta en menú de invocaciones. Ronda completada.")
                    break

                # ── ESTADO 5: PJ promocional / mensaje intermedio ──
                # Tocar en centro de pantalla para cerrar posibles popups
                # Solo si ya tocamos skip y no hemos encontrado nada más
                if skip_ya_tocado and not ssr_ya_manejado:
                    # Verificar si hay algún template de mensaje promocional
                    pos_promo = self.vision.find_template(
                        screen, "templates/btn_skip_summon.png", threshold=0.7
                    )
                    if pos_promo:
                        # Apareció skip de nuevo (más animación pendiente)
                        log.info("Skip reapareció. Continuando animación...")
                        skip_ya_tocado = False  # Permitir tocar de nuevo
                        continue

                # Si no pasó nada, acelerar con tap genérico
                self.device.tap(200, 200)
                time.sleep(POLL_INTERVAL)

            # Timeout de animación
            if time.time() - inicio_anim >= MAX_ANIM_TIME:
                log.warning("Timeout de animación (%ds). Forzando limpieza...", MAX_ANIM_TIME)

            # Actualizar contador
            if ssr_en_esta_ronda:
                rondas_sin_ssr = 0
                log.info("✅ SSR en esta ronda. Contador reiniciado.")
            else:
                rondas_sin_ssr += 1
                log.info("Sin SSR esta ronda (%d consecutivas).", rondas_sin_ssr)

            # Limpieza final de la ronda
            self.clear_loot_windows()
            time.sleep(0.8)
            log.info("Ronda %d/%d completada.", ronda, veces)

        log.info("--" * 40)
        log.info("Invocación Premium finalizada.")
        log.info("Rondas ejecutadas : %d/%d", min(ronda, veces), veces)
        log.info(" SSR obtenidos  : %d", ssr_total)
        log.info("Rondas sin SSR : %d consecutivas al final", rondas_sin_ssr)
        log.info("--" * 40)

    # ── Tower of Trials ──
    def do_tower_of_trials(self) -> bool:
        log.info("Módulo: Tower of Trials")
        screen = self.device.screenshot()
        pos_tot = self.vision.find_template(screen, "templates/btn_tot_home.png", threshold=0.85)
        if not pos_tot:
            log.error("No se encontró el botón de Tower of Trials.")
            return False

        self.device.tap(pos_tot[0], pos_tot[1])
        self.wait_for_screen_stable(timeout=5, interval=0.5)

        # Cofre
        screen = self.device.screenshot()
        pos_chest = self.vision.find_template(screen, "templates/btn_tot_chest.png", threshold=0.8)
        if pos_chest:
            self.device.tap(pos_chest[0], pos_chest[1] - 15)
            time.sleep(1.5)
            self.clear_loot_windows()

        # Fast Forward
        screen = self.device.screenshot()
        pos_ff = self.vision.find_template(screen, "templates/btn_fast_forward_menu.png", threshold=0.85)
        if pos_ff:
            log.info("Abriendo menú de Fast Forward...")
            self.device.tap(pos_ff[0], pos_ff[1])
            self.wait_for_screen_stable(timeout=5, interval=0.5)

            acls = 0
            intentos_flecha = 0
            max_acls = 2
            max_intentos_flecha = 3

            while acls < max_acls and intentos_flecha < max_intentos_flecha:
                pos_green = self.wait_for_template(
                    "templates/btn_ff_green.png",
                    timeout=2, threshold=0.85, interval=0.3
                )
                if pos_green:
                    log.info("  Fast Forward #%d encontrado. Ejecutando...", acls + 1)
                    self.device.tap(pos_green[0], pos_green[1])
                    time.sleep(2.5)
                    self.device.tap(100, 100)
                    time.sleep(0.8)
                    acls += 1
                    intentos_flecha = 0
                    self.wait_for_screen_stable(timeout=3, interval=0.5)
                    continue

                screen = self.device.screenshot()
                pos_arrow = self.vision.find_template(screen, "templates/btn_ff_arrow.png", threshold=0.85)
                if pos_arrow:
                    log.info("  Flecha de FF encontrada, pasando de página...")
                    self.device.tap(pos_arrow[0], pos_arrow[1])
                    time.sleep(1.2)
                    intentos_flecha += 1
                    continue

                log.info("  No hay más Fast Forward disponibles.")
                break

            self.cerrar_ventana()
            time.sleep(0.8)

        # Explorar (3 veces)
        for _ in range(3):
            self.clear_loot_windows()
            screen = self.device.screenshot()
            pos_exp = self.vision.find_template(screen, "templates/btn_explore.png", threshold=0.85)
            if pos_exp:
                log.info("Explorando...")
                self.device.tap(pos_exp[0], pos_exp[1])
                time.sleep(2.5)
                self.clear_loot_windows()
            else:
                break

        # Boss (con reintentos por empate)
        reintentos = 0
        while reintentos < 3:
            screen = self.device.screenshot()
            pos_boss = self.vision.find_template(screen, "templates/btn_challenge_boss.png", threshold=0.85)
            if not pos_boss:
                break
            log.info("Desafiando al Boss...")
            self.device.tap(pos_boss[0], pos_boss[1])
            log.info("Esperando respuesta del servidor...")
            time.sleep(6)
            if self.handle_battle_sequence() == "draw":
                reintentos += 1
                log.warning("Empate en Torre (%d/3). Reintentando...", reintentos)
                time.sleep(1.5)
            else:
                break

        if reintentos == 3:
            log.warning("Límite de empates alcanzado en Torre.")

        self.return_to_home()
        self.limpiar_banners_home()
        return True

    # ── Alianza ──
    def do_alliance_quest(self) -> bool:
        log.info("Módulo: Misiones de Gremio")

        screen = self.device.screenshot()
        pos_bw = self.vision.find_template(screen, "templates/btn_battalion_warfare.png", threshold=0.85)
        if not pos_bw:
            log.error("No se encontró btn_battalion_warfare.")
            return False

        self.device.tap(pos_bw[0], pos_bw[1])
        self.wait_for_screen_stable(timeout=4, interval=0.5)

        screen = self.device.screenshot()
        pos_aq = self.vision.find_template(screen, "templates/btn_alliance_quest.png", threshold=0.85)
        if not pos_aq:
            log.error("No se encontró btn_alliance_quest.")
            self.cerrar_ventana()
            self.return_to_home()
            return False

        self.device.tap(pos_aq[0], pos_aq[1])
        self.wait_for_screen_stable(timeout=6, interval=0.5)

        es_vip = self.account.is_vip_server(self._sid) if self.account else False

        if es_vip:
            log.info("Servidor %s es VIP. Buscando botón especial...", self._sid)
            pos_ch = self.wait_for_template(
                "templates/btn_challenge_boss_3.png", timeout=6, threshold=0.85
            )
            if pos_ch:
                log.info("Botón VIP encontrado. Ejecutando limpieza rápida...")
                self.device.tap(pos_ch[0], pos_ch[1])
                self.wait_for_screen_stable(timeout=8, interval=0.5)
                self.clear_loot_windows()
                self.cerrar_ventana()
                # self.return_to_home()
                return True
            else:
                log.warning("No se encontró botón VIP. Usando flujo normal...")

        log.info("Buscando botón de desafío normal...")
        pos_ch = self.wait_for_template(
            "templates/btn_challenge_boss_2.png", timeout=6, threshold=0.85
        )
        if not pos_ch:
            log.error("No se encontró el botón de desafío.")
            self.cerrar_ventana()
            self.return_to_home()
            return False

        self.device.tap(pos_ch[0], pos_ch[1])
        self.handle_battle_sequence()
        self.clear_loot_windows()
        self.cerrar_ventana()
        return True

    # ── Arena ──
    def do_arena(self) -> bool:
        log.info("Módulo: Arena (5 batallas)")
        screen = self.device.screenshot()

        arena_templates = ["templates/arena.png", "templates/btn_arena.png"]
        resultado = self.vision.find_any(screen, arena_templates, threshold=0.85)
        pos_arena = (resultado[1], resultado[2]) if resultado else None

        if not pos_arena:
            log.info("No estamos en el mapa de warfare. Intentando entrar...")
            pos_warfare = self.vision.find_template(
                screen, "templates/btn_battalion_warfare.png", threshold=0.85
            )
            if pos_warfare:
                self.device.tap(pos_warfare[0], pos_warfare[1])
                self.wait_for_screen_stable(timeout=5, interval=0.5)
                screen = self.device.screenshot()
                resultado = self.vision.find_any(screen, arena_templates, threshold=0.85)
                pos_arena = (resultado[1], resultado[2]) if resultado else None

        if not pos_arena:
            log.error("No se encontró el icono de Arena.")
            return False

        self.device.tap(pos_arena[0], pos_arena[1])
        self.wait_for_screen_stable(timeout=4, interval=0.5)

        screen = self.device.screenshot()
        arena_mode_templates = [
            "templates/btn_arena.png",
            "templates/arena_top1.png",
            "templates/arena_top2.png",
            "templates/arena_top3.png",
            "templates/arena_top4.png",
            "templates/arena_top5.png",
        ]

        arenas = []
        for template in arena_mode_templates:
            encontrados = self.vision.find_all_templates(screen, template, threshold=0.85)
            if encontrados:
                arenas.extend(encontrados)

        if not arenas:
            log.error("No se encontraron modos de Arena.")
            self.cerrar_ventana()
            return False

        arenas.sort(key=lambda p: p[0])
        self.device.tap(int(arenas[0][0]), int(arenas[0][1] + 190))
        self.wait_for_screen_stable(timeout=4, interval=0.5)

        for i in range(5):
            log.info("Combate %d/5...", i + 1)
            reintentos = 0
            while reintentos < 3:
                screen = self.device.screenshot()
                oponentes = self.vision.find_all_templates(
                    screen, "templates/challenge_area.png", threshold=0.85
                )
                if not oponentes:
                    log.warning("No se encontraron oponentes.")
                    break
                oponentes.sort(key=lambda p: p[1])
                self.device.tap(oponentes[0][0], oponentes[0][1])

                if self.handle_battle_sequence() == "draw":
                    reintentos += 1
                    log.warning("Empate en Arena (%d/3). Reintentando...", reintentos)
                    time.sleep(1.5)
                else:
                    break
            if reintentos == 3:
                log.warning("Límite de empates alcanzado en Arena.")
            time.sleep(1.5)

        log.info("Arena finalizada.")
        self.cerrar_ventana()
        return True

    # ═══════════════════════════════════════════════════════════════════════
    #  INVOCACIONES GRATUITAS  —  VERSIÓN CORREGIDA
    # ═══════════════════════════════════════════════════════════════════════
    def do_summons(self) -> bool:
        log.info("🌟 Módulo: Invocaciones")

        # 1. Navegar a invocaciones
        screen = self.device.screenshot()
        pos_nav = self.vision.find_template(screen, "templates/btn_summon_nav.png", threshold=0.85)
        if not pos_nav:
            log.error("No se encontró el botón de navegación de invocaciones.")
            return False

        self.device.tap(pos_nav[0], pos_nav[1])
        # FIX: Mayor timeout para animaciones de banners
        self.wait_for_screen_stable(timeout=6, interval=0.5)

        # 2. Buscar banner de invocaciones gratuitas (con polling generoso)
        encontrado = False
        intentos_banner = 0
        free_templates = [
            "templates/btn_summon_x1_free.png",
            "templates/btn_summon_x10_free.png"
        ]

        while not encontrado and intentos_banner < 3:
            # FIX: Usar wait_for_template con timeout corto en lugar de screenshot instantáneo
            # Esto da tiempo a que los banners terminen su animación de entrada
            result = self.vision.wait_for_template(
                self.device.screenshot,
                free_templates[0],  # x1_free
                timeout=2,
                threshold=0.7,  # FIX: Bajar de 0.9 a 0.85 (menos estricto)
                interval=0.2
            )
            if not result:
                result = self.vision.wait_for_template(
                    self.device.screenshot,
                    free_templates[1],  # x10_free
                    timeout=2,
                    threshold=0.7,
                    interval=0.2
                )

            if result:
                encontrado = True
                log.info("  [✓] Banner con invocaciones gratuitas encontrado.")
            else:
                # Intentar navegar con flecha
                pos_arrow = self.vision.find_template(
                    self.device.screenshot(),
                    "templates/btn_summon_arrow_left.png",
                    threshold=0.85
                )
                if pos_arrow:
                    log.debug("  Navegando banners con flecha (intento %d)...", intentos_banner + 1)
                    self.device.tap(pos_arrow[0], pos_arrow[1])
                    time.sleep(1.5)  # FIX: Dar tiempo a la transición de banner
                    intentos_banner += 1
                else:
                    log.warning("  No se encontró flecha para navegar banners.")
                    break

        if not encontrado:
            log.warning("  No se encontraron banners con invocaciones gratuitas.")
            self._salir_de_invocaciones()
            self.return_to_home()
            self.limpiar_banners_home()
            return True  # No es un error, solo no hay gratis

        # 3. Reclamar cofre de amigos (si existe)
        pos_chest = self.wait_for_template(
            "templates/btn_friend_chest.png",
            timeout=3,
            threshold=0.8,
            interval=0.5
        )
        if pos_chest:
            log.info("  [+] Reclamando cofre de amigos...")
            self.device.tap(pos_chest[0], pos_chest[1])
            self.wait_for_screen_stable(timeout=4, interval=0.5)
            self.clear_loot_windows()

        # 4. Invocación x1 gratuita
        pos_x1 = self.wait_for_template(
            "templates/btn_summon_x1_free.png",
            timeout=2,
            threshold=0.7,
            interval=0.5
        )
        if pos_x1:
            log.info("  [+] Haciendo clic en botón x1...")
            self.device.tap(pos_x1[0], pos_x1[1])
            time.sleep(1)
            pos_confirm = self.wait_for_template(
                "templates/btn_confirm_summon.png",
                timeout=3,
                threshold=0.8
            )
            if pos_confirm:
                log.info("  [+] Confirmando invocación x1...")
                self.device.tap(pos_confirm[0], pos_confirm[1])
                self._limpiar_invocacion()
            else:
                log.warning("  No apareció confirmación para x1.")

        # 5. Invocación x10 gratuita
        pos_x10 = self.wait_for_template(
            "templates/btn_summon_x10_free.png",
            timeout=2,
            threshold=0.7,
            interval=0.5
        )
        if pos_x10:
            log.info("  [+] Haciendo clic en botón x10...")
            self.device.tap(pos_x10[0], pos_x10[1])
            time.sleep(1)
            pos_confirm = self.wait_for_template(
                "templates/btn_confirm_summon.png",
                timeout=3,
                threshold=0.8
            )
            if pos_confirm:
                log.info("  [+] Confirmando invocación x10...")
                self.device.tap(pos_confirm[0], pos_confirm[1])
                self._limpiar_invocacion()
            else:
                log.warning("  No apareció confirmación para x10.")

        # 6. Salir de invocaciones
        self._salir_de_invocaciones()
        self.limpiar_banners_home()
        return True

    def _salir_de_invocaciones(self):
        log.info("Cerrando pantalla de invocaciones...")
        time.sleep(1)

        # FIX: Usar wait_for_template en lugar de screenshot instantáneo
        pos_back = self.wait_for_template(
            "templates/btn_back_summon.png",
            timeout=4,
            threshold=0.85,
            interval=0.5
        )
        if pos_back:
            log.info("Botón back de invocaciones encontrado. Presionando...")
            self.device.tap(pos_back[0], pos_back[1])
            time.sleep(1.5)
            # Verificar que salimos
            screen = self.device.screenshot()
            if not self.vision.find_template(screen, "templates/btn_summon_nav.png", threshold=0.8):
                log.info("Salida exitosa de invocaciones.")
                return

        log.warning("No se encontró btn_back_summon o no funcionó. Usando cerrar_ventana()...")
        self.cerrar_ventana()
        time.sleep(1.5)

        screen = self.device.screenshot()
        if self.vision.find_template(screen, "templates/btn_summon_nav.png", threshold=0.8):
            log.info("Forzando salida con back físico...")
            self.device.d.press("back")
            time.sleep(1.5)

        log.info("Salida de invocaciones completada.")

    # ── Gasto de maná (Sweep) ──
    def do_spend_mana(self) -> bool:
        log.info("Módulo: Sweep de Eventos")
        time.sleep(2)

        # 1. Buscar banners de eventos activos
        eventos = None
        for intento in range(3):
            screen = self.device.screenshot()
            eventos = self.vision.find_all_templates(screen, "templates/label_ends_in.png", threshold=0.75)
            if eventos:
                break
            if intento < 2:
                log.debug("No se encontraron eventos. Reintentando (%d/3)...", intento + 1)
                time.sleep(1.5)

        if not eventos:
            log.warning("No se encontraron banners de eventos activos.")
            return True

        # 2. Tomar SOLO el primer evento (el más alto en pantalla)
        eventos.sort(key=lambda p: p[1])
        pos_evento = eventos[0]

        log.info("[>] Evento #1 (procesamiento único)...")
        self.device.tap(pos_evento[0], pos_evento[1])
        self.wait_for_screen_stable(timeout=5, interval=0.5)

        # 3. Buscar etapa EX disponible (10 > 9 > 8)
        etapa_encontrada = False
        for etapa in ["stage_ex_10.png", "stage_ex_9.png", "stage_ex_8.png"]:
            screen = self.device.screenshot()
            pos_s = self.vision.find_template(screen, f"templates/{etapa}", threshold=0.85)
            if pos_s:
                log.info("Etapa: %s", etapa.replace(".png", ""))
                self.device.tap(pos_s[0], pos_s[1])
                self.wait_for_screen_stable(timeout=4, interval=0.5)
                etapa_encontrada = True
                break

        if not etapa_encontrada:
            log.info("Sin etapas EX disponibles en este evento.")
            self.return_to_home()
            self.limpiar_banners_home()
            return True

        # 4. Realizar sweeps (máximo 3)
        # Usamos while en lugar de for para poder reintentar sin perder el contador
        # cuando se recupera maná.
        sweeps_completados = 0
        while sweeps_completados < 3:
            screen = self.device.screenshot()
            pos_sweep = self.vision.find_template(screen, "templates/btn_sweep.png", threshold=0.85)
            if not pos_sweep:
                log.warning("Botón Sweep no detectado. Saliendo del loop de sweeps.")
                break

            self.device.tap(pos_sweep[0], pos_sweep[1])
            time.sleep(1.5)  # Esperar a que aparezca popup de maná o ventana de loot

            # === LLAMADA A LA FUNCIÓN DE RECUPERACIÓN ===
            if self.check_and_recover_mana():
                log.info("Maná insuficiente detectado y recuperado. Reintentando sweep...")
                # No incrementamos sweeps_completados porque el sweep anterior
                # no se ejecutó (el juego mostró popup y requiere tocar sweep de nuevo).
                continue
            # =============================================

            # Si llegamos aquí, no hubo popup de maná: el sweep fue exitoso.
            log.info("Sweep #%d completado.", sweeps_completados + 1)
            time.sleep(1.5)
            self.clear_loot_windows()
            sweeps_completados += 1

        # 5. Cerrar ventanas y volver a home
        for _ in range(2):
            self.cerrar_ventana()

        self.return_to_home()
        self.limpiar_banners_home()
        time.sleep(1.5)

        return True

    # ── Reclamar recompensas ──
    def claim_all_rewards(self) -> bool:
        log.info("Módulo: Reclamar Recompensas")

        def _abrir_menu():
            screen = self.device.screenshot()
            pos = self.vision.find_template(screen, "templates/btn_menu_arrow_down.png", threshold=0.85)
            if pos:
                self.device.tap(pos[0], pos[1])
                time.sleep(1)

        # Buzón
        _abrir_menu()
        screen = self.device.screenshot()
        pos_mail = self.vision.find_template(screen, "templates/btn_mailbox_icon.png", threshold=0.85)
        if pos_mail:
            log.info("Accediendo al buzón...")
            self.device.tap(pos_mail[0], pos_mail[1])
            self.wait_for_screen_stable(timeout=3, interval=0.5)

            screen = self.device.screenshot()
            pos_claim = self.vision.find_template(screen, "templates/btn_claim_all.png", threshold=0.85)
            if pos_claim:
                log.info("Claim All del buzón...")
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(2)
                self.clear_loot_windows()
            else:
                log.debug("Sin correos pendientes.")

            self.cerrar_ventana()
            time.sleep(1)

        # Misiones
        _abrir_menu()
        screen = self.device.screenshot()
        pos_missions = self.vision.find_template(screen, "templates/btn_missions_icon.png", threshold=0.85)
        if not pos_missions:
            log.warning("No se encontró el icono de Misiones.")
            self.return_to_home()
            self.limpiar_banners_home()
            return False

        log.info("Accediendo a misiones...")
        self.device.tap(pos_missions[0], pos_missions[1])
        self.wait_for_screen_stable(timeout=4, interval=0.5)

        screen = self.device.screenshot()
        pos_tab = self.vision.find_template(screen, "templates/tab_daily.png", threshold=0.85)
        if pos_tab:
            log.info("Seleccionando pestaña Daily...")
            self.device.tap(pos_tab[0], pos_tab[1])
            time.sleep(1.5)

        MAX_ITER = 4
        vacios_consecutivos = 0
        historial_cofres = set()

        log.debug("Barrido de misiones y cofres (máx %d ciclos)...", MAX_ITER)

        for iteracion in range(1, MAX_ITER + 1):
            reclamado = False
            screen = self.device.screenshot()

            pos_claim = self.vision.find_template(screen, "templates/btn_claim_all.png", threshold=0.85)
            if pos_claim:
                log.info("Ciclo %d - Reclamando misiones...", iteracion)
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(2)
                self.clear_loot_windows()
                time.sleep(0.8)
                reclamado = True

            if not reclamado:
                pos_chest = self.vision.find_template(screen, "templates/chest_ready.png", threshold=0.82)
                if pos_chest:
                    key = (int(pos_chest[0]), int(pos_chest[1]))
                    if key not in historial_cofres:
                        log.info("Ciclo %d - Cofre detectado.", iteracion)
                        self.device.tap(pos_chest[0], pos_chest[1])
                        historial_cofres.add(key)
                        time.sleep(2)
                        self.clear_loot_windows()
                        time.sleep(0.8)
                        reclamado = True

            if reclamado:
                vacios_consecutivos = 0
            else:
                vacios_consecutivos += 1
                log.debug("Ciclo %d vacío (%d/2).", iteracion, vacios_consecutivos)
                self.device.tap(100, 100)
                time.sleep(1)

            if vacios_consecutivos >= 2:
                log.info("Interfaz limpia. Finalizando barrido.")
                break
        else:
            log.warning("Se agotaron las %d iteraciones de seguridad.", MAX_ITER)

        log.info("Saliendo de misiones...")
        screen = self.device.screenshot()
        pos_back = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.85)
        if pos_back:
            self.device.tap(pos_back[0], pos_back[1])
            time.sleep(1.5)
        else:
            self.device.d.press("back")
            time.sleep(1.5)

        log.info("Módulo de recompensas completado.")
        self.cerrar_ventana()
        self.limpiar_banners_home()
        return True
