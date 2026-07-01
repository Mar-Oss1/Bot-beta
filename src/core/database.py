import json
import os
from datetime import datetime, date

# 1. Obtener la ruta exacta de este archivo (database.py)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Subir niveles hasta llegar a la carpeta raíz "evertale-bot"
project_root = os.path.dirname(os.path.dirname(current_dir))

# 3. Construir la ruta a prueba de fallos hacia accounts/accounts.json
ACCOUNTS_FILE = os.path.join(project_root, "accounts", "accounts.json")


class Account:
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.name = data.get("name")
        self.serial = data.get("serial")
        self.enabled = data.get("enabled", True)
        self.priority = data.get("priority", 1)
        self.progress = data.get("progress", {})
        self.last_run = data.get("last_run")
        self.notes = data.get("notes", "")
        self.servers = data.get("servers", [])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "serial": self.serial,
            "enabled": self.enabled,
            "priority": self.priority,
            "progress": self.progress,
            "last_run": self.last_run,
            "notes": self.notes,
            "servers": self.servers
        }

    def get_today_progress(self, server_id=None):
        """Retorna el progreso de hoy (soporta opcionalmente server_id)"""
        today = str(date.today())
        day_data = self.progress.get(today, {})

        default_tasks = {
            "daily_missions": False,
            "events": False,
            "story": False,
            "login_bonus": False
        }

        if server_id:
            return day_data.get(server_id, default_tasks)

        return day_data if day_data else default_tasks

    def mark_task_done(self, task_name, server_id=None):
        """Marca una tarea como completada hoy, separando por servidor si es necesario"""
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
        """Verifica si una tarea ya se completó hoy en un servidor específico"""
        return self.get_today_progress(server_id).get(task_name, False)

    def pending_tasks(self, server_id=None):
        """Lista de tareas pendientes hoy. Si tiene servidores, desglosa por servidor."""
        all_tasks = ["login_bonus", "daily_missions", "events", "story"]

        if server_id:
            tp = self.get_today_progress(server_id)
            return [t for t in all_tasks if not tp.get(t, False)]

        if self.servers:
            pending = []
            for s in self.servers:
                sid = s["server_id"]
                tp = self.get_today_progress(sid)
                srv_pending = [f"{t} ({sid})" for t in all_tasks if not tp.get(t, False)]
                pending.extend(srv_pending)
            return pending
        else:
            tp = self.get_today_progress()
            return [t for t in all_tasks if not tp.get(t, False)]

    def completion_percent(self):
        """Porcentaje de tareas completadas hoy, adaptado para multi-server"""
        all_tasks = ["login_bonus", "daily_missions", "events", "story"]

        if self.servers:
            total_tasks = len(all_tasks) * len(self.servers)
            done = 0
            for s in self.servers:
                tp = self.get_today_progress(s["server_id"])
                done += sum(1 for t in all_tasks if tp.get(t, False))
            return int((done / total_tasks) * 100) if total_tasks > 0 else 0
        else:
            tp = self.get_today_progress()
            done = sum(1 for t in all_tasks if tp.get(t, False))
            return int((done / len(all_tasks)) * 100)


    def mark_login_failed(self):
        """Registra un fallo de login en el progreso de hoy."""
        today = str(date.today())
        if today not in self.progress:
            self.progress[today] = {}

        # Incrementamos el contador de fallos
        fail_count = self.progress[today].get("login_fail_count", 0) + 1
        self.progress[today]["login_failed"] = True
        self.progress[today]["login_fail_count"] = fail_count
        self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M")

    def has_failed_too_many_times(self, limit=2):
        """Verifica si la cuenta ya falló más veces de las permitidas hoy."""
        today = str(date.today())
        fail_count = self.progress.get(today, {}).get("login_fail_count", 0)
        return fail_count >= limit



class Database:
    def __init__(self):
        self.accounts: list[Account] = []
        self._ensure_file()
        self.load()

    def _ensure_file(self):
        """Crea el archivo si no existe"""
        if not os.path.exists(ACCOUNTS_FILE):
            os.makedirs(os.path.dirname(ACCOUNTS_FILE), exist_ok=True)
            with open(ACCOUNTS_FILE, "w") as f:
                json.dump({"accounts": []}, f, indent=2)

    def load(self):
        """Carga las cuentas desde el JSON"""
        with open(ACCOUNTS_FILE, "r") as f:
            data = json.load(f)
        self.accounts = [Account(a) for a in data.get("accounts", [])]
        print(f"📂 {len(self.accounts)} cuentas cargadas")

    def save(self):
        """Guarda el estado actual al JSON"""
        data = {"accounts": [a.to_dict() for a in self.accounts]}
        with open(ACCOUNTS_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_account(self, name, serial=None, priority=1, notes="", servers=None):
        """Agrega una cuenta nueva (opcionalmente con lista de servidores)"""
        new_id = max([a.id for a in self.accounts], default=0) + 1
        account_data = {
            "id": new_id,
            "name": name,
            "serial": serial,
            "priority": priority,
            "notes": notes
        }
        if servers:
            account_data["servers"] = servers
        account = Account(account_data)
        self.accounts.append(account)
        self.save()
        print(f"✅ Cuenta agregada: {name}")
        return account

    def get_account(self, account_id):
        """Busca una cuenta por ID"""
        for a in self.accounts:
            if a.id == account_id:
                return a
        return None

    def get_pending_accounts(self):
        """
        Retorna cuentas con tareas pendientes hoy,
        que no hayan superado el límite de fallos de login.
        """
        pending = []
        for a in self.accounts:
            if not a.enabled:
                continue

            # Si ya falló demasiadas veces hoy, la ignoramos
            if a.has_failed_too_many_times(limit=2):
                continue

            # Si tiene tareas pendientes, la agregamos
            if len(a.pending_tasks()) > 0:
                pending.append(a)

        return sorted(pending, key=lambda a: a.priority)

    def print_status(self):
        """Muestra el estado de todas las cuentas"""
        print("\n" + "=" * 70)
        print(f"{'CUENTA':<25} {'%':>4}  {'PENDIENTE'}")
        print("=" * 70)
        for a in self.accounts:
            pct = a.completion_percent()
            # Limitar la longitud del texto de pendientes para que no rompa la consola si son muchas
            pending_str = ", ".join(a.pending_tasks())
            if len(pending_str) > 35:
                pending_str = pending_str[:32] + "..."
            elif not pending_str:
                pending_str = "Todo completo ✅"

            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            print(f"{a.name:<25} {pct:>3}%  {bar}  {pending_str}")
        print("=" * 70 + "\n")