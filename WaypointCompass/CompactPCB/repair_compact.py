"""Repair the exact remaining items reported by native KiCad DRC."""
import json
from pathlib import Path
source=Path(__file__).with_name('route_compact.py').read_text()
source=source.replace("if list(board.GetTracks()) or list(board.Zones()): raise RuntimeError('Build a fresh placement before routing')",'')
a=source.index('# Short switching loops');b=source.index('def save():',a)
source=source[:a]+source[b:]
source=source[:source.index('# Via connections to inner power/ground planes.')]
exec(compile(source,str(Path(__file__).with_name('route_compact.py')),'exec'))
report=json.loads((ROOT/'checks/routed.json').read_text());lookup={p.m_Uuid.AsString():p for p in board.GetPads()};lookup.update({t.m_Uuid.AsString():t for t in board.GetTracks()})
removed=set()
for v in report['violations']:
 if v['type']!='hole_to_hole':continue
 aa,bb=[lookup[i['uuid']] for i in v['items']]
 if aa.m_Uuid.AsString() in removed or bb.m_Uuid.AsString() in removed:continue
 assert isinstance(aa,k.PCB_VIA) and isinstance(bb,k.PCB_VIA) and aa.GetNetname()==bb.GetNetname()
 apos=(k.ToMM(aa.GetPosition().x)-100,k.ToMM(aa.GetPosition().y)-100);bpos=(k.ToMM(bb.GetPosition().x)-100,k.ToMM(bb.GetPosition().y)-100)
 if aa.GetNetname()!='/GND':
  for ll in (k.F_Cu,k.B_Cu):seg(aa.GetNetname(),apos,bpos,.12,ll)
 removed.add(aa.m_Uuid.AsString());board.Remove(aa)
# Recreate obstacle lists after removing duplicate thermal vias.
OB=[[],[]];vias={}
for p in board.GetPads():
 bb=p.GetBoundingBox();x=k.ToMM(bb.GetX())-100;y=k.ToMM(bb.GetY())-100;w=k.ToMM(bb.GetWidth());h=k.ToMM(bb.GetHeight())
 obj=('circle' if p.GetShape()==k.PAD_SHAPE_CIRCLE else 'rect',p.GetNetname(),x+w/2,y+h/2,w/2,h/2,p.GetAttribute()==k.PAD_ATTRIB_NPTH)
 for ll,layer in enumerate((k.F_Cu,k.B_Cu)):
  if p.IsOnLayer(layer):OB[ll].append(obj)
for t in board.GetTracks():observe_track(t)
for v in report['unconnected_items']:
 aitem,bitem=[lookup[i['uuid']] for i in v['items']]
 name=aitem.GetNetname();assert name==bitem.GetNetname()
 def node(item,desc):
  xy=(desc['pos']['x']-100,desc['pos']['y']-100)
  layers=tuple(ll for ll,layer in enumerate((k.F_Cu,k.B_Cu)) if item.IsOnLayer(layer))
  return (*xy,item.GetNetCode(),type(item).__name__,'',layers)
 a=node(aitem,v['items'][0]);b=node(bitem,v['items'][1]);ok=False
 for width in (.4,.2,.15,.12):
  masks=[raster(name,width,ll) for ll in range(2)];vm=[raster(name,.4,ll) for ll in range(2)]
  states=astar(a,b,masks,vm)
  if states:
   addpath(name,a,b,states,width);ok=True;print('Connected',name,a[:2],b[:2],'width',width,flush=True);break
 if not ok:print('UNRESOLVED',name,a,b,flush=True)
board.BuildConnectivity();k.ZONE_FILLER(board).Fill(board.Zones());save();print('Repair complete',flush=True)
