import uiautomator2 as u2
import cv2
import pytesseract
from PIL import Image

# Ruta de Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

print("Conectando al dispositivo...")
d = u2.connect()

print("Dispositivo:", d.device_info['model'])
print("Resolución:", d.window_size())

print("Tomando screenshot...")
screen = d.screenshot()
screen.save("../screenshots/test.png")

print("Leyendo pantalla con OpenCV...")
img = cv2.imread("../screenshots/test.png")
print("Tamaño imagen:", img.shape)

print("\n✅ Todo OK — el bot puede ver y controlar el teléfono")