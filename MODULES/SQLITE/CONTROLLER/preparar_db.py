from MODULES.SQLITE.CONTROLLER.sqlite import crear_base_de_datos_final
from MODULES.rutas import convert_rutas

import time, os

rutas_dict = convert_rutas()

# 3. Asignamos las rutas completas a variables para usarlas en el script
RUTA_COMPLETA_EXCEL = os.path.join(rutas_dict["ruta_panel"],"Panel.xlsm")
RUTA_COMPLETA_DB = os.path.join(rutas_dict["ruta_script_python"],"mapa.db")

# --- Definición de Fuentes en Excel (sin cambios) ---
NOMBRE_HOJA_PANEL_OBRA = "Panel Control"
TABLA_PANEL_OBRA = "TablaPanelControl"
NOMBRE_HOJA_COORDENADAS = "Coordenadas"
TABLA_COORDENADAS ="TablaCoordenadas"
NOMBRE_HOJA_VIALIDAD = "Vialidad"
TABLA_VIALIDAD ="TablaVialidad"


if __name__ == '__main__':
    print("=====================================================")
    print("--- INICIANDO LA CREACIÓN/ACTUALIZACIÓN DE LA BD ---")
    print("--- Este proceso puede tardar... Por favor, espera. ---")

    start_time = time.time()

    # Llamamos a la función para que lea el Excel y cree mapa.db
    crear_base_de_datos_final()

    end_time = time.time()
    print(f"--- ¡ÉXITO! La base de datos 'mapa.db' ha sido creada/actualizada en {end_time - start_time:.2f} segundos. ---")
    print("--- Ahora puedes ejecutar 'app.py' de forma segura. ---")
    print("=====================================================")