import json
import os
from datetime import datetime, date

# 1. Obtener la ruta exacta de este archivo (database.py)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Subir niveles hasta llegar a la carpeta raíz "evertale-bot"
# (De 'core' sube a 'src', y de 'src' sube a 'evertale-bot')
project_root = os.path.dirname(os.path.dirname(current_dir))

# 3. Construir la ruta a prueba de fallos hacia accounts/accounts.json
ACCOUNTS_FILE = os.path.join(project_root, "accounts", "accounts.json")

class Account:
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.name = data.get("name")
        self.serial = data.get("serial")        # serial ADB del teléfono
        self.enabled = data.get("enabled", True)
        self.priority = data.get("priority", 1) # 1=alta, 2=media, 3=baja
        self.progress = data.get("progress", {})
        self.last_run = data.get("last_run")
        self.notes = data.get("notes", "")
        # --- NUEVO: Campo para servidores ---
        self.servers = data.get("servers", [])  # lista de dicts: [{"server_id": "SA-e"}, {"server_id": "SA-6"}]

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
            "servers": self.servers   # <--- Se guarda en el JSON
        }

    def get_today_progress(self):
        """Retorna el progreso de hoy"""
        today = str(date.today())
        return self.progress.get(today, {
            "daily_missions": False,
            "events": False,
            "story": False,
            "login_bonus": False
        })

    def mark_task_done(self, task_name):
        """Marca una tarea como completada hoy"""
        today = str(date.today())
        if today not in self.progress:
            self.progress[today] = {}
        self.progress[today][task_name] = True
        self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M")

    def is_task_done(self, task_name):
        """Verifica si una tarea ya se completó hoy"""
        return self.get_today_progress().get(task_name, False)

    def pending_tasks(self):
        """Lista de tareas pendientes hoy"""
        today_progress = self.get_today_progress()
        all_tasks = ["login_bonus", "daily_missions", "events", "story"]
        return [t for t in all_tasks if not today_progress.get(t, False)]

    def completion_percent(self):
        """Porcentaje de tareas completadas hoy"""
        today_progress = self.get_today_progress()
        all_tasks = ["login_bonus", "daily_missions", "events", "story"]
        done = sum(1 for t in all_tasks if today_progress.get(t, False))
        return int((done / len(all_tasks)) * 100)


class Database:
    def __init__(self):
        self.accounts: list[Account] = []
        self._ensure_file()
        self.load()

    def _ensure_file(self):
        """Crea el archivo si no existe"""
        if not os.path.exists(ACCOUNTS_FILE):
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
        ordenadas por prioridad
        """
        pending = [a for a in self.accounts
                   if a.enabled and len(a.pending_tasks()) > 0]
        return sorted(pending, key=lambda a: a.priority)

    def print_status(self):
        """Muestra el estado de todas las cuentas"""
        print("\n" + "="*50)
        print(f"{'CUENTA':<20} {'%':>4}  {'PENDIENTE'}")
        print("="*50)
        for a in self.accounts:
            pct = a.completion_percent()
            pending = ", ".join(a.pending_tasks()) or "Todo completo ✅"
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            print(f"{a.name:<20} {pct:>3}%  {bar}  {pending}")
        print("="*50 + "\n")