"""Four-layer prototype routing; final native KiCad DRC is the acceptance gate."""
import math,json,re,heapq,itertools,sys
from collections import defaultdict
import numpy as np
from build_compact import k,pt,ROOT,NAME,project
board=k.LoadBoard(str(ROOT/(NAME+'.kicad_pcb')))
if list(board.GetTracks()) or list(board.Zones()): raise RuntimeError('Build a fresh placement before routing')
FPS={f.GetReference():f for f in board.GetFootprints()}
def pad(ref,n):
 pp=[p for p in FPS[ref].Pads() if p.GetNumber()==str(n) and p.IsOnLayer(k.B_Cu)]
 return max(pp,key=lambda p:p.GetSize().x*p.GetSize().y)
def xy(p):return (k.ToMM(p.GetPosition().x)-100,k.ToMM(p.GetPosition().y)-100)
def net(p):return p.GetNetname()
def seg(name,a,b,width=.15,layer=k.B_Cu):
 if math.dist(a,b)<1e-7:return
 t=k.PCB_TRACK(board);t.SetStart(pt(a[0]+100,a[1]+100));t.SetEnd(pt(b[0]+100,b[1]+100));t.SetWidth(k.FromMM(width));t.SetLayer(layer);t.SetNetCode(board.FindNet(name).GetNetCode());board.Add(t);return t
vias={}
def via(name,p,size=.4):
 key=(name,round(p[0],6),round(p[1],6))
 if key in vias:return vias[key]
 v=k.PCB_VIA(board);v.SetPosition(pt(p[0]+100,p[1]+100));v.SetWidth(k.FromMM(size));v.SetDrill(k.FromMM(.2));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNetCode(board.FindNet(name).GetNetCode());board.Add(v);vias[key]=v;return v
def path(name,points,width=.15,layer=k.B_Cu):
 for a,b in zip(points,points[1:]):seg('/'+name,a,b,width,layer)
# Short switching loops and quiet feedback support, all on the rear copper.
path('BB_L1',[xy(pad('U5',1)),(37.1,24.14),(37.1,26.275),xy(pad('L1',1))],.4)
path('BB_L2',[xy(pad('U5',10)),(41.9,24.14),(41.9,26.275),xy(pad('L1',2))],.4)
path('SYS',[xy(pad('U5',4)),xy(pad('C14',1))],.35)
path('SYS',[xy(pad('U5',2)),(36.55,23),xy(pad('C14',1))],.35)
path('SYS',[xy(pad('C14',1)),(34.2,23.25),(34.2,24.85),xy(pad('C15',1))],.35)
path('3V3',[xy(pad('U5',9)),(42.63,23),xy(pad('R19',1)),(44.49,23.26),xy(pad('C16',1))],.4)
path('3V3',[xy(pad('R19',1)),(44.1,24.16),(44.1,25.5),xy(pad('C17',1))],.4)
path('BB_AUX',[xy(pad('U5',6)),xy(pad('C18',1))],.15)
path('BB_FB',[xy(pad('U5',8)),(42.2,22.5),xy(pad('R19',2))],.12)
path('BB_FB',[xy(pad('R19',2)),(42.5,22.14)],.12)
via('/BB_FB',(42.5,22.14));via('/BB_FB',(42.5,25.36))
path('BB_FB',[(42.5,22.14),(42.5,25.36)],.12,k.F_Cu)
path('BB_FB',[(42.5,25.36),xy(pad('R20',1))],.12)
path('GPS_SW',[xy(pad('U6',5)),(49.9,21.5),(50.5,20.9),(50.5,18.5),xy(pad('L2',2))],.35)
path('SYS',[xy(pad('U6',3)),(46.85,21),(46.85,19.5),xy(pad('L2',1))],.3)
path('SYS',[xy(pad('L2',1)),(46,17.35),xy(pad('C19',1))],.45)
path('GPS_5V',[xy(pad('U6',6)),xy(pad('C20',1)),xy(pad('C21',1))],.35)
path('GPS_FB',[xy(pad('U6',1)),(46.5,23.287),(46.5,27.525),xy(pad('R21',2))],.12)
path('GPS_FB',[xy(pad('R21',2)),(46.025,28.8),(45.6,29.225),(44.65,29.225),xy(pad('R22',1))],.12)
# USB: long run on front copper over an uninterrupted In1 ground plane.
# Differential pair is .15 mm wide with .15 mm edge gap. Fab must tune impedance to stackup.
path('USB_M',[xy(pad('R6',1)),(23,11.7)],.15);via('/USB_M',(23,11.7))
path('USB_P',[xy(pad('R7',1)),(21,11.7)],.15);via('/USB_P',(21,11.7))
path('USB_M',[(23,11.7),(24.3,13),(24.3,28.5),(26.05,30.25),(30.25,30.25)],.15,k.F_Cu)
path('USB_P',[(21,11.7),(22.6,13.3),(22.6,14.7),(24,16.1),(24,28.62),(25.93,30.55),(28.05,30.55),(28.35,30.85)],.15,k.F_Cu)
via('/USB_M',(30.25,30.25));via('/USB_P',(28.35,30.85))
path('USB_M',[(30.25,30.25),xy(pad('U8',6))],.15)
path('USB_P',[(28.35,30.85),xy(pad('U8',4))],.15)
path('USB_M_MCU',[xy(pad('R6',2)),(24,9.175),xy(pad('U1',23))],.15)
path('USB_P_MCU',[xy(pad('R7',2)),(21,8.3),(24.85,8.3),xy(pad('U1',24))],.15)

def save():
 k.SaveBoard(str(ROOT/(NAME+'.kicad_pcb')),board);project()
 p=ROOT/(NAME+'.kicad_pcb');p.write_text(re.sub(r'\(layers "\*\.Cu"(?: "[^"]+")*\)','(layers "*.Cu" "*.Mask")',p.read_text()))
if '--manual-only' in sys.argv:save();print('Manual power and USB routes saved');sys.exit()
# Raster route remaining point-to-point nets; SMT pads are restricted to their actual layer.
STEP=.05;NX=1081;NY=801;AREA=NX*NY;CLEAR=.1;MARGIN=.006
OB=[[],[]]; nodes=defaultdict(list); drillpads=[]; pads_by_node={}
for p in board.GetPads():
 bb=p.GetBoundingBox();x=k.ToMM(bb.GetX())-100;y=k.ToMM(bb.GetY())-100;w=k.ToMM(bb.GetWidth());h=k.ToMM(bb.GetHeight())
 obj=('circle' if p.GetShape()==k.PAD_SHAPE_CIRCLE else 'rect',p.GetNetname(),x+w/2,y+h/2,w/2,h/2,p.GetAttribute()==k.PAD_ATTRIB_NPTH)
 for ll,layer in enumerate((k.F_Cu,k.B_Cu)):
  if p.IsOnLayer(layer):OB[ll].append(obj)
 if p.GetAttribute() in (k.PAD_ATTRIB_PTH,k.PAD_ATTRIB_NPTH):
  drillpads.append((p.GetNetname(),*xy(p),max(k.ToMM(p.GetDrillSize().x),k.ToMM(p.GetDrillSize().y))/2,p.GetAttribute()==k.PAD_ATTRIB_PTH))
 if p.GetNetname() and not p.GetNetname().startswith('unconnected-'):
  layers=tuple(ll for ll,layer in enumerate((k.F_Cu,k.B_Cu)) if p.IsOnLayer(layer))
  node=(*xy(p),p.GetNetCode(),p.GetParentFootprint().GetReference(),p.GetNumber(),layers)
  nodes[p.GetNetname()].append(node);pads_by_node[node]=p
def observe_track(t):
 if isinstance(t,k.PCB_VIA):
  p=(k.ToMM(t.GetPosition().x)-100,k.ToMM(t.GetPosition().y)-100);rad=k.ToMM(t.GetWidth(k.F_Cu))/2
  for ll in range(2):OB[ll].append(('circle',t.GetNetname(),*p,rad,rad,False))
  vias[(t.GetNetname(),round(p[0],6),round(p[1],6))]=t
 else:
  a=(k.ToMM(t.GetStart().x)-100,k.ToMM(t.GetStart().y)-100);b=(k.ToMM(t.GetEnd().x)-100,k.ToMM(t.GetEnd().y)-100);w=k.ToMM(t.GetWidth())
  ll=0 if t.GetLayer()==k.F_Cu else 1;OB[ll].append(('segment',t.GetNetname(),*a,*b,w))
for t in board.GetTracks():observe_track(t)

def raster(name,width,ll):
 mask=np.zeros((NY,NX),dtype=np.uint8);edge=.25+width/2+MARGIN;ce=math.ceil(edge/STEP)
 mask[:ce,:]=1;mask[-ce:,:]=1;mask[:,:ce]=1;mask[:,-ce:]=1
 for typ,nn,x,y,a,b,hole in OB[ll]:
  if nn==name:continue
  extra=(.2 if hole else CLEAR)+width/2+MARGIN
  if typ=='segment':
   xx,yy,oldw=a,b,hole;radius=oldw/2+CLEAR+width/2+MARGIN
   c0=max(0,math.floor((min(x,xx)-radius)/STEP));c1=min(NX-1,math.ceil((max(x,xx)+radius)/STEP))
   r0=max(0,math.floor((min(y,yy)-radius)/STEP));r1=min(NY-1,math.ceil((max(y,yy)+radius)/STEP))
  else:
   c0=max(0,math.floor((x-a-extra)/STEP));c1=min(NX-1,math.ceil((x+a+extra)/STEP))
   r0=max(0,math.floor((y-b-extra)/STEP));r1=min(NY-1,math.ceil((y+b+extra)/STEP))
  if c0>c1 or r0>r1:continue
  py=np.arange(r0,r1+1,dtype=float)[:,None]*STEP;px=np.arange(c0,c1+1,dtype=float)[None,:]*STEP
  if typ=='rect':dx=np.maximum(abs(px-x)-a,0);dy=np.maximum(abs(py-y)-b,0);blocked=dx*dx+dy*dy<=extra*extra
  elif typ=='circle':blocked=(px-x)**2+(py-y)**2<=(a+extra)**2
  else:
   vx=xx-x;vy=yy-y;t=np.clip(((px-x)*vx+(py-y)*vy)/(vx*vx+vy*vy or 1),0,1);blocked=(px-x-t*vx)**2+(py-y-t*vy)**2<=radius*radius
  mask[r0:r1+1,c0:c1+1]|=blocked
 if width>=.39:
  holes=[(n,x,y,.1,False) for n,x,y in vias]+drillpads
  for nn,x,y,r,is_pth in holes:
   radius=r+.1+.25+MARGIN
   c0=max(0,math.floor((x-radius)/STEP));c1=min(NX-1,math.ceil((x+radius)/STEP));r0=max(0,math.floor((y-radius)/STEP));r1=min(NY-1,math.ceil((y+radius)/STEP))
   py=np.arange(r0,r1+1,dtype=float)[:,None]*STEP;px=np.arange(c0,c1+1,dtype=float)[None,:]*STEP
   mask[r0:r1+1,c0:c1+1]|=(px-x)**2+(py-y)**2<radius*radius
  for nn,x,y,r,is_pth in holes:
   if nn==name:mask[round(y/STEP),round(x/STEP)]=0
 return mask.tobytes()

def index(x,y):return round(y/STEP)*NX+round(x/STEP)
def coord(s):i=s%AREA;return (i%NX*STEP,i//NX*STEP)
MOVES=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,2**.5),(1,-1,2**.5),(-1,1,2**.5),(-1,-1,2**.5)]
def astar(start,target,masks,vm,onlyback=False):
 source=index(*start[:2]);goal=index(*target[:2]);gx=goal%NX;gy=goal//NX
 if all(masks[ll][goal] for ll in target[5]):return None
 def h(p):dx=abs(p%NX-gx);dy=abs(p//NX-gy);return max(dx,dy)+.41421356237*min(dx,dy)
 costs={};parents={};queue=[];count=itertools.count();settled=set()
 for ll in start[5]:
  if onlyback and ll==0:continue
  if not masks[ll][source]:costs[source+ll*AREA]=0;heapq.heappush(queue,(h(source),next(count),source+ll*AREA))
 while queue:
  _,_,s=heapq.heappop(queue)
  if s in settled:continue
  settled.add(s);ll=s//AREA;i=s%AREA
  if i==goal and ll in target[5]:
   path=[s]
   while s in parents:s=parents[s];path.append(s)
   return path[::-1]
  x=i%NX;y=i//NX;c=costs[s]
  for dx,dy,d in MOVES:
   xx=x+dx;yy=y+dy
   if not(0<=xx<NX and 0<=yy<NY):continue
   p=yy*NX+xx
   if masks[ll][p]:continue
   if dx and dy and (masks[ll][y*NX+xx] or masks[ll][yy*NX+x]):continue
   ns=p+ll*AREA;nc=c+d+(0.005 if ll==0 else 0)
   if nc<costs.get(ns,math.inf):costs[ns]=nc;parents[ns]=s;heapq.heappush(queue,(nc+h(p),next(count),ns))
  if not onlyback and not vm[0][i] and not vm[1][i]:
   ns=i+(1-ll)*AREA;nc=c+40
   if nc<costs.get(ns,math.inf):costs[ns]=nc;parents[ns]=s;heapq.heappush(queue,(nc+h(i),next(count),ns))
  if len(settled)>900000:return None
 return None

def addpath(name,a,b,states,width):
 groups=[];pts=[];ll=states[0]//AREA
 for s in states:
  nl=s//AREA
  if nl!=ll:
   pp=coord(s);pts.append(pp);groups.append((ll,pts));pts=[pp]
   if not any(nn==name and is_pth and math.dist(pp,(x,y))<.04 for nn,x,y,r,is_pth in drillpads):
    v=via(name,pp);observe_track(v)
   ll=nl
  pts.append(coord(s))
 groups.append((ll,pts));groups[0][1].insert(0,a[:2]);groups[-1][1].append(b[:2])
 for ll,points in groups:
  cc=[]
  for pp in points:
   if cc and math.dist(cc[-1],pp)<1e-7:continue
   while len(cc)>1:
    x,y=cc[-2:]
    if abs((y[0]-x[0])*(pp[1]-y[1])-(y[1]-x[1])*(pp[0]-y[0]))<1e-7:cc.pop()
    else:break
   cc.append(pp)
  for p,q in zip(cc,cc[1:]):observe_track(seg(name,p,q,width,k.F_Cu if ll==0 else k.B_Cu))
# Via connections to inner power/ground planes. Avoid solder lands except deliberate thermal vias.
plane_report=[]
for name in ('/GND','/3V3'):
 seenpads=set()
 for p in list(board.GetPads()):
  if p.GetNetname()!=name or p.GetAttribute()==k.PAD_ATTRIB_PTH or not p.IsOnLayer(k.B_Cu):continue
  pos=xy(p)
  if pos in seenpads:continue
  seenpads.add(pos)
  ref=p.GetParentFootprint().GetReference();number=p.GetNumber();a=(*pos,p.GetNetCode(),ref,number,(1,))
  masks=[raster(name,.12,ll) for ll in range(2)];vm=[raster(name,.4,ll) for ll in range(2)]
  # Larger EP pads accept thermal vias; other vias go beyond SMD solder lands.
  thermal=(ref in ('U4','U5') and number in ('17','11'))
  bb=p.GetBoundingBox();x0=k.ToMM(bb.GetX())-100;y0=k.ToMM(bb.GetY())-100;x1=x0+k.ToMM(bb.GetWidth());y1=y0+k.ToMM(bb.GetHeight())
  candidates=[]
  for dy in range(-35,36):
   for dx in range(-35,36):
    x=round(pos[0]/STEP)*STEP+dx*STEP;y=round(pos[1]/STEP)*STEP+dy*STEP
    if not(0<x<54 and 0<y<40):continue
    d=(x-pos[0])**2+(y-pos[1])**2
    if not thermal and x0-.23<x<x1+.23 and y0-.23<y<y1+.23:continue
    i=index(x,y)
    if not vm[0][i] and not vm[1][i]:candidates.append((d,x,y))
  ok=False
  for _,x,y in sorted(candidates)[:80]:
   target=(x,y,p.GetNetCode(),ref,'via',(1,));states=astar(a,target,masks,vm,onlyback=True)
   if states:
    addpath(name,a,target,states,.12);v=via(name,(x,y));observe_track(v);ok=True;break
  if not ok:print('PLANE ESCAPE FAILED',name,ref,number,pos,flush=True)
  plane_report.append((name,ref,number,ok))
print('Plane escapes:',sum(p[3] for p in plane_report),'/',len(plane_report),flush=True)
# Remaining nets get a minimum spanning tree. Existing short routes remain part of the tree.
priority=['/USB_M','/USB_P','/USB_M_MCU','/USB_P_MCU','/BB_L1','/BB_L2','/GPS_SW','/BB_AUX','/BB_FB','/GPS_FB','/SYS','/GPS_5V','/VBAT','/CELL_NEG','/FET_MID']
report=[]
for name in sorted(nodes,key=lambda n:(priority.index(n) if n in priority else 100,len(nodes[n]))):
 if name in ('/GND','/3V3'):continue
 nn=nodes[name];dedup=[]
 for n in nn:
  if not any(math.dist(n[:2],a[:2])<1e-6 for a in dedup):dedup.append(n)
 nn=dedup
 board.BuildConnectivity();conn=board.GetConnectivity()
 cluster={i.m_Uuid.AsString() for i in conn.GetConnectedItems(pads_by_node[nn[0]])};cluster.add(pads_by_node[nn[0]].m_Uuid.AsString())
 tree=[n for n in nn if pads_by_node[n].m_Uuid.AsString() in cluster];todo=[n for n in nn if n not in tree];routes=0;fail=[]
 while todo:
  a,b=min(((a,b) for a in tree for b in todo),key=lambda p:math.dist(p[0][:2],p[1][:2]))
  width=.12 if name in ('/BB_FB','/GPS_FB') else .4 if name in ('/VBUS','/SYS','/VBAT','/CELL_NEG','/FET_MID','/GPS_5V','/GPS_VCC') else .15
  # Wide power outside fine-pitch pads; short pin fanout is handled by manual power routes.
  masks=[raster(name,width,ll) for ll in range(2)];vm=[raster(name,.4,ll) for ll in range(2)]
  states=astar(a,b,masks,vm)
  if states is None:fail.append([a[3:5],b[3:5]]);print('FAILED',name,a[3:5],b[3:5],flush=True)
  else:addpath(name,a,b,states,width);routes+=1
  tree.append(b);todo.remove(b)
  board.BuildConnectivity();conn=board.GetConnectivity()
  cluster={i.m_Uuid.AsString() for i in conn.GetConnectedItems(pads_by_node[tree[0]])};cluster.add(pads_by_node[tree[0]].m_Uuid.AsString())
  for n in list(todo):
   if pads_by_node[n].m_Uuid.AsString() in cluster:tree.append(n);todo.remove(n)
 print('Routed',name,routes,'failed',len(fail),flush=True);report.append(dict(net=name,routes=routes,failed=fail))
 save()
# Internal planes + rear solid ground pour. Cell negative is never assigned to GND.
for layer,name in ((k.In1_Cu,'/GND'),(k.In2_Cu,'/3V3'),(k.B_Cu,'/GND')):
 z=k.ZONE(board);z.SetLayer(layer);z.SetNetCode(board.FindNet(name).GetNetCode());z.SetLocalClearance(k.FromMM(.10));z.SetMinThickness(k.FromMM(.1));z.SetPadConnection(k.ZONE_CONNECTION_FULL)
 outline=z.Outline();outline.NewOutline()
 for x,y in ((100.3,100.3),(153.7,100.3),(153.7,139.7),(100.3,139.7)):outline.Append(k.FromMM(x),k.FromMM(y))
 board.Add(z)
board.BuildConnectivity();k.ZONE_FILLER(board).Fill(board.Zones());save()
(ROOT/'routing_report.json').write_text(json.dumps(dict(plane_escapes=plane_report,nets=report),indent=2))
print('Completed routing,',len(board.GetTracks()),'tracks/vias',flush=True)
