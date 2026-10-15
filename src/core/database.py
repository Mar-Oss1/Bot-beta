import json
import os
from datetime import datetime, date, timedelta
from core.config import ACCOUNTS_FILE, PROGRESS_FILE

SUBMODULOS_DIARIOS = ["tower", "alliance", "arena", "defense", "summons", "mana", "rewards"]


class Account:
    def __init__(self, config: dict, progress_data: dict = None):
        self.id = config.get("id")
        self.name = config.get("name")
        self.serial = config.get("serial")
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 1)
        self.notes = config.get("notes", "")
        self.servers = config.get("servers", [])

        p = progress_data or {}
        self.progress = p.get("days", {})
        self.last_run = p.get("last_run")
        self._limpiar_historial_antiguo(dias_max=14)

    def _limpiar_historial_antiguo(self, dias_max: int = 14):
        """Evita que progress.json crezca infinitamente borrando fechas de hace más de 14 días."""
        limite = str(date.today() - timedelta(days=dias_max))
        fechas_viejas = [d for d in self.progress.keys() if d < limite]
        for d in fechas_viejas:
            del self.progress[d]

    def to_config(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "serial": self.serial,
            "enabled": self.enabled,
            "priority": self.priority,
            "notes": self.notes,
            "servers": self.servers,
        }

    def to_progress(self) -> dict:
        return {
            "last_run": self.last_run,
            "days": self.progress,
        }

    def get_today_progress(self, server_id=None) -> dict:
        today = str(date.today())
        day_data = self.progress.get(today, {})
        default_tasks = {"daily_missions": False, "login_bonus": False}

        if server_id and server_id != "DEFAULT":
            return day_data.get(server_id, default_tasks)
        return day_data if day_data else default_tasks

    def mark_task_done(self, task_name: str, server_id=None):
        today = str(date.today())
        if today not in self.progress:
            self.progress[today] = {}

        if server_id and server_id != "DEFAULT":
            if server_id not in self.progress[today]:
                self.progress[today][server_id] = {}
            self.progress[today][server_id][task_name] = True
        else:
            self.progress[today][task_name] = True

        self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M")

    def is_task_done(self, task_name: str, server_id=None) -> bool:
        return self.get_today_progress(server_id).get(task_name, False)

    def pending_tasks(self, server_id=None) -> list[str]:
        if server_id:
            tp = self.get_today_progress(server_id)
            if tp.get("daily_missions", False):
                return []
            return [m for m in SUBMODULOS_DIARIOS if not tp.get(m, False)]

        if self.servers:
            pending = []
            for s in self.servers:
                sid = s["server_id"]
                tp = self.get_today_progress(sid)
                if not tp.get("daily_missions", False):
                    faltan = [m for m in SUBMODULOS_DIARIOS if not tp.get(m, False)]
                    if faltan:
                        pending.append(f"{sid}: {len(faltan)} mód.")
            return pending

        tp = self.get_today_progress()
        if tp.get("daily_missions", False):
            return []
        return [m for m in SUBMODULOS_DIARIOS if not tp.get(m, False)]

    def completion_percent(self) -> int:
        """Calcula el % real basado en los 7 submódulos diarios por cada servidor."""
        servidores = [s["server_id"] for s in self.servers] if self.servers else [None]
        total = len(SUBMODULOS_DIARIOS) * len(servidores)
        done = 0
        for sid in servidores:
            tp = self.get_today_progress(sid)
            if tp.get("daily_missions", False):
                done += len(SUBMODULOS_DIARIOS)
            else:
                done += sum(1 for m in SUBMODULOS_DIARIOS if tp.get(m, False))
        return int((done / total) * 100) if total > 0 else 0

    def mark_login_failed(self):
        today = str(date.today())
        if today not in self.progress:
            self.progress[today] = {}
        self.progress[today]["login_failed"] = True
        self.progress[today]["login_fail_count"] = self.progress[today].get("login_fail_count", 0) + 1
        self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M")

    def has_failed_too_many_times(self, limit: int = 2) -> bool:
        today = str(date.today())
        return self.progress.get(today, {}).get("login_fail_count", 0) >= limit

    def get_server_config(self, server_id):
        for s in self.servers:
            if s.get("server_id") == server_id:
                return s
        return None

    def is_vip_server(self, server_id) -> bool:
        cfg = self.get_server_config(server_id)
        return cfg.get("vip", False) if cfg else False


class Database:
    def __init__(self):
        self.accounts: list[Account] = []
        self._cambios_pendientes = False
        self._ensure_files()
        self.load()

    def _ensure_files(self):
        os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
        if not os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                json.dump({"accounts": []}, f, indent=2)
        if not os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump({"progress": {}}, f, indent=2)

    def load(self):
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            progress_data = json.load(f).get("progress", {})

        self.accounts = [
            Account(config=a, progress_data=progress_data.get(str(a["id"]), {}))
            for a in config_data.get("accounts", [])
        ]
        print(f"📂 {len(self.accounts)} cuentas cargadas")

    def save_config(self):
        data = {"accounts": [a.to_config() for a in self.accounts]}
        self._write_safe(ACCOUNTS_FILE, data)

    def save_progress(self):
        data = {"progress": {str(a.id): a.to_progress() for a in self.accounts}}
        self._write_safe(PROGRESS_FILE, data)

    def save(self):
        self._cambios_pendientes = True

    def commit(self):
        if not self._cambios_pendientes:
            return
        self.save_config()
        self.save_progress()
        self._cambios_pendientes = False
        print("💾 Disco actualizado (Commit exitoso).")

    def _write_safe(self, path: str, data: dict):
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)

    def add_account(self, name, serial=None, priority=1, notes="", servers=None):
        new_id = max([a.id for a in self.accounts], default=0) + 1
        account = Account(config={
            "id": new_id, "name": name, "serial": serial, "enabled": True,
            "priority": priority, "notes": notes, "servers": servers or []
        }, progress_data={})
        self.accounts.append(account)
        self.save()
        self.commit()
        print(f"✅ Cuenta agregada: {name}")
        return account

    def get_account(self, account_id) -> Account | None:
        for a in self.accounts:
            if a.id == account_id:
                return a
        return None

    def get_pending_accounts(self) -> list[Account]:
        pending = [
            a for a in self.accounts
            if a.enabled and not a.has_failed_too_many_times(limit=2) and len(a.pending_tasks()) > 0
        ]
        return sorted(pending, key=lambda a: a.priority)

    def print_status(self):
        print("\n" + "=" * 75)
        print(f"{'PRI':<4} {'CUENTA':<22} {'%':>4}  {'PROGRESO':<10}  {'PENDIENTE / ESTADO'}")
        print("=" * 75)
        for a in sorted(self.accounts, key=lambda x: x.priority):
            if not a.enabled:
                print(f"{a.priority:<4} {a.name:<22} {'--':>4}  {'░░░░░░░░░░'}  ⏸️ Deshabilitada")
                continue
            pct = a.completion_percent()
            pending_str = ", ".join(a.pending_tasks())
            if len(pending_str) > 34:
                pending_str = pending_str[:31] + "..."
            elif not pending_str:
                pending_str = "Todo completo ✅"
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            print(f"{a.priority:<4} {a.name:<22} {pct:>3}%  {bar}  {pending_str}")
        print("=" * 75)