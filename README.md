# Bot-beta

[Español](#español) | [English](#english)

---

## Español

### 📌 Descripción

**Bot-beta** es un bot en **Python** para automatizar tareas repetitivas en un juego RPG, usando **OpenCV** (detección visual por plantillas), captura de pantalla y flujo de acciones por tareas.

El proyecto está estructurado para separar captura, detección, lógica central y tareas, facilitando el mantenimiento y la extensión.

---

### 🧱 Estructura del proyecto

```text
Bot-beta/
├─ src/
│  ├─ main.py
│  ├─ capture.py
│  ├─ setup_templates.py
│  ├─ test_connection.py
│  ├─ test_ocr.py
│  ├─ core/
│  ├─ tasks/
│  ├─ accounts/
│  ├─ logs/
│  ├─ Filesmodified/
│  ├─ screenshots/
│  └─ pantalla_test.png
├─ templates/
├─ screenshots/
└─ .gitignore
```

---

### ⚙️ Instalación

#### 1) Clonar el repositorio

```bash
git clone https://github.com/Mar-Oss1/Bot-beta.git
cd Bot-beta
```

#### 2) Crear entorno virtual (recomendado)

**Windows (PowerShell):**
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 3) Instalar dependencias

Si existe `requirements.txt`:
```bash
pip install -r requirements.txt
```

Instalación base recomendada:
```bash
pip install opencv-python numpy pillow pytesseract
```

> Si usas OCR, instala también **Tesseract OCR** en tu sistema.

---

### ▶️ Uso básico

Ejecutar el bot:

```bash
python src/main.py
```

Scripts de prueba:

```bash
python src/test_connection.py
python src/test_ocr.py
```

---

### 🔧 Configuración avanzada

> Basada en la arquitectura real del repositorio (`main.py`, `capture.py`, `setup_templates.py`, `core/`, `tasks/` y `templates/`).

#### 1) Resolución y entorno de ejecución
Para evitar falsos negativos en matching:
- Usa resolución fija y misma escala DPI.
- Mantén modo ventana/pantalla del juego constante.
- Evita overlays/filtros de color externos.

#### 2) Gestión de plantillas (`templates/`)
- Nombra plantillas con convención consistente (`btn_*`, `tab_*`, `stage_*`, etc.).
- Recorta elementos UI de forma precisa (sin bordes innecesarios).
- Versiona plantillas cuando cambie la UI del juego.

#### 3) Umbral de detección (confidence)
Ajusta umbral según ruido visual:
- Umbral más alto → menos falsos positivos, más estricta detección.
- Umbral más bajo → más tolerante, mayor riesgo de error.
- Recomendado: definir por tipo de elemento (botón grande vs texto pequeño).

#### 4) Timeouts y reintentos
En tareas automatizadas:
- Define timeout por acción crítica.
- Aplica reintentos con backoff corto.
- Si una pantalla no coincide, vuelve a estado base (home) y reintenta.

#### 5) Logs y depuración (`src/logs/`)
- Loguea: acción, template buscada, score de matching, resultado.
- Guarda capturas en fallos críticos para análisis posterior.
- Usa niveles de log (`INFO`, `WARN`, `ERROR`, `DEBUG`).

#### 6) OCR (cuando aplique)
- Preprocesar imagen antes de OCR (grises/threshold).
- Limitar OCR a ROI (región específica) para mayor precisión.
- Validar texto OCR con regex/listas permitidas.

---

### ✅ Buenas prácticas

- Centraliza configuración (thresholds, delays, rutas) en un único módulo.
- Separa “detección” de “acción” para facilitar pruebas.
- Añade validaciones previas antes de hacer clic (doble confirmación visual).
- Implementa “modo seguro” con tecla de parada de emergencia.

---

### ⚠️ Aviso

Este proyecto está orientado a automatización visual con fines educativos/experimentales. Verifica siempre los términos de uso de la plataforma donde se ejecute.

---

## English

### 📌 Description

**Bot-beta** is a **Python** bot that automates repetitive RPG game tasks using **OpenCV** (template-based visual detection), screen capture, and task-driven action flows.

The codebase is organized to separate capture, detection, core logic, and tasks for easier maintenance and scalability.

---

### 🧱 Project structure

```text
Bot-beta/
├─ src/
│  ├─ main.py
│  ├─ capture.py
│  ├─ setup_templates.py
│  ├─ test_connection.py
│  ├─ test_ocr.py
│  ├─ core/
│  ├─ tasks/
│  ├─ accounts/
│  ├─ logs/
│  ├─ Filesmodified/
│  ├─ screenshots/
│  └─ pantalla_test.png
├─ templates/
├─ screenshots/
└─ .gitignore
```

---

### ⚙️ Installation

#### 1) Clone repository

```bash
git clone https://github.com/Mar-Oss1/Bot-beta.git
cd Bot-beta
```

#### 2) Create virtual environment (recommended)

**Windows (PowerShell):**
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 3) Install dependencies

If `requirements.txt` exists:
```bash
pip install -r requirements.txt
```

Base setup:
```bash
pip install opencv-python numpy pillow pytesseract
```

> If OCR is enabled, install **Tesseract OCR** on your OS.

---

### ▶️ Basic usage

Run bot:

```bash
python src/main.py
```

Helper tests:

```bash
python src/test_connection.py
python src/test_ocr.py
```

---

### 🔧 Advanced configuration

#### 1) Resolution and runtime environment
- Use fixed resolution and DPI scale.
- Keep game window mode consistent.
- Avoid overlays or visual filters.

#### 2) Template management (`templates/`)
- Follow naming conventions (`btn_*`, `tab_*`, `stage_*`).
- Crop UI assets tightly for robust matching.
- Re-capture templates when game UI changes.

#### 3) Detection confidence thresholds
- Higher threshold: stricter detection, fewer false positives.
- Lower threshold: more tolerant, higher false positive risk.
- Prefer per-template/per-category thresholds.

#### 4) Timeouts and retries
- Add timeout per critical action.
- Use short retry backoff.
- On mismatch, return to a known safe screen and retry.

#### 5) Logging and debugging (`src/logs/`)
- Log action name, template target, match score, and outcome.
- Save screenshots on critical failures.
- Use standard log levels (`INFO/WARN/ERROR/DEBUG`).

#### 6) OCR tuning (if applicable)
- Preprocess image before OCR.
- Restrict OCR to specific ROI.
- Validate OCR output with regex/whitelists.

---

### ✅ Best practices

- Centralize config values (delays, thresholds, paths).
- Keep detection and action layers decoupled.
- Add visual confirmation before clicks.
- Include emergency stop workflow.

---

### ⚠️ Disclaimer

This repository is intended for educational/experimental visual automation. Ensure compliance with the game/platform terms of service.

---

## 👤 Author

**Mar-Oss1**  
Repository: [https://github.com/Mar-Oss1/Bot-beta](https://github.com/Mar-Oss1/Bot-beta)
