# MODULES/SQLITE/CONTROLLER/beneficiarios.py
import sqlite3
import pandas as pd
import io
import os
from MODULES import rutas


def get_db_connection():
    """Establece la conexión a la base de datos."""
    rutas_dict = rutas.convert_rutas()
    RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
    conn = sqlite3.connect(RUTA_DB)
    # Habilitar el soporte para llaves foráneas es una buena práctica
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_beneficiarios_por_proyecto(sap_id):
    """Obtiene todos los beneficiarios de un proyecto."""
    try:
        conn = get_db_connection()
        # row_factory permite obtener los resultados como diccionarios
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Beneficiarios WHERE sap_id = ?", (sap_id,))
        beneficiarios = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return beneficiarios, 200
    except Exception as e:
        print(f"Error en get_beneficiarios_por_proyecto: {e}")
        return {"error": str(e)}, 500

def create_beneficiario(data):
    """Crea un nuevo beneficiario."""
    # Lógica para crear un nuevo registro en la DB
    # ... (Implementar lógica de inserción)
    return {"mensaje": "Creado (lógica pendiente)"}, 201

def update_beneficiario(beneficiario_id, data):
    """Actualiza un beneficiario existente en la base de datos."""
    fields = [
        'numero_beneficiario', 'nombre_completo', 'rut', 'instalacion_interior',
        'lbt', 'lmt', 'empalme', 'aumento_potencia', 'servidumbre', 'comentario_servidumbre'
    ]
    
    sql_set_parts = []
    values = []
    
    for field in fields:
        if field in data:
            sql_set_parts.append(f"{field} = ?")
            values.append(data[field])
            
    if not sql_set_parts:
        return {"error": "No hay datos para actualizar"}, 400

    values.append(beneficiario_id)
    
    sql = f"UPDATE Beneficiarios SET {', '.join(sql_set_parts)} WHERE id = ?"
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, tuple(values))
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": "Beneficiario no encontrado"}, 404
        return {"mensaje": "Beneficiario actualizado con éxito"}, 200
    except Exception as e:
        print(f"Error en update_beneficiario: {e}")
        return {"error": str(e)}, 500
    finally:
        if conn:
            conn.close()

def delete_beneficiario(beneficiario_id):
    """Elimina un beneficiario de la base de datos."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Beneficiarios WHERE id = ?", (beneficiario_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": "Beneficiario no encontrado"}, 404
        return {"mensaje": "Beneficiario eliminado con éxito"}, 200
    except Exception as e:
        print(f"Error en delete_beneficiario: {e}")
        return {"error": str(e)}, 500
    finally:
        if conn:
            conn.close()

# MODULES/SQLITE/CONTROLLER/beneficiarios.py

def upload_beneficiarios_from_file(sap_id, file):
    """
    Reemplaza o inserta los beneficiarios para un proyecto, verificando
    primero que el proyecto exista.
    """
    conn = None
    try:
        # --- Lectura y preparación del DataFrame (esta parte no cambia) ---
        column_map = {
            'N° Beneficiario': 'numero_beneficiario', 'Nombre Completo': 'nombre_completo',
            'RUT': 'rut', 'Instalacion Interior': 'instalacion_interior', 'LBT': 'lbt',
            'LMT': 'lmt', 'Empalme': 'empalme', 'Aumento de Potencia': 'aumento_potencia',
            'Servidumbre': 'servidumbre', 'Comentario Servidumbre': 'comentario_servidumbre'
        }
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(file, dtype=str)
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(file, dtype=str)
        else:
            return {"error": "Formato de archivo no soportado."}, 400

        if 'ID' in df.columns: df = df.drop(columns=['ID'])
        if 'id' in df.columns: df = df.drop(columns=['id'])

        df.rename(columns=column_map, inplace=True)
        df['sap_id'] = str(sap_id)
        db_cols = list(column_map.values()) + ['sap_id']
        df_to_insert = df[[col for col in df.columns if col in db_cols]]

        # --- Lógica de Base de Datos ---
        conn = get_db_connection()
        cursor = conn.cursor()

        # PASO 1: Verificar que el proyecto exista en la tabla Proyectos (tu requisito principal).
        cursor.execute("SELECT COUNT(*) FROM Proyectos WHERE Sap = ?", (str(sap_id),))
        if cursor.fetchone()[0] == 0:
            error_message = f"El proyecto con SAP ID '{sap_id}' no existe. No se pueden cargar beneficiarios."
            return {"error": error_message}, 404

        # PASO 2: Eliminar TODOS los beneficiarios antiguos asociados a este sap_id.
        # Si no existe ninguno (tu segundo caso), este comando simplemente no hará nada y no dará error.
        cursor.execute("DELETE FROM Beneficiarios WHERE sap_id = ?", (str(sap_id),))

        # PASO 3: Insertar los nuevos registros del archivo Excel.
        # Esto funciona tanto para el caso de reemplazo como para una inserción nueva.
        df_to_insert.to_sql('Beneficiarios', conn, if_exists='append', index=False)

        # PASO 4: Confirmar la transacción completa (DELETE + INSERT).
        conn.commit()

        return {"mensaje": f"{len(df.index)} beneficiarios han sido cargados exitosamente."}, 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error inesperado al subir archivo de beneficiarios: {e}")
        return {"error": f"Error inesperado procesando el archivo: {e}"}, 500

    finally:
        if conn:
            conn.close()


def download_beneficiarios_as_excel(sap_id):
    """Obtiene los beneficiarios de la DB y los devuelve como un archivo Excel en memoria."""
    conn = get_db_connection()
    query = f"SELECT * FROM Beneficiarios WHERE sap_id = '{sap_id}'"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Mapeo inverso para nombres de columna amigables en el Excel
    column_rename = {
        'id': 'ID',
        'sap_id': 'SAP',
        'numero_beneficiario': 'N° Beneficiario',
        'nombre_completo': 'Nombre Completo',
        'rut': 'RUT',
        'instalacion_interior': 'Instalación Interior',
        'lbt': 'LBT',
        'lmt': 'LMT',
        'empalme': 'Empalme',
        'aumento_potencia': 'Aumento de Potencia',
        'servidumbre': 'Servidumbre',
        'comentario_servidumbre': 'Comentario Servidumbre'
    }
    df.rename(columns=column_rename, inplace=True)

    # Crear un buffer de bytes en memoria para el archivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Beneficiarios')
    output.seek(0)
    
    return output