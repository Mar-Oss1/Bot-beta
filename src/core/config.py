# core/config.py
import os
from dotenv import load_dotenv

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_CORE_DIR))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# --- Tesseract OCR ---
TESSERACT_CMD: str = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# --- ADB ---
DEVICE_SERIAL: str = os.getenv("DEVICE_SERIAL", "221013206")
APP_PACKAGE: str = os.getenv("APP_PACKAGE", "com.zigzagame.evertale")

# --- Rutas ---
PROJECT_ROOT: str = _PROJECT_ROOT

# --- Horarios de eventos ---
# Defensas
ALLIANCE_WAR_WINDOW = (10, 0, 20, 45)   # 10:00 AM a 8:45 PM
WAR_OF_REALMS_WINDOW = (10, 0, 21, 45)  # 10:00 AM a 9:45 PM

# Raids (asedios)
RAID_WINDOWS = [
    (11, 46, 12, 45),  # 11:45 AM a 12:45 PM
    (18, 46, 19, 45),  # 6:45 PM a 7:45 PM
]