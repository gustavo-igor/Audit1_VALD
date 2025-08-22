# Archivo: MODULES/SQLITE/CONTROLLER/proyectos_detalles.py (VERSIÓN FINAL)
import pandas as pd
import sqlite3
import os
from MODULES import rutas
from MODULES.notificaciones import crear_notificacion

def get_proyecto_details(sap_id):
    """
    Busca en la base de datos todos los detalles de un único proyecto,
    incluyendo sus coordenadas y la información del cliente.
    """
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        
        conn = sqlite3.connect(RUTA_DB)
        
        # --- CONSULTA SQL CORREGIDA Y FINAL ---
        # Une las 3 tablas usando la columna 'Sap' como pivote.
        query = """
            SELECT 
                p.*, 
                c."P. Y" AS Latitud, 
                c."P. X" AS Longitud,
                cl."Nombre Cliente",
                cl."Correo",
                cl."Fono cliente" AS "Fono Cliente"
            FROM 
                Proyectos p
            LEFT JOIN 
                Coordenadas c ON p.Sap = c.Sap
            LEFT JOIN
                Clientes cl ON p.Sap = cl.Sap  -- CORRECCIÓN: Se une usando p.Sap = cl.Sap
            WHERE 
                p.Sap = ?
        """
        
        df = pd.read_sql_query(query, conn, params=(sap_id,))
        
        conn.close()

        if df.empty:
            print(f"ADVERTENCIA: No se encontró el proyecto con SAP ID: {sap_id}")
            return None

        # Convertimos la fila a un diccionario. Pandas manejará los nombres de las columnas.
        project_details = df.iloc[0].to_dict()
        
        # Pequeño ajuste para que las claves del JSON coincidan con las que espera el JavaScript
        if "Correo" in project_details:
            project_details["Correo Cliente"] = project_details.pop("Correo")

        return project_details

    except Exception as e:
        print(f"ERROR en get_proyecto_details para SAP ID {sap_id}: {e}")
        return None


def update_proyecto_details(sap_id, data, socketio_instance):
    """
    Actualiza los detalles de un proyecto en la tabla 'Proyectos'.
    """

    COLUMN_MAP = {
        'unidad': 'Unidad',
        'linea_negocio': 'Línea de Negocio',
        'valoriza': 'Valoriza',
        'programa_inversion': 'Programa de inversión',
        'id': 'ID',
        'id_posicion': 'ID Posicion',
        'tipo_inversion': 'Tipo inversion',
        'coordinador': 'Coordinador',
        'contratista': 'Contratista',
        'estado': 'Estado'
    }
        
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        
        conn = sqlite3.connect(RUTA_DB)
        cursor = conn.cursor()

        set_clauses = []
        values = []

        for key, value in data.items():
            if key in COLUMN_MAP:
                set_clauses.append(f'"{COLUMN_MAP[key]}" = ?')
                values.append(value)

        if not set_clauses:
            return False, "No hay campos válidos para actualizar."

        query = f"UPDATE Proyectos SET {', '.join(set_clauses)} WHERE Sap = ?"
        values.append(sap_id)
        
        if 'estado' in data and data['estado'] == 'En Ejecución':
            # Aquí necesitarías obtener los IDs de los usuarios a notificar
            # (Admin, Coordinador del proyecto, Contratista del proyecto)
            # Esta es una lógica compleja que puedes desarrollar, por ahora un placeholder:
            # notificar_a_usuarios_del_proyecto(sap_id, "El proyecto ha pasado a estado 'En Ejecución'", "proyecto", sap_id, socketio_instance)
            pass


        cursor.execute(query, tuple(values))
        conn.commit()
        
        conn.close()
        
        # Verificar si la actualización tuvo efecto
        if cursor.rowcount == 0:
            return False, f"No se encontró ningún proyecto con SAP ID {sap_id} para actualizar."

        return True, "Proyecto actualizado con éxito."

    except sqlite3.Error as e:
        print(f"ERROR de base de datos en update_proyecto_details: {e}")
        return False, f"Error de base de datos: {e}"
    except Exception as e:
        print(f"ERROR en update_proyecto_details para SAP ID {sap_id}: {e}")
        return False, f"Error del servidor: {e}"
