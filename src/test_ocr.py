import cv2
import pytesseract
import os

# Asegúrate de que esta ruta sea correcta
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def probar_ocr_gemas():
    # 1. Toma una captura manualmente y guárdala como 'pantalla_test.png'
    # O usa la que ya tienes en tu carpeta
    screen_path = "pantalla_test.png"

    if not os.path.exists(screen_path):
        print(f"❌ No encontré el archivo {screen_path}. Tómale una captura al juego.")
        return

    img = cv2.imread(screen_path)

    # 2.coordenadas de prueba
    X, Y, W, H = 1315, 50, 320, 60

    # 3. Recortar
    roi = img[Y:Y + H, X:X + W]

    # 4. Procesar para que Tesseract lo entienda
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)

    # 5. Guardar imágenes de prueba (¡Aquí está el truco que te dieron!)
    cv2.imwrite("debug_roi_gray.png", gray)
    cv2.imwrite("debug_roi_thresh.png", thresh)

    # 6. Leer
    texto = pytesseract.image_to_string(thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789')
    numeros = ''.join(filter(str.isdigit, texto))

    print(f"  [DEBUG] Texto detectado: '{texto}'")
    print(f"  [DEBUG] Números limpios: '{numeros}'")

    cv2.imshow("ROI Procesado (Presiona cualquier tecla para cerrar)", thresh)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    probar_ocr_gemas()