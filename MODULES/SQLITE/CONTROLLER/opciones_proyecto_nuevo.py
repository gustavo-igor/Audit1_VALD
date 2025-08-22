# Archivo: opciones_crud.py
import sqlite3,os,pandas as pd, io
from MODULES import rutas

# --- FUNCIONES GENÉRICAS PARA EL CRUD ---
# Usamos funciones genéricas para no repetir código.
# Estas funciones pueden operar sobre cualquier tabla de opciones.

allowed_tables = [
    'Estados', 
    'Coordinadores', 
    'Contratista', 
    'Unidades', 
    'Lineas_negocio', 
    'Comunas',
    'Brigada',
    'Roles'
    ]

def _get_db_connection():
    """Helper para obtener una conexión a la DB con row_factory."""
    rutas_dict = rutas.convert_rutas()
    RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")

    conn = sqlite3.connect(RUTA_DB)
    conn.row_factory = sqlite3.Row

    return conn

def get_all_options(table_name):
    """
    Obtiene todos los registros de una tabla de opciones específica.
    Ej: get_all_options('coordinadores')
    """

    conn = _get_db_connection()
    cursor = conn.cursor()
    # Usamos una lista blanca para seguridad, para evitar inyección SQL.
    
    if table_name not in allowed_tables:
        raise ValueError("Tabla no permitida")

    if table_name == 'Brigada':
        # Para Brigada, traemos también el contratista
        cursor.execute("SELECT id, nombre, contratista FROM Brigada ORDER BY nombre")
    elif table_name == 'Roles':
        # Se selecciona 'nombre_rol' pero se le da el alias 'nombre' para que el frontend lo entienda
        cursor.execute("SELECT id, nombre_rol AS nombre FROM Roles ORDER BY id")
    else:
        # Para las demás, solo id y nombre
        cursor.execute(f"SELECT id, nombre FROM {table_name} ORDER BY nombre")

    return [dict(row) for row in cursor.fetchall()]


def get_option_by_id(table_name, option_id):
    """Obtiene un único registro por su ID."""
    if table_name not in allowed_tables:
        raise ValueError(f"Tabla '{table_name}' no permitida.")

    conn = _get_db_connection()
    cursor = conn.cursor()
    
    if table_name == 'Brigada':
        cursor.execute("SELECT id, nombre, contratista FROM Brigada WHERE id = ?", (option_id,))
    else:
        cursor.execute(f"SELECT id, nombre FROM {table_name} WHERE id = ?", (option_id,))
        
    option = cursor.fetchone()
    conn.close()
    return dict(option) if option else None

def create_option(table_name, data):
    """
    Crea un nuevo registro en una tabla de opciones.
    'data' debe ser un diccionario con la clave 'nombre'.
    """
    nombre = data.get('nombre')
    if not nombre:
        return None, "El campo 'nombre' es requerido."

    if table_name not in allowed_tables:
        return None, "Tabla no permitida"

    nombre = data.get('nombre')
    if not nombre:
        return None, "El campo 'nombre' es requerido."
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        # LÓGICA CORREGIDA PARA BRIGADA
        if table_name == 'Brigada':
            contratista = data.get('contratista')
            if not contratista:
                return None, "Debe seleccionar un contratista para la brigada."
            cursor.execute("INSERT INTO Brigada (nombre, contratista) VALUES (?, ?)", (nombre, contratista))
        else:
            cursor.execute(f"INSERT INTO {table_name} (nombre) VALUES (?)", (nombre,))
        conn.commit()
        new_id = cursor.lastrowid
        return {"id": new_id, **data}, None
    except sqlite3.IntegrityError:
        return None, f"El valor '{nombre}' ya existe."
    finally:
        conn.close()

def update_option(table_name, option_id, data):
    """Actualiza un registro existente."""
    if table_name not in allowed_tables:
        return False, f"Tabla '{table_name}' no permitida."
    nombre = data.get('nombre')
    if not nombre:
        return False, "El campo 'nombre' es requerido."
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        # LÓGICA CORREGIDA PARA BRIGADA
        if table_name == 'Brigada':
            contratista = data.get('contratista')
            if not contratista:
                return False, "Debe seleccionar un contratista."
            cursor.execute("UPDATE Brigada SET nombre = ?, contratista = ? WHERE id = ?", (nombre, contratista, option_id))
        else:
            cursor.execute(f"UPDATE {table_name} SET nombre = ? WHERE id = ?", (nombre, option_id))
        conn.commit()
        return cursor.rowcount > 0, None
    except sqlite3.IntegrityError:
        return False, f"El valor '{nombre}' ya existe."
    finally:
        conn.close()

def delete_option(table_name, option_id):
    """
    Elimina un registro de una tabla de opciones por su ID.
    """

    if table_name not in allowed_tables:
        return False, "Tabla no permitida"
        
    conn = _get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (option_id,))
        conn.commit()
        return cursor.rowcount > 0, None
    except Exception as e:
        conn.rollback()
        return False, str(e)

def export_table_to_excel(table_name):
    """
    Obtiene todos los datos de una tabla y los devuelve como un archivo Excel en memoria.
    """
    # 1. Validamos la tabla como en las otras funciones
    if table_name not in allowed_tables:
        raise ValueError(f"Tabla '{table_name}' no permitida.")

    # 2. Reutilizamos la función que ya tenemos para obtener todos los datos
    all_data = get_all_options(table_name)

    if not all_data:
        # Si no hay datos, podrías devolver un buffer vacío o manejar el error
        return None

    # 3. Creamos un DataFrame de pandas con los datos
    df = pd.DataFrame(all_data)

    # 4. Creamos un "archivo" Excel en la memoria RAM
    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=table_name)
    
    # 5. Preparamos el buffer para ser leído desde el principio
    output_buffer.seek(0)
    
    # 6. Devolvemos el buffer que contiene el archivo Excel
    return output_buffer