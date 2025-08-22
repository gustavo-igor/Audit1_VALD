import sqlite3, os, datetime, pandas as pd
from werkzeug.utils import secure_filename
from MODULES import rutas

# Definimos una ruta base para guardar los archivos subidos
rutas_dict = rutas.convert_rutas()
UPLOAD_FOLDER = os.path.join(rutas_dict["ruta_guardado_OT"])
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def subir_documentos(sap_id, files, comentario):
    """
    Guarda los archivos en el servidor y registra sus datos en la BD.
    """

    print(f"--- DEBUG EN documentos.py ---")
    print(f"Comentario que se pasará a la base de datos: '{comentario}'")
    print(f"----------------------------")


    try:
        # Crea una carpeta específica para el proyecto si no existe
        proyecto_folder = os.path.join(UPLOAD_FOLDER, str(sap_id.replace("/","")))
        if not os.path.exists(proyecto_folder):
            os.makedirs(proyecto_folder)

        conn = sqlite3.connect(os.path.join(rutas_dict["ruta_script_python"], "mapa.db"))
        cursor = conn.cursor()

        for f in files:
            # Aseguramos un nombre de archivo seguro
            filename = secure_filename(f.filename)
            file_path = os.path.join(proyecto_folder, filename)
            f.save(file_path)

            query = """
                INSERT INTO Documentos (sap_id, id_tarea, nombre_archivo, path_archivo, comentario, usuario_subida)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            # Asumimos que el usuario está en la sesión, si no, puedes poner un valor por defecto
            usuario = "usuario_ejemplo" 
            cursor.execute(query, (sap_id, None, filename, file_path, comentario, usuario))

        conn.commit()
        conn.close()
        return True, "Archivos subidos correctamente"
    except Exception as e:
        print(f"Error en subir_documentos: {e}")
        return False, str(e)

def listar_documentos(sap_id):
    """Obtiene la lista de documentos para un proyecto específico."""
    try:
        conn = sqlite3.connect(os.path.join(rutas_dict["ruta_script_python"], "mapa.db"))
        query = "SELECT * FROM Documentos WHERE sap_id = ? ORDER BY fecha_subida DESC"
        # Usamos pandas para convertir fácilmente la consulta a un formato amigable para JSON
        df = pd.read_sql_query(query, conn, params=(sap_id,))
        conn.close()
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Error en listar_documentos: {e}")
        return []

def eliminar_documento(id_documento):
    """Elimina un documento de la BD y del sistema de archivos."""
    try:
        conn = sqlite3.connect(os.path.join(rutas_dict["ruta_script_python"], "mapa.db"))
        cursor = conn.cursor()

        # Primero, obtenemos la ruta del archivo para poder borrarlo
        cursor.execute("SELECT path_archivo FROM Documentos WHERE id_documento = ?", (id_documento,))
        resultado = cursor.fetchone()
        
        if not resultado:
            conn.close()
            return False, "Documento no encontrado"

        path_archivo = resultado[0]

        # Borramos el registro de la BD
        cursor.execute("DELETE FROM Documentos WHERE id_documento = ?", (id_documento,))
        conn.commit()
        conn.close()

        # Borramos el archivo físico del servidor
        if os.path.exists(path_archivo):
            os.remove(path_archivo)
        
        return True, "Documento eliminado"
    except Exception as e:
        print(f"Error en eliminar_documento: {e}")
        return False, str(e)
    
def subir_adjunto_para_tarea(id_tarea, files):
    """
    Guarda un archivo para una tarea específica. Primero busca el sap_id
    de la tarea y luego lo guarda en la tabla Documentos.
    """
    conn = None
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        cursor = conn.cursor()

        # 1. Obtenemos el sap_id de la tarea para saber en qué carpeta guardar
        cursor.execute("SELECT Sap FROM Tareas WHERE id_tarea = ?", (id_tarea,))
        resultado = cursor.fetchone()
        if not resultado:
            return False, "La tarea asociada no fue encontrada."
        
        sap_id = resultado[0]

        # 2. Creamos la carpeta del proyecto si no existe
        proyecto_folder = os.path.join(UPLOAD_FOLDER, str(sap_id.replace("/", ""))) # Asegúrate de que UPLOAD_FOLDER esté definida
        if not os.path.exists(proyecto_folder):
            os.makedirs(proyecto_folder)

        # 3. Guardamos cada archivo y registramos en la BD
        for f in files:
            filename = secure_filename(f.filename) # Importa secure_filename de werkzeug.utils
            file_path = os.path.join(proyecto_folder, filename)
            f.save(file_path)

            query = """
                INSERT INTO Documentos (sap_id, id_tarea, nombre_archivo, path_archivo, usuario_subida)
                VALUES (?, ?, ?, ?, ?)
            """
            usuario = "usuario_ejemplo"
            # Insertamos tanto el sap_id como el id_tarea
            cursor.execute(query, (sap_id, id_tarea, filename, file_path, usuario))

        conn.commit()
        return True, "Archivos subidos correctamente"

    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en subir_adjunto_para_tarea: {e}")
        return False, str(e)
    finally:
        if conn: conn.close()

def listar_adjuntos_por_tarea(id_tarea):
    """Obtiene la lista de documentos para una tarea específica."""
    try:
        conn = sqlite3.connect(os.path.join(rutas_dict["ruta_script_python"], "mapa.db"))
        # Filtramos por id_tarea, excluyendo los que son solo del proyecto (id_tarea IS NULL)
        query = "SELECT * FROM Documentos WHERE id_tarea = ? ORDER BY fecha_subida DESC"
        df = pd.read_sql_query(query, conn, params=(id_tarea,))
        conn.close()
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Error en listar_adjuntos_por_tarea: {e}")
        return []
    
def get_documento_por_id(id_documento):
    """
    Busca un documento en la BD por su ID y devuelve su ruta y nombre.
    """
    try:
        # Asumo que la variable rutas_dict está disponible o la obtienes de alguna manera
        conn = sqlite3.connect(os.path.join(rutas_dict["ruta_script_python"], "mapa.db"))
        cursor = conn.cursor()
        query = "SELECT path_archivo, nombre_archivo FROM Documentos WHERE id_documento = ?"
        cursor.execute(query, (id_documento,))
        resultado = cursor.fetchone()
        conn.close()
        return resultado # Devuelve una tupla (path_archivo, nombre_archivo) o None
    except Exception as e:
        print(f"Error en get_documento_por_id: {e}")
        return None