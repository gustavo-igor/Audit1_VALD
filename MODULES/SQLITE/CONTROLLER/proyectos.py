import jsonify, os, pandas as pd, sqlite3
from flask import Flask, request, session, redirect, url_for, render_template,jsonify 

# Importamos nuestro módulo de rutas para saber dónde está la base de datos
from MODULES import rutas
from MODULES.maps import mapear_estado_a_categoria

def get_allowed_saps():
    """
    Devuelve una lista de SAPs permitidos para el usuario en sesión.
    Si es Admin, devuelve None (sin filtro).
    """
    rol = session.get('rol')
    if rol == 'Administrador':
        return None

    conn = sqlite3.connect(os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db"))
    
    saps = []
    # ▼▼▼ CAMBIO: Usamos el campo 'filtro_asociado' de la sesión ▼▼▼
    filtro = session.get('filtro_asociado')

    if rol == 'Coordinador':
        df = pd.read_sql_query("SELECT Sap FROM Proyectos WHERE Coordinador = ?", conn, params=(filtro,))
        saps = df['Sap'].tolist()

    elif rol == 'Contratista':
        df = pd.read_sql_query("SELECT Sap FROM Proyectos WHERE Contratista = ?", conn, params=(filtro,))
        saps = df['Sap'].tolist()
        
    conn.close()
    return saps


def get_Proyectos(search_params):
    """
    Recibe parámetros de búsqueda y devuelve un diccionario con los datos
    formateados como espera DataTables (server-side).
    """
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)

        # Usamos .get() para evitar errores si un parámetro no viene en la petición
        draw = search_params.get('draw', 0)
        start = search_params.get('start', 0)
        length = search_params.get('length', 10)
        
        base_query = "FROM Proyectos"
        where_clauses = []
        query_params = []

        # --- LÓGICA DE FILTROS (Tu lógica AND ya era correcta) ---
        # Se ha hecho más robusta con .get()

        text_filters = {
            'Sap': 'sap', 
            'Descripción': 'descripcion', 
            'WF': 'wf'  # El filtro 'wf' busca en la columna 'Valoriza'
        }
        for db_col, param_key in text_filters.items():
            # Usamos .get() para seguridad. Si el valor es None o "", no entra al if.
            filter_value = search_params.get(param_key)
            if filter_value:
                # Encerrar siempre los nombres de columna en "" es una buena práctica.
                where_clauses.append(f'"{db_col}" LIKE ?')
                query_params.append(f"%{filter_value}%")

        multi_select_filters = {
            'Contratista': 'contratista', 
            'Coordinador': 'coordinador', 
            'Estado': 'estado'
        }
        for db_col, param_key in multi_select_filters.items():
            filter_value = search_params.get(param_key)
            if filter_value:
                # El .split('|') genera una lista de los valores seleccionados
                values = filter_value.split('|')
                placeholders = ', '.join(['?'] * len(values))
                where_clauses.append(f'"{db_col}" IN ({placeholders})')
                query_params.extend(values)
        
        where_sql = ""
        # Esta parte construye la cláusula WHERE uniendo todas las condiciones
        # activas con "AND", logrando exactamente el comportamiento que deseas.
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)
        
        # --- FIN DE LA LÓGICA DE FILTROS ---

        # 1. Contar el total de registros en la tabla (sin filtros)
        total_records = conn.execute("SELECT COUNT(*) FROM Proyectos").fetchone()[0]

        # 2. Contar registros que coinciden con el filtro (para la paginación)
        records_filtered_query = f"SELECT COUNT(*) {base_query} {where_sql}"
        records_filtered = conn.execute(records_filtered_query, query_params).fetchone()[0]

        # 3. Obtener los datos de la página actual, con los filtros aplicados
        # Se encierran todas las columnas en "" para seguridad
        select_cols = '"Sap", "Contratista", "Coordinador", "Estado", "Descripción", "WF"'
        limit_sql = f"LIMIT ? OFFSET ?"
        final_query = f"SELECT {select_cols} {base_query} {where_sql} ORDER BY Sap {limit_sql}"
        
        # Añadimos los parámetros de limit y offset al final de la lista de parámetros
        final_query_params = query_params + [length, start]
        df_proyectos = pd.read_sql_query(final_query, conn, params=final_query_params)

        conn.close()
        
        # Aplicamos la función que ahora sí existe
        if not df_proyectos.empty and 'Estado' in df_proyectos.columns:
            df_proyectos['Categoria'] = df_proyectos['Estado'].apply(mapear_estado_a_categoria)
        else:
            # Si el dataframe está vacío, igual creamos la columna para consistencia
            df_proyectos['Categoria'] = pd.Series(dtype='str')

        df_proyectos = df_proyectos.to_dict(orient='records')
        # El formato de retorno es el que DataTables espera
        return {
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': records_filtered,
            'data': df_proyectos
        }

    except Exception as e:
        print(f"Error fatal en get_Proyectos: {e}")
        # En caso de error, devolver una respuesta válida para que DataTables no se congele
        return {
            'draw': search_params.get('draw', 0), 
            'data': [], 
            'recordsTotal': 0, 
            'recordsFiltered': 0,
            'error': str(e) # Es útil enviar el mensaje de error para depurar en el navegador
        }

def get_filter_options_data():
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")

        with sqlite3.connect(RUTA_DB) as conn:
            contratistas = pd.read_sql_query(
                "SELECT DISTINCT Contratista " \
                "FROM Proyectos " \
                "WHERE Contratista IS NOT NULL", 
                conn)['Contratista'].tolist()
            
            coordinadores = pd.read_sql_query("" \
            "SELECT DISTINCT Coordinador " \
            "FROM Proyectos " \
            "WHERE Coordinador IS NOT NULL", 
            conn)['Coordinador'].tolist()

            estados = pd.read_sql_query("" \
            "SELECT DISTINCT Estado " \
            "FROM Proyectos " \
            "WHERE Estado IS NOT NULL", 
            conn)['Estado'].tolist()

            sap = pd.read_sql_query(
                "SELECT Sap " \
                "FROM Proyectos " \
                "WHERE Sap IS NOT NULL ORDER BY Sap",
                conn)['Sap'].tolist()

            lineas_negocio = pd.read_sql_query(
                """
                SELECT DISTINCT "Línea de Negocio" 
                FROM Proyectos 
                WHERE "Línea de Negocio" IS NOT NULL 
                ORDER BY "Línea de Negocio"
                """,
                conn)['Línea de Negocio'].tolist()

        
        return {
            'contratistas': contratistas,
            'coordinadores': coordinadores,
            'estados': estados,
            'sap': sap,
            'lineas_de_negocio': lineas_negocio
        }

    except Exception as e:
        print(f"Error en /api/filter_options: {e}")
        return jsonify({}), 500

def get_proyectos_para_selector(search_term=""):
    """
    Obtiene una lista de proyectos (SAP y Nombre) para selectores,
    filtrando por un término de búsqueda.
    """
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # --- CORRECCIÓN AQUÍ ---
        # Se añade una cláusula WHERE para filtrar por SAP o por Nombre.
        # El operador LIKE con '%' busca cualquier coincidencia.
        query = """
            SELECT 
            Sap, 
            Descripción 
            FROM Proyectos 
            WHERE 
            Sap LIKE ? 
            OR Descripción LIKE ? 
            ORDER BY Sap
        """
        # El término de búsqueda se pasa como parámetro a la consulta
        params = (f'%{search_term}%', f'%{search_term}%')
        cursor.execute(query, params)
        
        proyectos = cursor.fetchall()
        conn.close()

        lista_proyectos = [{"id": row["Sap"], "text": f"{row['Sap']} - {row['Descripción']}"} for row in proyectos]
        
        return lista_proyectos

    except Exception as e:
        print(f"Error en get_proyectos_para_selector: {e}")
        return []

def get_fechas_proyecto(sap_id):
    """Obtiene el registro de fechas para un proyecto específico."""
    conn = sqlite3.connect(os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db"))
    conn.row_factory = sqlite3.Row
    
    try:
        # Buscamos las fechas asociadas al SAP ID
        fechas = conn.execute("SELECT * FROM Fechas WHERE Sap = ?", (sap_id,)).fetchone()
        
        if fechas:
            return dict(fechas), 200
        else:
            # Si no hay fechas, devolvemos un objeto vacío en lugar de un error
            return {}, 200
    except Exception as e:
        print(f"Error en get_fechas_proyecto: {e}")
        return {"error": str(e)}, 500
    finally:
        conn.close()