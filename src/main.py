import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import Database
from core.device import Device
from core.vision import Vision
from tasks.startup import Startup
from tasks.daily_missions import DailyMissions
from tasks.change_account import ChangeAccount
from tasks.change_server import ChangeServer

def main():
    print("=== INICIANDO EVERTALE BOT ===")

    # 1. Cargamos la base de datos
    db = Database()
    db.print_status()

    cuentas_pendientes = db.get_pending_accounts()
    if not cuentas_pendientes:
        print("\n ✅ Todas las cuentas han terminado sus tareas hoy. ¡A descansar!")
        return

    # 2. Inicializar visión y dispositivo
    vis = Vision(threshold=0.8)  # 80% de confianza para los templates
    dev = Device()

    print("\n[🔌] Conectando al dispositivo...")
    serial = dev.get_serial()
    if not serial:
        print(" ❌ No se encontró ningún dispositivo ADB conectado. Revisa la depuración USB.")
        return

    dev.serial = serial
    if not dev.connect():
        print(" ❌ No se pudo establecer conexión con uiautomator2. Saliendo.")
        return

    print("\n[🧹] Limpiando estado inicial (Forzando cierre de Evertale si estaba abierto)...")
    dev.d.app_stop("com.zigzagame.evertale")

    # 3. Bucle principal de farmeo
    for cuenta in cuentas_pendientes:
        print(f"\n" + "=" * 45)
        print(f" 🚀 PROCESANDO CUENTA: {cuenta.name} (Prioridad {cuenta.priority})")
        print("=" * 45)

        max_reintentos = 3
        exito_cambio = False

        # --- PASO A y B: Bucle de Reintentos para Abrir y Cambiar Cuenta ---
        for intento in range(max_reintentos):
            print(f" [🔌] Arrancando Evertale (Intento {intento + 1}/{max_reintentos})...")
            dev.open_app()
            time.sleep(14)  # Tiempo para que el juego cargue y muestre el logo/nube

            if cuenta.serial:
                cambiador = ChangeAccount(dev, vis)
                exito_cambio = cambiador.execute(cuenta.serial)

                if exito_cambio:
                    print(" [✅] Inyección exitosa. Esperando que el juego vuelva a la pantalla de título...")
                    time.sleep(12)  # Le damos tiempo tras el reinicio automático del juego
                    break  # Salió bien, rompemos el bucle de reintentos
                else:
                    print(f" [⚠️] Falló el cambio para {cuenta.name}. Limpiando memoria y reiniciando...")
                    dev.d.app_stop("com.zigzagame.evertale")
                    time.sleep(3)
            else:
                print(" [i] La cuenta no tiene serial configurado. Entrando directo...")
                exito_cambio = True
                break

        if not exito_cambio:
            print(f" [❌] Imposible acceder a {cuenta.name} tras {max_reintentos} intentos. Saltando a la siguiente...")
            continue

        # --- NUEVO BUCLE DE SERVIDORES DINÁMICO ---
        servidores = getattr(cuenta, "servers", [])
        if not servidores:
            servidores = [{"server_id": "DEFAULT"}]

        for index, servidor in enumerate(servidores):
            server_id = servidor.get("server_id", "DEFAULT")

            # Si ya hicimos un servidor en esta misma cuenta, el juego estará cerrado. Hay que reabrirlo.
            if index > 0:
                print(f"\n [🔌] Reabriendo juego para procesar el siguiente servidor ({server_id})...")
                dev.open_app()
                time.sleep(14)

            # Verificamos si necesitamos navegar a otro servidor en la UI
            if server_id != "DEFAULT":
                print(f"\n[🔄] Verificando servidor: {server_id}")
                cambiador_serv = ChangeServer(dev, vis)
                template_path = f"templates/label_{server_id.lower()}.png"
                if not cambiador_serv.execute(template_path):
                    print(f" ⚠️ Falló la validación/cambio a {server_id}. Saltando servidor...")
                    dev.d.app_stop("com.zigzagame.evertale")
                    continue

            # --- PASO C: SECUENCIA DE ARRANQUE (Rompehielos) ---
            print("\n [⚔️] Iniciando Rompehielos (Cerrando banners y pop-ups)...")
            arranque = Startup(dev, vis)
            if not arranque.execute():
                print(f" ⚠️ Saltando el servidor {server_id} por problemas de atasco en el inicio.")
                dev.d.app_stop("com.zigzagame.evertale")  # Forzamos el cierre
                continue  # Pasamos al siguiente servidor

            # --- PASO D: MISIONES DIARIAS ---
            print("\n [📜] Ejecutando Misiones Diarias...")
            rutina_misiones = DailyMissions(dev, vis)
            exito = rutina_misiones.execute()

            if exito:
                print(f" [✅] Misiones de {cuenta.name} completadas en el servidor {server_id}.")
            else:
                print(f" ⚠️ Las misiones de {cuenta.name} en {server_id} no se completaron correctamente.")

            # --- PASO E: LIMPIEZA DEL SERVIDOR ACTUAL ---
            print(f"\n [✓] Ciclo terminado para el servidor {server_id}. Cerrando juego...")
            dev.d.app_stop("com.zigzagame.evertale")
            time.sleep(4)  # Pausa breve

        # Una vez que termina TODOS los servidores de la cuenta, guardamos progreso
        cuenta.mark_task_done("daily_missions")
        cuenta.mark_task_done("login_bonus")
        db.save()
        print(f" 💾 Progreso global guardado exitosamente para la cuenta {cuenta.name}.")

if __name__ == "__main__":
    main()