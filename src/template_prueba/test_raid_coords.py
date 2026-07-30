# test_raid_coords.py
import os
import sys
import cv2
import numpy as np
from PIL import Image
import pytesseract
import re
import json
import glob

# Ajustar ruta para importar desde core.config
# Si estás ejecutando desde src/template_prueba, sube dos niveles
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import TESSERACT_CMD, PROJECT_ROOT

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Configuración de monstruos
MONSTER_TYPES = {
    "brown": {
        "template": "templates/raid_monster_brown.png",
        "priority": 1,
        "resource": "Green Potions (Character)",
        "name": "Café"
    },
    "purple": {
        "template": "templates/raid_monster_purple.png",
        "priority": 2,
        "resource": "Minerals + Fruit",
        "name": "Morado"
    },
    "yellow": {
        "template": "templates/raid_monster_yellow.png",
        "priority": 3,
        "resource": "Blue Potions (Weapon)",
        "name": "Amarillo"
    },
    "turquoise": {
        "template": "templates/raid_monster_turquoise.png",
        "priority": 4,
        "resource": "Minerals",
        "name": "Turquesa"
    },
    "blue": {
        "template": "templates/raid_monster_blue.png",
        "priority": 5,
        "resource": "Minerals",
        "name": "Azul"
    },
}

MONSTER_POSITIONS = [
    {"y": 260, "icon_x": 1075, "power_x": 1250, "enter_x": 1775, "icon_y_offset": 0},
    {"y": 420, "icon_x": 1075, "power_x": 1250, "enter_x": 1775, "icon_y_offset": 0},
    {"y": 560, "icon_x": 1075, "power_x": 1250, "enter_x": 1775, "icon_y_offset": 0},
    {"y": 700, "icon_x": 1075, "power_x": 1250, "enter_x": 1775, "icon_y_offset": 0},
    {"y": 850, "icon_x": 1075, "power_x": 1250, "enter_x": 1775, "icon_y_offset": 0},
]

ICON_HALF_W = 70
ICON_HALF_H = 60

POWER_HALF_W_LEFT = 80
POWER_HALF_W_RIGHT = 150
POWER_HALF_H = 20


def leer_poder_desde_roi(roi_cv):
    """Aplica OCR a un ROI ya recortado (cv2), probando binarización normal e invertida."""
    def _ocr_con_threshold(thresh_img):
        texto = pytesseract.image_to_string(
            thresh_img,
            config="--psm 7 -c tessedit_char_whitelist=0123456789.,KMkm"
        )
        return texto.strip()

    def _parsear(texto_limpio):
        if not texto_limpio:
            return 0
        if 'M' in texto_limpio or 'm' in texto_limpio:
            numeros = re.findall(r'[\d.]+', texto_limpio)
            if numeros:
                return int(float(numeros[0]) * 1_000_000)
            return 0
        elif 'K' in texto_limpio or 'k' in texto_limpio:
            numeros = re.findall(r'[\d.]+', texto_limpio)
            if numeros:
                return int(float(numeros[0]) * 1_000)
            return 0
        else:
            numeros = re.sub(r'[^\d]', '', texto_limpio)
            if numeros and len(numeros) <= 9:
                return int(numeros)
            return 0

    try:
        escala = 3  # antes 2 — más resolución ayuda a números pequeños
        roi_escalada = cv2.resize(roi_cv, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(roi_escalada, cv2.COLOR_BGR2GRAY)

        # Intento 1: binarización normal
        _, thresh_normal = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        texto = _ocr_con_threshold(thresh_normal)
        texto_limpio = re.sub(r'[^\d.,KMkm]', '', texto)
        poder = _parsear(texto_limpio)

        # Intento 2: si no dio nada útil, probar invertido (texto claro sobre fondo oscuro)
        if poder == 0:
            _, thresh_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            texto2 = _ocr_con_threshold(thresh_inv)
            texto_limpio2 = re.sub(r'[^\d.,KMkm]', '', texto2)
            poder2 = _parsear(texto_limpio2)
            if poder2 > 0:
                return poder2, texto2

        return poder, texto
    except Exception as e:
        return 0, f"Error: {e}"


def detectar_tipo_monstruo(roi_pil):
    """Detecta el tipo de monstruo en una ROI PIL."""
    mejor_tipo = None
    mejor_conf = 0
    roi_cv = cv2.cvtColor(np.array(roi_pil), cv2.COLOR_RGB2BGR)
    roi_gray = cv2.cvtColor(roi_cv, cv2.COLOR_BGR2GRAY)

    for tipo, config in MONSTER_TYPES.items():
        template_path = os.path.join(PROJECT_ROOT, config["template"])
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            continue
        if template.shape[0] > roi_gray.shape[0] or template.shape[1] > roi_gray.shape[1]:
            continue
        try:
            res = cv2.matchTemplate(roi_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > 0.65 and max_val > mejor_conf:
                mejor_conf = max_val
                mejor_tipo = tipo
        except cv2.error:
            continue
    return mejor_tipo, mejor_conf


def probar_coordenadas(image_path):
    """Carga la imagen, dibuja las coordenadas y prueba OCR/tipos."""
    if not os.path.exists(image_path):
        print(f"❌ No se encontró la imagen: {image_path}")
        return

    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        print(f"❌ No se pudo leer la imagen: {image_path}")
        return
    h, w = img_bgr.shape[:2]
    print(f"📷 Imagen cargada: {w}x{h}")

    img_draw = img_bgr.copy()
    resultados = {}

    for idx, pos in enumerate(MONSTER_POSITIONS):
        y = pos["y"]
        power_x = pos["power_x"]
        enter_x = pos["enter_x"]
        icon_x = pos["icon_x"]

        print(f"\n--- Monstruo {idx + 1} (y={y}) ---")

        cv2.circle(img_draw, (power_x, y), 10, (0, 255, 0), -1)
        cv2.circle(img_draw, (enter_x, y), 10, (255, 0, 0), -1)
        cv2.circle(img_draw, (icon_x, y), 10, (0, 0, 255), -1)

        # Poder
        # Poder — offset asimétrico + su propio offset vertical calibrable
        power_y = y + pos.get("power_y_offset", 0)
        x1 = max(0, power_x - POWER_HALF_W_LEFT)
        x2 = min(w, power_x + POWER_HALF_W_RIGHT)
        y1 = max(0, power_y - POWER_HALF_H)
        y2 = min(h, power_y + POWER_HALF_H)
        roi_power = img_bgr[y1:y2, x1:x2]

        # Debug visual: rectángulo real usado para leer el poder
        cv2.rectangle(img_draw, (x1, y1), (x2, y2), (0, 255, 0), 2)
        poder, texto_ocr = leer_poder_desde_roi(roi_power)
        print(f"  📊 Poder OCR: '{texto_ocr}' → {poder}")

        # Tipo
        icon_y = y + pos.get("icon_y_offset", 0)
        icon_roi_x1 = max(0, icon_x - ICON_HALF_W)
        icon_roi_x2 = min(w, icon_x + ICON_HALF_W)
        icon_roi_y1 = max(0, icon_y - ICON_HALF_H)
        icon_roi_y2 = min(h, icon_y + ICON_HALF_H)
        roi_icon_cv = img_bgr[icon_roi_y1:icon_roi_y2, icon_roi_x1:icon_roi_x2]

        # Debug visual: dibuja el rectángulo real que se está usando para detectar el icono
        cv2.rectangle(img_draw, (icon_roi_x1, icon_roi_y1), (icon_roi_x2, icon_roi_y2), (0, 200, 255), 2)
        roi_icon_pil = Image.fromarray(cv2.cvtColor(roi_icon_cv, cv2.COLOR_BGR2RGB))
        tipo, conf = detectar_tipo_monstruo(roi_icon_pil)
        if tipo:
            print(f"  🎯 Tipo: {MONSTER_TYPES[tipo]['name']} (confianza: {conf:.2f})")
        else:
            print(f"  ❌ Tipo no detectado")

        resultados[idx] = {
            "y": y,
            "power_x": power_x,
            "enter_x": enter_x,
            "power_ocr": texto_ocr,
            "power_val": poder,
            "tipo": tipo,
            "confianza": conf,
        }

    output_path = "raid_coords_test_output.png"
    cv2.imwrite(output_path, img_draw)
    print(f"\n✅ Imagen con anotaciones guardada como: {output_path}")

    json_path = "raid_coords_test_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"📄 Resultados guardados en: {json_path}")

    try:
        cv2.imshow("Test Coordenadas Raids", img_draw)
        print("Presiona cualquier tecla para cerrar la ventana...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except:
        pass


def listar_imagenes():
    """Busca imágenes en varias ubicaciones: script, raíz, screenshots."""
    extensiones = ["*.png", "*.jpg", "*.jpeg"]
    imagenes = []

    # 1. Carpeta del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for ext in extensiones:
        imagenes.extend(glob.glob(os.path.join(script_dir, ext)))
        imagenes.extend(glob.glob(os.path.join(script_dir, "screenshots", ext)))

    # 2. Raíz del proyecto (dos niveles arriba)
    project_root = os.path.dirname(os.path.dirname(script_dir))
    for ext in extensiones:
        imagenes.extend(glob.glob(os.path.join(project_root, ext)))
        imagenes.extend(glob.glob(os.path.join(project_root, "screenshots", ext)))

    # 3. Carpeta actual (si es diferente)
    for ext in extensiones:
        imagenes.extend(glob.glob(ext))

    # Eliminar duplicados y ordenar
    return sorted(set(imagenes))


if __name__ == "__main__":
    print("🔍 PRUEBA DE COORDENADAS RAIDS\n")

    # Buscar imágenes disponibles
    imagenes = listar_imagenes()

    if imagenes:
        print("📸 Imágenes encontradas:")
        for i, img in enumerate(imagenes, 1):
            # Mostrar solo el nombre base para más claridad
            nombre = os.path.basename(img)
            print(f"  {i}. {nombre}")
        print("  0. Especificar otra ruta manualmente")

        try:
            opcion = input("\nSelecciona el número de la imagen (0 para manual): ").strip()
            if opcion == "0":
                img_path = input("📁 Ruta completa de la imagen: ").strip()
            else:
                idx = int(opcion) - 1
                if 0 <= idx < len(imagenes):
                    img_path = imagenes[idx]
                else:
                    print("❌ Opción inválida. Usando la primera imagen.")
                    img_path = imagenes[0]
        except ValueError:
            print("❌ Entrada inválida. Usando la primera imagen.")
            img_path = imagenes[0]
    else:
        print("⚠️ No se encontraron imágenes automáticamente.")
        img_path = input("📁 Escribe la ruta de la captura (ej. screenshot.png o C:/ruta/imagen.png): ").strip()
        if not img_path:
            img_path = "screenshot.png"

    probar_coordenadas(img_path)
