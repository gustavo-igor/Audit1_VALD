

def cpresupuesto(session,def_proyecto):

    session.findById("wnd[0]").maximize
    session.findById("wnd[0]/tbar[0]/okcd").Text = "cj20n"
    session.findById("wnd[0]").sendVKey(0)
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[1]/shell/shellcont[1]/shell").topNode = "         23"
    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[0]/shell").pressButton("OPEN")
    session.findById("wnd[1]/usr/ctxtCNPB_W_ADD_OBJ_DYN-PROJ_EXT").Text = def_proyecto
    session.findById("wnd[1]").sendVKey(0)

    Position = "000002"

    session.findById("wnd[0]/shellcont/shellcont/shell/shellcont[0]/shell/shellcont[1]/shell").selectedNode = Position

    session.findById("wnd[0]/usr/subDETAIL_AREA:SAPLCNPB_M:1010/subVIEW_AREA:SAPLCJWB:3999/tabsTABCJWB/tabpGRND/ssubSUBSCR1:SAPLCJWB:1210/subSTATUS:SAPLCJWB:0700/btnBUTTON_INFORMATION").press()
    session.findById("wnd[0]/usr/tabsTABSTRIP_0300/tabpANWS/ssubSUBSCREEN:SAPLBSVA:0302/tblSAPLBSVATC_E/radJ_STMAINT-ANWS[0,1]").Selected = True
    session.findById("wnd[0]/tbar[0]/btn[3]").press()

    session.findById("wnd[0]").sendVKey (11)
    session.findById("wnd[0]").sendVKey(15)
    