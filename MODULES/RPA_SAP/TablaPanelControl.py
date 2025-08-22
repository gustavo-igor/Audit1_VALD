import win32com.client
import pandas as pd

def encontrar_tabla(nombre_archivo,nombre_hoja,nombre_tabla):

    try:
        excel_app = win32com.client.GetActiveObject("Excel.Application")
        print("✅ Conectado a la instancia de Excel activa.")


        workbook = None
        for wb in excel_app.Workbooks:
            if wb.Name == nombre_archivo:
                workbook = wb
                break
        
        if workbook is None:
            raise Exception(f"No se encontró un libro de trabajo abierto con el nombre '{nombre_archivo}'")
        
        print(f"✅ Libro de trabajo '{workbook.Name}' encontrado.")
        worksheet = workbook.Sheets(nombre_hoja)
        tabla_obj = worksheet.ListObjects(nombre_tabla)
        print(f"✅ Tabla '{tabla_obj.Name}' encontrada en la hoja '{worksheet.Name}'.")
        rango_tabla = tabla_obj.Range
        datos_tabla = rango_tabla.Value
        columnas = datos_tabla[0]
        filas_datos_tabla = datos_tabla[1:]
        
        # Creamos el DataFrame
        df_panel_control = pd.DataFrame(list(filas_datos_tabla), columns=columnas)
        print("✅ Datos de la tabla cargados exitosamente en un DataFrame de pandas.")
        
        return df_panel_control

    except Exception as e:
        print(f"❌ Error: {e}")
