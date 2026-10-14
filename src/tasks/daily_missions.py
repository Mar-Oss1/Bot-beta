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
                log.warning("OCR vacío. No se leyeron gemas.")
                return 0

            valor = int(numeros)
            log.info("Gemas leídas: %d", valor)
            return valor

        except Exception as e:
            log.error("Error de OCR: %s", e)
            return 0

    def _skip_animacion(self):
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

    def _limpiar_invocacion(self):
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

    # ── Gestión de combates con Polling Activo ──
    def handle_battle_sequence(self, timeout=20) -> str:
        log.info("Esperando resolución del combate...")
        inicio = time.time()

        while time.time() - inicio < timeout:
            screen = self.device.screenshot()

            resultado = self.vision.find_any(screen, [
                "templates/Draw.png",
                "templates/victory_banner.png",
                "templates/defeat_banner.png",
                "templates/btn_battle_skip.png",
                "templates/btn_battle_speed.png"
            ], threshold=0.85)

            if resultado:
                template, x, y = resultado

                if "Draw" in template:
                    log.info("EMPATE detectado. Cerrando...")
                    pos_ok = self.vision.find_template(screen, "templates/btn_draw_ok.png", threshold=0.85)
                    tap_x, tap_y = pos_ok if pos_ok else (x, y + 150)
                    self.device.tap(tap_x, tap_y)
                    time.sleep(2)
                    self.clear_loot_windows()
                    return "draw"

                elif "victory" in template or "defeat" in template:
                    log.info("Combate finalizado. Limpiando recompensas...")
                    self.clear_loot_windows()
                    return "finished"

                elif "skip" in template or "speed" in template:
                    log.debug("Botón de batalla visible. Acelerando/Saltando...")
                    self.device.tap(x, y)
                    time.sleep(1)
                    continue

            time.sleep(0.5)

        log.warning("Timeout (%ds) esperando resultado de batalla.", timeout)
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
            time.sleep(1.5)
            gemas_fin = self.leer_gemas()

        diferencia = gemas_fin - gemas_inicio
        log.info("--" * 40)
        log.info("REPORTE CONTABLE - %s", cuenta_label)
        log.info("  Ganancia Neta: %s%d gemas", "+" if diferencia >= 0 else "", diferencia)
        log.info("--" * 40)

        registrar_economia(
            cuenta_nombre=self.account.name if self.account else "Prueba",
            server_id=server_id,
            gemas_inicio=gemas_inicio,
            gemas_fin=gemas_fin,
        )

        return rutina_exitosa

    def do_lucky_fountain(self) -> bool:
        log.info("Módulo: Lucky Fountain")
        screen = self.device.screenshot()
        pos = self.vision.find_template(screen, "templates/btn_fountain_home.png", threshold=0.8)
        if not pos:
            log.error("No se encontró btn_fountain_home.")
            return False

        self.device.tap(pos[0], pos[1])
        self.wait_for_screen_stable(timeout=5, interval=0.5)

        tiradas = 0
        for fase in range(1, 5):
            screen = self.device.screenshot()
            pos_offer = self.vision.find_template(screen, "templates/btn_fountain_offer.png", threshold=0.8)
            if pos_offer:
                log.info("Tirando fase %d/4 ...", fase)
                self.device.tap(pos_offer[0], pos_offer[1])
                self.wait_for_screen_stable(timeout=6, interval=0.5)
                self.clear_loot_windows()
                time.sleep(0.8)
                tiradas += 1
            else:
                break

        self.cerrar_ventana()
        self.return_to_home()
        self.limpiar_banners_home()
        return tiradas > 0

    def _detectar_ssr(self) -> bool:
        screen = self.device.screenshot()
        img = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brillo_promedio = float(np.mean(gray))
        UMBRAL_SSR = 10.0
        es_ssr = brillo_promedio < UMBRAL_SSR

        if es_ssr:
            log.info("SSR detectado! Brillo: %.1f", brillo_promedio)
        return es_ssr

    def _manejar_animacion_ssr(self):
        log.info("Manejando animación SSR...")
        self.device.tap(760, 1200)
        time.sleep(1.5)
        pos_skip = self.wait_for_template(
            "templates/btn_skip_summon.png", timeout=5, threshold=0.7, interval=0.4
        )
        if pos_skip:
            self.device.tap(pos_skip[0], pos_skip[1])
            time.sleep(2)

    def do_premium_summons(self, veces: int = 1, parar_sin_ssr: int = 0):
        log.info("Módulo: Invocación Premium (%d vez/veces)", veces)
        rondas_sin_ssr = ssr_total = ronda = 0

        for ronda in range(1, veces + 1):
            if parar_sin_ssr > 0 and rondas_sin_ssr >= parar_sin_ssr:
                break

            pos_x10 = self.wait_for_template("templates/btn_summon_x10.png", timeout=5, threshold=0.8, interval=0.5)
            if not pos_x10:
                return

            self.device.tap(pos_x10[0], pos_x10[1])
            time.sleep(1)

            pos_confirm = self.wait_for_template("templates/btn_confirm_summon.png", timeout=4, threshold=0.8,
                                                 interval=0.3)
            if not pos_confirm:
                continue

            self.device.tap(pos_confirm[0], pos_confirm[1])
            time.sleep(1.5)

            ssr_en_esta_ronda = False
            inicio_anim = time.time()
            MAX_ANIM_TIME = 15
            skip_ya_tocado = ssr_ya_manejado = False

            while time.time() - inicio_anim < MAX_ANIM_TIME:
                screen = self.device.screenshot()

                if not ssr_ya_manejado and self._detectar_ssr():
                    ssr_en_esta_ronda = ssr_ya_manejado = True
                    ssr_total += 1
                    self._manejar_animacion_ssr()
                    skip_ya_tocado = False
                    inicio_anim = time.time()
                    continue

                if not skip_ya_tocado:
                    pos_skip = self.vision.find_template(screen, "templates/btn_skip_summon.png", threshold=0.7)
                    if pos_skip:
                        self.device.tap(pos_skip[0], pos_skip[1])
                        skip_ya_tocado = True
                        time.sleep(0.8)
                        continue

                pos_ok = self.vision.find_template(screen, "templates/btn_skip_ok.png", threshold=0.75)
                if pos_ok:
                    self.device.tap(pos_ok[0], pos_ok[1])
                    time.sleep(1)
                    break

                if self.vision.find_template(screen, "templates/btn_summon_x10.png", threshold=0.8):
                    break

                if skip_ya_tocado and not ssr_ya_manejado:
                    if self.vision.find_template(screen, "templates/btn_skip_summon.png", threshold=0.7):
                        skip_ya_tocado = False
                        continue

                self.device.tap(200, 200)
                time.sleep(0.4)

            if ssr_en_esta_ronda:
                rondas_sin_ssr = 0
            else:
                rondas_sin_ssr += 1

            self.clear_loot_windows()
            time.sleep(0.8)

    def do_tower_of_trials(self) -> bool:
        log.info("Módulo: Tower of Trials")
        pos_tot = self.vision.find_template(self.device.screenshot(), "templates/btn_tot_home.png", threshold=0.85)
        if not pos_tot:
            return False

        self.device.tap(pos_tot[0], pos_tot[1])
        self.wait_for_screen_stable(timeout=5, interval=0.5)

        pos_chest = self.vision.find_template(self.device.screenshot(), "templates/btn_tot_chest.png", threshold=0.8)
        if pos_chest:
            self.device.tap(pos_chest[0], pos_chest[1] - 15)
            time.sleep(1.5)
            self.clear_loot_windows()

        fast_forwards_completados = exploraciones_completadas = 0

        pos_ff = self.vision.find_template(self.device.screenshot(), "templates/btn_fast_forward_menu.png",
                                           threshold=0.85)
        if pos_ff:
            self.device.tap(pos_ff[0], pos_ff[1])
            self.wait_for_screen_stable(timeout=5, interval=0.5)
            intentos_flecha = 0

            while fast_forwards_completados < 2 and intentos_flecha < 3:
                pos_green = self.wait_for_template("templates/btn_ff_green.png", timeout=2, threshold=0.85,
                                                   interval=0.3)
                if pos_green:
                    self.device.tap(pos_green[0], pos_green[1])
                    time.sleep(2.5)
                    self.device.tap(100, 100)
                    time.sleep(0.8)
                    fast_forwards_completados += 1
                    intentos_flecha = 0
                    self.wait_for_screen_stable(timeout=3, interval=0.5)
                    continue

                pos_arrow = self.vision.find_template(self.device.screenshot(), "templates/btn_ff_arrow.png",
                                                      threshold=0.85)
                if pos_arrow:
                    self.device.tap(pos_arrow[0], pos_arrow[1])
                    time.sleep(1.2)
                    intentos_flecha += 1
                    continue
                break

            self.cerrar_ventana()
            time.sleep(0.8)

        for _ in range(3):
            self.clear_loot_windows()
            pos_exp = self.vision.find_template(self.device.screenshot(), "templates/btn_explore.png", threshold=0.85)
            if pos_exp:
                self.device.tap(pos_exp[0], pos_exp[1])
                time.sleep(2.5)
                self.clear_loot_windows()
                exploraciones_completadas += 1
            else:
                break

        pos_boss = self.vision.find_template(self.device.screenshot(), "templates/btn_challenge_boss.png",
                                             threshold=0.85)
        boss_completado = False
        if pos_boss:
            log.info("Desafiando al Boss...")
            self.device.tap(pos_boss[0], pos_boss[1])
            self.handle_battle_sequence()
            boss_completado = True

        self.return_to_home()
        self.limpiar_banners_home()

        return fast_forwards_completados >= 1 and exploraciones_completadas >= 2 and boss_completado

    def do_alliance_quest(self) -> bool:
        log.info("Módulo: Misiones de Gremio")

        pos_bw = self.vision.find_template(self.device.screenshot(), "templates/btn_battalion_warfare.png",
                                           threshold=0.85)
        if not pos_bw: return False

        self.device.tap(pos_bw[0], pos_bw[1])
        self.wait_for_screen_stable(timeout=4, interval=0.5)

        pos_aq = self.vision.find_template(self.device.screenshot(), "templates/btn_alliance_quest.png", threshold=0.85)
        if not pos_aq:
            self.cerrar_ventana()
            self.return_to_home()
            return False

        self.device.tap(pos_aq[0], pos_aq[1])
        self.wait_for_screen_stable(timeout=6, interval=0.5)

        if self.account and self.account.is_vip_server(self._sid):
            pos_ch = self.wait_for_template("templates/btn_challenge_boss_3.png", timeout=6, threshold=0.85)
            if pos_ch:
                self.device.tap(pos_ch[0], pos_ch[1])
                self.wait_for_screen_stable(timeout=8, interval=0.5)
                self.clear_loot_windows()
                self.cerrar_ventana()
                return True

        pos_ch = self.wait_for_template("templates/btn_challenge_boss_2.png", timeout=6, threshold=0.85)
        if not pos_ch:
            self.cerrar_ventana()
            self.return_to_home()
            return False

        self.device.tap(pos_ch[0], pos_ch[1])
        self.handle_battle_sequence()
        self.clear_loot_windows()
        self.cerrar_ventana()
        return True

    def do_arena(self) -> bool:
        log.info("Módulo: Arena (5 batallas)")
        screen = self.device.screenshot()

        resultado = self.vision.find_any(screen, ["templates/arena.png", "templates/btn_arena.png"], threshold=0.85)
        pos_arena = (resultado[1], resultado[2]) if resultado else None

        if not pos_arena:
            pos_warfare = self.vision.find_template(screen, "templates/btn_battalion_warfare.png", threshold=0.85)
            if pos_warfare:
                self.device.tap(pos_warfare[0], pos_warfare[1])
                self.wait_for_screen_stable(timeout=5, interval=0.5)
                resultado = self.vision.find_any(self.device.screenshot(),
                                                 ["templates/arena.png", "templates/btn_arena.png"], threshold=0.85)
                pos_arena = (resultado[1], resultado[2]) if resultado else None

        if not pos_arena:
            return False

        self.device.tap(pos_arena[0], pos_arena[1])
        self.wait_for_screen_stable(timeout=4, interval=0.5)

        arenas = []
        for template in ["templates/btn_arena.png", "templates/arena_top1.png", "templates/arena_top2.png",
                         "templates/arena_top3.png", "templates/arena_top4.png", "templates/arena_top5.png"]:
            arenas.extend(self.vision.find_all_templates(self.device.screenshot(), template, threshold=0.85))

        if not arenas:
            self.cerrar_ventana()
            return False

        arenas.sort(key=lambda p: p[0])
        self.device.tap(int(arenas[0][0]), int(arenas[0][1] + 190))
        self.wait_for_screen_stable(timeout=4, interval=0.5)

        batallas_exitosas = batallas_fallidas = 0

        for i in range(5):
            log.info("Combate %d/5...", i + 1)
            reintentos = 0
            combate_ok = False

            while reintentos < 3:
                oponentes = self.vision.find_all_templates(self.device.screenshot(), "templates/challenge_area.png",
                                                           threshold=0.85)
                if not oponentes:
                    break

                oponentes.sort(key=lambda p: p[1])
                self.device.tap(oponentes[0][0], oponentes[0][1])

                resultado_batalla = self.handle_battle_sequence()
                if resultado_batalla == "draw":
                    reintentos += 1
                    time.sleep(1.5)
                else:
                    combate_ok = True
                    break

            if combate_ok:
                batallas_exitosas += 1
                log.info("  ✓ Combate %d completado. Esperando enfriamiento del servidor (10s)...", i + 1)
                time.sleep(5)
            else:
                batallas_fallidas += 1
                time.sleep(2)

        self.cerrar_ventana()
        return batallas_exitosas >= 4

    def do_summons(self) -> bool:
        log.info("🌟 Módulo: Invocaciones")

        pos_nav = self.vision.find_template(self.device.screenshot(), "templates/btn_summon_nav.png", threshold=0.85)
        if not pos_nav: return False

        self.device.tap(pos_nav[0], pos_nav[1])
        self.wait_for_screen_stable(timeout=6, interval=0.5)

        encontrado, intentos_banner = False, 0
        while not encontrado and intentos_banner < 3:
            result = self.vision.wait_for_template(self.device.screenshot, "templates/btn_summon_x1_free.png",
                                                   timeout=2, threshold=0.7, interval=0.2) or \
                     self.vision.wait_for_template(self.device.screenshot, "templates/btn_summon_x10_free.png",
                                                   timeout=2, threshold=0.7, interval=0.2)
            if result:
                encontrado = True
            else:
                pos_arrow = self.vision.find_template(self.device.screenshot(), "templates/btn_summon_arrow_left.png",
                                                      threshold=0.85)
                if pos_arrow:
                    self.device.tap(pos_arrow[0], pos_arrow[1])
                    time.sleep(1.5)
                    intentos_banner += 1
                else:
                    break

        if not encontrado:
            self._salir_de_invocaciones()
            self.return_to_home()
            self.limpiar_banners_home()
            return True

        pos_chest = self.wait_for_template("templates/btn_friend_chest.png", timeout=3, threshold=0.8, interval=0.5)
        if pos_chest:
            self.device.tap(pos_chest[0], pos_chest[1])
            self.wait_for_screen_stable(timeout=4, interval=0.5)
            self.clear_loot_windows()

        invocaciones_hechas = 0
        for template in ["templates/btn_summon_x1_free.png", "templates/btn_summon_x10_free.png"]:
            pos_btn = self.wait_for_template(template, timeout=2, threshold=0.7, interval=0.5)
            if pos_btn:
                self.device.tap(pos_btn[0], pos_btn[1])
                time.sleep(1)
                pos_confirm = self.wait_for_template("templates/btn_confirm_summon.png", timeout=3, threshold=0.8)
                if pos_confirm:
                    self.device.tap(pos_confirm[0], pos_confirm[1])
                    self._limpiar_invocacion()
                    invocaciones_hechas += 1

        self._salir_de_invocaciones()
        self.limpiar_banners_home()
        return invocaciones_hechas > 0

    def _salir_de_invocaciones(self):
        time.sleep(1)
        pos_back = self.wait_for_template("templates/btn_back_summon.png", timeout=4, threshold=0.85, interval=0.5)
        if pos_back:
            self.device.tap(pos_back[0], pos_back[1])
            time.sleep(1.5)
            if not self.vision.find_template(self.device.screenshot(), "templates/btn_home_nav.png", threshold=0.8):
                return

        self.cerrar_ventana()
        time.sleep(1.5)
        if self.vision.find_template(self.device.screenshot(), "templates/btn_summon_nav.png", threshold=0.8):
            self.device.d.press("back")
            time.sleep(1.5)

    def do_spend_mana(self) -> bool:
        log.info("Módulo: Sweep de Eventos")
        time.sleep(2)

        eventos = None
        for intento in range(3):
            eventos = self.vision.find_all_templates(self.device.screenshot(), "templates/label_ends_in.png",
                                                     threshold=0.75)
            if eventos: break
            time.sleep(1.5)

        if not eventos: return True

        eventos.sort(key=lambda p: p[1])
        sweeps_totales = 0

        for i, pos_evento in enumerate(eventos):
            self.device.tap(pos_evento[0], pos_evento[1])
            self.wait_for_screen_stable(timeout=5, interval=0.5)

            etapa_encontrada = False
            for etapa in ["stage_ex_10.png", "stage_ex_9.png", "stage_ex_8.png"]:
                pos_s = self.vision.find_template(self.device.screenshot(), f"templates/{etapa}", threshold=0.7)
                if pos_s:
                    self.device.tap(pos_s[0], pos_s[1])
                    self.wait_for_screen_stable(timeout=4, interval=0.5)
                    etapa_encontrada = True
                    break

            if not etapa_encontrada:
                self.cerrar_ventana()
                time.sleep(1)
                self.return_to_home()
                self.limpiar_banners_home()
                time.sleep(1)
                continue

            sweeps_en_este_evento = 0
            while sweeps_en_este_evento < 3:
                pos_sweep = self.vision.find_template(self.device.screenshot(), "templates/btn_sweep.png",
                                                      threshold=0.85)
                if not pos_sweep: break

                self.device.tap(pos_sweep[0], pos_sweep[1])
                time.sleep(1.5)

                if self.check_and_recover_mana(): continue

                time.sleep(1.5)
                self.clear_loot_windows()
                sweeps_en_este_evento += 1

            sweeps_totales += sweeps_en_este_evento
            if sweeps_en_este_evento > 0:
                self.cerrar_ventana()
                time.sleep(1)
                self.return_to_home()
                self.limpiar_banners_home()
                time.sleep(1)
                return True

            self.cerrar_ventana()
            time.sleep(1)
            self.return_to_home()
            self.limpiar_banners_home()
            time.sleep(1)

        return sweeps_totales > 0

    def claim_all_rewards(self) -> bool:
        log.info("Módulo: Reclamar Recompensas")

        def _abrir_menu():
            pos = self.vision.find_template(self.device.screenshot(), "templates/btn_menu_arrow_down.png",
                                            threshold=0.85)
            if pos:
                self.device.tap(pos[0], pos[1])
                time.sleep(1)

        _abrir_menu()
        pos_mail = self.vision.find_template(self.device.screenshot(), "templates/btn_mailbox_icon.png", threshold=0.85)
        if pos_mail:
            self.device.tap(pos_mail[0], pos_mail[1])
            self.wait_for_screen_stable(timeout=4, interval=0.5)
            pos_claim = self.vision.find_template(self.device.screenshot(), "templates/btn_claim_all.png",
                                                  threshold=0.85)
            if pos_claim:
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(2)
                self.clear_loot_windows()
            self.cerrar_ventana()
            time.sleep(1)

        _abrir_menu()
        pos_missions = self.vision.find_template(self.device.screenshot(), "templates/btn_missions_icon.png",
                                                 threshold=0.85)
        if not pos_missions:
            self.return_to_home()
            self.limpiar_banners_home()
            return False

        self.device.tap(pos_missions[0], pos_missions[1])
        self.wait_for_screen_stable(timeout=4, interval=0.5)

        pos_tab = self.vision.find_template(self.device.screenshot(), "templates/tab_daily.png", threshold=0.85)
        if pos_tab:
            self.device.tap(pos_tab[0], pos_tab[1])
            time.sleep(1.5)

        vacios_consecutivos, historial_cofres = 0, set()
        for _ in range(4):
            reclamado, screen = False, self.device.screenshot()
            pos_claim = self.vision.find_template(screen, "templates/btn_claim_all.png", threshold=0.85)
            if pos_claim:
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
                        self.device.tap(pos_chest[0], pos_chest[1])
                        historial_cofres.add(key)
                        time.sleep(2)
                        self.clear_loot_windows()
                        time.sleep(0.8)
                        reclamado = True

            vacios_consecutivos = 0 if reclamado else vacios_consecutivos + 1
            if not reclamado:
                self.device.tap(100, 100)
                time.sleep(1)

            if vacios_consecutivos >= 2: break

        pos_back = self.vision.find_template(self.device.screenshot(), "templates/btn_back.png", threshold=0.85)
        self.device.tap(pos_back[0], pos_back[1]) if pos_back else self.device.d.press("back")
        time.sleep(1.5)

        self.cerrar_ventana()
        self.limpiar_banners_home()
        return True
