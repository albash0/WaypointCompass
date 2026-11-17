"""Attach locally generated connector models to the board and library.

Legacy generator for cable headers. Supplied module STEP models and direct
headers are attached by attach_module_models.py when module_models.json exists.
"""
import json
from build_carrier import ROOT, NAME, k, pt, board_text


def box(cx, cy, cz, sx, sy, sz, color):
    # KiCad VRML models use 0.1-inch model units, with Y up.
    values = [cx/2.54, -cy/2.54, cz/2.54, sx/2.54, sy/2.54, sz/2.54]
    return '''Transform { translation %.6f %.6f %.6f children [ Shape {
        appearance Appearance { material Material { diffuseColor %s } }
        geometry Box { size %.6f %.6f %.6f } } ] }''' % (
            values[0], values[1], values[2], color, values[3], values[4], values[5])


config=json.loads((ROOT/"module_config.json").read_text())
models=ROOT/"3dmodels"; models.mkdir(exist_ok=True)
board=k.LoadBoard(str(ROOT/(NAME+".kicad_pcb")))
by_ref={fp.GetReference():fp for fp in board.GetFootprints()}
for module in config["modules"]:
    if module.get("kind") == "button":
        continue
    if module["ref"] in ("J1","J2","J4","J5") and (ROOT/"module_models.json").exists():
        continue
    pieces=["#VRML V2.0 utf8"]
    male=module["ref"] in ("J3","JP1")
    for pin in module["pins"]:
        x,y=pin["at"]
        pieces.append(box(x,y,-1.5,0.64,0.64,3,"0.75 0.75 0.72"))
        if male:
            pieces.append(box(x,y,1.27,2.54,2.54,2.54,"0.06 0.06 0.065"))
            pieces.append(box(x,y,5.2,0.64,0.64,5.3,"0.80 0.67 0.35"))
        else:
            pieces.append(box(x,y,3.0,2.54,2.54,6.0,"0.055 0.055 0.06"))
            for dx,dy,sx,sy in ((-0.97,0,0.6,2.54),(0.97,0,0.6,2.54),
                               (0,-0.97,1.34,0.6),(0,0.97,1.34,0.6)):
                pieces.append(box(x+dx,y+dy,7.25,sx,sy,2.5,"0.055 0.055 0.06"))
            pieces.append(box(x+0.43,y,6.35,0.15,0.85,0.35,"0.80 0.67 0.35"))
    filename=module["footprint"]+".wrl"
    (models/filename).write_text("\n".join(pieces)+"\n")
    fp=by_ref[module["ref"]]
    fp.Models().clear()
    model=k.FP_3DMODEL()
    model.m_Filename="${KIPRJMOD}/3dmodels/"+filename
    model.m_Show=True
    fp.Models().push_back(model)
    standalone=k.Cast_to_FOOTPRINT(fp.Duplicate(False))
    if standalone.GetLayer()==k.B_Cu:
        standalone.Flip(standalone.GetPosition(),k.FLIP_DIRECTION_LEFT_RIGHT)
    standalone.SetPosition(pt(0,0)); standalone.SetOrientationDegrees(0)
    standalone.Reference().SetText("REF**")
    for pad in standalone.Pads():pad.SetNetCode(0)
    k.PCB_IO_KICAD_SEXPR().FootprintSave(str(ROOT/"CompassCarrier.pretty"),standalone)
for item in board.GetDrawings():
    if isinstance(item,k.PCB_TEXT) and item.GetText()=="+X FRONT":
        item.SetText("3V3 SENSOR")
if not any(isinstance(item,k.PCB_TEXT) and item.GetText()=="FRONT <" for item in board.GetDrawings()):
    board_text(board,"FRONT <",118,126.8,0.8)
k.SaveBoard(str(ROOT/(NAME+".kicad_pcb")),board)
print("Added self-contained connector models")

if (ROOT/"module_models.json").exists():
    import attach_module_models
