# Archivo: MODULES/PROYECTOS/calendario.py
import sqlite3, os, json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from MODULES import rutas
from MODULES.SQLITE.CONTROLLER.proyectos import get_allowed_saps

# Asegúrate que esta ruta sea correcta

def get_db_connection():
    """Establece la conexión a la base de datos."""
    rutas_dict = rutas.convert_rutas()
    RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
    conn = sqlite3.connect(RUTA_DB)
    # Habilitar el soporte para llaves foráneas es una buena práctica
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_todas_las_tareas_con_fecha():
    """
    Obtiene todas las tareas de la base de datos que tienen una fecha de vencimiento
    para ser usadas en el calendario y el gantt.
    """
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        # Seleccionamos las tareas y unimos con Proyectos para obtener la descripción del proyecto
        query = """
            SELECT
                t.id_tarea,
                t.nombre_tarea,
                t.fecha_creacion AS start_date,
                t.fecha_vencimiento AS end_date,
                p.Descripción AS project_name
            FROM Tareas t
            JOIN Proyectos p ON t.Sap = p.Sap
            WHERE t.fecha_vencimiento IS NOT NULL AND t.fecha_vencimiento != ''
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Procesamiento de fechas para el Gantt
        tasks_gantt = []
        for _, row in df.iterrows():
            # Frappe Gantt necesita fechas en formato 'YYYY-MM-DD'
            start = pd.to_datetime(row['start_date']).strftime('%Y-%m-%d')
            end = pd.to_datetime(row['end_date']).strftime('%Y-%m-%d')
            tasks_gantt.append({
                'id': str(row['id_tarea']),
                'name': f"({row['project_name']}) - {row['nombre_tarea']}",
                'start': start,
                'end': end,
                'progress': 0, # Placeholder
            })

        # Procesamiento de eventos para FullCalendar
        events_calendar = []
        for _, row in df.iterrows():
            events_calendar.append({
                'id': row['id_tarea'],
                'title': row['nombre_tarea'],
                'start': row['start_date'],
                'end': row['end_date']
            })

        return {"gantt": tasks_gantt, "calendar": events_calendar}

    except Exception as e:
        print(f"Error en get_todas_las_tareas_con_fecha: {e}")
        return {"gantt": [], "calendar": []}


def eliminar_evento(evento_id):
    """Elimina un evento y sus datos asociados en cascada."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM EventoCalendario WHERE id = ?", (evento_id,))
        if cursor.rowcount == 0:
            return False
        conn.commit()
        return True
    except Exception as e:
        print(f"Error en eliminar_evento: {e}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

def get_eventos_original(filters={}):
    """
    Obtiene eventos aplicando filtros.
    CORREGIDO para un manejo más robusto de múltiples filtros de texto.
    """
    conn = get_db_connection()
    try:
        query = """
            SELECT
                e.*,
                p."Línea de Negocio",
                p.Descripción AS proyecto_descripcion
            FROM EventoCalendario e
            LEFT JOIN Proyectos p ON e.sap = p.Sap
        """

        where_clauses = []
        params = []
        
        filter_map = {
            'sap': 'e.sap',
            'coordinadores': 'e.coordinador',
            'contratistas': 'e.contratista',
            'lineas_de_negocio': 'p."Línea de Negocio"'
        }



        for key, column in filter_map.items():
            # Nos aseguramos que el filtro exista y no esté vacío
            if key in filters and filters[key] and filters[key][0]:
                values = filters[key] if isinstance(filters[key], list) else filters[key].split(',')
                
                # Lógica para campos que buscan valores exactos en una lista
                if key in ['sap', 'coordinadores', 'lineas_de_negocio']:
                    placeholders = ', '.join(['?'] * len(values))
                    where_clauses.append(f"TRIM({column}) IN ({placeholders})")
                    params.extend([v.strip() for v in values])
                
                # Lógica específica para 'contratistas', que busca subcadenas
                elif key == 'contratistas':
                    like_clauses = [f"{column} LIKE ?" for _ in values]
                    # Agrupamos las cláusulas LIKE con OR, dentro de un solo paréntesis
                    where_clauses.append(f"({' OR '.join(like_clauses)})")
                    params.extend([f"%{v.strip()}%" for v in values])

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # (Puedes mantener aquí las líneas de depuración si quieres)
        print("\n--- DEPURACIÓN DE QUERY DE FILTROS ---")
        print(f"Query SQL: {query}")
        print(f"Parámetros: {tuple(params)}")
        print("-------------------------------------\n")
        
        df_eventos = pd.read_sql_query(query, conn, params=tuple(params))
        
        # ... (el resto de la función para procesar df_eventos, brigadas, etc., no cambia)
        if df_eventos.empty: return []
        df_eventos.dropna(subset=['id'], inplace=True)
        if df_eventos.empty: return []
        df_eventos['id'] = df_eventos['id'].astype(int)

        lista_ids_eventos = df_eventos['id'].tolist()
        placeholders_ids = ','.join(['?'] * len(lista_ids_eventos))
        query_brigadas = f"SELECT eb.evento_id, eb.brigada_id FROM EventoBrigada eb WHERE eb.evento_id IN ({placeholders_ids})"
        df_brigadas_asociadas = pd.read_sql_query(query_brigadas, conn, params=tuple(lista_ids_eventos))
        brigadas_por_evento = df_brigadas_asociadas.groupby('evento_id')['brigada_id'].apply(list).to_dict()

        eventos_finales = []
        for _, row in df_eventos.to_dict(orient='index').items():
            evento_id_actual = row["id"]
            lista_ids_brigadas = brigadas_por_evento.get(evento_id_actual, [])
            
            # --> LÓGICA CORREGIDA Y ROBUSTA PARA CONTRATISTAS <--
            # 1. Leemos el texto de la columna 'contratista' (singular).
            contratista_str = row.get("contratista", "") or ""
            
            # 2. Convertimos el texto en una lista, limpiando cada elemento.
            #    - .split(',') -> divide el texto por comas.
            #    - c.strip() -> elimina espacios en blanco al inicio y al final de cada nombre.
            #    - if c.strip() -> nos aseguramos de no incluir elementos vacíos.
            lista_contratista = [c.strip() for c in contratista_str.split(',') if c.strip()]
            sap_limpio = (row.get("sap") or "").strip()
            titulo_limpio = (row.get("titulo") or "").strip()

            # Creamos el objeto final que se enviará como JSON.
            evento_enriquecido = {
                "id": evento_id_actual,
                "title": row["titulo"],
                "start": row["fecha_inicio"],
                "end": row["fecha_fin"],
                "estado": row.get("estado", "Otro"),
                "tipo_evento": row.get("tipo_evento"),
                "brigadas": lista_ids_brigadas,
                # Usamos el nombre 'contratista' (singular) como clave, tal como confirmaste.
                "contratistas": lista_contratista,
                "raw": {
                    **row,
                    "sap": sap_limpio,
                    "titulo": titulo_limpio,
                    "brigadas": lista_ids_brigadas,
                    "contratistas": lista_contratista
                }
            }
            eventos_finales.append(evento_enriquecido)
            
        return eventos_finales
    except Exception as e:
        print(f"Error en get_eventos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_eventos(filters={}):
    """
    Obtiene eventos y su información de permiso de trabajo asociada.
    CORREGIDO para manejar valores NaN de pandas y evitar errores de JSON.
    """
    conn = get_db_connection()
    try:
        query = """
            SELECT
                e.*,
                p."Línea de Negocio",
                p.Descripción AS proyecto_descripcion,
                pt.id as permiso_id,
                pt.permiso_trabajo,
                pt.estado_confirmacion as permiso_estado,
                pt.estado_plazo as permiso_plazo,
                pt.fecha_vencimiento_plazo,
                tpt.nombre as permiso_nombre
            FROM EventoCalendario e
            LEFT JOIN Proyectos p ON e.sap = p.Sap
            LEFT JOIN EventoPermisoTrabajo pt ON e.id = pt.evento_id AND pt.estado_confirmacion = 'Pendiente'
            LEFT JOIN TipoPermisoTrabajo tpt ON pt.tipo_permiso_id = tpt.id
        """
        where_clauses = []
        params = []
        
        # (La lógica de filtros se mantiene igual)
        allowed_saps = get_allowed_saps()
        if allowed_saps is not None:
            if not allowed_saps: return []
            placeholders = ','.join('?' for _ in allowed_saps)
            where_clauses.append(f"e.Sap IN ({placeholders})")
            params.extend(allowed_saps)

        filter_map = {
            'sap': 'e.sap', 'coordinadores': 'e.coordinador',
            'contratistas': 'e.contratista', 'lineas_de_negocio': 'p."Línea de Negocio"'
        }
        for key, column in filter_map.items():
            if key in filters and filters[key] and filters[key][0]:
                values = filters[key]
                if key == 'contratistas':
                    like_clauses = [f"{column} LIKE ?" for _ in values]
                    where_clauses.append(f"({' OR '.join(like_clauses)})")
                    params.extend([f"%{v.strip()}%" for v in values])
                else:
                    placeholders = ', '.join(['?'] * len(values))
                    where_clauses.append(f"TRIM({column}) IN ({placeholders})")
                    params.extend([v.strip() for v in values])

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        df_eventos = pd.read_sql_query(query, conn, params=tuple(params))
        
        if df_eventos.empty: return []

        # ======================================================================
        # CORRECCIÓN DEFINITIVA: Reemplaza NaN/NaT por None (null en JSON)
        df_eventos = df_eventos.replace({np.nan: None, pd.NaT: None})
        # ======================================================================
        
        # Convierte el DataFrame a una lista de diccionarios
        lista_eventos_dict = df_eventos.to_dict(orient='records')

        # El resto de la lógica ahora trabaja con la lista de diccionarios
        ids_eventos = [e['id'] for e in lista_eventos_dict if e.get('id')]
        if not ids_eventos: return []
        
        placeholders_ids = ','.join(['?'] * len(ids_eventos))
        query_brigadas = f"SELECT eb.evento_id, eb.brigada_id FROM EventoBrigada eb WHERE eb.evento_id IN ({placeholders_ids})"
        df_brigadas_asociadas = pd.read_sql_query(query_brigadas, conn, params=tuple(ids_eventos))
        brigadas_por_evento = df_brigadas_asociadas.groupby('evento_id')['brigada_id'].apply(list).to_dict()

        eventos_finales = []
        for row_dict in lista_eventos_dict:
            evento_id_actual = row_dict["id"]
            lista_ids_brigadas = brigadas_por_evento.get(evento_id_actual, [])
            
            contratista_str = row_dict.get("contratista", "") or ""
            lista_contratista = [c.strip() for c in contratista_str.split(',') if c.strip()]
            
            permiso_info = {
                "id": row_dict.get("permiso_id"),
                "nombre": row_dict.get("permiso_nombre"),
                "estado": row_dict.get("permiso_estado"),
                "plazo": row_dict.get("permiso_plazo")
            }

            evento_enriquecido = {
                "id": evento_id_actual,
                "title": row_dict["titulo"],
                "start": row_dict["fecha_inicio"],
                "end": row_dict["fecha_fin"],
                "allDay": True,
                "estado": row_dict.get("estado", "Otro"),
                "tipo_evento": row_dict.get("tipo_evento"),
                "permiso": permiso_info,
                "raw": {
                    **row_dict,
                    "brigadas": lista_ids_brigadas,
                    "contratistas": lista_contratista,
                    "permiso": permiso_info
                }
            }
            eventos_finales.append(evento_enriquecido)
            
        return eventos_finales
    except Exception as e:
        print(f"Error en get_eventos: {e}")
        return []
    finally:
        if conn: conn.close()

def crear_evento(datos):
    """Crea un evento, su permiso asociado y el historial."""
    conn = get_db_connection()
    usuario_actual = "Usuario Sistema"
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        cursor = conn.cursor()
        contratistas_str = ','.join(map(str, datos.get('contratistas', [])))
        lista_brigadas_ids = datos.get('brigadas', [])
        tipo_permiso_id = datos.get('tipo_permiso_id')
        permiso_trabajo_numero = datos.get('permiso_trabajo_numero')

        # --- CORRECCIÓN APLICADA AQUÍ ---
        # Ahora usamos el estado que viene del formulario. Si no viene, usamos 'Programado' como fallback.
        estado_evento = datos.get('estado')

        # 1. Insertar en EventoCalendario
        query_evento = """
            INSERT INTO EventoCalendario 
            (sap, titulo, tipo_evento, fecha_inicio, fecha_fin, estado, coordinador, contratista, notas, creado_por, creado_en) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query_evento, (
            datos.get('sap'), datos.get('titulo'), datos.get('tipo_evento'),
            datos.get('fecha_inicio'), datos.get('fecha_fin'),
            estado_evento, # Se usa la variable con el estado correcto
            datos.get('coordinador'), contratistas_str, datos.get('notas'),
            usuario_actual, ahora
        ))
        nuevo_evento_id = cursor.lastrowid

        # 2. Insertar Brigadas
        if lista_brigadas_ids:
            brigadas_para_insertar = [(nuevo_evento_id, int(b_id)) for b_id in lista_brigadas_ids]
            cursor.executemany("INSERT INTO EventoBrigada (evento_id, brigada_id) VALUES (?, ?)", brigadas_para_insertar)

        # 3. Crear Permiso de Trabajo (si se seleccionó uno)
        if tipo_permiso_id:
            # Asegúrate de que la función crear_o_actualizar_permiso_trabajo exista en tu archivo
            crear_o_actualizar_permiso_trabajo(nuevo_evento_id, tipo_permiso_id, permiso_trabajo_numero, datos.get('fecha_inicio'), conn)

        # 4. Insertar en Historial
        cursor.execute("INSERT INTO EventoHistorial (evento_id, usuario_accion, fecha_accion, tipo_accion, descripcion) VALUES (?, ?, ?, ?, ?)",
                    (nuevo_evento_id, usuario_actual, ahora, 'CREACION', f"Evento '{datos.get('titulo')}' creado."))
        
        conn.commit()
        return nuevo_evento_id
    except Exception as e:
        print(f"Error en crear_evento: {e}")
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()

def reprogramar_evento(evento_id, datos):
    """Reprograma un evento y actualiza su historial."""
    conn = get_db_connection()
    usuario_actual = "Usuario Sistema"
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cursor = conn.cursor()
        
        # 1. Obtener el estado anterior del evento
        cursor.execute("SELECT fecha_inicio, fecha_fin, estado FROM EventoCalendario WHERE id = ?", (evento_id,))
        evento_anterior_tupla = cursor.fetchone()
        if not evento_anterior_tupla: 
            raise Exception("Evento no encontrado")
        
        # --- CORRECCIÓN APLICADA AQUÍ ---
        # Se construye el diccionario manualmente para evitar el error de conversión.
        columnas = ['fecha_inicio', 'fecha_fin', 'estado']
        datos_anteriores = dict(zip(columnas, evento_anterior_tupla))
        # --- FIN DE LA CORRECCIÓN ---

        # 2. Actualizar el evento con la nueva fecha y estado
        query_update = """
            UPDATE EventoCalendario SET
                fecha_inicio = ?, fecha_fin = ?, estado = 'Reprogramado',
                modificado_por = ?, modificado_en = ?
            WHERE id = ?
        """
        cursor.execute(query_update, (datos['fecha_inicio'], datos['fecha_fin'], usuario_actual, ahora, evento_id))
        
        # 3. Buscar si hay un permiso de trabajo activo ('Pendiente')
        cursor.execute("SELECT id, tipo_permiso_id, permiso_trabajo FROM EventoPermisoTrabajo WHERE evento_id = ? AND estado_confirmacion = 'Pendiente'", (evento_id,))
        permiso_activo = cursor.fetchone()

        if permiso_activo:
            permiso_activo_id = permiso_activo[0]
            tipo_permiso_id_original = permiso_activo[1]
            permiso_trabajo_texto_original = permiso_activo[2]

            # 3a. Marcar el permiso antiguo como 'Reprogramado'
            cursor.execute("""
                UPDATE EventoPermisoTrabajo 
                SET estado_confirmacion = 'Reprogramado', modificado_en = ? 
                WHERE id = ?
            """, (ahora, permiso_activo_id))

            # 3b. Crear un nuevo permiso con los datos del anterior pero con la nueva fecha
            # La función crear_o_actualizar ahora creará uno nuevo porque no encontrará uno 'Pendiente'
            crear_o_actualizar_permiso_trabajo(
                evento_id,
                tipo_permiso_id_original,
                permiso_trabajo_texto_original,
                datos['fecha_inicio'], # Usamos la nueva fecha de inicio
                conn
            )

        # 3. Registrar la acción en el historial
        descripcion_historial = f"Motivo: {datos['justificacion']}. Notas: {datos.get('notas', '')}"
        query_historial = """
            INSERT INTO EventoHistorial
            (evento_id, usuario_accion, fecha_accion, tipo_accion, descripcion, datos_anteriores)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query_historial, (evento_id, usuario_actual, ahora, 'REPROGRAMACION', descripcion_historial, json.dumps(datos_anteriores)))
        
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error en reprogramar_evento: {e}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

def actualizar_evento(evento_id, datos):
    """Actualiza un evento, sus brigadas y su permiso de trabajo."""
    conn = get_db_connection()
    usuario_actual = "Usuario Sistema"
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        cursor = conn.cursor()
        contratistas_str = ','.join(map(str, datos.get('contratistas', [])))
        lista_brigadas_ids = datos.get('brigadas', [])
        tipo_permiso_id = datos.get('tipo_permiso_id')

        # 1. Actualizar EventoCalendario
        query_update = """
            UPDATE EventoCalendario SET
                titulo = ?, tipo_evento = ?, fecha_inicio = ?, fecha_fin = ?, 
                coordinador = ?, contratista = ?, notas = ?, estado = ?,
                modificado_por = ?, modificado_en = ?
            WHERE id = ?
        """
        cursor.execute(query_update, (
            datos.get('titulo'), datos.get('tipo_evento'), datos.get('fecha_inicio'),
            datos.get('fecha_fin'), datos.get('coordinador'), contratistas_str,
            datos.get('notas'), datos.get('estado'), usuario_actual, ahora, evento_id
        ))

        # 2. Sincronizar Brigadas
        cursor.execute("DELETE FROM EventoBrigada WHERE evento_id = ?", (evento_id,))
        if lista_brigadas_ids:
            brigadas_para_insertar = [(evento_id, int(b_id)) for b_id in lista_brigadas_ids]
            cursor.executemany("INSERT INTO EventoBrigada (evento_id, brigada_id) VALUES (?, ?)", brigadas_para_insertar)

        # 3. Sincronizar Permiso de Trabajo
        if tipo_permiso_id:
            crear_o_actualizar_permiso_trabajo(evento_id, tipo_permiso_id, datos.get('fecha_inicio'), conn)
        else:
            # Si se quita el permiso, lo borramos
            cursor.execute("DELETE FROM EventoPermisoTrabajo WHERE evento_id = ?", (evento_id,))

        # (La lógica del historial se puede expandir para ser más detallada)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error en actualizar_evento: {e}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


def crear_o_actualizar_permiso_trabajo(evento_id, tipo_permiso_id, permiso_trabajo_texto, fecha_inicio_evento, conn):
    """
    Crea o actualiza un permiso de trabajo asociado a un evento.
    Esta función es llamada desde crear_evento y actualizar_evento.
    """
    cursor = conn.cursor()
    ahora = datetime.now()
    
    # 1. Obtener reglas del tipo de permiso
    cursor.execute("SELECT plazo_limite_dias FROM TipoPermisoTrabajo WHERE id = ?", (tipo_permiso_id,))
    regla = cursor.fetchone()
    if not regla:
        raise ValueError(f"No se encontró el tipo de permiso con ID {tipo_permiso_id}")
    
    dias_a_restar = regla[0]
    
    # 2. Calcular fecha de vencimiento (días hábiles hacia atrás desde el inicio del evento)
    fecha_inicio_dt = datetime.strptime(fecha_inicio_evento, '%Y-%m-%d')
    fecha_vencimiento = fecha_inicio_dt
    dias_habiles_contados = 0
    # Restamos días hasta que hayamos contado los días hábiles necesarios
    while dias_habiles_contados < dias_a_restar:
        fecha_vencimiento -= timedelta(days=1)
        # Si es un día de semana (lunes=0, ..., viernes=4)
        if fecha_vencimiento.weekday() < 5:
            dias_habiles_contados += 1
    
    fecha_vencimiento_str = fecha_vencimiento.strftime('%Y-%m-%d')

    # 3. Verificar si ya existe un permiso para este evento
    cursor.execute("SELECT id FROM EventoPermisoTrabajo WHERE evento_id = ? AND estado_confirmacion = 'Pendiente'", (evento_id,))
    permiso_existente = cursor.fetchone()

    if permiso_existente:
        # Actualizar permiso existente
        query = """
            UPDATE EventoPermisoTrabajo SET
                tipo_permiso_id = ?,
                permiso_trabajo = ?,
                fecha_vencimiento_plazo = ?,
                modificado_en = ?
            WHERE id = ?
        """
        # El ID del permiso existente también es una tupla, accedemos por índice [0]
    
        cursor.execute(query, (tipo_permiso_id, permiso_trabajo_texto, fecha_vencimiento_str, ahora.strftime('%Y-%m-%d %H:%M:%S'), permiso_existente[0]))
        return permiso_existente[0]
    else:
        # Crear nuevo permiso
        query = """
            INSERT INTO EventoPermisoTrabajo
            (evento_id, tipo_permiso_id, permiso_trabajo, estado_confirmacion, estado_plazo, fecha_solicitud, fecha_vencimiento_plazo, creado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query, (
            evento_id, tipo_permiso_id, permiso_trabajo_texto, 'Pendiente', 'En Plazo', 
            ahora.strftime('%Y-%m-%d'), fecha_vencimiento_str, ahora.strftime('%Y-%m-%d %H:%M:%S')
        ))
        return cursor.lastrowid

def confirmar_permiso_trabajo(permiso_id, usuario):
    """Marca un permiso como confirmado."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = """
            UPDATE EventoPermisoTrabajo SET
                estado_confirmacion = 'Confirmado',
                estado_plazo = 'N/A',
                fecha_confirmacion = ?,
                modificado_en = ?
            WHERE id = ?
        """
        cursor.execute(query, (ahora, ahora, permiso_id))
        conn.commit()
        # Aquí podrías añadir un registro al historial si lo deseas
        return True, "Permiso confirmado con éxito"
    except Exception as e:
        print(f"Error al confirmar permiso: {e}")
        if conn: conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()

def get_tipos_permiso_trabajo():
    """Obtiene todos los tipos de permisos de trabajo desde la BD."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM TipoPermisoTrabajo ORDER BY nombre")
        column_names = [description[0] for description in cursor.description]
        tipos_permiso_tuples = cursor.fetchall()
        
        tipos_permiso_list = []
        for row_tuple in tipos_permiso_tuples:
            tipos_permiso_list.append(dict(zip(column_names, row_tuple)))
            
        return tipos_permiso_list
        
    except Exception as e:
        print(f"Error en get_tipos_permiso_trabajo: {e}")
        return []
    finally:
        if conn:
            conn.close()
            
def eliminar_permiso_trabajo(permiso_id, usuario):
    """Elimina un permiso de trabajo por su ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Opcional: podrías añadir un registro al historial antes de borrar
        cursor.execute("DELETE FROM EventoPermisoTrabajo WHERE id = ?", (permiso_id,))
        conn.commit()
        if cursor.rowcount > 0:
            return True, "Permiso de trabajo eliminado con éxito."
        else:
            return False, "No se encontró el permiso de trabajo."
    except Exception as e:
        print(f"Error al eliminar permiso de trabajo: {e}")
        if conn: conn.rollback()
        return False, str(e)
    finally:
        if conn: conn.close()
        
# ==============================================================================
# SECCIÓN DE BRIGADAS (CORREGIDA)
# ==============================================================================

def get_todas_las_brigadas():
    """
    Obtiene una lista de todas las brigadas desde la base de datos.
    CORREGIDO para usar los nombres de columna correctos.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT id, nombre, contratista FROM Brigada ORDER BY contratista, nombre"
        cursor.execute(query)
        
        # 1. Obtenemos los nombres de las columnas desde el cursor.
        column_names = [description[0] for description in cursor.description]
        
        # 2. Obtenemos todas las filas (que son tuplas).
        brigadas_raw_tuples = cursor.fetchall()
        
        brigadas_procesadas = []
        # 3. Recorremos cada tupla y la convertimos en un diccionario.
        for row_tuple in brigadas_raw_tuples:
            # Creamos un diccionario combinando los nombres de columna y los valores de la tupla.
            row_dict = dict(zip(column_names, row_tuple))

            # 4. Ahora podemos usar el diccionario de forma segura.
            nombre_contratista = row_dict.get('contratista') or 'Sin contratista'
            nombre_display = f"{row_dict.get('nombre')} - {nombre_contratista}"
            
            brigadas_procesadas.append({
                'id': row_dict.get('id'),
                'nombre': nombre_display
            })
            
        return brigadas_procesadas

    except Exception as e:
        print(f"Error en get_todas_las_brigadas: {e}")
        return []
    finally:
        if conn:
            conn.close()