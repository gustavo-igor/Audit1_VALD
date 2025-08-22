import win32com.client

def iniciar_sesion_gui():
    # Iniciar SAP GUI
    sap_gui = win32com.client.GetObject("SAPGUI")
    application = sap_gui.GetScriptingEngine
    connection = application.Children(0)
    session = connection.Children(0)
    
    return session