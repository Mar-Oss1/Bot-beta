"""
Script de procesamiento de capturas de pantalla.
BORRA un área rectangular (como borrar en Paint) y conserva el resto.
Las coordenadas se calculan a partir del centro y tamaño del área.
"""

import os
import sys
import io
from PIL import Image

# =====================================================================
# CONFIGURACIÓN - ¡Ajusta aquí tus valores si es necesario!
# =====================================================================

# MODO: "crop" para quedarse con el rectángulo, "delete" para borrarlo
MODO = "delete"

# Coordenadas del área a borrar (left, upper, right, lower)
# Calculadas con: centro=(500,550), tamaño=(520,655)
# left = 500 - 260 = 240
# upper = 550 - 327 = 223 (redondeado de 222.5)
# right = 240 + 520 = 760
# lower = 223 + 655 = 878
COORDENADAS = (240, 223, 760, 878)

# Color de relleno para la zona borrada (solo en modo "delete")
# (255, 255, 255) = blanco, (0, 0, 0) = negro, "transparent" = transparente
RELLENO_BORRADO = (255, 255, 255)  # blanco sólido, como borrar en Paint

# Extensiones de imagen soportadas
EXTENSIONES_VALIDAS = ('.png', '.jpg', '.jpeg')


# =====================================================================


def obtener_imagenes_ordenadas(ruta_carpeta):
    """
    Devuelve una lista con las rutas absolutas de todas las imágenes
    dentro de 'ruta_carpeta', ordenadas por nombre.
    """
    archivos = os.listdir(ruta_carpeta)
    imagenes = [
        os.path.join(ruta_carpeta, f)
        for f in archivos
        if os.path.splitext(f.lower())[1] in EXTENSIONES_VALIDAS
    ]
    # Orden natural por nombre (importante para el índice secuencial)
    imagenes.sort(key=lambda x: os.path.basename(x).lower())
    return imagenes


def extraer_indice(nombre_archivo, prefijo):
    """
    Extrae el número entero del nombre de un archivo con formato:
        prefijo_<número>.png
    Ejemplo: 'Cuenta1_3.png' -> 3
    """
    base = os.path.splitext(nombre_archivo)[0]
    try:
        # El número es la parte final tras el último '_'
        numero = int(base.split('_')[-1])
        return numero
    except (ValueError, IndexError):
        # Si no se puede extraer, devolvemos un valor alto para que quede al final
        return float('inf')


def ajustar_caja(caja, ancho, alto):
    """
    Ajusta la caja para que no se salga de los bordes de la imagen.
    Si la caja se sale parcialmente, la recorta al borde.
    Si la caja está completamente fuera, devuelve None.
    """
    left, upper, right, lower = caja

    # Ajustar a los bordes de la imagen
    left = max(0, min(left, ancho))
    upper = max(0, min(upper, alto))
    right = max(left, min(right, ancho))
    lower = max(upper, min(lower, alto))

    # Verificar que la caja tenga área positiva
    if right <= left or lower <= upper:
        return None

    return (left, upper, right, lower)


def procesar_cuenta(ruta_cuenta, nombre_cuenta):
    """
    Procesa todas las imágenes de una cuenta:
        - Crea la carpeta 'procesadas'.
        - Borra el área especificada de cada imagen.
        - Guarda los archivos modificados con el nuevo nombre.
        - Al final, genera el PDF consolidado.

    Retorna True si todo fue correcto, False si hubo errores graves.
    """
    print(f"\n>>> Procesando cuenta: {nombre_cuenta}")

    # Ruta de la subcarpeta de salida
    carpeta_procesadas = os.path.join(ruta_cuenta, "procesadas")
    os.makedirs(carpeta_procesadas, exist_ok=True)

    # Lista de imágenes originales ordenadas
    imagenes = obtener_imagenes_ordenadas(ruta_cuenta)
    total_imagenes = len(imagenes)
    if total_imagenes == 0:
        print("    No se encontraron imágenes. Se omite esta cuenta.")
        return True

    # Lista donde guardaremos las rutas de las imágenes procesadas
    imagenes_procesadas = []

    for idx, ruta_img in enumerate(imagenes, start=1):
        try:
            # Abrir imagen
            with Image.open(ruta_img) as img:
                ancho, alto = img.size

                # Ajustar la caja a los límites de la imagen
                caja_efectiva = ajustar_caja(COORDENADAS, ancho, alto)

                if caja_efectiva is None:
                    print(f"    [AVISO] Imagen '{os.path.basename(ruta_img)}' "
                          f"- área a borrar completamente fuera de la imagen. Se omite.")
                    continue

                if MODO == "delete":
                    # BORRAR el área especificada (pintarla del color de relleno)
                    resultado = img.copy()

                    if isinstance(RELLENO_BORRADO, tuple):
                        # Relleno con color sólido
                        ancho_caja = caja_efectiva[2] - caja_efectiva[0]
                        alto_caja = caja_efectiva[3] - caja_efectiva[1]

                        # Crear un rectángulo del color de relleno
                        parche = Image.new('RGB', (ancho_caja, alto_caja), RELLENO_BORRADO)
                        resultado.paste(parche, (caja_efectiva[0], caja_efectiva[1]))

                    elif RELLENO_BORRADO == "transparent":
                        # Relleno transparente (requiere modo RGBA)
                        if resultado.mode != 'RGBA':
                            resultado = resultado.convert('RGBA')

                        ancho_caja = caja_efectiva[2] - caja_efectiva[0]
                        alto_caja = caja_efectiva[3] - caja_efectiva[1]

                        transparente = Image.new('RGBA', (ancho_caja, alto_caja), (0, 0, 0, 0))
                        resultado.paste(transparente, (caja_efectiva[0], caja_efectiva[1]), transparente)

                elif MODO == "crop":
                    # RECORTAR (quedarse solo con el interior del área)
                    resultado = img.crop(caja_efectiva)

                else:
                    print(f"    [ERROR] Modo desconocido: {MODO}. Use 'delete' o 'crop'.")
                    return False

                # Convertir a RGB si tiene canal alfa (necesario para guardar como PNG/PDF)
                if resultado.mode in ('RGBA', 'LA', 'P'):
                    resultado = resultado.convert('RGB')

                # Nombre del archivo de salida
                nombre_salida = f"{nombre_cuenta}_{idx}.png"
                ruta_salida = os.path.join(carpeta_procesadas, nombre_salida)

                # Guardar imagen procesada
                resultado.save(ruta_salida, format='PNG')
                imagenes_procesadas.append(ruta_salida)

                print(f"    [{idx}/{total_imagenes}] Guardado: {nombre_salida}")

        except Exception as e:
            print(f"    [ERROR] No se pudo procesar '{os.path.basename(ruta_img)}': {e}")
            continue  # continuar con la siguiente imagen

    # ------------------------------------------------------------------
    # Generar PDF consolidado con todas las imágenes procesadas
    # ------------------------------------------------------------------
    if not imagenes_procesadas:
        print("    No se generaron imágenes procesadas. Se omite la creación del PDF.")
        return True

    # Ordenar por índice numérico extraído del nombre del archivo
    imagenes_procesadas.sort(key=lambda p: extraer_indice(os.path.basename(p), nombre_cuenta))

    # Preparar imágenes para el PDF
    imagenes_pdf = []
    for ruta_imagen in imagenes_procesadas:
        try:
            with Image.open(ruta_imagen) as img:
                # Asegurar RGB sin canal alfa
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Forzar la imagen a ser tratada como PNG pura
                # Esto evita el error KeyError: 'JPEG' en sistemas sin soporte JPEG
                with io.BytesIO() as buffer:
                    img.save(buffer, format='PNG')
                    buffer.seek(0)
                    img_png = Image.open(buffer)
                    # Cargar la imagen para desvincularla del buffer
                    img_png.load()
                    imagenes_pdf.append(img_png)

        except Exception as e:
            print(f"    [ERROR] Al preparar imagen para PDF '{ruta_imagen}': {e}")

    if not imagenes_pdf:
        print("    No se pudo cargar ninguna imagen para el PDF.")
        return False

    # Guardar PDF
    nombre_pdf = f"{nombre_cuenta}_Enciclopedia.pdf"
    ruta_pdf = os.path.join(carpeta_procesadas, nombre_pdf)

    try:
        # La primera imagen se guarda con save_all=True y append_images con el resto
        imagenes_pdf[0].save(
            ruta_pdf,
            save_all=True,
            append_images=imagenes_pdf[1:],
            optimize=False,
            resolution=100.0
        )
        print(f"    PDF creado exitosamente: {ruta_pdf}")
    except Exception as e:
        print(f"    [ERROR] Falló la creación del PDF: {e}")
        return False
    finally:
        # Cerrar todas las imágenes abiertas para el PDF
        for img in imagenes_pdf:
            img.close()

    return True


def main():
    """
    Punto de entrada principal.
    Determina la ruta absoluta de la carpeta raíz 'capturas_cuentas'
    (situada en el mismo directorio que el script) y procesa todas las cuentas.
    """
    # Obtener la ruta absoluta del directorio donde se ejecuta el script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    carpeta_raiz = os.path.join(script_dir, "capturas_cuentas")

    if not os.path.isdir(carpeta_raiz):
        print(f"ERROR: No se encontró la carpeta raíz en: {carpeta_raiz}")
        print("Crea una carpeta llamada 'capturas_cuentas' en el mismo directorio que este script.")
        print("Dentro de ella, crea una subcarpeta por cada cuenta con sus imágenes.")
        sys.exit(1)

    print("=" * 60)
    print("PROCESADOR DE CAPTURAS DE PANTALLA")
    print("=" * 60)
    print(f"Modo: {MODO}")
    print(f"Coordenadas: {COORDENADAS}")
    print(f"Relleno: {RELLENO_BORRADO}")
    print(f"Carpeta raíz: {carpeta_raiz}")
    print("=" * 60)

    # Iterar sobre las subcarpetas (cada una es una cuenta)
    cuentas_procesadas = 0
    for entrada in os.listdir(carpeta_raiz):
        ruta_entrada = os.path.join(carpeta_raiz, entrada)
        if os.path.isdir(ruta_entrada):
            nombre_cuenta = entrada
            exito = procesar_cuenta(ruta_entrada, nombre_cuenta)
            if exito:
                cuentas_procesadas += 1

    print("\n" + "=" * 60)
    print(f"✅ Procesamiento finalizado. Cuentas procesadas: {cuentas_procesadas}")
    print("=" * 60)

    # Pausa para que puedas ver el resultado si lo ejecutas con doble clic
    input("\nPresiona Enter para salir...")


if __name__ == "__main__":
    main()