# core/config.py
import os
from dotenv import load_dotenv

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
# Si estructura es evertale-bot/src/core/config.py -> sube a evertale-bot/
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(_CORE_DIR))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# --- Directorios y Archivos Centralizados ---
LOGS_DIR: str = os.path.join(PROJECT_ROOT, "logs")
ACCOUNTS_DIR: str = os.path.join(PROJECT_ROOT, "accounts")
ACCOUNTS_FILE: str = os.path.join(ACCOUNTS_DIR, "accounts.json")
PROGRESS_FILE: str = os.path.join(ACCOUNTS_DIR, "progress.json")
ECONOMIA_FILE: str = os.path.join(LOGS_DIR, "economia_log.jsonl")

# --- Tesseract OCR ---
TESSERACT_CMD: str = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# --- ADB ---
DEVICE_SERIAL: str = os.getenv("DEVICE_SERIAL", "221013206")
APP_PACKAGE: str = os.getenv("APP_PACKAGE", "com.zigzagame.evertale")

# --- Horarios de eventos ---
ALLIANCE_WAR_WINDOW = (10, 0, 20, 45)   # 10:00 AM a 8:45 PM
WAR_OF_REALMS_WINDOW = (10, 0, 21, 45)  # 10:00 AM a 9:45 PM

RAID_WINDOWS = [
    (11, 46, 12, 45),  # 11:46 AM a 12:45 PM
    (18, 46, 19, 45),  # 6:46 PM a 7:45 PM
]