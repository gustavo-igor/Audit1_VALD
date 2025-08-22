# Archivo: matrizriesgo.py

from flask import jsonify
from MODULES import rutas
import sqlite3, os, datetime, pandas as pd

def obtener_riesgos_por_proyecto(sap_id):
    """
    Obtiene todos los riesgos y oportunidades asociados a un SAP de proyecto.
    """
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        # Usamos 'with' para asegurar que la conexión se cierre automáticamente
        with sqlite3.connect(RUTA_DB) as conn:
            query = """
                SELECT 
                    id_riesgo, 
                    sap_proyecto, 
                    clasificacion, 
                    descripcion_riesgo,
                    comentario_descripcion, 
                    proceso, probabilidad, 
                    impacto,
                    acciones_mitigacion, 
                    responsable_area, 
                    responsable_nombre,
                    costo_acciones, 
                    fecha_implementacion, 
                    estado, 
                    comentarios_generales
                FROM MatrizRiesgo
                WHERE sap_proyecto = ?
                ORDER BY id_riesgo DESC
                """
            
            # ❗ CORRECCIÓN 1: Añadir la coma para crear una tupla (sap_id,)
            df_riesgo = pd.read_sql_query(query, conn, params=(sap_id,))
            
            lista_riesgos = df_riesgo.to_dict(orient='records')
            
            # ❗ CORRECCIÓN 2: Devolver la lista de Python directamente.
            # La ruta en app.py se encargará de hacer el jsonify.
            return lista_riesgos

    except Exception as e:
        print(f"Error en obtener_riesgos_por_proyecto: {e}")
        # Devolvemos una lista vacía en caso de error para no romper el frontend.
        return []

def obtener_riesgo_por_id(id_riesgo):
    """
    Obtiene un único riesgo por su ID.
    """
    conn = None
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        
        conn.row_factory = sqlite3.Row # Esto permite acceder a las columnas por nombre
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM MatrizRiesgo WHERE id_riesgo = ?", (id_riesgo,))
        riesgo = cursor.fetchone()
        
        if riesgo is None:
            return jsonify({'error': 'Riesgo no encontrado'}), 404
            
        return jsonify(dict(riesgo)), 200

    except Exception as e:
        print(f"Error en obtener_riesgo_por_id: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

def crear_riesgo(datos):
    """
    Crea un nuevo registro de riesgo/oportunidad en la base de datos.
    """
    conn = None
    try:

        sap_proyecto = datos.get('sap_proyecto')
        if not sap_proyecto:
            return jsonify({'error': 'El campo sap_proyecto es obligatorio'}), 400
        
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        cursor = conn.cursor()

        query = """
            INSERT INTO MatrizRiesgo (
                sap_proyecto, 
                clasificacion, 
                descripcion_riesgo, 
                comentario_descripcion,
                proceso, 
                probabilidad, 
                impacto, 
                acciones_mitigacion, 
                responsable_area,
                responsable_nombre, 
                costo_acciones, 
                fecha_implementacion, 
                estado,
                comentarios_generales
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        
        def to_int(value):
            return int(value) if value else None
            
        def to_float(value):
            return float(value) if value else None
        

        params = (
            sap_proyecto,
            datos.get('clasificacion'),
            datos.get('descripcion_riesgo'),
            datos.get('comentario_descripcion'),
            datos.get('proceso'),
            datos.get('probabilidad'),
            datos.get('impacto'),
            datos.get('acciones_mitigacion'),
            datos.get('responsable_area'),
            datos.get('responsable_nombre'),
            datos.get('costo_acciones'),
            datos.get('fecha_implementacion'),
            datos.get('estado'),
            datos.get('comentarios_generales')
        )
        
        cursor.execute(query, params)
        
        # ✅ CORRECCIÓN PRINCIPAL: Confirmar (guardar) la transacción
        conn.commit()

        nuevo_id = cursor.lastrowid
        riesgo_creado = {'id_riesgo': nuevo_id, **datos}

        return jsonify(riesgo_creado), 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error en crear_nueva_tarea: {e}")
        return {'error': str(e)}, 500
    finally:
        if conn:
            conn.close()

def actualizar_riesgo(id_riesgo, datos):
    """
    Actualiza un registro de riesgo/oportunidad existente.
    """
    conn = None
    try:
        # --- Conexión a la base de datos ---
        # rutas_dict = rutas.convert_rutas()
        # RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        RUTA_DB = "mapa.db" # Usando un path simple para el ejemplo
        conn = sqlite3.connect(RUTA_DB)
        cursor = conn.cursor()

        query = """
            UPDATE MatrizRiesgo SET
                clasificacion = ?, descripcion_riesgo = ?, comentario_descripcion = ?,
                proceso = ?, probabilidad = ?, impacto = ?, acciones_mitigacion = ?,
                responsable_area = ?, responsable_nombre = ?, costo_acciones = ?,
                fecha_implementacion = ?, estado = ?, comentarios_generales = ?
            WHERE id_riesgo = ?
            """
        
        params = (
            datos.get('clasificacion'), datos.get('descripcion_riesgo'), datos.get('comentario_descripcion'),
            datos.get('proceso'), datos.get('probabilidad'), datos.get('impacto'),
            datos.get('acciones_mitigacion'), datos.get('responsable_area'), datos.get('responsable_nombre'),
            datos.get('costo_acciones'), datos.get('fecha_implementacion'), datos.get('estado'),
            datos.get('comentarios_generales'),
            id_riesgo
        )
        
        cursor.execute(query, params)
        conn.commit()

        # ✅ **CORRECCIÓN 3: Respuesta consistente y manejo de "No encontrado"**
        # Se verifica si alguna fila fue afectada. Si no, significa que el ID no existía.
        if cursor.rowcount == 0:
            return jsonify({'error': 'Riesgo no encontrado'}), 404
        
        # Se retorna una respuesta JSON, igual que en la función de crear.
        return jsonify({'mensaje': 'Riesgo actualizado correctamente'}), 200
    
    except Exception as e:
        if conn:
            conn.rollback()
        # ✅ **CORRECCIÓN 4: Mensaje de error corregido**
        print(f"Error en actualizar_riesgo: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        # ✅ **CORRECCIÓN 5: El conn.close() debe estar en el finally**
        # Esto asegura que la conexión siempre se cierre, incluso si ocurre un error.
        if conn:
            conn.close()

def eliminar_riesgo(id_riesgo):
    """
    Elimina un registro de riesgo/oportunidad de la base de datos
    utilizando una conexión directa y manejo explícito.
    """
    conn = None
    try:
        # --- Conexión a la base de datos ---
        # Asumo que esta lógica es correcta para tu proyecto
        # rutas_dict = rutas.convert_rutas()
        # RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        RUTA_DB = "mapa.db" # Usando un path simple para el ejemplo
        conn = sqlite3.connect(RUTA_DB)
        cursor = conn.cursor()

        # Ejecutar la sentencia DELETE
        cursor.execute("DELETE FROM MatrizRiesgo WHERE id_riesgo = ?", (id_riesgo,))
        
        # Guardar los cambios en la base de datos
        conn.commit()
        
        # Verificar si alguna fila fue eliminada
        if cursor.rowcount == 0:
            return jsonify({'error': 'Riesgo no encontrado'}), 404

        return jsonify({'mensaje': 'Riesgo eliminado correctamente'}), 200

    except Exception as e:
        # Revertir cambios si ocurre un error
        if conn:
            conn.rollback()
        print(f"Error en eliminar_riesgo: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Asegurarse de que la conexión siempre se cierre
        if conn:
            conn.close()