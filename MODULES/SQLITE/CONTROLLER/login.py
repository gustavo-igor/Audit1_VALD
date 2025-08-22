# Archivo: MODULES/SQLITE/CONTROLLER/login.py
import sqlite3
import os
from MODULES import rutas
from MODULES.SQLITE.CONTROLLER.seguridad import verificar_password 

def verificar_credenciales(email, password, access_type):
    """
    Verifica las credenciales según el tipo de acceso seleccionado.
    """
    conn = sqlite3.connect(os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db"))
    conn.row_factory = sqlite3.Row
    
    try:
        user = conn.execute("SELECT * FROM Usuarios WHERE email = ?", (email,)).fetchone()

        # Validaciones comunes para ambos tipos de acceso
        if not user or user['estado'] != 'activo' or not verificar_password(user['password'], password):
            return None, "Credenciales incorrectas o usuario inactivo."

        role = conn.execute("SELECT * FROM Roles WHERE id = ?", (user['role_id'],)).fetchone()
        if not role:
            return None, "El usuario no tiene un rol asignado. Contacte al administrador."

        # =================================================================
        # LÓGICA DE FILTRADO BASADA EN EL TIPO DE ACCESO
        # =================================================================
        
        # Para acceso SAESA, el rol define el filtro
        if access_type == 'saesa':
            # Si un usuario SAESA no es Admin o Coordinador, no puede entrar por esta vía.
            if role['nombre_rol'] not in ['Administrador', 'Coordinador']:
                return None, "Acceso no permitido para este rol por la vía SAESA."
            
            # El nombre a filtrar para un coordinador es su nombre completo
            nombre_a_filtrar = user['nombre_completo'] if role['nombre_rol'] == 'Coordinador' else None

        # Para acceso Contratista, el rol debe ser Contratista
        elif access_type == 'contratista':
            if role['nombre_rol'] != 'Contratista':
                return None, "Este usuario no tiene permisos de contratista."
            
            # El nombre a filtrar es el que está en la columna 'contratista' del usuario
            nombre_a_filtrar = user['contratista']
            if not nombre_a_filtrar:
                return None, "El usuario contratista no tiene una empresa asociada."
        else:
            return None, "Tipo de acceso no válido."

        # =================================================================
        
        session_data = {
            'user_id': user['id'],
            'username': user['username'],
            'nombre_completo': user['nombre_completo'],
            'rol': role['nombre_rol'],
            # Guardamos el valor por el cual se debe filtrar, sea un nombre de coordinador o de contratista
            'filtro_asociado': nombre_a_filtrar, 
            'permisos': role['permisos'].split(',')
        }
        
        return session_data, None

    finally:
        conn.close()