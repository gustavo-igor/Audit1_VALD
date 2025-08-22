import win32com.client
import pytesseract
import time
import pyautogui
import pyperclip
import os
import pygetwindow as gw
import pandas as pd
import numpy as np

from PIL import Image


def norma_liquidacion_sap(session,Sap):
    global df_ponderado
    PEP_Construccion = f"{Sap}-01-01-"
    df_ponderado = calcular_porcentajes(df_export, Sap)
    CJ20N(session, Sap, PEP_Construccion, df_ponderado)

def CJ20N(session,def_proyecto,PEP_Construccion,df_ponderado):
    global df_pep
    df_pep = pd.DataFrame()

    # 1. FILTRAR: Buscar en df_ponderado todos los elementos que comienzan con el patrón.
    print(f"🔍 Paso 1: Filtrando WBS elements que comienzan con '{PEP_Construccion}'...")
    filtro_mask = df_ponderado['WBS element'].str.startswith(PEP_Construccion, na=False)
    pep_construccion_filtrado = df_ponderado[filtro_mask].copy()
    print(pep_construccion_filtrado)

    # 2. ORDENAR: Listar los resultados de menor a mayor según el "WBS element".
    print(" ordering... Paso 2: Ordenando los resultados de menor a mayor...")
    pep_construccion_filtrado = pep_construccion_filtrado.sort_values(by='WBS element', ascending=True)
    print(pep_construccion_filtrado)

    # 3. CONSTRUIR EL NUEVO DATAFRAME: Crear un nuevo df_pep con la estructura deseada.
    print("🏗️ Paso 3: Construyendo el nuevo DataFrame 'df_pep' con los datos filtrados.")

    if pep_construccion_filtrado.empty:
        print("⚠️ No se encontraron PEP de construcción. 'df_pep' estará vacío.")
        # Creamos un DataFrame vacío con las columnas correctas
        df_pep = pd.DataFrame(columns=["Tp", "PEP", "Espacio_1", "%", "Espacio_2", "Clase", "Costo"])
    else:
        # Creamos un diccionario para mapear las columnas viejas a las nuevas
        nuevos_datos = {
            "Tp": "PEP",  # Columna sin fuente de datos, la dejamos vacía (NaN)
            "PEP": pep_construccion_filtrado['WBS element'],
            "Espacio_1": "",
            "%": pep_construccion_filtrado['%'],
            "Espacio_2": "",
            "Clase": "TOT",
            "Costo": pep_construccion_filtrado['Precio']
        }
        
        # Creamos el DataFrame final a partir del diccionario
        df_pep = pd.DataFrame(nuevos_datos)
        df_pep = df_pep.reset_index(drop=True) 

    print("\n✅ DataFrame 'df_pep' final construido:")
    print(df_pep.to_string(index=False))


    # Ingresar a transacción CJ20N
    session.findById("wnd[0]/tbar[0]/okcd").text = "cj20n"
    session.findById("wnd[0]").sendVKey(0)
    time.sleep(1)
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[1]/shell/shellcont[1]/shell").topNode = "         23"
    
    # Abrir el proyecto
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[0]/shell").pressButton("OPEN")
    session.findById("wnd[1]/usr/ctxtCNPB_W_ADD_OBJ_DYN-PROJ_EXT").text = def_proyecto
    session.findById("wnd[1]").sendVKey(0)

    # Expandir nodo principal
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").selectedNode = "000002"
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").expandNode("000002")
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").topNode = "000001"

    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").selectedNode = "000001"
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[0]/shell").pressButton("ABLM")

    
    
    Grafo = None

    for i in range(1, 201):
        position = f"{i:06d}"
    
        session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").expandNode (position)
        session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").selectedNode = (position)
        
        try:
            PEP_Name = session.findById("wnd[0]/usr/subDETAIL_AREA:SAPLCNPB_M:1010/subIDENTIFICATION:SAPLCJWB:3990/ctxtPROJ-PSPID").text
        except Exception as e:
            print("No se pudo obtener el grafo")
            try:
                PEP_Name = session.findById("wnd[0]/usr/subDETAIL_AREA:SAPLCNPB_M:1010/subIDENTIFICATION:SAPLCJWB:3991/ctxtPRPS-POSID").text
            except Exception as e:
                pass

        try:
            Grafo = session.findById("wnd[0]/usr/subDETAIL_AREA:SAPLCNPB_M:1010/subIDENTIFICATION:SAPLCOKO:2816/ctxtCAUFVD-AUFNR").Text
        except Exception as e:
            print("No se pudo obtener el grafo")
            try:
                Grafo = session.findById("wnd[0]/usr/subDETAIL_AREA:SAPLCNPB_M:1010/subIDENTIFICATION:SAPLCONW:0110/txtAFVGD-AUFNRD").Text
            except Exception as e:
                pass
    
        if PEP_Name[:17] == PEP_Construccion:
            Grafo = None  #
            continue      # 

        if Grafo is not None:
            break  # Rompe y sale completamente del bucle 'for'

        if len(PEP_Name) == 21 and PEP_Name[14:16] != "01":
            # Estas interacciones con la GUI de SAP son casi idénticas.
            session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").selectedNode = position
            session.findById("wnd[0]").sendVKey(27)  # Tecla ESC

            for FilaArray, row in df_pep.iterrows():
                print(f"   -> Procesando fila {FilaArray + 1}/{len(df_pep)}: PEP {row['PEP']}")
            # Usamos f-strings para construir las IDs de forma más limpia.
            # Asumimos que los datos en 'arr' ya son strings. Si no, conviértelos con str().
                session.findById(f"wnd[0]/usr/tblSAPLKOBSTC_RULES/ctxtCOBRB-KONTY[0,{FilaArray}]").text = row['Tp']
                session.findById(f"wnd[0]/usr/tblSAPLKOBSTC_RULES/ctxtDKOBR-EMPGE[1,{FilaArray}]").text = row['PEP']
                session.findById(f"wnd[0]/usr/tblSAPLKOBSTC_RULES/txtCOBRB-PROZS[3,{FilaArray}]").text = row['%']
                session.findById(f"wnd[0]/usr/tblSAPLKOBSTC_RULES/ctxtCOBRB-PERBZ[5,{FilaArray}]").text = row['Clase']

            session.findById("wnd[0]").sendVKey(0)
            session.findById("wnd[0]/tbar[0]/btn[3]").press()

    session.findById("wnd[0]/tbar[0]/btn[11]").press()
    session.findById("wnd[0]/tbar[0]/btn[15]").press()

def CN47N(session,proyectos, ruta):
    global df_export

    session.findById("wnd[0]/tbar[0]/okcd").text = "CN47N"
    session.findById("wnd[0]").sendVKey(0)
    time.sleep(1)

    try:
        session.findById("wnd[1]/usr/ctxtTCNT-PROF_DB").text = "000000000001"
        session.findById("wnd[0]").sendVKey(0)
    except Exception as e:
        pass
    
    try:
        session.findById("wnd[0]/usr/ctxtCN_PROJN-LOW").caretPosition = 0
    except Exception as e:
        session.findById("wnd[0]").sendVKey(15)
        session.findById("wnd[0]/tbar[0]/okcd").text = "CN47N"
        session.findById("wnd[0]").sendVKey(0)
        session.findById("wnd[0]/usr/ctxtCN_PROJN-LOW").caretPosition = 0

    session.findById("wnd[0]/usr/btn%_CN_PROJN_%_APP_%-VALU_PUSH").press()
    session.findById("wnd[1]/tbar[0]/btn[16]").press()


    portapapeles = "\n".join(proyectos)
    pyperclip.copy(portapapeles)
    Nombre_archivo ="sap.txt"
    guardar_txt(ruta,Nombre_archivo,portapapeles)

    #Importar_archivo
    session.findById("wnd[1]/tbar[0]/btn[23]").press()
    session.findById("wnd[2]/usr/ctxtDY_PATH").text = ruta
    session.findById("wnd[2]/usr/ctxtDY_FILENAME").text = Nombre_archivo
    session.findById("wnd[2]/tbar[0]/btn[0]").press()
    session.findById("wnd[1]/tbar[0]/btn[8]").press()
    session.findById("wnd[0]/usr/ctxtP_DISVAR").text = "/CDG-Ti"
    session.findById("wnd[0]/tbar[1]/btn[8]").press()

    #Guardar_archivo
    session.findById("wnd[0]/usr/cntlALVCONTAINER/shellcont/shell").pressToolbarContextButton("&MB_EXPORT")
    session.findById("wnd[0]/usr/cntlALVCONTAINER/shellcont/shell").selectContextMenuItem("&XXL")
    session.findById("wnd[1]/usr/ctxtDY_PATH").text = ruta
    session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = "export.XLSx"
    session.findById("wnd[1]/tbar[0]/btn[11]").press()
    session.findById("wnd[0]").sendVKey(15)
    time.sleep(10)

    df_export = sumar_plan_coste_norma(ruta,session)
    #

def sumar_plan_coste_norma(ruta,session):
    excel, libro = obtener_libro_abierto_export("export.xlsx")
    #libro.Save()
    libro.Close()
    ruta_completa = os.path.join(ruta, "export.xlsx")
    df_PEP = pd.read_excel(ruta_completa, sheet_name="Sheet1")

    CN52N(session,ruta)
    excel, libro = obtener_libro_abierto_export("export.xlsx")
    #libro.Save()
    libro.Close()
    ruta_completa = os.path.join(ruta, "export.xlsx")
    df_materiales = pd.read_excel(ruta_completa, sheet_name="Sheet1")

    try:
        #Analizar PEP
        df_PEP = df_PEP.copy()
        df_PEP["prefijo"] = df_PEP["WBS element"].astype(str).str[:20]
        print(df_PEP[["prefijo", "WBS element"]].head())
        print(f"💰 Paso 3: Agrupando por 'prefijo' y sumando '{"Precio"}'...")

        #resultado_PEP = df_PEP.groupby("prefijo")["Precio"].sum().reset_index()
        resultado_PEP = df_PEP.groupby("WBS element")["Precio"].sum().reset_index()

        #resultado_PEP = resultado_PEP.sort_values(by="prefijo").reset_index(drop=True)
        resultado_PEP = resultado_PEP.sort_values(by="WBS element").reset_index(drop=True)

        print(resultado_PEP.to_string(index=False))

        #analizar materiales
        df_materiales = df_materiales.copy()
        if "Ctd.en UM entrada" in df_materiales.columns and "Price/LCurrency" in df_materiales.columns:
            # Paso 2: Convertir a numérico (por si vienen como texto)
            df_materiales["Ctd.en UM entrada"] = pd.to_numeric(df_materiales["Ctd.en UM entrada"], errors="coerce")
            df_materiales["Price/LCurrency"] = pd.to_numeric(df_materiales["Price/LCurrency"], errors="coerce")

            # Paso 3: Calcular Precio
            df_materiales["Precio"] = df_materiales["Ctd.en UM entrada"] * df_materiales["Price/LCurrency"]
            df_materiales["prefijo"] = df_materiales["WBS element"].astype(str).str[:20]
            print(df_materiales[["prefijo", "WBS element"]].head())


            #resultado_materiales = df_materiales.groupby("prefijo")["Precio"].sum().reset_index()
            resultado_materiales = df_materiales.groupby("WBS element")["Precio"].sum().reset_index()

            #resultado_materiales = resultado_materiales.sort_values(by="prefijo").reset_index(drop=True)
            resultado_materiales = resultado_materiales.sort_values(by="WBS element").reset_index(drop=True)


            print("\n✅ Precio calculado correctamente. Vista previa:")
            print(df_materiales[["WBS element", "Ctd.en UM entrada", "Price/LCurrency", "Precio"]].head())
            print(resultado_materiales.to_string(index=False))
        else:
            print("❌ Las columnas necesarias no están presentes en df_materiales.")

        # Paso 1: Unir los dos DataFrames        
        df_total = pd.concat([resultado_PEP, resultado_materiales], axis=0)
        print("🧮 Uniendo resultados de PEP y materiales:")
        print(df_total.head())
        print(df_total)

        # Paso 2: Agrupar nuevamente por 'prefijo' y sumar precios
        df_final = df_total.groupby("WBS element")["Precio"].sum().reset_index()
        df_final = df_final.sort_values(by="WBS element").reset_index(drop=True)

        # Paso 3: Mostrar resultado final
        print("\n📊 Resultado final (PEP + Materiales):")
        print(df_final.to_string(index=False))

        return df_final
    except Exception as e:
        print(f"❌ Error al agrupar: {e}")
        return None

def CN52N(session,ruta):
    session.findById("wnd[0]/tbar[0]/okcd").text = "CN52N"
    session.findById("wnd[0]").sendVKey(0)
    time.sleep(1)
    session.findById("wnd[0]/usr/btn%_CN_PROJN_%_APP_%-VALU_PUSH").press()
    session.findById("wnd[1]/tbar[0]/btn[16]").press()
    session.findById("wnd[1]/tbar[0]/btn[23]").press()
    session.findById("wnd[2]/usr/ctxtDY_PATH").text = ruta
    session.findById("wnd[2]/usr/ctxtDY_FILENAME").text = "sap.txt"
    session.findById("wnd[2]").sendVKey(0)
    session.findById("wnd[1]/tbar[0]/btn[8]").press()
    session.findById("wnd[0]/usr/ctxtP_DISVAR").text = "/MATERIALES"
    session.findById("wnd[0]/tbar[1]/btn[8]").press()
    session.findById("wnd[0]/usr/cntlALVCONTAINER/shellcont/shell").pressToolbarContextButton("&MB_EXPORT")
    session.findById("wnd[0]/usr/cntlALVCONTAINER/shellcont/shell").selectContextMenuItem("&XXL")
    session.findById("wnd[1]/usr/ctxtDY_PATH").text = ruta
    session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = "export.XLSx"
    session.findById("wnd[1]").sendVKey (11)
    session.findById("wnd[0]").sendVKey(15)
    time.sleep(10)

def calcular_porcentajes(df, sap):
    df = df.copy()

    # --- PASO 0: FILTRAR POR EL PEP DE CONSTRUCCIÓN ---
    # Este es el nuevo paso clave. Buscamos las filas que contienen la extensión.
    filtro_pep_construccion = f"{sap}-01-01-"
    print(f"\n🔍 Paso 0: Filtrando filas donde 'WBS element' contiene '{filtro_pep_construccion}'...")

    # Usamos .str.contains() para buscar el texto dentro de la columna.
    # na=False asegura que los valores nulos no causen errores.
    df_calculo = df[df["WBS element"].str.contains(filtro_pep_construccion, na=False)].copy()


    if df_calculo.empty:
        print("⚠️ ¡Atención! No se encontraron filas con ese PEP de construcción. No se puede continuar.")
        return df_calculo  # Devuelve un DataFrame vacío

    print(f"✅ Se encontraron {len(df_calculo)} filas que coinciden. Procediendo con los cálculos...")

    # --- De aquí en adelante, la lógica es la misma, pero se aplica sobre 'df_calculo' ---

    # Paso 1: Calcular el GRAN TOTAL de la columna 'Precio'
    df_calculo['Precio'] = pd.to_numeric(df_calculo['Precio'])
    suma_total = df_calculo['Precio'].sum()
    print(f"\n💰 Paso 1: El Gran Total de 'Precio' es: {suma_total:,.2f}")

    if suma_total == 0:
        print("⚠️ El total del precio es 0, no se pueden calcular porcentajes.")
        df_calculo['%'] = 0
        return df_calculo

    # Paso 2: Calcular el porcentaje inicial con decimales (SIN CONVERTIR A ENTERO)
    print("\n📊 Paso 2: Calculando porcentajes iniciales (con decimales)...")
    df_calculo['%'] = (df_calculo['Precio'] / suma_total) * 100
    
    # Paso 3: Ajustar filas que tienen precio > 0 pero cuyo porcentaje redondeado sería 0
    print("\n⚙️ Paso 3: Buscando y ajustando filas con precios muy bajos...")
    # La máscara correcta: filas con precio pero cuyo % es menor a 0.5 (redondearían a 0)
    cero_mask = (df_calculo['Precio'] > 0) & (df_calculo['%'] < 0.5)
    
    if cero_mask.any():
        num_ajustados = cero_mask.sum()
        print(f"   🔧 Se encontraron {num_ajustados} fila(s) con precio muy bajo. Se ajustarán a 1% cada una.")
        
        # Asignar 1% a estas filas
        df_calculo.loc[cero_mask, '%'] = 1
        
        # El total de porcentaje que "regalamos" es igual al número de filas ajustadas
        porcentaje_regalado = num_ajustados * 1
        
        # El resto de los porcentajes debe sumar (100 - porcentaje_regalado)
        porcentaje_restante_para_distribuir = 100 - porcentaje_regalado
        
        # Sumamos el precio de las filas que NO fueron ajustadas
        total_precio_no_ajustado = df_calculo.loc[~cero_mask, 'Precio'].sum()
        
        # Recalculamos el % para las filas NO ajustadas, basándonos en el nuevo total de %
        if total_precio_no_ajustado > 0:
            df_calculo.loc[~cero_mask, '%'] = \
                (df_calculo.loc[~cero_mask, 'Precio'] / total_precio_no_ajustado) * porcentaje_restante_para_distribuir

    # Paso 4: Redondear a enteros y asegurar que la suma total sea exactamente 100
    print("\n💯 Paso 4: Redondeando y ajustando para que la suma sea exactamente 100...")
    
    # Redondeamos AHORA, al final de los cálculos proporcionales
    df_calculo['%'] = df_calculo['%'].round(0)
    
    suma_actual = df_calculo['%'].sum()
    diferencia = 100 - suma_actual
    
    if diferencia != 0:
        print(f"   Suma actual tras redondear: {suma_actual}%. Diferencia de {diferencia:.0f}%. Ajustando...")
        # Identificar el índice de la fila con el mayor porcentaje (que no fue la ajustada a 1)
        idx_mayor = df_calculo.loc[~cero_mask, '%'].idxmax()
        # Sumar la diferencia (que puede ser positiva o negativa) a esa fila
        df_calculo.loc[idx_mayor, '%'] += diferencia
    
    # Convertir la columna a entero para una presentación limpia
    df_calculo['%'] = df_calculo['%'].astype(int)

    # Paso 5: Resultado final
    print("\n✅ Resultado final del cálculo de porcentajes:")
    print(df_calculo[["WBS element", "Precio", "%"]].to_string(index=False))
    print(f"\nVerificación -> Suma final de porcentajes: {df_calculo['%'].sum()}%")

    return df_calculo

def obtener_libro_abierto_export(nombre_archivo,tiempo_maximo=100, intervalo=1):
    excel = None
    try:
        # Intento 1: Conectar con una instancia ya activa y registrada.
        print("Intentando conectar con GetActiveObject...")
        excel = win32com.client.GetActiveObject("Excel.Application")
        print("✅ Conexión exitosa con una instancia de Excel activa.")
    except Exception as e:
        # Intento 2: Si falla, usar Dispatch que es más flexible.
        print(f"⚠️ GetActiveObject falló ({e}). Intentando con Dispatch...")
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            print("✅ Conexión exitosa a través de Dispatch.")
        except Exception as e_dispatch:
            print(f"❌ Error fatal: No se pudo conectar a Excel ni con GetActiveObject ni con Dispatch: {e_dispatch}")
            return None, None

    # Si la conexión fue exitosa, ahora busca el libro.
    tiempo_esperado = 0
    while tiempo_esperado < tiempo_maximo:
        # Comprobar si hay libros abiertos. Workbooks.Count es la cantidad.
        if excel.Workbooks.Count == 0:
            print("La instancia de Excel no tiene libros abiertos. Esperando...")
        
        for wb in excel.Workbooks:
            print(f"🔍 Evaluando libro abierto: {wb.Name}")
            if nombre_archivo.lower() in wb.Name.lower():
                print(f"✅ ¡Libro encontrado!: {wb.Name}")
                return excel, wb # Retorna el objeto de la app y el libro
        
        time.sleep(intervalo)
        tiempo_esperado += intervalo
        print(f"Libro no encontrado. Reintentando... ({tiempo_esperado}s)")

    print(f"❌ No se encontró el libro '{nombre_archivo}' después de {tiempo_maximo} segundos.")
    return None, None
    
def obtener_libro_abierto(nombre_archivo):
    try:
        excel = win32com.client.GetActiveObject("Excel.Application")
        for wb in excel.Workbooks:
            print(f"🔍 Encontrado: {wb.Name}")
            if nombre_archivo.lower() in wb.Name.lower():   
                print(f"✅ Archivo encontrado: {wb.Name}")
                hoja=encontrar_hoja(wb)
                return excel, wb, hoja
        print("Archivo no encontrado entre los libros abiertos.")
        return None, None, None
    except Exception as e:
        print(f"Error al conectar con Excel: {e}")
        return None, None, None

def encontrar_hoja(libro):
    for hoja in libro.Sheets:
        if "nor" in hoja.Name.lower() and "liquid" in hoja.Name.lower():
            hoja3 = hoja
            print(f"Nombre de Hoja3: {hoja3.Name}")
            break
    return hoja3

def guardar_txt(ruta,nombre_archivo,lista_datos):
    ruta_completa = os.path.join(ruta, nombre_archivo)
    try:

        with open(ruta_completa, "w", encoding="utf-8") as archivo:
            archivo.write(lista_datos)
        print(f"Archivo '{nombre_archivo}' creado con éxito.")
    except Exception as e:
        print(f"Error al guardar archivo '{nombre_archivo}': {e}")

def pegar_y_copiar(excel,hoja_norma):
    try:
        hoja_norma.activate()
    except Exception as e:
        print(f"Error al pegar/copiar datos: {e}")

    rng_paste = hoja_norma.Range("R2")
    try:
        rng_paste.select()
    except Exception as e:
        print(f"Error al pegar/copiar datos: {e}")
    
    excel.Selection.PasteSpecial()
    last_row = hoja_norma.Cells(hoja_norma.Rows.Count, "R").End(-4162).Row  # -4162 es xlUp
    rng_copiar = hoja_norma.Range(f"R2:R{last_row}")
    rng_copiar.Copy()