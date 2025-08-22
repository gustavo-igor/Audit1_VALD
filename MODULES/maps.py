import jsonify, os, pandas as pd, sqlite3
from flask import Flask, request, session, redirect, url_for, render_template,jsonify 

# Importamos nuestro módulo de rutas para saber dónde está la base de datos
from MODULES import rutas

"""
def Creacion_mapas(bounds, categorias_seleccionadas=None, contratistas_seleccionados=None):
    try:

        if not categorias_seleccionadas or not contratistas_seleccionados:
            return []
        
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")

        with sqlite3.connect(RUTA_DB) as conn:
            # La consulta ahora también trae la columna 'Contratista'
            query = 
                SELECT 
                    p.Sap, 
                    p.Descripción, 
                    p.Estado,
                    p.Unidad,
                    p."Línea de Negocio", -- Las comillas son importantes para nombres con espacios
                    p.Comuna,
                    p.WF,
                    p."WF SCM",
                    p.Coordinador,
                    p.Contratista,
                    c."P. X" AS Longitud, 
                    c."P. Y" AS Latitud
                FROM Proyectos p 
                LEFT JOIN Coordenadas c ON p.Sap = c.Sap
                WHERE 
                    (CAST(c."P. Y" AS REAL) BETWEEN ? AND ?) AND 
                    (CAST(c."P. X" AS REAL) BETWEEN ? AND ?);
            
            params_tuple = (bounds['south'], bounds['north'], bounds['west'], bounds['east'])
            df_proyectos_full = pd.read_sql_query(query, conn, params=params_tuple)
        
        df_proyectos_full.dropna(subset=['Latitud', 'Longitud'], inplace=True)
        
        if df_proyectos_full.empty:
            return []

        df_proyectos_full['Categoria'] = df_proyectos_full['Estado'].apply(mapear_estado_a_categoria)

        # Se aplica el filtrado secuencial
        df_proyectos = df_proyectos_full
        if categorias_seleccionadas:
            df_proyectos = df_proyectos[df_proyectos['Categoria'].isin(categorias_seleccionadas)]
        
        # Se añade el filtro por contratista
        if contratistas_seleccionados:
            df_proyectos = df_proyectos[df_proyectos['Contratista'].isin(contratistas_seleccionados)]

        return df_proyectos.to_dict(orient='records')

    except Exception as e:
        print(f"Error en Creacion_mapas: {e}")
        return []
"""    

# Archivo: maps.py

def Creacion_mapas(bounds, categorias_seleccionadas=None, contratistas_seleccionados=None):
    try:
        # ¡IMPORTANTE! Se elimina la validación incorrecta de "if not ... or not ..."
        # Ahora la función no devolverá [] si solo uno de los filtros está vacío.
        
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")

        with sqlite3.connect(RUTA_DB) as conn:
            # Empezamos con la consulta base que trae todos los proyectos con coordenadas.
            query = """
                SELECT 
                    p.Sap, p.Descripción, p.Estado, p.Unidad,
                    p."Línea de Negocio", p.Comuna, p.WF, p."WF SCM",
                    p.Coordinador, p.Contratista,
                    c."P. X" AS Longitud, 
                    c."P. Y" AS Latitud
                FROM Proyectos p 
                LEFT JOIN Coordenadas c ON p.Sap = c.Sap
                WHERE c."P. Y" IS NOT NULL AND c."P. X" IS NOT NULL
            """
            
            params_tuple = () # Inicializamos los parámetros como una tupla vacía.

            # Si se proporcionaron límites (es decir, no es la llamada para el buscador)...
            # ...añadimos dinámicamente el filtro de límites (bounds) a la consulta.
            if bounds:
                # Se usa AND porque ya existe un WHERE en la consulta base
                query += """
                    AND (CAST(c."P. Y" AS REAL) BETWEEN ? AND ?) 
                    AND (CAST(c."P. X" AS REAL) BETWEEN ? AND ?);
                """
                params_tuple = (bounds['south'], bounds['north'], bounds['west'], bounds['east'])

            # Ejecutamos la consulta (que será diferente si vienen bounds o no)
            df_proyectos_full = pd.read_sql_query(query, conn, params=params_tuple)
        
        df_proyectos_full.dropna(subset=['Latitud', 'Longitud'], inplace=True)
        
        if df_proyectos_full.empty:
            return []

        df_proyectos_full['Categoria'] = df_proyectos_full['Estado'].apply(mapear_estado_a_categoria)

        # Tu lógica de filtrado posterior está PERFECTA y se mantiene.
        # Esta se aplica sobre el resultado de la consulta (sea completa o acotada por límites).
        df_proyectos = df_proyectos_full
        if categorias_seleccionadas:
            df_proyectos = df_proyectos[df_proyectos['Categoria'].isin(categorias_seleccionadas)]
        
        if contratistas_seleccionados:
            df_proyectos = df_proyectos[df_proyectos['Contratista'].isin(contratistas_seleccionados)]

        return df_proyectos.to_dict(orient='records')

    except Exception as e:
        print(f"Error en Creacion_mapas: {e}")
        return []

def mapear_estado_a_categoria(estado):
    """
    Toma un estado de proyecto y lo asigna a una categoría consolidada.
    """
    if not isinstance(estado, str):
        return "Sin Asignar" # Si el estado no es texto, lo asigna aquí

    # Convertimos a minúsculas y sin espacios para una comparación robusta
    estado_limpio = estado.strip().lower()

    if estado_limpio in ["puesta en servicio", "cerrado ctec", "enviado a ctec", "no ejecutado", "enviado ctec"]:
        return "Terminado"
    elif estado_limpio in ["ejecución"]:
        return "Ejecución"
    elif estado_limpio in ["solicitado", "sin asignar"]:
        return "Sin Asignar"
    elif estado_limpio in ["paralizado"]:
        return "Paralizado"
    else:
        return "Otro" # Categoría para cualquier otro estado no definido

def obtener_categorias_unicas():
    """
    Consulta la base de datos para obtener una lista de todas las
    categorías de proyecto únicas y ordenadas.
    """
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")

        with sqlite3.connect(RUTA_DB) as conn:
            # CORRECCIÓN: Seleccionamos la columna que SÍ existe en la DB: 'Estado'
            query = "SELECT DISTINCT Estado FROM Proyectos WHERE Estado IS NOT NULL;"
            df_estados = pd.read_sql_query(query, conn)

        if df_estados.empty:
            return []

        # CORRECCIÓN: Aplicamos la función de mapeo a la columna 'Estado' que hemos leído.
        # El método .unique() de pandas nos devuelve solo los valores únicos.
        categorias_unicas = df_estados['Estado'].apply(mapear_estado_a_categoria).unique()
        
        # Devolvemos la lista ordenada alfabéticamente para una mejor presentación en el panel.
        return sorted(list(categorias_unicas))

    except Exception as e:
        print(f"Error en obtener_categorias_unicas: {e}")
        return []
    
def obtener_contratistas_unicos():
    """Obtiene una lista de todos los contratistas únicos."""
    try:
        rutas_dict = rutas.convert_rutas()
        RUTA_DB = os.path.join(rutas_dict["ruta_script_python"], "mapa.db")
        with sqlite3.connect(RUTA_DB) as conn:
            query = "SELECT DISTINCT Contratista FROM Proyectos WHERE Contratista IS NOT NULL AND Contratista != '' ORDER BY Contratista"
            df = pd.read_sql_query(query, conn)
        return df['Contratista'].tolist()
    except Exception as e:
        print(f"Error en obtener_contratistas_unicos: {e}")
        return []