# Bot-beta

Bot-beta es un bot en Python para automatizar flujos repetitivos dentro de **Evertale** mediante:
- control de dispositivo Android por **ADB** (`uiautomator2`),
- detección visual por plantillas con **OpenCV**,
- y OCR con **Tesseract** en tareas que leen texto.

## Estado actual del proyecto

Actualmente el bot ofrece un menú interactivo (`src/main.py`) con ejecuciones manuales y automáticas para:
- flujo completo de misiones diarias por cuenta/servidor,
- cambio de cuenta y cambio de servidor,
- farmeo de evento,
- defensa,
- raids automáticos,
- sweep de eventos automáticos.

La persistencia de cuentas/progreso se maneja en archivos JSON locales creados en tiempo de ejecución dentro de `accounts/` (raíz del proyecto).

## Requisitos

- Python 3.10+ (recomendado)
- Un dispositivo Android accesible por ADB
- Tesseract OCR instalado en el sistema (necesario para funciones OCR)

Dependencias Python usadas por el código:
- `uiautomator2`
- `opencv-python`
- `numpy`
- `pytesseract`
- `Pillow`
- `python-dotenv`

## Instalación

```bash
git clone https://github.com/Mar-Oss1/Bot-beta.git
cd Bot-beta
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install uiautomator2 opencv-python numpy pytesseract Pillow python-dotenv
```

## Configuración

El proyecto carga variables desde `.env` en la raíz.

Variables soportadas actualmente (`src/core/config.py`):

- `TESSERACT_CMD` (ruta al ejecutable de Tesseract)
- `DEVICE_SERIAL` (serial ADB del dispositivo)
- `APP_PACKAGE` (package name de la app)

Ejemplo de `.env`:

```env
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
DEVICE_SERIAL=221013206
APP_PACKAGE=com.zigzagame.evertale
```

> Ajusta los valores a tu entorno real. No subas `.env` al repositorio.

## Ejecución

Desde la raíz del repositorio:

```bash
python src/main.py
```

Scripts auxiliares disponibles:

```bash
python src/capture.py
python src/test_connection.py
python src/test_ocr.py
python src/template_prueba/test_raid_coords.py
```

## Estructura relevante

```text
Bot-beta/
├─ src/
│  ├─ main.py
│  ├─ capture.py
│  ├─ core/
│  │  ├─ config.py
│  │  ├─ database.py
│  │  ├─ device.py
│  │  ├─ flow_helpers.py
│  │  ├─ logger.py
│  │  └─ vision.py
│  ├─ tasks/
│  ├─ template_prueba/
│  ├─ test_connection.py
│  └─ test_ocr.py
├─ templates/
├─ screenshots/
└─ accounts/            # se crea en ejecución (ignorado por git)
```

## Privacidad y seguridad

- Los datos de cuentas y progreso son sensibles: se almacenan localmente en `accounts/*.json`.
- Si en algún momento esos datos se versionaron en commits previos, **borrarlos del árbol actual no elimina automáticamente el historial**.
- Si hubo exposición de códigos, seriales u otra información sensible, debes **rotar/revocar credenciales** y evaluar limpieza de historial con herramientas como `git filter-repo` o BFG.

## Limitaciones conocidas

- El bot depende de resolución/interfaz visual del juego y de la calidad de las plantillas en `templates/`.
- Cambios de UI del juego pueden romper detecciones.
- Varias acciones asumen que el dispositivo está conectado y estable por ADB.

## Solución de problemas básica

1. **No conecta al dispositivo**
   - Verifica `adb devices` y que `DEVICE_SERIAL` coincida.
2. **No encuentra templates**
   - Revisa rutas en `templates/` y que la pantalla del juego coincida con las capturas.
3. **OCR falla o lee mal**
   - Confirma `TESSERACT_CMD` y que Tesseract esté instalado correctamente.
4. **No hay cuentas para procesar**
   - Revisa que exista `accounts/accounts.json` con cuentas válidas o deja que el bot cree la estructura inicial.
