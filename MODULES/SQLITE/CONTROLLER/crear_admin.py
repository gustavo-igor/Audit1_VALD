import sqlite3
import os
from MODULES import rutas
from MODULES.SQLITE.CONTROLLER.seguridad import encriptar_password 

# --- CONFIGURACIÓN DEL USUARIO ADMINISTRADOR ---
# Elige una contraseña segura para el administrador
CONTRASENA_ADMIN = "admin" 

# --- NO MODIFICAR DEBAJO DE ESTA LÍNEA ---

def crear_usuario_admin():
    """
    Inserta el usuario administrador en la base de datos con una contraseña encriptada.
    """
    print("--- Creando usuario administrador ---")
    
    # Encriptamos la contraseña
    password_hasheada = encriptar_password(CONTRASENA_ADMIN)
    
    # Conectamos a la base de datos
    rutas_dict = rutas.convert_rutas()
    RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
    conn = sqlite3.connect(RUTA_DB)
    cursor = conn.cursor()

    try:
        # El role_id del Administrador es 1 (según la inserción que hicimos antes)
        cursor.execute("""
            INSERT INTO Usuarios (username, email, password, nombre_completo, contratista, estado, role_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            'Jorge Tolten',                        # username
            'jorge@tolten.cl',          # email
            password_hasheada,              # contraseña encriptada
            'Jorge tolten',    # nombre_completo
            None,                           # contratista (el admin no tiene)
            'activo',                       # estado
            1                               # role_id (1 = Administrador)
        ))
        
        conn.commit()
        print("✅ ¡Usuario 'admin' creado con éxito!")
        print(f"   - Email para iniciar sesión: admin@tuempresa.com")
        print(f"   - Contraseña: {CONTRASENA_ADMIN}")

    except sqlite3.IntegrityError:
        print("⚠️  El usuario 'admin' o el email 'admin@tuempresa.com' ya existe en la base de datos.")
    except Exception as e:
        print(f"❌ Ocurrió un error al crear el usuario: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    crear_usuario_admin()