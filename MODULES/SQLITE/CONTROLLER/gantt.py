# Archivo: MODULES/SQLITE/CONTROLLER/gantt.py

import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta

from MODULES import rutas

# Archivo: MODULES/SQLITE/CONTROLLER/gantt.py

def get_gantt_por_proyecto(sap_id):
    tasks_list = []
    links_list = []
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        with sqlite3.connect(RUTA_DB) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 1. Obtener tareas usando los nombres en español y creando alias para el frontend
            query_tasks = """
                SELECT 
                    id, 
                    texto as text, 
                    fecha_inicio as start_date, 
                    duracion as duration, 
                    progreso as progress, 
                    parent 
                FROM Gantt_Tareas 
                WHERE sap_proyecto = ?
            """
            cursor.execute(query_tasks, (sap_id,))
            for row in cursor.fetchall():
                task = dict(row)
                task['progress'] = task['progress'] / 100.0 # Convertir a decimal
                tasks_list.append(task)
            
            # 2. Obtener links
            if tasks_list:
                task_ids = [task['id'] for task in tasks_list]
                placeholders = ','.join('?' for _ in task_ids)
                query_links = f"SELECT id, source, target, type FROM Gantt_Links WHERE source IN ({placeholders})"
                cursor.execute(query_links, task_ids)
                links_list = [dict(row) for row in cursor.fetchall()]
        
        return {"data": tasks_list, "links": links_list}
    except Exception as e:
        print(f"Error en get_gantt_por_proyecto: {e}")
        return {"data": [], "links": []}

# --- CREAR TAREA O SUBTAREA ---
def crear_gantt_task(task_data):
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        
        parent = int(task_data.get('parent', 0))
        # VALIDACIÓN: Impedir crear subtareas de subtareas
        if parent != 0:
            with sqlite3.connect(RUTA_DB) as conn_check:
                cursor_check = conn_check.cursor()
                cursor_check.execute("SELECT parent FROM Gantt_Tareas WHERE id = ?", (parent,))
                padre_del_padre = cursor_check.fetchone()
                if padre_del_padre and padre_del_padre[0] != 0:
                    return False, "No se pueden crear subtareas dentro de otras subtareas."

        sap_id = task_data.get('sap_id')
        texto = task_data.get('text')
        start_date_str = task_data.get('start_date')
        duracion = int(task_data.get('duration', 1))
        progreso = int(task_data.get('progress', 0) * 100)
        
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
        end_date_obj = start_date_obj + timedelta(days=duracion)

        with sqlite3.connect(RUTA_DB) as conn:
            cursor = conn.cursor()
            query = """
                INSERT INTO Gantt_Tareas (sap_proyecto, texto, fecha_inicio, fecha_fin, duracion, progreso, parent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (sap_id, texto, start_date_obj, end_date_obj, duracion, progreso, parent))
            new_id = cursor.lastrowid
            conn.commit()
        return True, new_id
    except Exception as e:
        print(f"Error en crear_gantt_task: {e}")
        return False, str(e)

# --- ACTUALIZAR TAREA O SUBTAREA ---
def actualizar_gantt_task(task_id, data):
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        
        with sqlite3.connect(RUTA_DB) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Gantt_Tareas WHERE id = ?", (task_id,))
            current_task = cursor.fetchone()
            if not current_task: return False, "Tarea no encontrada"

            texto = data.get('text', current_task['texto'])
            start_date_str = data.get('start_date', current_task['fecha_inicio'])
            duration_val = data.get("duration")
            duracion = int(duration_val) if duration_val is not None else current_task["duracion"]
            progress_val = data.get("progress")
            progreso = int(float(progress_val) * 100) if progress_val is not None else current_task["progreso"]
            parent = data.get("parent", current_task["parent"])

            start_date_obj = datetime.strptime(start_date_str.split(" ")[0], '%Y-%m-%d')
            end_date_obj = start_date_obj + timedelta(days=duracion)
            
            query = """
                UPDATE Gantt_Tareas
                SET texto = ?, fecha_inicio = ?, fecha_fin = ?, duracion = ?, progreso = ?, parent = ?
                WHERE id = ?
            """
            cursor.execute(query, (texto, start_date_obj, end_date_obj, duracion, progreso, parent, task_id))
            conn.commit()
        return True, "Tarea actualizada"
    except Exception as e:
        print(f"Error en actualizar_gantt_task: {e}")
        return False, str(e)

# --- ELIMINAR TAREAS ---
def eliminar_gantt_batch(task_ids):
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        with sqlite3.connect(RUTA_DB) as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' for _ in task_ids)
            query = f"DELETE FROM Gantt_Tareas WHERE id IN ({placeholders})"
            cursor.execute(query, task_ids)
            conn.commit()
        return True, "Tareas eliminadas"
    except Exception as e:
        print(f"Error en eliminar_gantt_batch: {e}")
        return False, str(e)

# =======================================================
# FUNCIONES PARA DEPENDENCIAS (LINKS)
# =======================================================

def crear_gantt_link(data):
    """ Guarda una nueva dependencia en la tabla Gantt_Links. """
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        source = data.get('source')
        target = data.get('target')
        link_type = data.get('type')

        with sqlite3.connect(RUTA_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Gantt_Links (source, target, type)
                VALUES (?, ?, ?)
            """, (source, target, link_type))
            new_id = cursor.lastrowid
            conn.commit()
        return True, new_id
    except Exception as e:
        print(f"Error en crear_gantt_link: {e}")
        return False, str(e)

def actualizar_gantt_link(link_id, data):
    """ Actualiza una dependencia en la tabla Gantt_Links. """
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        source = data.get('source')
        target = data.get('target')
        link_type = data.get('type')

        with sqlite3.connect(RUTA_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Gantt_Links
                SET source = ?, target = ?, type = ?
                WHERE id = ?
            """, (source, target, link_type, link_id))
            conn.commit()
        return True, "Dependencia actualizada"
    except Exception as e:
        print(f"Error en actualizar_gantt_link: {e}")
        return False, str(e)

def eliminar_gantt_link(link_id):
    """ Elimina una dependencia de la tabla Gantt_Links. """
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        with sqlite3.connect(RUTA_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Gantt_Links WHERE id = ?", (link_id,))
            conn.commit()
        return True, "Dependencia eliminada"
    except Exception as e:
        print(f"Error en eliminar_gantt_link: {e}")
        return False, str(e)
