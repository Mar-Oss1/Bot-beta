import json
import os
from datetime import datetime, date

ACCOUNTS_FILE = "accounts/accounts.json"
PROGRESS_FILE = "accounts/progress.json"


# ══════════════════════════════════════════════════════════════════════════════
# MODELO DE CUENTA
# ══════════════════════════════════════════════════════════════════════════════

class Account:
    def __init__(self, config: dict, progress_data: dict = None):
        # ── Configuración fija (viene de accounts.json) ────────────────────
        self.id       = config.get("id")
        self.name     = config.get("name")
        self.serial   = config.get("serial")
        self.enabled  = config.get("enabled", True)
        self.priority = config.get("priority", 1)
        self.notes    = config.get("notes", "")
        self.servers  = config.get("servers", [])

        # ── Estado mutable (viene de progress.json) ────────────────────────
        p = progress_data or {}
        self.progress = p.get("days", {})
        self.last_run = p.get("last_run")

    # ── Serialización separada ─────────────────────────────────────────────

    def to_config(self) -> dict:
        """Solo la configuración fija → accounts.json"""
        return {
            "id":       self.id,
            "name":     self.name,
            "serial":   self.serial,
            "enabled":  self.enabled,
            "priority": self.priority,
            "notes":    self.notes,
            "servers":  self.servers,
        }

    def to_progress(self) -> dict:
        """Solo el estado mutable → progress.json"""
        return {
            "last_run": self.last_run,
            "days":     self.progress,
        }

    # ── Lógica de progreso ─────────────────────────────────────────────────

    def get_today_progress(self, server_id=None):
        today = str(date.today())
        day_data = self.progress.get(today, {})

        default_tasks = {
            "daily_missions": False,
            "events":         False,
            "story":          False,
            "login_bonus":    False,
        }

        if server_id:
            return day_data.get(server_id, default_tasks)

        return day_data if day_data else default_tasks

    def mark_task_done(self, task_name, server_id=None):
        """Marca una tarea como completada hoy"""
        today = str(date.today())
        if today not in self.progress:
            self.progress[today] = {}

        if server_id:
            if server_id not in self.progress[today]:
                self.progress[today][server_id] = {}
            self.progress[today][server_id][task_name] = True
        else:
            self.progress[today][task_name] = True

        self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M")

    def is_task_done(self, task_name, server_id=None):
        return self.get_today_progress(server_id).get(task_name, False)

    def pending_tasks(self, server_id=None):
        all_tasks = ["login_bonus", "daily_missions", "events", "story"]

        if server_id:
            tp = self.get_today_progress(server_id)
            return [t for t in all_tasks if not tp.get(t, False)]

        if self.servers:
            pending = []
            for s in self.servers:
                sid = s["server_id"]
                tp = self.get_today_progress(sid)
                pending.extend(
                    [f"{t} ({sid})" for t in all_tasks if not tp.get(t, False)]
                )
            return pending

        tp = self.get_today_progress()
        return [t for t in all_tasks if not tp.get(t, False)]

    def completion_percent(self):
        all_tasks = ["login_bonus", "daily_missions", "events", "story"]

        if self.servers:
            total = len(all_tasks) * len(self.servers)
            done = sum(
                sum(1 for t in all_tasks if self.get_today_progress(s["server_id"]).get(t, False))
                for s in self.servers
            )
            return int((done / total) * 100) if total > 0 else 0

        tp = self.get_today_progress()
        done = sum(1 for t in all_tasks if tp.get(t, False))
        return int((done / len(all_tasks)) * 100)

    def mark_login_failed(self):
        today = str(date.today())
        if today not in self.progress:
            self.progress[today] = {}
        fail_count = self.progress[today].get("login_fail_count", 0) + 1
        self.progress[today]["login_failed"] = True
        self.progress[today]["login_fail_count"] = fail_count
        self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M")

    def has_failed_too_many_times(self, limit=2):
        today = str(date.today())
        return self.progress.get(today, {}).get("login_fail_count", 0) >= limit


# ══════════════════════════════════════════════════════════════════════════════
# BASE DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

class Database:
    def __init__(self):
        self.accounts: list[Account] = []
        self._ensure_files()
        self.load()

    # ── Inicialización ─────────────────────────────────────────────────────

    def _ensure_files(self):
        """Crea ambos archivos si no existen"""
        os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)

        if not os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "w") as f:
                json.dump({"accounts": []}, f, indent=2)

        if not os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, "w") as f:
                json.dump({"progress": {}}, f, indent=2)

    # ── Carga ──────────────────────────────────────────────────────────────

    def load(self):
        """Carga configuración y progreso por separado y los une en Account"""
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            progress_data = json.load(f).get("progress", {})

        self.accounts = [
            Account(
                config=a,
                progress_data=progress_data.get(str(a["id"]), {})
            )
            for a in config_data.get("accounts", [])
        ]
        print(f"📂 {len(self.accounts)} cuentas cargadas")

    # ── Guardado separado ──────────────────────────────────────────────────

    def save_config(self):
        """
        Guarda SOLO la configuración fija en accounts.json.
        Llamar cuando cambies enabled, priority, serial, servers, etc.
        """
        data = {"accounts": [a.to_config() for a in self.accounts]}
        self._write_safe(ACCOUNTS_FILE, data)

    def save_progress(self):
        """
        Guarda SOLO el progreso diario en progress.json.
        Llamar después de cada tarea completada.
        """
        data = {
            "progress": {
                str(a.id): a.to_progress()
                for a in self.accounts
            }
        }
        self._write_safe(PROGRESS_FILE, data)

    def save(self):
        """
        Guarda ambos archivos.
        Mantiene compatibilidad con el código existente que llama db.save().
        """
        self.save_config()
        self.save_progress()

    def _write_safe(self, path: str, data: dict):
        """
        Escritura atómica: escribe en .tmp y luego renombra.
        Si el proceso muere a mitad, el archivo original queda intacto.
        """
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)  # atómico en Windows y Linux

    # ── CRUD de cuentas ────────────────────────────────────────────────────

    def add_account(self, name, serial=None, priority=1, notes="", servers=None):
        """Agrega una cuenta nueva"""
        new_id = max([a.id for a in self.accounts], default=0) + 1
        config = {
            "id":       new_id,
            "name":     name,
            "serial":   serial,
            "enabled":  True,
            "priority": priority,
            "notes":    notes,
            "servers":  servers or [],
        }
        account = Account(config=config, progress_data={})
        self.accounts.append(account)
        self.save()
        print(f"✅ Cuenta agregada: {name}")
        return account

    def get_account(self, account_id) -> Account | None:
        for a in self.accounts:
            if a.id == account_id:
                return a
        return None

    def get_pending_accounts(self) -> list[Account]:
        """Cuentas con tareas pendientes hoy, ordenadas por prioridad"""
        pending = [
            a for a in self.accounts
            if a.enabled
            and not a.has_failed_too_many_times(limit=2)
            and len(a.pending_tasks()) > 0
        ]
        return sorted(pending, key=lambda a: a.priority)

    # ── Utilidades ─────────────────────────────────────────────────────────

    def print_status(self):
        print("\n" + "=" * 70)
        print(f"{'CUENTA':<25} {'%':>4}  {'PENDIENTE'}")
        print("=" * 70)
        for a in self.accounts:
            pct = a.completion_percent()
            pending_str = ", ".join(a.pending_tasks())
            if len(pending_str) > 35:
                pending_str = pending_str[:32] + "..."
            elif not pending_str:
                pending_str = "Todo completo ✅"
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            print(f"{a.name:<25} {pct:>3}%  {bar}  {pending_str}")
        print("=" * 70 + "\n")