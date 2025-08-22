# Archivo: MODULES/PROYECTOS/tareas.py
import sqlite3, os, datetime
import pandas as pd
from datetime import datetime, timedelta
from MODULES import rutas

from flask import session
from MODULES.SQLITE.CONTROLLER.proyectos import get_allowed_saps 
from MODULES.notificaciones import crear_notificacion



def get_tareas_por_proyecto(sap_id):
    """Obtiene todas las tareas para un proyecto específico."""
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)

        # 1. Obtener las tareas principales
        query_tareas = "SELECT * FROM Tareas WHERE sap = ?"
        df_tareas = pd.read_sql_query(query_tareas, conn, params=(sap_id,))
        
        # Convertir a una lista de diccionarios para poder modificarla
        lista_tareas = df_tareas.to_dict(orient='records')

        # 2. Para cada tarea, obtener su checklist y añadirla
        query_checklist = "SELECT * FROM ChecklistItems WHERE id_tarea = ?"
        for tarea in lista_tareas:
            id_tarea = tarea['id_tarea']
            df_checklist = pd.read_sql_query(query_checklist, conn, params=(id_tarea,))
            # Añadimos la lista de subtareas al diccionario de la tarea principal
            tarea['checklist'] = df_checklist.to_dict(orient='records')
            
        return lista_tareas

    except Exception as e:
        print(f"Error en get_tareas_por_proyecto: {e}")
        return []
    finally:
        if conn:
            conn.close()

def actualizar_estado_tarea_proyecto(id_tarea, nuevo_estado):

    rutas_dict = rutas.convert_rutas()
    RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")

    """Actualiza el estado de una tarea específica."""
    # Lista de estados válidos para seguridad
    estados_validos = ["Pendiente", "En Proceso", "En Revisión", "Completada", "Bloqueada"]
    if nuevo_estado not in estados_validos:
        return False, "Estado no válido"

    try:
        conn = sqlite3.connect(RUTA_DB)
        cursor = conn.cursor()
        # Actualizamos también la fecha de modificación
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = "UPDATE Tareas SET estado = ?, fecha_modificacion = ? WHERE id_tarea = ?"
        cursor.execute(query, (nuevo_estado, fecha_actual, id_tarea))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0, "Actualización exitosa"
    except Exception as e:
        print(f"Error en actualizar_estado_tarea: {e}")
        return False, str(e)

def crear_nueva_tarea_proyecto(datos_tarea):
    """Crea una nueva tarea y sus subtareas en la base de datos."""
    conn = None
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        cursor = conn.cursor()
        
        query = """
            INSERT INTO Tareas (
                Sap, nombre_tarea, brigada, descripcion, estado, prioridad, 
                coordinador, contratista, etiqueta, fecha_creacion, fecha_vencimiento
            ) VALUES (?, ?, ?, ?, ?, ?, ?,? ,?, ?, ?)
        """
        fecha_actual =datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params = (
            datos_tarea.get('proyecto_sap'),
            datos_tarea.get('nombre_tarea'),
            datos_tarea.get('brigada'),
            datos_tarea.get('descripcion'),
            datos_tarea.get('estado'),
            datos_tarea.get('prioridad'),
            datos_tarea.get('coordinador'),
            datos_tarea.get('contratista'),
            datos_tarea.get('etiqueta'),
            fecha_actual,
            datos_tarea.get('fecha_vencimiento')
        )
        cursor.execute(query, params)
        id_nueva_tarea = cursor.lastrowid
        
        checklist_items = datos_tarea.get('checklist', [])
        if checklist_items:
            query_checklist = "INSERT INTO ChecklistItems (id_tarea, texto_item, completado) VALUES (?, ?, ?)"
            for item in checklist_items:
                texto_subtarea = item.get('texto') if isinstance(item, dict) else item
                completado = 1 if isinstance(item, dict) and item.get('completada') else 0
                cursor.execute(query_checklist, (id_nueva_tarea, texto_subtarea, completado))

        conn.commit()
        
        # MODIFICACIÓN: Devolvemos la tarea completa, incluyendo la checklist que acabamos de guardar.
        df_nueva_tarea = pd.read_sql_query("SELECT * FROM Tareas WHERE id_tarea = ?", conn, params=(id_nueva_tarea,))
        tarea_creada = df_nueva_tarea.to_dict(orient='records')[0]
        
        # Añadimos la checklist al objeto que se devuelve
        df_checklist_creada = pd.read_sql_query("SELECT * FROM ChecklistItems WHERE id_tarea = ?", conn, params=(id_nueva_tarea,))
        tarea_creada['checklist'] = df_checklist_creada.to_dict(orient='records')

        return tarea_creada, 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error en crear_nueva_tarea: {e}")
        return {'error': str(e)}, 500
    finally:
        if conn:
            conn.close()
            
def get_todas_las_tareas_original():
    """
    Obtiene TODAS las tareas de la BD, incluyendo sus subtareas (checklist) para el Kanban global.
    """
    conn = None
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)

        # 1. Obtener todas las tareas principales
        query_tareas = "SELECT * FROM Tareas ORDER BY fecha_vencimiento ASC"
        df_tareas = pd.read_sql_query(query_tareas, conn)

        # --- Adaptación de datos para el frontend ---
        if 'Sap' in df_tareas.columns:
            df_tareas.rename(columns={'Sap': 'proyecto_sap'}, inplace=True)
        if 'fecha_vencimiento' in df_tareas.columns:
            df_tareas['fecha_vencimiento'] = pd.to_datetime(df_tareas['fecha_vencimiento'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
        if 'fecha_creacion' in df_tareas.columns:
            df_tareas['fecha_creacion'] = pd.to_datetime(df_tareas['fecha_creacion'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        
        lista_tareas = df_tareas.to_dict(orient='records')

        # 2. Para cada tarea, obtener su checklist y añadirla
        query_checklist = "SELECT * FROM ChecklistItems WHERE id_tarea = ?"
        for tarea in lista_tareas:
            id_tarea = tarea['id_tarea']
            df_checklist = pd.read_sql_query(query_checklist, conn, params=(id_tarea,))
            # Añadimos la lista de subtareas al diccionario de la tarea principal
            tarea['checklist'] = df_checklist.to_dict(orient='records')
            
        return lista_tareas

    except Exception as e:
        print(f"Error en get_todas_las_tareas: {e}")
        return []
    finally:
        if conn:
            conn.close()
            
def get_todas_las_tareas():
    """
    Obtiene TODAS las tareas para el Kanban global, aplicando el filtro de seguridad
    basado en el rol del usuario en sesión.
    """
    conn = None
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)

        # ▼▼▼ 2. SE APLICA EL FILTRO DE SEGURIDAD ANTES DE LA CONSULTA ▼▼▼
        
        # Consulta base que une Tareas y Proyectos para obtener datos del coordinador y contratista
        query = """
            SELECT 
                t.*,
                p.Coordinador AS coordinador,
                p.Contratista AS contratista
            FROM Tareas t
            LEFT JOIN Proyectos p ON t.Sap = p.Sap
        """
        
        params = []
        where_clauses = []

        allowed_saps = get_allowed_saps()
        if allowed_saps is not None: # Si el usuario NO es Administrador
            if not allowed_saps:
                return [] # Si no tiene SAPs asignados, devuelve una lista vacía.
            
            placeholders = ','.join('?' for _ in allowed_saps)
            where_clauses.append(f"t.Sap IN ({placeholders})")
            params.extend(allowed_saps)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY fecha_vencimiento ASC"

        df_tareas = pd.read_sql_query(query, conn, params=tuple(params))
        
        # --- 3. PROCESAMIENTO DE DATOS (SIN CAMBIOS) ---
        if 'Sap' in df_tareas.columns:
            df_tareas.rename(columns={'Sap': 'proyecto_sap'}, inplace=True)
        if 'fecha_vencimiento' in df_tareas.columns:
            df_tareas['fecha_vencimiento'] = pd.to_datetime(df_tareas['fecha_vencimiento'], errors='coerce').dt.strftime('%Y-%m-%d').fillna('')
        if 'fecha_creacion' in df_tareas.columns:
            df_tareas['fecha_creacion'] = pd.to_datetime(df_tareas['fecha_creacion'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        
        lista_tareas = df_tareas.to_dict(orient='records')

        query_checklist = "SELECT * FROM ChecklistItems WHERE id_tarea = ?"
        for tarea in lista_tareas:
            id_tarea = tarea['id_tarea']
            df_checklist = pd.read_sql_query(query_checklist, conn, params=(id_tarea,))
            tarea['checklist'] = df_checklist.to_dict(orient='records')
            
        return lista_tareas

    except Exception as e:
        print(f"Error en get_todas_las_tareas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_checklist_por_tarea(id_tarea):
    
    conn = None
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)

        query = "SELECT * FROM ChecklistItems WHERE id_tarea = ?"
        df_checklist = pd.read_sql_query(query, conn, params=(int(id_tarea),))
        
        return df_checklist.to_dict(orient='records')
    
    except Exception as e:
        print(f"Error en get_todas_las_tareas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def eliminar_tarea_por_id(task_id):
    """
    Elimina una tarea específica de la base de datos por su ID.
    """
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        with sqlite3.connect(RUTA_DB) as conn:
            cursor = conn.cursor()
            # Se ejecuta la sentencia DELETE para la tarea con el ID proporcionado
            cursor.execute("""
                DELETE FROM Tareas 
                WHERE id_tarea = ?""", (task_id,))
            conn.commit()
            # Verificamos si se eliminó alguna fila
            if cursor.rowcount > 0:
                return {"mensaje": f"Tarea {task_id} eliminada con éxito"}, 200
            else:
                return {"error": f"No se encontró la tarea con ID {task_id}"}, 404
    except Exception as e:
        print(f"Error en eliminar_tarea_por_id: {e}")
        return {"error": str(e)}, 500

def actualizar_tarea(id_tarea, data):
    """
    Actualiza todos los campos de una tarea existente, incluyendo su checklist.
    """
    conn = None # Definimos conn aquí para poder usarlo en el bloque except
    try:
        # Extraemos todos los campos del objeto de datos
        nombre_tarea = data.get('nombre_tarea')
        descripcion = data.get('descripcion')
        prioridad = data.get('prioridad')
        estado = data.get('estado')
        fecha_vencimiento = data.get('fecha_vencimiento')
        coordinador = data.get('coordinador')
        contratista = data.get('contratista')
        etiqueta = data.get('etiqueta')
        checklist_items = data.get('checklist', []) # Obtenemos la lista de checklist
        
        # Actualizamos la fecha de modificación al momento actual
        fecha_modificacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        cursor = conn.cursor()

        # --- Inicia la transacción ---

        # 1. Actualiza la tabla principal 'Tareas'
        query_update_tarea = """
            UPDATE Tareas
            SET
                nombre_tarea = ?, descripcion = ?, prioridad = ?,
                estado = ?, fecha_vencimiento = ?, coordinador = ?,
                contratista = ?, etiqueta = ?, fecha_modificacion = ?
            WHERE id_tarea = ?
        """
        params_tarea = (
            nombre_tarea, descripcion, prioridad, estado, 
            fecha_vencimiento, coordinador, contratista, etiqueta,
            fecha_modificacion, id_tarea
        )
        cursor.execute(query_update_tarea, params_tarea)
        
        # --- 2. Actualiza la tabla 'ChecklistItems' ---
        
        # a) Borramos todos los items antiguos asociados a esta tarea
        cursor.execute("DELETE FROM ChecklistItems WHERE id_tarea = ?", (id_tarea,))

        # b) Insertamos la nueva lista de items que viene del frontend
        if checklist_items:
            query_checklist = "INSERT INTO ChecklistItems (id_tarea, texto_item, completado) VALUES (?, ?, ?)"
            for item in checklist_items:
                # El frontend envía un objeto con 'texto' y 'completado'
                texto_item = item.get('texto_item') or item.get('texto')
                estado_completado = item.get('completado') or item.get('completada')
                completado = 1 if estado_completado else 0
                if texto_item:
                    cursor.execute(query_checklist, (id_tarea, texto_item, completado))


        # Si todo ha ido bien, confirmamos todos los cambios
        conn.commit()
        
        return {"mensaje": f"Tarea {id_tarea} actualizada con éxito"}, 200

    except Exception as e:
        if conn:
            conn.rollback() # Si algo falla, deshacemos todos los cambios
        print(f"Error en actualizar_tarea: {e}")
        return {"error": str(e)}, 500
    
    finally:
        if conn:
            conn.close()


#comentarios de modal tareas

def agregar_comentario(id_tarea, data):
    try:
        texto = data.get('texto')
        usuario = data.get('usuario', 'Usuario Actual') # O tomarlo de la sesión de usuario
        if not texto:
            return {"error": "El texto del comentario no puede estar vacío"}, 400

        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        with sqlite3.connect(RUTA_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           INSERT INTO Comentarios 
                           (tarea_id, 
                           autor, 
                           texto_comentario) 
                           VALUES (?, ?, ?)""",
                           (id_tarea, usuario, texto))
            conn.commit()
        return {"mensaje": "Comentario añadido con éxito"}, 201
    except Exception as e:
        return {"error": str(e)}, 500

def get_comentarios_por_tarea(id_tarea):
    """ Obtiene todos los comentarios para una tarea específica. """
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        with sqlite3.connect(RUTA_DB) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM Comentarios WHERE tarea_id = ? ORDER BY fecha_creacion DESC"
            cursor.execute(query, (id_tarea,))
            comentarios = [dict(row) for row in cursor.fetchall()]
        return {"comentarios": comentarios}, 200
    except Exception as e:
        return {"error": str(e)}, 500

def actualizar_comentario(id_comentario, data):
    """ Actualiza el texto de un comentario existente. """
    try:
        texto = data.get('texto')
        if not texto:
            return {"error": "El texto no puede estar vacío"}, 400
        
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        with sqlite3.connect(RUTA_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Comentarios SET texto_comentario = ? WHERE id = ?", (texto, id_comentario))
            conn.commit()
        return {"mensaje": "Comentario actualizado"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

def eliminar_comentario(id_comentario):
    """ Elimina un comentario por su ID. """
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        with sqlite3.connect(RUTA_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Comentarios WHERE id = ?", (id_comentario,))
            conn.commit()
        return {"mensaje": "Comentario eliminado"}, 200
    except Exception as e:
        return {"error": str(e)}, 500


#Notificaciones

def revisar_tareas_proximas_a_vencer(socketio_instance):
    """
    Busca tareas vencidas o próximas a vencer (5 días) y envía notificaciones
    a los usuarios correspondientes si no tienen ya una notificación sin leer.
    Esta función es llamada por el planificador diario.
    """
    print("INICIANDO REVISIÓN DIARIA DE TAREAS...")
    conn = None
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        conn.row_factory = sqlite3.Row
        
        fecha_hoy = datetime.now().date()
        fecha_limite = fecha_hoy + timedelta(days=5)

        # 1. OBTENER TAREAS RELEVANTES (VENCIDAS O PRÓXIMAS A VENCER)
        # Se une con Proyectos para obtener el coordinador y contratista.
        query_tareas = """
            SELECT 
                t.id_tarea,
                t.nombre_tarea,
                t.fecha_vencimiento,
                t.Sap,
                p.Coordinador,
                p.Contratista
            FROM Tareas t
            JOIN Proyectos p ON t.proyecto_sap = p.Sap
            WHERE t.estado != 'Completada'
                AND t.fecha_vencimiento IS NOT NULL
                AND date(t.fecha_vencimiento) <= ?
        """
        tareas_a_notificar = conn.execute(query_tareas, (fecha_limite.strftime('%Y-%m-%d'),)).fetchall()
        print(f"Se encontraron {len(tareas_a_notificar)} tareas por notificar.")

        if not tareas_a_notificar:
            return

        # 2. OBTENER TODOS LOS USUARIOS PARA FILTRAR LOCALMENTE
        usuarios = conn.execute("SELECT id, nombre_completo, contratista, role_id FROM Usuarios WHERE estado = 'activo'").fetchall()
        rol_admin_id = conn.execute("SELECT id FROM Roles WHERE nombre_rol = 'Administrador'").fetchone()['id']

        # 3. PROCESAR CADA TAREA Y DETERMINAR A QUIÉN NOTIFICAR
        for tarea in tareas_a_notificar:
            usuarios_a_notificar_ids = set()

            # Añadir a todos los administradores
            for user in usuarios:
                if user['role_id'] == rol_admin_id:
                    usuarios_a_notificar_ids.add(user['id'])
            
            # Añadir al coordinador del proyecto
            for user in usuarios:
                if user['nombre_completo'] == tarea['Coordinador']:
                    usuarios_a_notificar_ids.add(user['id'])

            # Añadir a los usuarios del contratista del proyecto
            for user in usuarios:
                if user['contratista'] == tarea['Contratista']:
                    usuarios_a_notificar_ids.add(user['id'])

            # Determinar si la tarea está vencida o por vencer para el mensaje
            fecha_vencimiento = datetime.strptime(tarea['fecha_vencimiento'], '%Y-%m-%d').date()
            dias_restantes = (fecha_vencimiento - fecha_hoy).days
            
            if dias_restantes < 0:
                mensaje = f"¡Alerta! La tarea '{tarea['nombre_tarea']}' del proyecto {tarea['proyecto_sap']} está VENCIDA."
            else:
                mensaje = f"Aviso: La tarea '{tarea['nombre_tarea']}' del proyecto {tarea['proyecto_sap']} vence en {dias_restantes} días."

            # 4. PARA CADA USUARIO, VERIFICAR Y ENVIAR NOTIFICACIÓN
            for user_id in usuarios_a_notificar_ids:
                # Verificar si ya existe una notificación NO LEÍDA para esta tarea y este usuario
                notif_existente = conn.execute("""
                    SELECT id FROM Notificaciones 
                    WHERE usuario_id = ? AND tipo = 'tarea' AND referencia_id = ? AND leido = 0
                """, (user_id, str(tarea['id_tarea']))).fetchone()

                if not notif_existente:
                    # Si no hay una notificación pendiente, creamos una nueva
                    print(f"Enviando notificación a usuario ID {user_id} por tarea ID {tarea['id_tarea']}")
                    crear_notificacion(
                        usuario_id=user_id,
                        mensaje=mensaje,
                        tipo='tarea',
                        referencia_id=str(tarea['id_tarea']),
                        socketio_instance=socketio_instance
                    )
                else:
                    print(f"Usuario ID {user_id} ya tiene una notificación pendiente para la tarea ID {tarea['id_tarea']}. Omitiendo.")

    except Exception as e:
        print(f"ERROR en la tarea programada de revisión de tareas: {e}")
    finally:
        if conn:
            conn.close()
        print("REVISIÓN DIARIA DE TAREAS FINALIZADA.")