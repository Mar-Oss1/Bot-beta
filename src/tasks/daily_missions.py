"""
tasks/daily_missions.py

Módulo principal de misiones diarias del bot Evertale.

CAMBIOS VS VERSIÓN ANTERIOR:
- Eliminado: sistema paralelo estado_diario.json
- El estado de cada módulo se guarda en Account.progress (accounts.json)
  usando mark_task_done(modulo, server_id) después de cada módulo completado.
- Soporte real multi-servidor: execute(server_id) diferencia qué servidor
  se está procesando y guarda el estado por separado para cada uno.
- Tesseract: ruta leída desde .env via core/config.py (sin hardcoding).
- Logging: reemplaza todos los print() por log.info / log.warning / log.error.
- Economía: guarda gemas en logs/economia_log.jsonl al final de cada sesión.
"""
import time
import datetime
import cv2
import pytesseract

from core.config import TESSERACT_CMD
from core.logger import get_logger
from core.economia import registrar_economia

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

log = get_logger("daily_missions")


class DailyMissions:
    """
    Recibe el objeto Account y Database para registrar el progreso
    directamente en accounts.json después de cada módulo, sin archivo auxiliar.
    """

    def __init__(self, device, vision, account, db):
        self.device = device
        self.vision = vision
        self.account = account     # objeto Account de core/database.py
        self.db = db               # objeto Database para llamar db.save()

    # ──────────────────────────────────────────
    # HELPERS DE ESTADO (delegan a Account)
    # ──────────────────────────────────────────
    def _modulo_completado(self, modulo: str) -> bool:
        """
        Consulta si el módulo ya fue completado hoy para este servidor.
        Para cuentas sin servidor, server_id es None (raíz del día).
        """
        if self.account is None:
            return False
        return self.account.is_task_done(modulo, self._sid)

    def _completar_modulo(self, modulo: str):
        """
        Marca el módulo como completado y guarda inmediatamente en disco.
        Si el bot se cae después de esto, el módulo no se repite.
        """
        if self.account is None:
            return
        self.account.mark_task_done(modulo, self._sid)
        if self.db is not None:
            self.db.save()
        log.debug("Módulo '%s' guardado en accounts.json [server: %s]", modulo, self._sid or "DEFAULT")

    @property
    def _sid(self):
        """
        Convierte "DEFAULT" a None para que mark_task_done/is_task_done
        guarden el estado directamente bajo la fecha (sin sub-clave de servidor).
        """
        return None if self._server_id == "DEFAULT" else self._server_id

    # ──────────────────────────────────────────
    # OCR — CONTADOR DE GEMAS
    # ──────────────────────────────────────────
    def leer_gemas(self) -> int:
        """
        Lee el contador de gemas con OCR usando un recorte fijo de pantalla.
        Coordenadas calibradas para 2400×1080 (POCO X5 Pro en landscape).
        """
        log.info("👁️  Escaneando contador de gemas...")
        try:
            X, Y, W, H = 1315, 35, 290, 50
            screen_path = "temp_gems_ocr.png"
            self.device.d.screenshot(screen_path)
            img = cv2.imread(screen_path)

            if img is None:
                log.warning("No se pudo leer la captura para OCR.")
                return 0

            roi = img[Y:Y + H, X:X + W]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)

            texto = pytesseract.image_to_string(
                thresh, config="--psm 7 -c tessedit_char_whitelist=0123456789"
            )
            numeros = "".join(filter(str.isdigit, texto))

            import os
            if os.path.exists(screen_path):
                os.remove(screen_path)

            # Si OCR falla, guardar debug para diagnóstico
            if not numeros:
                debug_path = f"logs/debug_ocr_{datetime.datetime.now().strftime('%H%M%S')}.png"
                os.makedirs("logs", exist_ok=True)
                cv2.imwrite(debug_path, thresh)
                log.warning("OCR devolvió vacío. Debug guardado en %s", debug_path)
                return 0

            valor = int(numeros)
            log.info("💎 Gemas leídas: %d", valor)
            return valor

        except Exception as e:
            log.error("Error de OCR: %s", e)
            return 0

    # ──────────────────────────────────────────
    # FUNCIONES BASE DE INTERACCIÓN
    # ──────────────────────────────────────────
    def cerrar_ventana(self, screen=None):
        """Cierre unificado: botón X → btn_back → back físico de Android."""
        if screen is None:
            screen = self.device.screenshot()

        pos = self.vision.find_template(screen, "templates/btn_cerrar_x.png", threshold=0.8)
        if pos:
            log.debug("Cerrando con botón X")
            self.device.tap(pos[0], pos[1])
            time.sleep(2)
            return

        pos = self.vision.find_template(screen, "templates/btn_back.png", threshold=0.9)
        if pos:
            log.debug("Cerrando con btn_back.png")
            self.device.tap(pos[0], pos[1])
            time.sleep(2)
            return

        log.debug("Sin botón de cierre detectado. Usando back de Android.")
        self.device.d.press("back")
        time.sleep(2)

    def clear_loot_windows(self):
        """Cierra ventanas de fin de batalla / nivel / loot hasta 5 veces."""
        templates = [
            "templates/pantalla_loot.png",
            "templates/level_up.png",
            "templates/rewards.png",
            "templates/victory_banner.png",
            "templates/defeat_banner.png",
        ]
        intentos = 0
        while intentos < 5:
            screen = self.device.screenshot()
            if any(self.vision.find_template(screen, t, threshold=0.9) for t in templates):
                log.debug("Ventana de loot/victoria detectada. Cerrando...")
                self.device.tap(100, 100)
                time.sleep(1.5)
                intentos += 1
            else:
                break

    def _limpiar_invocacion(self):
        """Salta la animación de invocación y cierra las pantallas de resultado."""
        log.debug("Esperando botón Skip de invocación...")
        for _ in range(3):
            screen = self.device.screenshot()
            pos = self.vision.find_template(screen, "templates/btn_skip_scene.png", threshold=0.75)
            if pos:
                self.device.tap(pos[0], pos[1])
                log.debug("Animación saltada.")
                time.sleep(2)
                break
            time.sleep(1)
        else:
            log.debug("Sin botón Skip. Esperando animación natural...")
            time.sleep(5)

        intentos = 0
        while intentos < 6:
            screen = self.device.screenshot()
            pos_ok = self.vision.find_template(screen, "templates/btn_result_ok.png", threshold=0.8)
            pos_rw = self.vision.find_template(screen, "templates/rewards.png", threshold=0.8)
            if pos_ok:
                self.device.tap(pos_ok[0], pos_ok[1])
                time.sleep(1.5)
                intentos = 0
            elif pos_rw:
                self.device.tap(100, 100)
                time.sleep(1.5)
                intentos = 0
            else:
                intentos += 1
                time.sleep(1)

    def return_to_home(self):
        screen = self.device.screenshot()
        pos = self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.9)
        if pos:
            self.device.tap(pos[0], pos[1])
            time.sleep(3)

    def handle_battle_sequence(self) -> str:
        """
        Maneja el flujo de una batalla.
        Retorna "draw" si detecta empate, "finished" si terminó normalmente.
        El llamador decide si reintenta (máx 3 veces en torre/arena).
        """
        time.sleep(2)
        screen = self.device.screenshot()
        pos_draw = self.vision.find_template(screen, "templates/Draw.png", threshold=0.9)

        if pos_draw:
            log.info("⚖️  EMPATE detectado.")
            pos_ok = self.vision.find_template(screen, "templates/btn_draw_ok.png", threshold=0.9)
            if pos_ok:
                self.device.tap(pos_ok[0], pos_ok[1])
            time.sleep(2)
            return "draw"

        log.debug("Intentando saltar/acelerar batalla...")
        time.sleep(2)

        for _ in range(3):
            screen = self.device.screenshot()
            pos_skip = self.vision.find_template(screen, "templates/btn_battle_skip.png", threshold=0.9)
            pos_speed = self.vision.find_template(screen, "templates/btn_battle_speed.png", threshold=0.9)
            if pos_skip:
                self.device.tap(pos_skip[0], pos_skip[1])
                log.debug("Batalla saltada.")
                time.sleep(4)
                break
            elif pos_speed:
                self.device.tap(pos_speed[0], pos_speed[1])
                time.sleep(1)

        self.clear_loot_windows()
        return "finished"

    def check_and_recover_mana(self) -> bool:
        screen = self.device.screenshot()
        pos = self.vision.find_template(screen, "templates/mana_insuficiente.png", threshold=0.9)
        if not pos:
            return False

        log.info("💧 Aviso de maná detectado. Recuperando...")
        pos_ok = self.vision.find_template(screen, "templates/btn_ok_restore.png", threshold=0.9)
        self.device.tap((pos_ok or pos)[0], (pos_ok or pos)[1])
        time.sleep(2)

        screen2 = self.device.screenshot()
        pos_cb = self.vision.find_template(screen2, "templates/checkbox_mana.png", threshold=0.9)
        if pos_cb:
            self.device.tap(pos_cb[0], pos_cb[1])
            time.sleep(1.5)

        self.cerrar_ventana(self.device.screenshot())
        time.sleep(2)
        return True

    # ──────────────────────────────────────────
    # ORQUESTADOR PRINCIPAL
    # ──────────────────────────────────────────
    def execute(self, server_id: str = "DEFAULT") -> bool:
        """
        Ejecuta la rutina diaria completa para el servidor indicado.
        Cada módulo se verifica contra accounts.json antes de ejecutar
        y se guarda inmediatamente al completar.

        Args:
            server_id: "SA-3", "SA-6", "DEFAULT", etc. Se usa como clave
                       en Account.progress para separar el estado por servidor.
        """
        self._server_id = server_id
        cuenta_label = f"{self.account.name if self.account else 'Prueba'} [{server_id}]"

        log.info("=" * 55)
        log.info("📜 Iniciando Rutina Diaria — %s", cuenta_label)
        log.info("=" * 55)

        self.return_to_home()
        time.sleep(2)

        gemas_inicio = self.leer_gemas()
        log.info("💎 Gemas al empezar: %d", gemas_inicio)

        # Lucky Fountain (días 14, 15, 30, 31)
        dia = datetime.datetime.now().day
        if dia in [14, 15, 30, 31]:
            if not self._modulo_completado("fountain"):
                log.info("📅 Día %d → activando Lucky Fountain", dia)
                self.do_lucky_fountain()
            else:
                log.info("⏭️  Lucky Fountain ya completada.")

        # Módulos en orden
        modulos = [
            ("tower",    self.do_tower_of_trials,  "Tower of Trials"),
            ("alliance", self.do_alliance_quest,    "Misiones de Gremio"),
            ("arena",    self.do_arena,             "Arena"),
            ("summons",  self.do_summons,           "Invocaciones"),
            ("mana",     self.do_spend_mana,        "Gasto de Maná"),
            ("rewards",  self.claim_all_rewards,    "Reclamo de Recompensas"),
        ]

        for key, func, label in modulos:
            if not self._modulo_completado(key):
                log.info("▶️  Ejecutando: %s", label)
                func()
                self._completar_modulo(key)
            else:
                log.info("⏭️  %s ya completado.", label)

        # Marcar la sesión completa
        self._completar_modulo("daily_missions")
        self._completar_modulo("login_bonus")

        # OCR final y registro económico
        self.return_to_home()
        time.sleep(3)
        gemas_fin = self.leer_gemas()
        if gemas_fin == 0:
            log.warning("Lectura de gemas cero, reintentando...")
            time.sleep(2)
            gemas_fin = self.leer_gemas()

        diferencia = gemas_fin - gemas_inicio
        log.info("━" * 40)
        log.info("📊 REPORTE CONTABLE — %s", cuenta_label)
        log.info("  💎 Gemas inicio : %d", gemas_inicio)
        log.info("  💎 Gemas fin    : %d", gemas_fin)
        log.info("  📈 Ganancia Neta: %s%d gemas", "+" if diferencia >= 0 else "", diferencia)
        log.info("━" * 40)

        # Guardar en el log económico histórico
        registrar_economia(
            cuenta_nombre=self.account.name if self.account else "Prueba",
            server_id=server_id,
            gemas_inicio=gemas_inicio,
            gemas_fin=gemas_fin,
        )

        log.info("✅ Rutina completada para %s", cuenta_label)
        return True

    # ──────────────────────────────────────────
    # MÓDULOS DE JUEGO
    # ──────────────────────────────────────────
    def do_lucky_fountain(self):
        log.info("⛲ Módulo: Lucky Fountain")
        screen = self.device.screenshot()
        pos = self.vision.find_template(screen, "templates/btn_fountain_home.png", threshold=0.8)
        if pos:
            self.device.tap(pos[0], pos[1])
            time.sleep(3)

        for fase in range(1, 5):
            screen = self.device.screenshot()
            pos_offer = self.vision.find_template(screen, "templates/btn_fountain_offer.png", threshold=0.8)
            if pos_offer:
                log.info("  [+] Tirando fase %d/4...", fase)
                self.device.tap(pos_offer[0], pos_offer[1])
                time.sleep(4)
                self.clear_loot_windows()
                time.sleep(1)
            else:
                log.warning("  [!] No se puede tirar más.")
                break

        log.debug("Cerrando Lucky Fountain...")
        self.cerrar_ventana()
        self.return_to_home()
        self._completar_modulo("fountain")

    def do_premium_summons(self):
        log.info("🌠 Módulo: Invocación Premium")
        screen = self.device.screenshot()
        pos_x10 = self.vision.find_template(screen, "templates/btn_summon_x10.png", threshold=0.8)
        if not pos_x10:
            log.error("No se encontró el botón x10. ¿Estás en el banner correcto?")
            return

        self.device.tap(pos_x10[0], pos_x10[1])
        time.sleep(1.5)

        screen = self.device.screenshot()
        pos_confirm = self.vision.find_template(screen, "templates/btn_confirm_summon.png", threshold=0.8)
        if pos_confirm:
            log.info("  [+] Confirmando invocación...")
            self.device.tap(pos_confirm[0], pos_confirm[1])
            self._limpiar_invocacion()
        else:
            log.error("No apareció la ventana de confirmación.")

    def do_tower_of_trials(self):
        log.info("🗼 Módulo: Tower of Trials")
        screen = self.device.screenshot()
        pos_tot = self.vision.find_template(screen, "templates/btn_tot_home.png", threshold=0.9)
        if not pos_tot:
            log.error("No se encontró el botón de Tower of Trials.")
            return

        self.device.tap(pos_tot[0], pos_tot[1])
        time.sleep(5)

        # Cofre
        screen = self.device.screenshot()
        pos_chest = self.vision.find_template(screen, "templates/btn_tot_chest.png", threshold=0.9)
        if pos_chest:
            self.device.tap(pos_chest[0], pos_chest[1] - 10)
            time.sleep(2)
            self.clear_loot_windows()

        # Fast Forward
        screen = self.device.screenshot()
        pos_ff = self.vision.find_template(screen, "templates/btn_fast_forward_menu.png", threshold=0.9)
        if pos_ff:
            self.device.tap(pos_ff[0], pos_ff[1])
            time.sleep(3)
            acels, intentos_flecha = 0, 0
            while acels < 2 and intentos_flecha < 3:
                screen = self.device.screenshot()
                pos_green = self.vision.find_template(screen, "templates/btn_ff_green.png", threshold=0.9)
                if pos_green:
                    self.device.tap(pos_green[0], pos_green[1])
                    time.sleep(2)
                    self.clear_loot_windows()
                    acels += 1
                else:
                    pos_arrow = self.vision.find_template(screen, "templates/btn_ff_arrow.png", threshold=0.9)
                    if pos_arrow:
                        self.device.tap(pos_arrow[0], pos_arrow[1])
                        time.sleep(1.5)
                        intentos_flecha += 1
                    else:
                        break
            self.device.tap(100, 100)
            time.sleep(1)

        # Explorar x3
        for _ in range(3):
            self.clear_loot_windows()
            screen = self.device.screenshot()
            pos_exp = self.vision.find_template(screen, "templates/btn_explore.png", threshold=0.9)
            if pos_exp:
                self.device.tap(pos_exp[0], pos_exp[1])
                time.sleep(3)
                self.clear_loot_windows()
            else:
                break

        # Jefe con reintento por empate
        reintentos = 0
        while reintentos < 3:
            screen = self.device.screenshot()
            pos_boss = self.vision.find_template(screen, "templates/btn_challenge_boss.png", threshold=0.9)
            if not pos_boss:
                break
            self.device.tap(pos_boss[0], pos_boss[1])

            # --- ESPERA DE 5 SEGUNDOS AÑADIDA AQUÍ ---
            log.info("  [⏳] Esperando 5 segundos a que el servidor responda...")
            time.sleep(5)
            # ----------------------------------------

            if self.handle_battle_sequence() == "draw":
                reintentos += 1
                log.warning("Empate en Torre (%d/3). Reintentando...", reintentos)
                time.sleep(2)
            else:
                break

        if reintentos == 3:
            log.warning("Límite de empates alcanzado en Torre.")

        self.return_to_home()

    def do_alliance_quest(self):
        log.info("🛡️  Módulo: Misiones de Gremio")
        screen = self.device.screenshot()
        pos_bw = self.vision.find_template(screen, "templates/btn_battalion_warfare.png", threshold=0.9)
        if not pos_bw:
            return
        self.device.tap(pos_bw[0], pos_bw[1])
        time.sleep(2)

        screen = self.device.screenshot()
        pos_aq = self.vision.find_template(screen, "templates/btn_alliance_quest.png", threshold=0.9)
        if pos_aq:
            self.device.tap(pos_aq[0], pos_aq[1])
            time.sleep(2)

        screen = self.device.screenshot()
        pos_ch = self.vision.find_template(screen, "templates/btn_challenge_boss_2.png", threshold=0.9)
        if pos_ch:
            self.device.tap(pos_ch[0], pos_ch[1])
            self.handle_battle_sequence()  # Una sola vez (F2P, no reintenta)
            for _ in range(3):
                self.device.tap(2200, 500)
                time.sleep(1)

        self.cerrar_ventana()

    def do_arena(self):
        log.info("🏟️  Módulo: Arena (5 batallas)")
        screen = self.device.screenshot()
        pos_arena = self.vision.find_template(screen, "templates/arena.png", threshold=0.9)
        if not pos_arena:
            log.error("No se encontró el ícono de Arena.")
            return

        self.device.tap(pos_arena[0], pos_arena[1])
        time.sleep(4)

        screen = self.device.screenshot()
        arenas = self.vision.find_all_templates(screen, "templates/btn_arena.png", threshold=0.9)
        if not arenas:
            log.error("No se encontraron los modos de Arena.")
            self.return_to_home()
            return

        arenas.sort(key=lambda p: p[0])
        self.device.tap(int(arenas[0][0]), int(arenas[0][1] + 190))
        time.sleep(3)

        for i in range(5):
            log.info("  🥊 Combate %d/5...", i + 1)
            reintentos = 0
            while reintentos < 3:
                screen = self.device.screenshot()
                oponentes = self.vision.find_all_templates(screen, "templates/challenge_area.png", threshold=0.9)
                if not oponentes:
                    log.warning("No se encontraron oponentes.")
                    break
                oponentes.sort(key=lambda p: p[1])
                self.device.tap(oponentes[0][0], oponentes[0][1])
                if self.handle_battle_sequence() == "draw":
                    reintentos += 1
                    log.warning("Empate en Arena (%d/3). Reintentando...", reintentos)
                    time.sleep(2)
                else:
                    break
            if reintentos == 3:
                log.warning("Límite de empates alcanzado. Avanzando.")
            time.sleep(2)

        log.info("  ✅ Arena finalizada.")
        self.return_to_home()

    def do_summons(self):
        log.info("🌟 Módulo: Invocaciones")
        screen = self.device.screenshot()
        pos_nav = self.vision.find_template(screen, "templates/btn_summon_nav.png", threshold=0.9)
        if not pos_nav:
            return
        self.device.tap(pos_nav[0], pos_nav[1])
        time.sleep(3)

        # Buscar banner con summon gratis
        encontrado, intentos = False, 0
        while not encontrado and intentos < 5:
            screen = self.device.screenshot()
            if self.vision.find_template(screen, "templates/btn_summon_x1_free.png", threshold=0.9):
                encontrado = True
            else:
                pos_arrow = self.vision.find_template(screen, "templates/btn_summon_arrow_left.png", threshold=0.9)
                if pos_arrow:
                    self.device.tap(pos_arrow[0], pos_arrow[1])
                    time.sleep(1.5)
                intentos += 1

        if encontrado:
            screen = self.device.screenshot()
            pos_chest = self.vision.find_template(screen, "templates/btn_friend_chest.png", threshold=0.9)
            if pos_chest:
                self.device.tap(pos_chest[0], pos_chest[1])
                time.sleep(1)
                self.clear_loot_windows()

            screen = self.device.screenshot()
            pos_x1 = self.vision.find_template(screen, "templates/btn_summon_x1_free.png", threshold=0.9)
            if pos_x1:
                log.info("  [+] Invocación x1...")
                self.device.tap(pos_x1[0], pos_x1[1])
                self._limpiar_invocacion()

            screen = self.device.screenshot()
            pos_x10 = self.vision.find_template(screen, "templates/btn_summon_x10_free.png", threshold=0.9)
            if pos_x10:
                log.info("  [+] Invocación x10...")
                self.device.tap(pos_x10[0], pos_x10[1])
                self._limpiar_invocacion()

        # Salida forzada al Home
        intentos_salida = 0
        while intentos_salida < 5:
            screen = self.device.screenshot()
            if self.vision.find_template(screen, "templates/btn_home_nav.png", threshold=0.9):
                break
            self.cerrar_ventana(screen)
            time.sleep(2)
            intentos_salida += 1

        self.return_to_home()

    def do_spend_mana(self):
        log.info("💧 Módulo: Sweep de Eventos")
        screen = self.device.screenshot()
        eventos = self.vision.find_all_templates(screen, "templates/label_ends_in.png", threshold=0.8)

        if not eventos:
            log.warning("No se encontraron banners de eventos activos.")
            return

        eventos.sort(key=lambda p: p[1])
        mana_agotado = False

        for idx, pos_evento in enumerate(eventos):
            if mana_agotado:
                log.info("Maná agotado. Deteniendo barrido.")
                break

            log.info("  [>] Evento #%d...", idx + 1)
            self.device.tap(pos_evento[0], pos_evento[1])
            time.sleep(4)

            etapa_encontrada = False
            for etapa in ["stage_ex_10.png", "stage_ex_9.png", "stage_ex_8.png"]:
                screen = self.device.screenshot()
                pos_s = self.vision.find_template(screen, f"templates/{etapa}", threshold=0.95)
                if pos_s:
                    log.info("  🔍 Etapa: %s", etapa.replace(".png", ""))
                    self.device.tap(pos_s[0], pos_s[1])
                    time.sleep(3)
                    etapa_encontrada = True
                    break

            if not etapa_encontrada:
                log.info("  Sin etapas EX disponibles en este evento.")
                self.return_to_home()
                time.sleep(2)
                continue

            for i in range(3):
                screen = self.device.screenshot()
                pos_sweep = self.vision.find_template(screen, "templates/btn_sweep.png", threshold=0.9)
                if pos_sweep:
                    self.device.tap(pos_sweep[0], pos_sweep[1])
                    time.sleep(1.5)
                    if self.check_and_recover_mana():
                        self.device.tap(pos_sweep[0], pos_sweep[1])
                        time.sleep(1.5)
                    log.info("  [+] Sweep #%d completado.", i + 1)
                    time.sleep(2)
                    self.clear_loot_windows()
                else:
                    log.warning("  Botón Sweep no detectado. Maná agotado.")
                    mana_agotado = True
                    break

            for _ in range(2):
                self.cerrar_ventana()

            self.return_to_home()
            time.sleep(2)

    def claim_all_rewards(self):
        log.info("🎁 Módulo: Reclamar Recompensas")

        def _abrir_menu():
            screen = self.device.screenshot()
            pos = self.vision.find_template(screen, "templates/btn_menu_arrow_down.png", threshold=0.9)
            if pos:
                self.device.tap(pos[0], pos[1])
                time.sleep(1.5)

        # Buzón
        _abrir_menu()
        screen = self.device.screenshot()
        pos_mail = self.vision.find_template(screen, "templates/btn_mailbox_icon.png", threshold=0.9)
        if pos_mail:
            self.device.tap(pos_mail[0], pos_mail[1])
            time.sleep(2)
            screen = self.device.screenshot()
            pos_claim = self.vision.find_template(screen, "templates/btn_claim_all.png", threshold=0.9)
            if pos_claim:
                self.device.tap(pos_claim[0], pos_claim[1])
                time.sleep(2)
                self.clear_loot_windows()
            self.cerrar_ventana()

        # Misiones diarias
        _abrir_menu()
        screen = self.device.screenshot()
        pos_missions = self.vision.find_template(screen, "templates/btn_missions_icon.png", threshold=0.9)
        if pos_missions:
            self.device.tap(pos_missions[0], pos_missions[1])
            time.sleep(2)
            screen = self.device.screenshot()
            pos_tab = self.vision.find_template(screen, "templates/tab_daily.png", threshold=0.9)
            if pos_tab:
                self.device.tap(pos_tab[0], pos_tab[1])
                time.sleep(1.5)

            log.debug("Barrido de misiones y cofres...")
            intentos_vacios = 0
            while intentos_vacios < 2:
                algo = False
                screen = self.device.screenshot()
                pos_claim = self.vision.find_template(screen, "templates/btn_claim_all.png", threshold=0.9)
                if pos_claim:
                    self.device.tap(pos_claim[0], pos_claim[1])
                    time.sleep(2)
                    self.clear_loot_windows()
                    algo = True
                if not algo:
                    pos_chest = self.vision.find_template(screen, "templates/chest_ready.png", threshold=0.9)
                    if pos_chest:
                        self.device.tap(pos_chest[0], pos_chest[1])
                        time.sleep(2)
                        self.clear_loot_windows()
                        algo = True
                intentos_vacios = 0 if algo else intentos_vacios + 1
                if not algo:
                    time.sleep(1.5)

            log.info("  ✅ Barrido completado.")

        self.return_to_home()
