import pyperclip

from MODULES.RPA_SAP.TablaPanelControl import encontrar_tabla

def cambio_nombre(session,def_proyecto):

    nombre_archivo = "Panel.xlsm" # Nombre del archivo abierto
    nombre_hoja = "Panel Control"
    nombre_tabla = "TablaPanelControl"

    df_panel_control = encontrar_tabla(nombre_archivo,nombre_hoja,nombre_tabla)
    df_resultado = df_panel_control[df_panel_control['Sap'] == def_proyecto]

    fila_datos = df_resultado.iloc[0]
    nombre_pep = fila_datos["Cambio Nombre"]
    
    pyperclip.copy(nombre_pep)

    session.findById("wnd[0]").maximize
    session.findById("wnd[0]/tbar[0]/okcd").Text = "cj20n"
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[1]/shell/shellcont[1]/shell").topNode = "         23"
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[0]/shell").pressButton("OPEN")
    session.findById("wnd[1]/usr/ctxtCNPB_W_ADD_OBJ_DYN-PROJ_EXT").Text = def_proyecto
    session.findById("wnd[1]").sendVKey(0)


    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").selectedNode = "000001"
    session.findById("wnd[0]/usr/subDETAIL_AREA:SAPLCNPB_M:1010/subIDENTIFICATION:SAPLCJWB:3990/btnBUTTON_CHANGE_TEXT").press()
    session.findById("wnd[0]/mbar/menu[0]/menu[5]").Select()
    session.findById("wnd[1]/usr/btnSPOP-OPTION1").press()

    session.findById("wnd[0]/tbar[1]/btn[9]").press()
    session.findById("wnd[0]/tbar[0]/btn[3]").press()
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").selectedNode = "000002"
    session.findById("wnd[0]/usr/subDETAIL_AREA:SAPLCNPB_M:1010/subIDENTIFICATION:SAPLCJWB:3991/btnBUTTON_CHANGE_TEXT").press()
    session.findById("wnd[0]/mbar/menu[0]/menu[5]").Select()
    session.findById("wnd[1]/usr/btnSPOP-OPTION1").press()
    session.findById("wnd[0]/tbar[1]/btn[9]").press()
    session.findById("wnd[0]/tbar[0]/btn[3]").press()

    session.findById("wnd[0]").sendVKey(11)
    session.findById("wnd[0]").sendVKey(15)