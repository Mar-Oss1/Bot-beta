"""
core/config.py
Configuración central del bot. Lee el archivo .env de la raíz del proyecto
y expone las constantes necesarias para todos los módulos.
USO: from core.config import TESSERACT_CMD, DEVICE_SERIAL, APP_PACKAGE
"""
import os
from dotenv import load_dotenv

# Sube desde core/ → src/ → raíz del proyecto para encontrar el .env
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_CORE_DIR))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# --- Tesseract OCR ---
TESSERACT_CMD: str = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # fallback por si no hay .env
)

# --- ADB ---
DEVICE_SERIAL: str = os.getenv("DEVICE_SERIAL", "22101320G")
APP_PACKAGE: str = os.getenv("APP_PACKAGE", "com.zigzagame.evertale")

# --- Rutas del proyecto ---
PROJECT_ROOT: str = _PROJECT_ROOT
