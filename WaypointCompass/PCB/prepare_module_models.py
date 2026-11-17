"""Create colored assembly copies and straight header models from reference STEPs.

Requires cadquery-ocp 8 in an isolated Python environment. Original module
files are retained; electrical landing patterns always keep their 2.54 mm pitch.
"""
import json
from inspect_step_models import ROOT, bbox, load, solids
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.STEPCAFControl import STEPCAFControl_Reader, STEPCAFControl_Writer
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorGen
from OCP.collections import Sequence_TDF_Label
from OCP.STEPControl import STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB

MODEL_DIR=ROOT/'3dmodels/modules'
ASSEMBLY_DIR=ROOT/'3dmodels/assembly'
ASSEMBLY_DIR.mkdir(exist_ok=True)

def document():
    return TDocStd_Document(TCollection_ExtendedString('BinXCAF'))

def strip_header(filename, destination, predicate):
    doc=document(); reader=STEPCAFControl_Reader()
    assert reader.ReadFile(str(MODEL_DIR/filename))==IFSelect_RetDone
    assert reader.Transfer(doc)
    tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots=Sequence_TDF_Label(); tool.GetFreeShapes(roots)
    assert roots.Length()==1
    root=roots.Value(1); children=Sequence_TDF_Label()
    tool.GetComponents_s(root,children)
    removed=[]
    for i in range(1,children.Length()+1):
        child=children.Value(i)
        bounds=bbox(tool.GetShape_s(child))
        if predicate(bounds):
            removed.append(bounds); tool.RemoveComponent(child)
    assert len(removed)==1, (filename,removed)
    tool.UpdateAssemblies()
    writer=STEPCAFControl_Writer(); assert writer.Transfer(root,STEPControl_AsIs)
    assert writer.Write(str(ASSEMBLY_DIR/destination))==IFSelect_RetDone
    return {'removed_header_bbox':removed[0], 'remaining_solids':len(list(solids(load(ASSEMBLY_DIR/destination))))}

removed={
    'TFT':strip_header('TFT_GC9A01.step','TFT_no_header.step',lambda b:b[2]>23 and b[1]<-1),
    'GY521':strip_header('GY_521.step','GY521_no_header.step',lambda b:b[1]<0),
}
config=json.loads((ROOT/'module_config.json').read_text())
for module in config['modules']:
    if module['ref'] not in ('J1','J2','J3','J4','J5','JP1'): continue
    cable = module['ref'] in ('J3','JP1')
    doc=document(); st=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct=XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    for pin in module['pins']:
        x,y=pin['at']; y=-y
        for z,sx,sy,sz,color in [
            (0,2.54,2.54,2.54,(0.06,0.06,0.065)),
            (-3 if cable else -2.6,0.64,0.64,10.85 if cable else 8.4,(0.80,0.67,0.35)),
        ]:
            shape=BRepPrimAPI_MakeBox(gp_Pnt(x-sx/2,y-sy/2,z),sx,sy,sz).Shape()
            label=st.AddShape(shape,False)
            ct.SetColor(label,Quantity_Color(*color,Quantity_TOC_RGB),XCAFDoc_ColorGen)
    writer=STEPCAFControl_Writer(); assert writer.Transfer(doc,STEPControl_AsIs)
    destination = ROOT/'3dmodels'/(module['footprint']+'.step') if cable else ASSEMBLY_DIR/(module['ref']+'_straight_headers.step')
    assert writer.Write(str(destination))==IFSelect_RetDone

models={
    'J1':{'file':'modules/ESP32S3_SuperMini.step','rotation':[0,0,0],'offset':[0,-0.1016,2.54]},
    'J2':{'file':'assembly/TFT_no_header.step','rotation':[-90,0,0],'offset':[0,24.996,2.54]},
    'J4':{'file':'assembly/GY521_no_header.step','rotation':[-90,0,-90],'offset':[-20.41818,3.94334,-2.69916]},
    'J5':{'file':'modules/GY_271.step','rotation':[0,0,0],'offset':[0,-5.25,3.84]},
}
metadata={
    'mounting':'Male headers soldered into both boards; no female sockets',
    'module_to_carrier_gap_mm':2.54,
    'source_geometry_role':'User-confirmed reference geometry; retain existing PCB dimensions and hole positions',
    'models':models, 'derived_models':removed,
    'differences':[
        'ESP32 reference model: 2.5019 mm pitch and 15.0368 mm row spacing; carrier remains 2.54 mm and 15.24 mm.',
        'GY271 reference model: 2.60 mm pitch; carrier remains 2.54 mm.',
        'TFT reference model: 18.86 mm mounting-hole spacing; carrier remains 19.26 mm from supplied drawing.',
        'TFT reference model pin row is 24.996 mm from its round PCB center; carrier uses 24.74 mm from supplied drawing.',
    ],
}
(ROOT/'module_models.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('Prepared four module placements, two header-free STEP copies, and four straight-header STEP models.')
