import win32com.client
import time
import pandas as pd
from datetime import datetime

from MODULES.RPA_SAP.TablaPanelControl import encontrar_tabla

def Programa(session, def_proyecto):

    nombre_archivo = "Panel.xlsm" # Nombre del archivo abierto
    nombre_hoja = "Panel Control"
    nombre_tabla = "TablaPanelControl"

    df_panel_control = encontrar_tabla(nombre_archivo,nombre_hoja,nombre_tabla)

    
    if df_panel_control is not None:
        try:
            # --- EL CAMBIO CLAVE ESTÁ AQUÍ ---

            # 1. Buscar la fila usando una condición en la columna "Sap"
            print(f"\n🔍 Buscando la fila donde la columna 'Sap' es igual a '{def_proyecto}'...")
            
            # Esto crea un nuevo DataFrame que contiene solo las filas que cumplen la condición.
            df_resultado = df_panel_control[df_panel_control['Sap'] == def_proyecto]

            # 2. Verificar si se encontró alguna fila
            if df_resultado.empty:
                # Si el DataFrame resultante está vacío, no se encontró el ID.
                raise ValueError(f"No se encontró ninguna fila con el valor '{def_proyecto}' en la columna 'Sap'.")
            
            # Opcional: Advertir si se encontraron múltiples filas con el mismo ID
            if len(df_resultado) > 1:
                print(f"⚠️ Advertencia: Se encontraron {len(df_resultado)} filas para el Sap ID '{def_proyecto}'. Se utilizará la primera.")
            
            # 3. Seleccionar la primera fila encontrada del resultado
            fila_datos = df_resultado.iloc[0]
            
            # --- El resto del código para extraer datos de la fila es idéntico ---
            print("✅ Fila encontrada exitosamente.")
            
            row_sap = fila_datos["Sap"]
            col_programa = fila_datos["Programa de inversión"]
            col_id = fila_datos["ID Posicion"]
            nombre_pep = fila_datos["Cambio Nombre"]

            # Imprimimos los resultados para verificar
            print(f"\n✅ Datos leídos para el Sap ID {def_proyecto}:")
            print(f"   - Sap: {row_sap}")
            print(f"   - Programa de inversión: {col_programa}")
            print(f"   - ID Posicion: {col_id}")
            print(f"   - Cambio Nombre: {nombre_pep}")

        except (KeyError, ValueError) as e:
            print(f"❌ Error en la búsqueda de datos: {e}")
    
    # Ingresar a transacción CJ20N
    session.findById("wnd[0]/tbar[0]/okcd").text = "cj20n"
    session.findById("wnd[0]").sendVKey(0)
    time.sleep(1)
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[1]/shell/shellcont[1]/shell").topNode = "         23"
    
    # Abrir el proyecto
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[0]/shell").pressButton("OPEN")
    session.findById("wnd[1]/usr/ctxtCNPB_W_ADD_OBJ_DYN-PROJ_EXT").text = def_proyecto
    session.findById("wnd[1]").sendVKey(0)

    Position = "000002"

    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").selectedNode = "000002"
    session.findById("wnd[0]").sendVKey(40)
    session.findById("wnd[1]/usr/ctxtRAIP1-PRNAM").Text = col_programa
    session.findById("wnd[1]/usr/ctxtRAIP1-POSID").Text = col_id
    session.findById("wnd[1]/usr/txtRAIP1-GJAHR").Text = datetime.now().year
    session.findById("wnd[1]/tbar[0]/btn[0]").press()
    session.findById("wnd[0]").sendVKey(11)
    session.findById("wnd[0]").sendVKey(15)


