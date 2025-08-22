# Archivo: MODULES/SQLITE/CONTROLLER/roles.py
import sqlite3, os
from MODULES import rutas

# Lista de todos los módulos disponibles en la plataforma
ALL_MODULES = ['dashboard', 'calendario', 'proyectos', 'kanban', 'rpa', 'mapa', 'tablas']

def _get_db_connection():
    conn = sqlite3.connect(os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db"))
    conn.row_factory = sqlite3.Row
    return conn

def get_all_roles():
    """Obtiene todos los roles para la tabla de gestión."""
    conn = _get_db_connection()
    roles = conn.execute("SELECT id, nombre_rol, permisos FROM Roles").fetchall()
    conn.close()
    return [dict(row) for row in roles], 200

def get_role_permissions(role_id):
    """Obtiene los detalles y permisos de un rol específico."""
    conn = _get_db_connection()
    role = conn.execute("SELECT id, nombre_rol, permisos FROM Roles WHERE id = ?", (role_id,)).fetchone()
    conn.close()
    if not role:
        return {"error": "Rol no encontrado"}, 404
    
    # Devuelve el rol y la lista completa de módulos para construir los checkboxes
    return {
        "role": dict(role),
        "all_modules": ALL_MODULES
    }, 200

def update_role_permissions(role_id, data):
    """Actualiza la lista de permisos para un rol."""
    permissions_list = data.get('permisos', [])
    if not isinstance(permissions_list, list):
        return {"error": "El formato de permisos es incorrecto"}, 400

    # Convierte la lista de permisos en un string separado por comas
    permisos_str = ",".join(permissions_list)

    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Roles SET permisos = ? WHERE id = ?", (permisos_str, role_id))
    conn.commit()
    conn.close()

    return {"mensaje": "Permisos actualizados con éxito"}, 200