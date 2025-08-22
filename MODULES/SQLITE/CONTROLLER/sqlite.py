import pandas as pd, xlwings as xw
import sqlite3, os, sys, time

from decimal import Decimal

from MODULES.SQLITE.CONTROLLER.database_setup import configurar_base_de_datos # Importas la función



# ==============================================================================
# --- MANEJO DE RUTAS DEL PROYECTO ---
# ==============================================================================
# 1. Añadimos la carpeta raíz del proyecto al path de Python para que encuentre los módulos
directorio_script_actual = os.path.dirname(os.path.abspath(__file__))
directorio_proyecto_raiz = os.path.dirname(os.path.dirname(os.path.dirname(directorio_script_actual)))
if directorio_proyecto_raiz not in sys.path:
    sys.path.append(directorio_proyecto_raiz)

# 2. Importamos nuestro módulo de rutas y obtenemos el diccionario
from MODULES.rutas import convert_rutas
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
NOMBRE_HOJA_TAREA = "Tarea"
TABLA_TAREA = "TablaTarea"
NOMBRE_HOJA_CHECKLISTITEMS = "ChecklistItems"
TABLA_CHECKLISTITEMS = "TablaChecklistItems"
NOMBRE_HOJA_COMENTARIOS = "Comentarios"
TABLA_COMENTARIOS = "TablaComentarios"
NOMBRE_HOJA_USUARIO = "Usuario"
TABLA_USUARIO = "TablaUsuario"
NOMBRE_HOJA_EVENTOCALENDARIO = "EventosCalendario"
TABLA_EVENTOCALENDARIO = "TablaEventosCalendario"
NOMBRE_HOJA_EVENTOBRIGADA = "EventoBrigada"
TABLA_EVENTOBRIGADA = "TablaEventoBrigada"
NOMBRE_HOJA_BRIGADA = "Brigada"
TABLA_BRIGADA = "TablaBrigada"
NOMBRE_HOJA_EVENTOHISTORIAL = "EventoHistorial"
TABLA_EVENTOHISTORIAL = "TablaEventoHistorial"

# ==============================================================================
# --- FUNCIÓN AUXILIAR DE CONEXIÓN INTELIGENTE (CORREGIDA) ---
# ==============================================================================
def conectar_a_excel(ruta_completa_archivo: str) -> tuple:
    """
    Función inteligente para conectarse a un archivo Excel usando su ruta completa.
    Detecta si el archivo ya está abierto o si necesita abrir una nueva instancia.
    """
    # Verificamos si el archivo existe en el disco antes de intentar cualquier cosa
    if not os.path.exists(ruta_completa_archivo):
        print(f"❌ ERROR FATAL: El archivo no existe en la ruta: '{ruta_completa_archivo}'")
        return None, None, False

    nombre_archivo_base = os.path.basename(ruta_completa_archivo)
    print(f"Buscando si el libro '{nombre_archivo_base}' ya está abierto...")
    
    for app in xw.apps:
        for book in app.books:
            if book.name.lower() == nombre_archivo_base.lower():
                print(f"✅ Encontrado '{nombre_archivo_base}' abierto en una instancia de Excel existente (PID: {app.pid}).")
                return book, app, False

    print(f"'{nombre_archivo_base}' no está abierto. Iniciando una nueva instancia de Excel en segundo plano...")
    try:
        app = xw.App(visible=False)
        # Usamos la ruta completa para abrir el libro
        book = app.books.open(ruta_completa_archivo)
        print(f"✅ Nueva instancia de Excel (PID: {app.pid}) creada y libro abierto.")
        return book, app, True
    except Exception as e:
        print(f"❌ ERROR: No se pudo iniciar Excel o abrir el archivo. Error de xlwings: {e}")
        if 'app' in locals() and app:
            app.quit()
        return None, None, False

# ==============================================================================
# --- FUNCIÓN PRINCIPAL DE CREACIÓN DE LA BASE DE DATOS ---
# ==============================================================================
def crear_base_de_datos_final():

    #configurar_base_de_datos()

    print(f"--- Creando base de datos desde '{os.path.basename(RUTA_COMPLETA_EXCEL)}' ---")
    
    book, app, app_fue_creada_por_script = None, None, False
    try:
        # 1. CONECTAR DE FORMA INTELIGENTE (usando la ruta completa)
        book, app, app_fue_creada_por_script = conectar_a_excel(RUTA_COMPLETA_EXCEL)
        
        if not book: return

        # 2. LEER DATOS (lógica sin cambios)
        print("\n--- Leyendo tablas fuente de Excel... ---")
        df_panel_control = book.sheets[NOMBRE_HOJA_PANEL_OBRA].tables[TABLA_PANEL_OBRA].range.options(pd.DataFrame, index=False, header=True).value
        df_coordenadas = book.sheets[NOMBRE_HOJA_COORDENADAS].tables[TABLA_COORDENADAS].range.options(pd.DataFrame, index=False, header=True).value
        df_vialidad = book.sheets[NOMBRE_HOJA_VIALIDAD].tables[TABLA_VIALIDAD].range.options(pd.DataFrame, index=False, header=True).value
        df_tareas = book.sheets[NOMBRE_HOJA_TAREA].tables[TABLA_TAREA].range.options(pd.DataFrame, index=False, header=True).value
        df_checklistitems = book.sheets[NOMBRE_HOJA_CHECKLISTITEMS].tables[TABLA_CHECKLISTITEMS].range.options(pd.DataFrame, index=False, header=True).value
        df_comentarios = book.sheets[NOMBRE_HOJA_COMENTARIOS].tables[TABLA_COMENTARIOS].range.options(pd.DataFrame, index=False, header=True).value
        df_usuario = book.sheets[NOMBRE_HOJA_USUARIO].tables[TABLA_USUARIO].range.options(pd.DataFrame, index=False, header=True).value
        df_eventocalendario = book.sheets[NOMBRE_HOJA_EVENTOCALENDARIO].tables[TABLA_EVENTOCALENDARIO].range.options(pd.DataFrame, index=False, header=True).value
        df_eventobrigada = book.sheets[NOMBRE_HOJA_EVENTOBRIGADA].tables[TABLA_EVENTOBRIGADA].range.options(pd.DataFrame, index=False, header=True).value
        df_brigada = book.sheets[NOMBRE_HOJA_BRIGADA].tables[TABLA_BRIGADA].range.options(pd.DataFrame, index=False, header=True).value
        df_eventohistorial = book.sheets[NOMBRE_HOJA_EVENTOHISTORIAL].tables[TABLA_EVENTOHISTORIAL].range.options(pd.DataFrame, index=False, header=True).value



        print("✅ Tablas fuente leídas correctamente.")

        # 3. NORMALIZAR DATOS (lógica sin cambios)
        print("\n--- Normalizando la tabla 'Panel Control'... ---")
        columnas_proyectos = ['Unidad', 'Línea de Negocio', 'Comuna', 'Sector Urbano o Rural','WF SCM','WF', 'Sap', 'Valoriza', 'Programa de inversión', 'N° ID', 'ID', 'ID Posicion', 'Descripción', 'Tipo inversion', 'Coordinador', 'Contratista', 'Empresa', 'Estado', 'OBSERVACION']
        columnas_clientes = ['Correo', 'Fono cliente', 'Nombre Cliente', 'Sap']

        # ... (definir las otras listas de columnas aquí)
        
        df_proyectos = df_panel_control[[col for col in columnas_proyectos if col in df_panel_control.columns]]
        df_clientes = df_panel_control[[col for col in columnas_clientes if col in df_panel_control.columns]]
        # ... (crear los otros DataFrames aquí)

        dataframes_a_guardar = {
            "Proyectos": df_proyectos, 
            "Clientes": df_clientes, 
            "Coordenadas": df_coordenadas, 
            "Vialidad": df_vialidad, 
            "Tareas": df_tareas, 
            "ChecklistItems": df_checklistitems, 
            "Comentarios": df_comentarios,
            "Usuario": df_usuario,
            "EventoCalendario": df_eventocalendario,
            "EventoBrigada": df_eventobrigada,
            "Brigada": df_brigada,
            "EventoHistorial": df_eventohistorial

            } # Ejemplo abreviado
        print("✅ DataFrames de destino creados.")

        # 4. GUARDAR EN SQLITE (usando la ruta completa)
        with sqlite3.connect(RUTA_COMPLETA_DB) as conn:
            print(f"\n--- Guardando datos en '{os.path.basename(RUTA_COMPLETA_DB)}'... ---")
            for nombre_tabla, df in dataframes_a_guardar.items():
                if df is None or df.empty:
                    print(f"   - ⚠️ Tabla '{nombre_tabla}' está vacía. Se omitirá.")
                    continue
                for col in df.columns:
                    if not df[col].dropna().empty and isinstance(df[col].dropna().iloc[0], Decimal):
                        df[col] = df[col].apply(str)
                df.to_sql(nombre_tabla, conn, if_exists='replace', index=False)
                print(f"   - Tabla '{nombre_tabla}' guardada.")
            print("\n✅ ¡Éxito! Base de datos poblada.")

    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante el proceso principal: {e}")
    finally:
        # 5. LIMPIEZA INTELIGENTE (lógica sin cambios)
        if app_fue_creada_por_script and app:
            print("\n--- Cerrando la instancia de Excel iniciada por el script... ---")
            app.quit()
        elif book:
            print("\n--- El libro ya estaba abierto, no se cerrará la aplicación de Excel. Desconectando... ---")
        print("--- PROCESO FINALIZADO. ---")

# ... (tus otras importaciones y funciones como conectar_a_excel se mantienen igual) ...

def crear_base_de_datos_final_conversarDB():
    print(f"--- Sincronizando datos desde '{os.path.basename(RUTA_COMPLETA_EXCEL)}' ---")
    
    book, app, app_fue_creada_por_script = None, None, False
    try:
        # --- 1. CONECTAR DE FORMA INTELIGENTE ---
        book, app, app_fue_creada_por_script = conectar_a_excel(RUTA_COMPLETA_EXCEL)
        if not book: return

        # --- 2. LEER DATOS DE EXCEL ---
        print("\n--- Leyendo tablas fuente de Excel... ---")
        df_panel_control = book.sheets[NOMBRE_HOJA_PANEL_OBRA].tables[TABLA_PANEL_OBRA].range.options(pd.DataFrame, index=False, header=True).value
        df_coordenadas = book.sheets[NOMBRE_HOJA_COORDENADAS].tables[TABLA_COORDENADAS].range.options(pd.DataFrame, index=False, header=True).value
        df_vialidad = book.sheets[NOMBRE_HOJA_VIALIDAD].tables[TABLA_VIALIDAD].range.options(pd.DataFrame, index=False, header=True).value
        # Leemos también el DataFrame de Brigada desde Excel
        df_brigada_excel = book.sheets[NOMBRE_HOJA_BRIGADA].tables[TABLA_BRIGADA].range.options(pd.DataFrame, index=False, header=True).value
        
        print("✅ Tablas fuente leídas correctamente.")

        # --- 3. NORMALIZAR DATOS ---
        print("\n--- Normalizando datos... ---")
        columnas_proyectos = ['Unidad', 'Línea de Negocio', 'Comuna', 'Sector Urbano o Rural','WF SCM','WF', 'Sap', 'Valoriza', 'Programa de inversión', 'N° ID', 'ID', 'ID Posicion', 'Descripción', 'Tipo inversion', 'Coordinador', 'Contratista', 'Empresa', 'Estado', 'OBSERVACION']
        df_proyectos = df_panel_control[[col for col in columnas_proyectos if col in df_panel_control.columns]]

        dataframes_a_guardar = {
            "Proyectos": df_proyectos, 
            "Coordenadas": df_coordenadas, 
            "Vialidad": df_vialidad,
        }
        print("✅ DataFrames de destino creados.")

        # --> MODIFICADO: 'Brigada' ya no está en esta lista porque se manejará por separado.
        tablas_a_reemplazar_desde_excel = [
            "Proyectos",
            "Coordenadas",
            "Vialidad"
        ]

        # --- 4. GUARDAR Y SINCRONIZAR EN SQLITE ---
        with sqlite3.connect(RUTA_COMPLETA_DB) as conn:
            print(f"\n--- Guardando datos maestros en '{os.path.basename(RUTA_COMPLETA_DB)}'... ---")
            
            # Bucle para reemplazar las tablas maestras principales
            for nombre_tabla, df in dataframes_a_guardar.items():
                if nombre_tabla in tablas_a_reemplazar_desde_excel:
                    print(f"   - 🔄  Reemplazando tabla maestra '{nombre_tabla}' desde Excel...")
                    df.to_sql(nombre_tabla, conn, if_exists='replace', index=False)
                    print(f"     - ✅ Tabla '{nombre_tabla}' actualizada.")
            
            # --- NUEVO BLOQUE: Sincronización inteligente de la tabla 'Brigada' ---
            print("\n--- Sincronizando tabla de Brigadas (modo de solo agregar nuevas) ---")
            try:
                # 1. Leemos los IDs de las brigadas que YA existen en la base de datos
                df_brigada_db = pd.read_sql_query("SELECT id_brigada FROM Brigada", conn)
                ids_existentes = set(df_brigada_db['id_brigada'])
                print(f"   - Se encontraron {len(ids_existentes)} brigadas existentes en la base de datos.")

                # 2. Filtramos el DataFrame de Excel para quedarnos solo con las brigadas NUEVAS
                if not df_brigada_excel.empty:
                    df_nuevas_brigadas = df_brigada_excel[~df_brigada_excel['id_brigada'].isin(ids_existentes)]
                else:
                    df_nuevas_brigadas = pd.DataFrame() # DataFrame vacío si el excel no tiene brigadas

                # 3. Si hay nuevas brigadas, las añadimos a la tabla existente.
                if not df_nuevas_brigadas.empty:
                    print(f"   - Se encontraron {len(df_nuevas_brigadas)} nuevas brigadas en el Excel para agregar.")
                    # Usamos if_exists='append' para AÑADIR los datos sin borrar la tabla.
                    df_nuevas_brigadas.to_sql('Brigada', conn, if_exists='append', index=False)
                    print(f"   - ✅ Se agregaron {len(df_nuevas_brigadas)} nuevas brigadas a la base de datos.")
                else:
                    print("   - ✅ No se encontraron nuevas brigadas para agregar. La tabla está actualizada.")
            
            except Exception as e:
                print(f"   - ❌ Error durante la sincronización de la tabla Brigada: {e}")

            print("\n✅ ¡Éxito! Sincronización de datos maestros completada.")

    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante el proceso principal: {e}")
    finally:
        # --- 5. LIMPIEZA INTELIGENTE ---
        if app_fue_creada_por_script and app:
            print("\n--- Cerrando la instancia de Excel iniciada por el script... ---")
            app.quit()
        elif book:
            print("\n--- El libro ya estaba abierto, no se cerrará la aplicación de Excel. Desconectando... ---")
        print("--- PROCESO FINALIZADO. ---")

if __name__ == '__main__':
    start_time = time.time()

    # Llamamos a la función para que lea el Excel y cree mapa.db
    crear_base_de_datos_final_conversarDB()

    end_time = time.time()  


### Resumen de las Correcciones Clave

