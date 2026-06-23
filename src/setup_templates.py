from PIL import Image

# Cargar screenshot de pantalla principal
def recortar(imagen_path, output_path, x, y, w, h):
    img = Image.open(imagen_path)
    region = img.crop((x, y, x+w, y+h))
    region.save(output_path)
    print(f"✅ Template guardado: {output_path}")

# Desde pantalla principal (imagen 1)
recortar("screenshots/pantalla_principal.png", "templates/btn_bonus.png",     680, 75,  100, 60)

# Desde pantalla de misiones diarias (imagen 4)
recortar("screenshots/misiones_diarias.png",   "templates/btn_reclamar.png",  1240, 410, 160, 55)
recortar("screenshots/misiones_diarias.png",   "templates/btn_rec_todo.png",  1240, 635, 160, 55)
recortar("screenshots/misiones_diarias.png",   "templates/btn_en_curso.png",  1240, 410, 160, 55)
recortar("screenshots/misiones_diarias.png",   "templates/tab_diarias.png",   130,  95,  270, 70)