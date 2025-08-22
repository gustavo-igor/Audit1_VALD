import os
import msal
import requests
import pandas as pd
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import base64

load_dotenv() # Carga las variables desde el .env

# --- CONFIGURACIÓN DE LA API ---

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Files.ReadWrite", "User.Read"]


# --- FUNCIONES DE AUTENTICACIÓN ---
def _build_msal_app(cache=None):
    # Verificación crucial para asegurar que las credenciales se cargaron.
    if not all([CLIENT_ID, CLIENT_SECRET, TENANT_ID]):
        raise ValueError("Error de configuración: Faltan AZURE_CLIENT_ID, AZURE_CLIENT_SECRET o AZURE_TENANT_ID en el entorno.")
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET, token_cache=cache
    )

def get_auth_url(redirect_uri):
    msal_app = _build_msal_app()
    flow = msal_app.initiate_auth_code_flow(SCOPES, redirect_uri=redirect_uri)
    print("Contenido completo del diccionario 'flow':", flow) 
    if "error" in flow:
        raise Exception(f"Error al generar URL de Auth: {flow.get('error_description')}")
    return flow['auth_uri'], flow['state']

def get_token_from_code(code, session_state, redirect_uri):
    msal_app = _build_msal_app()
    result = msal_app.acquire_token_by_authorization_code(code, scopes=SCOPES, redirect_uri=redirect_uri)
    return result

def get_token_from_cache(serialized_cache):
    cache = msal.SerializableTokenCache()
    if serialized_cache:
        cache.deserialize(serialized_cache)
    msal_app = _build_msal_app(cache)
    accounts = msal_app.get_accounts()
    if accounts:
        result = msal_app.acquire_token_silent(SCOPES, account=accounts[0])
        return result, cache.serialize()
    return None, None

# --- FUNCIONES DE INTERACCIÓN CON EXCEL ---
def _codificar_sharing_link(sharing_url):
    url_bytes = sharing_url.encode('utf-8')
    base64_bytes = base64.b64encode(url_bytes)
    base64_string = base64_bytes.decode('utf-8')
    return base64_string.replace('+', '-').replace('/', '_').rstrip('=')

def _get_file_ids_from_sharing_link(access_token, sharing_url):
    """Función interna para obtener IDs de un enlace."""
    encoded_url = _codificar_sharing_link(sharing_url)
    endpoint = f"https://graph.microsoft.com/v1.0/shares/u!{encoded_url}"
    headers = {'Authorization': 'Bearer ' + access_token}
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    share_info = response.json()
    drive_id = share_info.get('parentReference', {}).get('driveId')
    item_id = share_info.get('id')
    return drive_id, item_id

def leer_tabla_desde_sharing_link(access_token, sharing_url, sheet_name, table_name):
    """Lee una tabla de Excel a partir de un enlace de SharePoint y la devuelve como DataFrame."""
    drive_id, item_id = _get_file_ids_from_sharing_link(access_token, sharing_url)
    if not drive_id or not item_id:
        raise Exception("No se pudieron obtener los IDs del archivo desde el enlace.")

    endpoint = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/worksheets/{sheet_name}/tables/{table_name}/range"
    headers = {'Authorization': 'Bearer ' + access_token}
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    data = response.json().get('values', [])
    
    if len(data) < 1: return pd.DataFrame()
    return pd.DataFrame(data[1:], columns=data[0])

def escribir_df_en_tabla_desde_sharing_link(access_token, df, sharing_url, sheet_name, table_name):
    """Escribe un DataFrame en una tabla de Excel usando un enlace de SharePoint."""
    drive_id, item_id = _get_file_ids_from_sharing_link(access_token, sharing_url)
    if not drive_id or not item_id:
        raise Exception("No se pudieron obtener los IDs del archivo desde el enlace.")

    # La API para actualizar las filas de una tabla es esta:
    endpoint = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/worksheets/{sheet_name}/tables/{table_name}/rows/add"
    
    headers = {'Authorization': 'Bearer ' + access_token, 'Content-Type': 'application/json'}
    
    # Primero borramos los datos existentes en la tabla para evitar duplicados
    clear_endpoint = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/worksheets/{sheet_name}/tables/{table_name}/rows/clear"
    requests.post(clear_endpoint, headers=headers)

    # Convertimos el DataFrame a una lista de listas para el cuerpo del JSON
    valores_a_escribir = df.values.tolist()
    
    # Creamos el cuerpo de la petición
    json_body = {
        "index": None, # Añade las filas al final
        "values": valores_a_escribir
    }
    
    response = requests.post(endpoint, headers=headers, json=json_body)
    response.raise_for_status()
    return True
    """
    Lee una tabla de Excel a partir de un enlace para compartir de SharePoint.

    Args:
        access_token (str): El token de acceso para la API de Graph.
        sharing_url (str): La URL completa para compartir del archivo Excel.
        sheet_name (str): El nombre de la hoja que contiene la tabla.
        table_name (str): El nombre de la Tabla de Excel a leer.

    Returns:
        Un DataFrame de Pandas con los datos, o None si ocurre un error.
    """
    try:
        # 1. Codificar el enlace para usarlo en la API
        encoded_url = _codificar_sharing_link(sharing_url)
        
        # 2. Llamar al endpoint /shares para obtener los IDs del archivo
        print(f"1. Obteniendo IDs del archivo desde el enlace de SharePoint...")
        endpoint_shares = f"https://graph.microsoft.com/v1.0/shares/u!{encoded_url}"
        
        headers = {'Authorization': 'Bearer ' + access_token}
        response_shares = requests.get(endpoint_shares, headers=headers)
        response_shares.raise_for_status()
        
        share_info = response_shares.json()
        drive_id = share_info.get('parentReference', {}).get('driveId')
        item_id = share_info.get('id')

        if not drive_id or not item_id:
            print("❌ No se pudieron obtener los IDs (driveId, itemId) desde el enlace.")
            return None
            
        print(f"   ✅ DriveID: {drive_id}, ItemID: {item_id}")

        # 3. Usar los IDs para construir el endpoint de la tabla y leerla
        print(f"2. Leyendo la tabla '{table_name}'...")
        endpoint_tabla = (
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/workbook/"
            f"worksheets/{sheet_name}/tables/{table_name}/range"
        )
        
        response_tabla = requests.get(endpoint_tabla, headers=headers)
        response_tabla.raise_for_status()
        
        data = response_tabla.json()
        valores = data.get('values', [])
        
        if len(valores) < 1:
            return pd.DataFrame()
        
        df = pd.DataFrame(valores[1:], columns=valores[0])
        return df

    except requests.exceptions.HTTPError as err:
        print(f"❌ Error en la llamada a la API de Graph: {err}")
        print(f"   Detalles: {err.response.text}")
        return None
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")
        return None

    """Escribe un DataFrame completo en una hoja de Excel, sobreescribiendo desde la celda de inicio."""
    # El endpoint para actualizar un rango.
    endpoint = f"https://graph.microsoft.com/v1.0/me/drive/root:/{file_path}:/workbook/worksheets/{sheet_name}/range(address='{celda_inicio}')/update"
    
    # Preparamos los datos en el formato que la API de Graph espera: una lista de listas.
    valores_a_escribir = [df.columns.tolist()] + df.values.tolist()
    
    json_body = {
        "values": valores_a_escribir
    }
    
    headers = {'Authorization': 'Bearer ' + access_token, 'Content-Type': 'application/json'}
    
    # La operación de escritura se hace con un método PATCH.
    response = requests.patch(endpoint, headers=headers, json=json_body)
    
    # Comprobamos si la operación fue exitosa (código de estado 200 OK)
    return response.status_code == 200