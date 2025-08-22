import sqlite3
import os
from MODULES import rutas
import random

def get_detalle_dashboard_proyecto(sap_id):
    """
    Obtiene los datos de detalle para la tarjeta del dashboard de un proyecto.
    """
    try:
        # CONEXIÓN A LA BASE DE DATOS
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        with sqlite3.connect(RUTA_DB) as conn:
            # Lógica para consultar tus datos...
            # NOTA: Como no tenemos la tabla con estos datos específicos,
            # esta función devuelve DATOS DE EJEMPLO.
            # Deberás adaptar la consulta SQL a tu modelo de datos real.
            
            # --- EJEMPLO de cómo sería la consulta real ---
            # cursor = conn.cursor()
            # query = """
            #     SELECT p.Etapa, p.Fecha_PES, r.Plazo, r.Costo, r.Calidad, a.Fisico_Plan, a.Fisico_Real, ...
            #     FROM Proyectos p
            #     JOIN Riesgos r ON p.Sap = r.sap_proyecto
            #     JOIN Avances a ON p.Sap = a.sap_proyecto
            #     WHERE p.Sap = ?
            # """
            # cursor.execute(query, (sap_id,))
            # datos_reales = cursor.fetchone()

            # --- Datos de ejemplo que devolvemos por ahora ---
            datos_ejemplo = {
                "nombre_proyecto": f"Proyecto {sap_id}",
                "etapa_actual": "Obras",
                "fecha_pes_plan": "30/11/2025",
                "riesgo_plazo": "ok",      # ok, alerta, critico
                "riesgo_costo": "ok",
                "riesgo_calidad": "alerta",
                "avance_fisico_plan": 66,   # En porcentaje (ej: 66%)
                "avance_fisico_real": 65,
                "avance_monetario_plan_mms": 1417.2, # En MM$
                "avance_monetario_real_mms": 1428.7,
                "avance_monetario_plan_porc": 62, # En porcentaje (ej: 62%)
                "avance_monetario_real_porc": 59
            }
        return datos_ejemplo, 200

    except Exception as e:
        print(f"Error en get_detalle_dashboard_proyecto: {e}")
        return {"error": str(e)}, 500

def get_avance_financiero_general():
    """
    Obtiene los datos agregados para el gráfico de avance financiero.
    - El Plan se calcula desde la tabla 'Budget'.
    - El Real se simula con datos de ejemplo por ahora.
    """
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        cursor = conn.cursor()

        # --- 1. OBTENER DATOS PLANIFICADOS ---
        # Asumimos que el plan base es el 'Budget' del año actual (2025 en este caso)
        periodo_actual = 2025
        
        # Consulta para sumar los valores monetarios por mes para el plan
        query_plan = """
            SELECT
                strftime('%m', fecha) as mes,
                SUM(valor_monetario) as total_planificado
            FROM Budget
            WHERE
                periodo = ? AND
                outlook = 'Budget' AND
                tipo_avance = 'Monetario' AND
                valor_monetario IS NOT NULL
            GROUP BY mes
            ORDER BY mes;
        """
        cursor.execute(query_plan, (periodo_actual,))
        resultados_plan = cursor.fetchall()
        
        conn.close()

        # --- 2. PROCESAR DATOS PLANIFICADOS ---
        labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        plan_mensual = [0] * 12 # Inicializa una lista con 12 ceros

        for row in resultados_plan:
            mes_idx = int(row[0]) - 1 # El mes '01' corresponde al índice 0
            plan_mensual[mes_idx] = row[1]

        # Calcular el acumulado del plan
        plan_acumulado = []
        acumulado = 0
        for valor in plan_mensual:
            acumulado += valor
            plan_acumulado.append(acumulado)

        # --- 3. SIMULAR DATOS REALES ---
        # Generamos valores reales como una pequeña variación del plan
        real_mensual = [round(p * random.uniform(0.85, 1.1), 2) for p in plan_mensual]
        
        # Calcular el acumulado real
        real_acumulado = []
        acumulado_real = 0
        for valor in real_mensual:
            acumulado_real += valor
            real_acumulado.append(acumulado_real)

        # --- 4. CONSTRUIR RESPUESTA FINAL ---
        datos_finales = {
            "labels": labels,
            "plan_mensual": plan_mensual,
            "real_mensual": real_mensual,
            "plan_acumulado": plan_acumulado,
            "real_acumulado": real_acumulado
        }
        return datos_finales, 200

    except Exception as e:
        print(f"Error en get_avance_financiero_general: {e}")
        return {"error": str(e)}, 500

