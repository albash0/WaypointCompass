"""Measure supplied STEP geometry with OpenCascade; no source models are edited."""
import json
from pathlib import Path
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder

ROOT = Path(__file__).resolve().parent

def load(path):
    reader=STEPControl_Reader()
    assert reader.ReadFile(str(path)) == IFSelect_RetDone, path
    reader.TransferRoots()
    return reader.OneShape()

def bbox(shape):
    box=Bnd_Box()
    BRepBndLib.AddOptimal_s(shape,box,False,False)
    lo,hi=box.CornerMin(),box.CornerMax()
    return [round(v,5) for v in (lo.X(),lo.Y(),lo.Z(),hi.X(),hi.Y(),hi.Z())]

def solids(shape):
    ex=TopExp_Explorer(shape,TopAbs_SOLID)
    while ex.More():
        yield TopoDS.Solid(ex.Current())
        ex.Next()

def cylinders(shape):
    results=set()
    ex=TopExp_Explorer(shape,TopAbs_FACE)
    while ex.More():
        surface=BRepAdaptor_Surface(TopoDS.Face(ex.Current()))
        if surface.GetType()==GeomAbs_Cylinder:
            cylinder=surface.Cylinder()
            r=cylinder.Radius()
            if 0.25<r<1.6:
                p=cylinder.Location(); d=cylinder.Axis().Direction()
                results.add((round(r,5),tuple(round(v,5) for v in (p.X(),p.Y(),p.Z())),
                             tuple(round(v,5) for v in (d.X(),d.Y(),d.Z()))))
        ex.Next()
    return sorted(results)

if __name__ == '__main__':
    results={}
    for path in sorted((ROOT/'3dmodels/modules').glob('*.step')):
        shape=load(path)
        parts=[]
        for i,part in enumerate(solids(shape)):
            props=GProp_GProps(); BRepGProp.VolumeProperties_s(part,props)
            bounds=bbox(part)
            parts.append({'index':i,'bbox':bounds,'volume':round(props.Mass(),4),
                          'cylinders':cylinders(part)})
        results[path.name]={'bbox':bbox(shape),'parts':parts}
    output=ROOT/'checks/STEP-model-measurements.json'
    output.write_text(json.dumps(results,indent=2)+'\n')
    for name,data in results.items():
        print(name,'overall',data['bbox'],'solids',len(data['parts']))
        for part in sorted(data['parts'],key=lambda p:p['volume'],reverse=True)[:6]:
            print('  solid',part['index'],'bbox',part['bbox'],'volume',part['volume'])
            print('  cylinders',part['cylinders'][:30])
