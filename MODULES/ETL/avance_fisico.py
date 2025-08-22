import sqlite3
import os
from MODULES import rutas
import random

# --- FUNCIÓN ACTUALIZADA PARA AVANCE FÍSICO (MENSUAL) ---
def get_avance_fisico_general():
    """
    Prepara los datos para el gráfico de avance físico MENSUAL.
    - El Plan se calcula desde la tabla 'Budget'.
    - El Real se simula con datos de ejemplo por ahora.
    """
    try:
        RUTA_DB = os.path.join(rutas.convert_rutas()["ruta_script_python"], "mapa.db")
        conn = sqlite3.connect(RUTA_DB)
        cursor = conn.cursor()

        periodo_actual = 2025 # Año para el análisis
        
        # La consulta para obtener el promedio mensual sigue siendo la misma
        query_plan = """
            SELECT
                strftime('%m', fecha) as mes,
                AVG(valor_porcentual) as promedio_planificado
            FROM Budget
            WHERE
                periodo = ? AND
                outlook = 'Budget' AND
                tipo_avance = 'Fisico' AND
                valor_porcentual IS NOT NULL
            GROUP BY mes
            ORDER BY mes;
        """
        cursor.execute(query_plan, (periodo_actual,))
        resultados_plan = cursor.fetchall()
        
        conn.close()

        # --- LÓGICA MODIFICADA ---
        # 1. Procesar los resultados para obtener el plan mensual
        plan_mensual = [0.00] * 12
        for row in resultados_plan:
            mes_idx = int(row[0]) - 1
            if row[1] is not None:
                plan_mensual[mes_idx] = round(row[1] * 100, 1)
            else:
                plan_mensual[mes_idx] = 0.0
        
        # Simular el avance real mensual con una pequeña variación
        # Esta parte ahora funcionará correctamente porque 'plan_mensual' ya está en la escala 0-100.
        real_mensual = [round(p * random.uniform(0.9, 1.15), 1) for p in plan_mensual]
        real_mensual = [min(val, 100) for val in real_mensual] # Aseguramos que no pase de 100


        # 3. Preparar el diccionario final con los datos mensuales
        datos_finales = {
            "labels": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
            "plan_mensual": plan_mensual,
            "real_mensual": real_mensual
        }
        return datos_finales, 200

    except Exception as e:
        print(f"Error en get_avance_fisico_general: {e}")
        return {"error": str(e)}, 500