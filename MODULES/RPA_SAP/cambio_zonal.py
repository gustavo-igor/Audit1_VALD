

def cambio_de_zonal(session,def_proyecto):

    session.findById("wnd[0]").maximize
    session.findById("wnd[0]/tbar[0]/okcd").Text = "cj20n"
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[1]/shell/shellcont[1]/shell").topNode = "         23"
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[0]/shell").pressButton("OPEN")
    session.findById("wnd[1]/usr/ctxtCNPB_W_ADD_OBJ_DYN-PROJ_EXT").Text = def_proyecto
    session.findById("wnd[1]").sendVKey(0)

    session.findById("wnd[0]").sendVKey (21)
    session.findById("wnd[1]/usr/subTABSTRIP:SAPLMASSINTERFACE:0118/subTABSTRIP:SAPLMASSINTERFACE:0120/tabsTBSTRP_TABLES/tabpTAB2").select()
    session.findById("wnd[2]/usr/ssubRAHMEN:SAPLCNFA:0111/subALLE_FELDER:SAPLCNFA:0130/btnSUCHEN").press()
    session.findById("wnd[3]/usr/sub:SAPLSPO4:0300/txtSVALD-VALUE[0,21]").text = "Solicitante"
    session.findById("wnd[3]").sendVKey (0)
    session.findById("wnd[2]/usr/ssubRAHMEN:SAPLCNFA:0111/subAUSWAHL:SAPLCNFA:0140/btnAUSWAEHLEN").press()
    session.findById("wnd[2]").sendVKey (0)
    session.findById("wnd[1]/usr/subTABSTRIP:SAPLMASSINTERFACE:0118/subTABSTRIP:SAPLMASSINTERFACE:0120/tabsTBSTRP_TABLES/tabpTAB2/ssubFIELDS:SAPLMASSINTERFACE:0130/sub:SAPLMASSINTERFACE:0130/ctxtMOD_FIELD-VALUE-LEFT[0,40]").text = "3"
    session.findById("wnd[1]").sendVKey (8)

    
    try:
        session.findById("wnd[0]").sendVKey (3)
        session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").selectedNode = "000001"
        session.findById("wnd[0]/usr/subDETAIL_AREA:SAPLCNPB_M:1010/subVIEW_AREA:SAPLCJWB:3998/tabsPTABSCR/tabpPGND/ssubSUBSCR2:SAPLCJWB:1205/ctxtPROJ-ASTNR").text = "3"
        session.findById("wnd[0]").sendVKey (0)

        session.findById("wnd[0]").sendVKey (11)
        #session.findById("wnd[1]/usr/btnSPOP-OPTION1").press()
    except Exception as e:
        session.findById("wnd[1]").sendVKey (12)
        session.findById("wnd[1]").sendVKey (12)
        session.findById("wnd[0]").sendVKey (15)
    
    