import pandas as pd
import os

def filtrar_valdivia(nombre_archivo):
    ruta = os.path.join(r'C:\Users\abdiel.reyes\Downloads', nombre_archivo)
    
    try:
        df = pd.read_csv(ruta,skiprows=14)
    except FileNotFoundError:
        print("Archivo no encontrado.")
        return
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return

    if 'Área' not in df.columns:
        print("La columna 'Zonal' no existe en el archivo.")
        return

    # Filtrar las filas donde 'Zonal' sea 'valdivia'
    df_filtrado = df[df['Área'].str.lower() == 'valdivia']

    # Crear el nombre del archivo de salida .xlsx
    nombre_base = os.path.splitext(nombre_archivo)[0]
    nombre_salida = nombre_base + '_valdivia.xlsx'
    ruta_salida = os.path.join(r'C:\Users\abdiel.reyes\Downloads', nombre_salida)

    # Guardar como archivo Excel
    df_filtrado.to_excel(ruta_salida, index=False, engine='openpyxl')

    print(f"Archivo filtrado guardado como Excel en: {ruta_salida}")

if __name__ == "__main__":
    filtrar_valdivia('Reporte_de_ubicaciones_de_activo_en_sistema_de_red-saesa.csv')  # Reemplaza 'archivo.csv' con el nombre real
