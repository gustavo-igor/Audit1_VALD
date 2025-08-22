# Archivo: MODULES/SQLITE/CONTROLLER/dashboard_data.py (Actualizado)

import sqlite3
import os
import random
from datetime import datetime
from MODULES import rutas

def get_detalle_dashboard_proyecto(sap_id):
    """
    Obtiene los datos de detalle para la tarjeta del dashboard de un proyecto,
    consultando las tablas Proyectos y Budget.
    """
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        conn.row_factory = sqlite3.Row # Para acceder a los datos por nombre de columna
        cursor = conn.cursor()

        query_1 = """
            SELECT Descripción, 
            Estado 
            FROM Proyectos 
            WHERE Sap = ?
        """
        # --- CONSULTA 1: OBTENER DATOS BÁSICOS DE LA TABLA 'Proyectos' ---
        cursor.execute(query_1, (sap_id,))
        proyecto_info = cursor.fetchone()

        if not proyecto_info:
            return {"error": f"Proyecto con SAP ID {sap_id} no encontrado."}, 404

        nombre_proyecto = proyecto_info['Descripción']
        etapa_actual = proyecto_info['Estado']

        # --- CONSULTA 2: OBTENER DATOS PLANIFICADOS DESDE 'Budget' (para el mes actual) ---
        hoy = datetime.now()
        periodo_actual = hoy.year
        mes_actual_str = hoy.strftime('%Y-%m-01') # Primer día del mes actual

        query_2 ="""
        SELECT valor_fecha 
        FROM Budget 
        WHERE sap_proyecto = ? 
        AND tipo_avance = 'PES' 
        AND periodo = ? 
        AND outlook = 'Budget'
            LIMIT 1
        """

        # Obtener Fecha PES Planificada
        cursor.execute(query_2, (sap_id, periodo_actual))
        pes_row = cursor.fetchone()
        fecha_pes_plan = pes_row['valor_fecha'] if pes_row else "No definido"


        query_3 = """
            SELECT valor_porcentual 
            FROM Budget 
            WHERE sap_proyecto = ? 
            AND tipo_avance = 'Fisico' 
            AND date(fecha) = ?
        """
        # Obtener Avance Físico Planificado para el mes actual
        cursor.execute(query_3, (sap_id, mes_actual_str))
        fisico_row = cursor.fetchone()
        avance_fisico_plan = fisico_row['valor_porcentual'] if fisico_row else 0

        query_4 = """
            SELECT valor_monetario 
            FROM Budget 
            WHERE sap_proyecto = ? 
            AND tipo_avance = 'Monetario' 
            AND date(fecha) = ?
        """
        # Obtener Avance Monetario Planificado para el mes actual
        cursor.execute(query_4, (sap_id, mes_actual_str))
        monetario_row = cursor.fetchone()
        # Asumimos que el valor monetario está en la misma unidad que se mostrará (MM$)
        avance_monetario_plan_mms = monetario_row['valor_monetario'] if monetario_row else 0
        
        conn.close()

        # --- DATOS SIMULADOS (REAL Y RIESGO) ---
        # Estos valores serán reemplazados cuando tengas una fuente de datos real.
        avance_fisico_real = round(avance_fisico_plan * random.uniform(0.9, 1.1), 0)
        avance_monetario_real_mms = round(avance_monetario_plan_mms * random.uniform(0.85, 1.05), 1)

        # Para el porcentaje monetario, necesitamos un plan total. Por ahora, lo simulamos.
        total_plan_monetario = avance_monetario_plan_mms * 4 # Simulación simple
        avance_monetario_plan_porc = round((avance_monetario_plan_mms / total_plan_monetario) * 100) if total_plan_monetario > 0 else 0
        avance_monetario_real_porc = round((avance_monetario_real_mms / total_plan_monetario) * 100) if total_plan_monetario > 0 else 0
        
        # Como indicaste, el usuario podría seleccionar esto. Por ahora, son fijos.
        riesgo_plazo = "ok"
        riesgo_costo = "alerta"
        riesgo_calidad = "critico"

        # --- CONSTRUCCIÓN DE LA RESPUESTA FINAL ---
        datos_finales = {
            "sap_id": sap_id,
            "nombre_proyecto": nombre_proyecto,
            "etapa_actual": etapa_actual,
            "fecha_pes_plan": fecha_pes_plan,
            "riesgo_plazo": riesgo_plazo,
            "riesgo_costo": riesgo_costo,
            "riesgo_calidad": riesgo_calidad,
            "avance_fisico_plan": avance_fisico_plan,
            "avance_fisico_real": avance_fisico_real,
            "avance_monetario_real_mms": avance_monetario_real_mms,
            "avance_monetario_plan_porc": avance_monetario_plan_porc,
            "avance_monetario_real_porc": avance_monetario_real_porc
        }
        return datos_finales, 200

    except Exception as e:
        print(f"Error en get_detalle_dashboard_proyecto: {e}")
        return {"error": str(e)}, 500

