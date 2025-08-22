# Archivo: MODULES/ETL/budget.py (VERSIÓN FINAL)

import pandas as pd
import sqlite3
import os
from datetime import datetime
import re


def procesar_y_cargar_budget(periodo, outlook='Budget'):
    """
    Lee un Excel con formato de encabezados ($) y (%), lo transforma y lo carga.
    """
    print(f"--- Iniciando ETL para presupuesto {outlook} del período {periodo} ---")
    ruta_excel = "C:\\Users\\abdiel.reyes\\OneDrive - Sociedad Austral de Electricidad S.A\\Budget.xlsx"
    ruta_db = "C:\\Users\\abdiel.reyes\\OneDrive - Sociedad Austral de Electricidad S.A\\Documentos - Panel de Obras Valdivia\\Python\\PANEL\\mapa.db"
    print(f"🗄️  Conectando a la base de datos en: {ruta_db}")

    try:
        # --- 1. EXTRACT: Leer el archivo Excel ---
        df = pd.read_excel(ruta_excel, sheet_name="Hoja1")
        print(f"Éxito: {len(df)} filas leídas del Excel.")

        # --- 2. TRANSFORM ---
        # (Toda la sección de Transformación que ya teníamos sigue siendo correcta y no necesita cambios)
        columnas_id = ['Periodo', 'Outlook', 'Sap', 'Nombre', 'Zonal', 'Empresa', 'PES Plan']
        columnas_monetarias = [col for col in df.columns if '$' in col]
        columnas_fisicas = [col for col in df.columns if '%' in col]
        df_monetario = pd.melt(df, id_vars=columnas_id, value_vars=columnas_monetarias, var_name='mes_texto', value_name='valor_monetario')
        df_monetario['tipo_avance'] = 'Monetario'
        df_fisico = pd.melt(df, id_vars=columnas_id, value_vars=columnas_fisicas, var_name='mes_texto', value_name='valor_porcentual')
        df_fisico['tipo_avance'] = 'Fisico'
        df_pes = df[columnas_id].copy()
        df_pes.rename(columns={'PES Plan': 'valor_fecha'}, inplace=True)
        df_pes['tipo_avance'] = 'PES'
        df_pes['fecha'] = pd.to_datetime(df_pes['Periodo'].astype(str) + '-01-01')
        df_monetario_y_fisico = pd.concat([df_monetario, df_fisico], ignore_index=True)
        def limpiar_nombre_mes(texto_columna):
            match = re.search(r'([A-Za-z]+)', texto_columna)
            return match.group(1) if match else None
        df_monetario_y_fisico['mes_limpio'] = df_monetario_y_fisico['mes_texto'].apply(limpiar_nombre_mes)
        mes_map = {'Ene': '01', 'Feb': '02', 'Mar': '03', 'Abr': '04', 'May': '05', 'Jun': '06', 'Jul': '07', 'Ago': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dic': '12'}
        def construir_fecha(row):
            try:
                periodo = int(row['Periodo'])
                mes_num = mes_map[row['mes_limpio'].capitalize()]
                return datetime.strptime(f"{periodo}-{mes_num}-01", "%Y-%m-%d").date()
            except: return None
        df_monetario_y_fisico['fecha'] = df_monetario_y_fisico.apply(construir_fecha, axis=1)
        df_transformado = pd.concat([df_monetario_y_fisico, df_pes], ignore_index=True)
        df_transformado.dropna(subset=['fecha'], inplace=True)
        df_transformado.dropna(subset=['valor_monetario', 'valor_porcentual', 'valor_fecha'], how='all', inplace=True)
        print(f"Transformación: Se generaron {len(df_transformado)} registros en total.")

        # --- 3. LOAD: Cargar los datos en la base de datos ---
        conn = sqlite3.connect(ruta_db)
        cursor = conn.cursor()

        # Limpieza de datos antiguos (mejorada para manejar múltiples outlooks)
        if not df_transformado.empty:
            periodo_a_limpiar = df_transformado['Periodo'].iloc[0]
            outlooks_a_limpiar = tuple(df_transformado['Outlook'].unique())
            placeholders = ','.join('?' for _ in outlooks_a_limpiar)
            query_delete = f"DELETE FROM Budget WHERE periodo = ? AND outlook IN ({placeholders})"
            params = [periodo_a_limpiar] + list(outlooks_a_limpiar)
            cursor.execute(query_delete, params)
            print(f"Se eliminaron los registros antiguos para el período {periodo_a_limpiar} y outlooks: {outlooks_a_limpiar}.")

        registros_cargados = 0
        for _, row in df_transformado.iterrows():
            # --- CORRECCIÓN AQUÍ ---
            valor_fecha_para_db = None
            # Verificamos si hay un valor en la columna 'valor_fecha'
            if pd.notna(row.get('valor_fecha')):
                try:
                    # Intentamos convertir el valor a una fecha
                    valor_fecha_para_db = pd.to_datetime(row.get('valor_fecha')).strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    # Si falla (porque es "No aplica" o cualquier otro texto),
                    # valor_fecha_para_db simplemente se queda como None.
                    pass
            
            # El resto de las conversiones se mantiene igual
            fecha_para_db = pd.to_datetime(row['fecha']).strftime('%Y-%m-%d') if pd.notna(row['fecha']) else None

            cursor.execute("""
                INSERT INTO Budget (sap_proyecto, fecha, periodo, outlook, tipo_avance, valor_monetario, valor_porcentual, valor_fecha)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['Sap'], 
                fecha_para_db,
                row['Periodo'], 
                row['Outlook'], 
                row['tipo_avance'], 
                row.get('valor_monetario'),
                row.get('valor_porcentual'),
                valor_fecha_para_db # Usamos la variable que ya manejó el error
            ))
            registros_cargados += 1
                
        conn.commit()
        conn.close()
        
        print(f"Éxito: Se cargaron {registros_cargados} registros en la tabla 'Budget'.")
        print("--- Proceso ETL finalizado ---")
        return True

    except Exception as e:
        print(f"Error durante el proceso ETL: {e}")
        return False

if __name__ == '__main__':
    periodo = 2025
    procesar_y_cargar_budget(periodo)