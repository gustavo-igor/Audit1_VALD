import os, time, xlwings as xw, pandas as pd, re
import time
from playwright.sync_api import sync_playwright, TimeoutError, Page
from flask_socketio import SocketIO, emit


from MODULES import login, rutas
from MODULES.RPA_SAP.TablaPanelControl import encontrar_tabla
from MODULES import graph_api

url_reporte = "https://frontel.sharepoint.com/sites/valoriza/SitePages/ReporteDetalle_SPBox.aspx?Proyecto="

nombre_archivo = "Panel.xlsm" # Nombre del archivo abierto
nombre_hoja = "Panel Control"
nombre_tabla = "TablaPanelControl"

def valoriza (def_proyecto):
    
    valoriza=Leer_panel_obras (def_proyecto)
    url_valoriza = f"{url_reporte}{valoriza}"
    
    return url_valoriza
    
def Leer_panel_obras (def_proyecto):
    
    df_panel_control = encontrar_tabla(nombre_archivo,nombre_hoja,nombre_tabla)

    df_resultado = df_panel_control[df_panel_control['Sap'] == def_proyecto]

    if df_resultado.empty:
        # Si el DataFrame resultante está vacío, no se encontró el ID.
        raise ValueError(f"No se encontró ninguna fila con el valor '{def_proyecto}' en la columna 'Sap'.")
    
    # Opcional: Advertir si se encontraron múltiples filas con el mismo ID
    if len(df_resultado) > 1:
        print(f"⚠️ Advertencia: Se encontraron {len(df_resultado)} filas para el Sap ID '{def_proyecto}'. Se utilizará la primera.")
    
    fila_datos = df_resultado.iloc[0]
    print("✅ Fila encontrada exitosamente.")
    
    Valoriza = str(int(fila_datos["Valoriza"]))

    return Valoriza

def esperar_login(url,correo,contraseña):
        Playwright = sync_playwright().start()
        browser = Playwright.chromium.launch(headless=False)  # headless=False para ver el navegador
        page = browser.new_page()
        page.goto(url)
        autenticado(page, browser,correo,contraseña)
        #listar_ids_de_la_pagina(page)
        try:
            # Espera hasta 60 segundos por el elemento.
            elemento_esperado = page.wait_for_selector("#NombreObra", state='visible', timeout=120000)
            print("✅ ¡Elemento encontrado y visible!")
        except TimeoutError:
            print(f"❌ Error: El elemento no apareció después de esperar 60 segundos.")
            print("Verifica el selector o si la página cargó correctamente.")
        return page,browser

def listar_ids_de_la_pagina(page):
    """
    Usa JavaScript para encontrar todos los elementos que tienen un atributo 'id',
    y devuelve una lista de ellos. Es mucho más eficiente.
    """
    elementos_con_id = page.evaluate("""
        () => {
            // 1. Selecciona solo los elementos que tienen un atributo 'id'.
            const elementos = document.querySelectorAll('[id]');
            
            // 2. Convierte la NodeList a un Array y extrae la información.
            return Array.from(elementos).map(el => {
                return {
                    id: el.id,
                    tag: el.tagName.toLowerCase(),
                    texto: el.innerText.trim().substring(0, 100) // Muestra solo los primeros 100 caracteres
                }
            // 3. Filtra los IDs que no estén vacíos (algunos elementos pueden tener id="").
            }).filter(e => e.id);
        }
    """)
    
    print("\n--- IDs encontrados en la página ---")
    for elemento in elementos_con_id:
        print(f"- ID: {elemento['id']}, Tag: <{elemento['tag']}>, Texto: '{elemento['texto']}'")
    print("----------------------------------\n")
    return elementos_con_id

def autenticado(page, browser, correo, contraseña, timeout = 120000):
    try:
            # Esperamos a que la redirección termine y aparezca el campo de email
            email_input = page.wait_for_selector("input[name='loginfmt']", state='visible', timeout = timeout)
            print("   - Rellenando email...")
            email_input.fill(correo)
            page.click("text=Siguiente")
            time.sleep(3)
            # Esperamos a que aparezca el campo de contraseña
            print("3. Esperando el campo de contraseña...")
            password_input = page.wait_for_selector("input[name='passwd']", state='visible',timeout = timeout)
            print("   - Rellenando contraseña...")
            password_input.fill(contraseña)
            page.locator("text=Iniciar sesión").click()

    except TimeoutError:
        print("❌ Error: No se pudo completar el proceso de login. La página de Microsoft no cargó como se esperaba.")
        browser.close()
        return # Salimos de la función
    
def Scrapping_valoriza(page,url):
    page.goto(url)
    Nombre_obra_id = page.wait_for_selector("#NombreObra", timeout=15000)
    Nombre_Obra = Nombre_obra_id.inner_text()

    Workflow_id = page.wait_for_selector("#Workflow", timeout=15000)
    Workflow = Workflow_id.inner_text()

    DetallePresupuesto_id = page.wait_for_selector("#DetallePresupuesto", timeout=15000)
    DetallePresupuesto = DetallePresupuesto_id.inner_text()

    spanTotalManoObra_id = page.wait_for_selector("#spanTotalManoObra_0", timeout=15000)
    TotalManoObra = spanTotalManoObra_id.inner_text()

    return Nombre_Obra, Workflow, DetallePresupuesto, TotalManoObra

def escribir_panel_obras(def_proyecto, Nombre_Obra, Workflow, DetallePresupuesto, TotalManoObra):

    emit(f"\n--- Conectando a '{nombre_archivo}' con xlwings ---")
    
    #------------ INICIO ENCONTRAR LIBRO EXCEL -------------#
    pids_antes = {app.pid for app in xw.apps}
    book = None
    try:
        book = xw.Book(nombre_archivo)
        sheet = book.sheets[nombre_hoja]
        tabla_excel = sheet.tables[nombre_tabla]
        df = tabla_excel.range.options(pd.DataFrame, index=False, header=True).value
        df['Sap'] = df['Sap'].astype(str)

        # 4. Encontrar la fila y columna para actualizar (igual que antes)
        indices_df = df.index[df['Sap'] == str(def_proyecto)].tolist()
        if not indices_df:
            print(f"❌ Error: No se encontró el Nro SAP '{def_proyecto}'.")
            return False
            
        indice_df = indices_df[0]
        primera_fila_tabla = tabla_excel.range.row
        fila_excel = primera_fila_tabla + 1 + indice_df
        
        
        encabezados = df.columns.tolist()
    #------------ FIN  ENCONTRAR LIBRO EXCEL -------------#

    #------------ INICIO SETEAR NOMBRE_OBRA -------------#
        Nombre_Obra = limpiar_Nombre_obra(Nombre_Obra)
    #------------ FIN SETEAR NOMBRE_OBRA -------------#

    #------------ INICIO PROGRAMA -------------#
        if "MV" in def_proyecto:
            programa = "S/V/RECLAMOS"
            programa_id = "S/V/RECLAMOS"
        else:
            programa, programa_id = clasificar_obra(DetallePresupuesto)
    #------------ FIN PROGRAMA -------------#

    #------------ INICIO AGREGAR DATOS A EXCEL -------------#
        col_descripcion = encabezados.index('Descripción') + 1
        sheet.range((fila_excel, col_descripcion)).value = Nombre_Obra


        if "SCM" in Workflow:
            col_workflow = encabezados.index('WF SCM') + 1
        else:
            col_workflow = encabezados.index('WF') + 1
        sheet.range((fila_excel, col_workflow)).value = Workflow


        col_programa = encabezados.index('ID') + 1
        sheet.range((fila_excel, col_programa)).value = programa

        col_programa_id = encabezados.index('ID Posicion') + 1
        sheet.range((fila_excel, col_programa_id)).value = programa_id

        col_mano_de_obra = encabezados.index('Presupuesto Mano de obra T1') + 1
        sheet.range((fila_excel, col_mano_de_obra)).value = int(TotalManoObra.replace('.', ''))

    #------------ FIN AGREGAR DATOS A EXCEL -------------#
        return True

    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante la operación con xlwings: {e}")
        return False
    finally:
        # 6. Lógica de limpieza inteligente
        if book:
            # Obtenemos el PID de la instancia de Excel a la que nos conectamos
            pid_actual = book.app.pid
            # Si el PID de nuestra instancia NO estaba en la lista original,
            # significa que nuestro script la creó, y por lo tanto, debemos cerrarla.
            if pid_actual not in pids_antes:
                print(f"Cerrando la instancia de Excel (PID: {pid_actual}) que fue iniciada por el script...")
                #book.app.quit()
            else:
                # Si la instancia ya existía, no la cerramos. Solo informamos.
                print("El libro ya estaba abierto por un usuario. No se cerrará la aplicación de Excel.")

def limpiar_Nombre_obra(Texto: str):
    rutas_dict = rutas.convert_rutas()
    DOWNLOAD_DIR = rutas_dict['ruta_guardado_MLL']
    ruta_archivo_claves = os.path.join(DOWNLOAD_DIR, "nombre_obra.txt")

    palabras_clave = []
    with open(ruta_archivo_claves, 'r', encoding='utf-8') as f:
            # Leemos cada línea, le quitamos espacios/saltos de línea y la agregamos a la lista
            for linea in f:
                palabra_limpia = linea.strip()
                if palabra_limpia: # Nos aseguramos de no agregar líneas vacías
                    palabras_clave.append(palabra_limpia)

    texto_upper = Texto.upper()

    for palabra in palabras_clave:
        # Buscamos la posición de la palabra clave
        indice = texto_upper.find(palabra)
        
        # Si la encontramos, devolvemos el texto desde esa posición en adelante
        if indice != -1:
            # Usamos el índice encontrado para cortar el string original
            return Texto[indice:].strip()
            
    # Si el bucle termina y no encontramos ninguna palabra clave,
    # devolvemos el texto original sin cambios.
    return Texto.strip()

def clasificar_obra(texto_descripcion: str) -> str:
    texto = texto_descripcion.upper()
    
    # Verificamos la presencia de las palabras clave principales
    hay_retiro_sed = "RETIRAR UNA SUBESTACIÓN" in texto
    hay_instalacion_sed = "INSTALAR UNA SUBESTACIÓN" in texto

    hay_construccion_linea = "CONSTRUIR" in texto and ("LÍNEA" in texto or "RED" in texto)
    es_media_tension = "MEDIA TENSIÓN" in texto
    es_baja_tension = "BAJA TENSIÓN" in texto

    # AUMENTO DE POTENCIA
    if hay_retiro_sed and hay_instalacion_sed:
        programa = "S/V/AUME"
        kva = extraer_kva_instalada(texto)
        programa_id = f"S/V/A_{kva}KVA"
        
        if kva:
            print(f"Potencia de la subestación instalada: {kva} KVA")
        return programa, programa_id

    # INSTALACION DE SUBESTACIÓN
    elif hay_instalacion_sed and not hay_retiro_sed:
        programa = "S/V/INSU"
        kva = extraer_kva_instalada(texto_descripcion)
        programa_id = f"S/V/I_{kva}KVA"
        if kva:
            print(f"Potencia de la subestación instalada: {kva} KVA")
        return programa, programa_id

    elif hay_construccion_linea and es_media_tension and not hay_instalacion_sed:
        programa = "S/V/EXTE"
        metros = extraer_metros_construidos(texto)
        print(f"Detectado: Extensión de Red MT de {metros} metros")
        # El ID de posición requiere una lógica de rangos (ej: E_MT50M).
        # Por ahora, generamos un ID simple para demostrar la extracción.
        programa_id = generar_id_posicion_extension(metros, "MT")
        return programa, programa_id

    # 4. EXTENSIÓN DE RED BAJA TENSIÓN (S/V/EXTE)
    elif hay_construccion_linea and es_baja_tension and not hay_instalacion_sed:
        programa = "S/V/EXTE"
        metros = extraer_metros_construidos(texto)
        print(f"Detectado: Extensión de Red BT de {metros} metros")
        programa_id = generar_id_posicion_extension(metros, "BT")
        return programa, programa_id


    return None, None

def extraer_kva_instalada(texto_descripcion: str) -> str | None:
    """
    Busca en la descripción la línea que menciona "Instalar una subestación"
    y extrae el valor de KVA usando expresiones regulares.

    Args:
        texto_descripcion (str): El texto completo de la obra.

    Returns:
        str: El valor de KVA como un string (ej: "25"), o None si no lo encuentra.
    """
    # Patrón de búsqueda:
    # - INSTALAR UNA SUBESTACIÓN: busca esta frase clave.
    # - .*: cualquier caracter.
    # - (\d+): captura uno o más dígitos (esto es el KVA que queremos).
    # - \s?KVA: un espacio opcional y la palabra KVA.
    # re.IGNORECASE hace que no importe si está en mayúsculas o minúsculas.
    patron = r"INSTALAR UNA SUBESTACIÓN.*? DE (\d+)\s?KVA"
    
    match = re.search(patron, texto_descripcion, re.IGNORECASE)
    
    if match:
        # El grupo 1 de la coincidencia es el número que capturamos (\d+)
        return match.group(1)
        
    return None # Si no hay coincidencia

def extraer_metros_construidos(texto_descripcion: str) -> int:

    """
    Busca todas las ocurrencias de "Construir X metros" y suma los metros.
    """
    # Patrón para encontrar números seguidos de "metros" después de "construir"
    patron = r"CONSTRUIR (\d+)\s?METROS"
    
    # re.findall encuentra TODAS las coincidencias y devuelve una lista de los grupos capturados
    matches = re.findall(patron, texto_descripcion, re.IGNORECASE)
    
    # Sumamos todos los metros encontrados
    total_metros = sum(int(m) for m in matches)
    
    return total_metros

def generar_id_posicion_extension(metros: int, tipo_tension: str) -> str:
    """
    Convierte una cantidad de metros en un ID de posición categórico.
    Ej: 115 metros y "BT" -> "E_BT>100M"

    Args:
        metros (int): La cantidad total de metros construidos.
        tipo_tension (str): El tipo de tensión, debe ser "MT" o "BT".

    Returns:
        str: El ID de posición categórico.
    """
    # Validamos que el tipo de tensión sea correcto para evitar errores
    if tipo_tension not in ["MT", "BT"]:
        return "TIPO_TENSION_INVALIDO"

    if metros <= 50:
        return f"S/V/E_{tipo_tension}50M"
    elif metros <= 100: # Esto cubre el rango de 51 a 100 metros
        return f"S/V/E_{tipo_tension}100M"
    else: # Cualquier valor mayor a 100
        return f"S/V/E_{tipo_tension}100M"