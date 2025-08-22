import asyncio
from playwright.sync_api import sync_playwright, Playwright, Browser, Page
#from upgrade import obtener_config


def iniciar_sesion_sharepoint(page: Page, url: str, usuario: str, contraseña: str):
    page.goto(url)

    # Ingresar usuario
    page.fill("#ssousername", usuario)
    # Ingresar contraseña
    page.fill("#password", contraseña)
    # Hacer clic en el botón (imagen con onclick)
    page.click("img[name='Image11']")
    # Esperar navegacion o confirmación
    page.wait_for_load_state("networkidle")

def iniciar_navegador(headless_mode: bool = False) -> tuple[Playwright, Browser, Page]:
    print("🚀 Iniciando Playwright y lanzando el navegador...")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless_mode)
    page = browser.new_page()
    print("✅ Navegador y página listos.")
    return playwright, browser, page

def validar_credenciales_graphapi(Nombre_employee):
    #config   = obtener_config()
    nombre_empleado_a_buscar = Nombre_employee
    credenciales = next(
    #(emp for emp in config.get("employees", []) if emp.get("employee") == nombre_empleado_a_buscar),
    None
)
    if credenciales:
        usuario = credenciales.get("usuario")
        contraseña = credenciales.get("clave")
        
        print(f"✅ Credenciales encontradas para el empleado '{nombre_empleado_a_buscar}':")
        print(f"   Usuario: {usuario}")
        print(f"   Contraseña: {contraseña}")
    else:
        print(f"❌ No se encontraron credenciales para el empleado '{nombre_empleado_a_buscar}'.")
    
    return usuario,contraseña