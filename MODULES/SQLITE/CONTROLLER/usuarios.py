# Archivo: MODULES/SQLITE/CONTROLLER/usuarios.py
import sqlite3, os
from MODULES import rutas
from MODULES.SQLITE.CONTROLLER.seguridad import encriptar_password

def _get_db_connection():
    conn = sqlite3.connect(os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db"))
    conn.row_factory = sqlite3.Row
    return conn

def get_all_users_with_details():
    """Obtiene todos los usuarios con el nombre de su rol para mostrar en la tabla."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    # Usamos un JOIN para obtener el nombre del rol en lugar de solo el ID
    cursor.execute("""
        SELECT u.id, u.username, u.email, u.nombre_completo, u.contratista, u.estado, r.nombre_rol
        FROM Usuarios u
        LEFT JOIN Roles r ON u.role_id = r.id
        ORDER BY u.nombre_completo
    """)
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users, 200

def get_user_by_id(user_id):
    """Obtiene los datos de un único usuario por su ID."""
    conn = _get_db_connection()
    user = conn.execute("SELECT id, username, email, nombre_completo, contratista, estado, role_id FROM Usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None, 200 if user else 404

def create_user(data):
    """Crea un nuevo usuario en la base de datos."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        if not data.get('password'):
            return {"error": "La contraseña es requerida para nuevos usuarios"}, 400

        hashed_password = encriptar_password(data['password'])
        
        cursor.execute("""
            INSERT INTO Usuarios (username, email, password, nombre_completo, contratista, estado, role_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data['username'], data['email'], hashed_password, data['nombre_completo'],
            data.get('contratista'), data['estado'], data['role_id']
        ))
        conn.commit()
        return {"mensaje": "Usuario creado con éxito"}, 201
    except sqlite3.IntegrityError as e:
        return {"error": f"Error de integridad: El usuario o email ya existe. {e}"}, 409
    finally:
        conn.close()

def update_user(user_id, data):
    """Actualiza un usuario existente."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        if data.get('password'): # Solo actualiza la contraseña si se proporciona una nueva
            hashed_password = encriptar_password(data['password'])
            cursor.execute("""
                UPDATE Usuarios SET username=?, email=?, password=?, nombre_completo=?, contratista=?, estado=?, role_id=?
                WHERE id=?
            """, (
                data['username'], data['email'], hashed_password, data['nombre_completo'],
                data.get('contratista'), data['estado'], data['role_id'], user_id
            ))
        else: # Actualiza todo excepto la contraseña
            cursor.execute("""
                UPDATE Usuarios SET username=?, email=?, nombre_completo=?, contratista=?, estado=?, role_id=?
                WHERE id=?
            """, (
                data['username'], data['email'], data['nombre_completo'],
                data.get('contratista'), data['estado'], data['role_id'], user_id
            ))
        conn.commit()
        return {"mensaje": "Usuario actualizado con éxito"}, 200
    except sqlite3.IntegrityError as e:
        return {"error": f"Error de integridad: El usuario o email ya existe. {e}"}, 409
    finally:
        conn.close()

def delete_user(user_id):
    """Elimina un usuario (o lo marca como inactivo). Por seguridad, es mejor desactivar."""
    # Aquí podrías cambiar el estado a 'inactivo' en lugar de borrar.
    # Por ahora, implementamos el borrado.
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Usuarios WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"mensaje": "Usuario eliminado con éxito"}, 200