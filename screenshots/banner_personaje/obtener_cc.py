import cv2

# Verificamos si la imagen carga correctamente
img = cv2.imread("Screenshot_20260630-201258_Evertale.png")
if img is None:
    print(
        "❌ Error: No se pudo abrir 'edited-image.jpg'. Asegúrate de que el archivo esté en la misma carpeta que este script.")
else:
    alto, ancho, canales = img.shape
    print(f"✅ Imagen cargada correctamente.")
    print(f"📏 Resolución total: {ancho}x{alto} px")
    print(
        "Por favor, usa Paint para ver las coordenadas (X, Y) del ratón en la esquina inferior izquierda y pásamelas.")

# Pon aquí el nombre de una de tus capturas reales
ruta_imagen = "Screenshot_20260630-201258_Evertale.png"

img = cv2.imread(ruta_imagen)

if img is None:
    print(f"❌ No se encontró la imagen: {ruta_imagen}")
else:
    print("🖱️ Instrucciones:")
    print("1. Dibuja un rectángulo con el mouse sobre el banner del personaje.")
    print("2. Puedes ajustar el recuadro arrastrando las esquinas.")
    print("3. Presiona ENTER o ESPACIO para confirmar la selección.")
    print("4. Presiona 'c' para cancelar y cerrar.")

    # Abre la herramienta interactiva
    roi = cv2.selectROI("Selecciona el banner del PJ", img, showCrosshair=True)
    cv2.destroyAllWindows()

    x, y, w, h = roi

    if w > 0 and h > 0:
        # Pillow necesita: (izquierda, arriba, derecha, abajo)
        izquierda = x
        arriba = y
        derecha = x + w
        abajo = y + h

        print("\n" + "=" * 50)
        print("🎯 ¡Aquí tienes tus coordenadas!")
        print(f"COORDENADAS = ({izquierda}, {arriba}, {derecha}, {abajo})")
        print("=" * 50 + "\n")
    else:
        print("⚠️ No se seleccionó ningún área.")
