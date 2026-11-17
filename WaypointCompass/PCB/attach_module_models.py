"""Attach local module and direct-header models while preserving PCB pad geometry."""
import json
from build_carrier import ROOT, NAME, k, pt

data=json.loads((ROOT/'module_models.json').read_text())
board=k.LoadBoard(str(ROOT/(NAME+'.kicad_pcb')))
by_ref={fp.GetReference():fp for fp in board.GetFootprints()}
for ref,spec in data['models'].items():
    fp=by_ref[ref]; fp.Models().clear()
    for filename,rotation,offset in [
        (spec['file'],spec['rotation'],spec['offset']),
        ('assembly/'+ref+'_straight_headers.step',[0,0,0],[0,0,0]),
    ]:
        model=k.FP_3DMODEL()
        model.m_Filename='${KIPRJMOD}/3dmodels/'+filename
        model.m_Rotation=k.VECTOR3D(*rotation)
        model.m_Offset=k.VECTOR3D(*offset)
        model.m_Show=True; fp.Models().push_back(model)
    standalone=k.Cast_to_FOOTPRINT(fp.Duplicate(False))
    if standalone.GetLayer()==k.B_Cu:
        standalone.Flip(standalone.GetPosition(),k.FLIP_DIRECTION_LEFT_RIGHT)
    standalone.SetPosition(pt(0,0)); standalone.SetOrientationDegrees(0)
    standalone.Reference().SetText('REF**')
    for pad in standalone.Pads():pad.SetNetCode(0)
    k.PCB_IO_KICAD_SEXPR().FootprintSave(str(ROOT/'CompassCarrier.pretty'),standalone)
k.SaveBoard(str(ROOT/(NAME+'.kicad_pcb')),board)
print('Attached four supplied reference modules and their direct soldered headers.')
