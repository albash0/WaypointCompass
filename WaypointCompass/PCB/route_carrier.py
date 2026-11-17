"""Route the generated carrier with conservative two-layer clearance rules.

KiCad DRC is the authority after routing; this script never substitutes for it.
"""
import heapq
import itertools
import json
import math
from collections import defaultdict

from build_carrier import ROOT, NAME, pt, k

STEP = 0.25
ORIGIN = (100.0, 100.0)
NX, NY = 241, 161
AREA = NX * NY
CLEARANCE = 0.2
MARGIN = 0.05
board = k.LoadBoard(str(ROOT / (NAME + ".kicad_pcb")))
if list(board.GetTracks()) or list(board.Zones()):
    raise RuntimeError("Run build_carrier.py first to generate a fresh placement.")
obstacles = [[], []]
existing_vias = set()
pad_nodes = defaultdict(list)
for pad in board.GetPads():
    x, y = k.ToMM(pad.GetPosition().x), k.ToMM(pad.GetPosition().y)
    net = pad.GetNetname()
    obj = ("rect" if pad.GetShape() == k.PAD_SHAPE_RECT else "circle", net,
           x, y, k.ToMM(pad.GetSize().x)/2, k.ToMM(pad.GetSize().y)/2,
           pad.GetAttribute() == k.PAD_ATTRIB_NPTH)
    for layer in range(2):
        obstacles[layer].append(obj)
    if net and not net.startswith("unconnected-"):
        pad_nodes[net].append((x, y, pad.GetNetCode(),pad.GetParentFootprint().GetReference(),pad.GetNumber()))
for nodes in pad_nodes.values():
    nodes.sort(key=lambda node:(node[3],int(node[4])))


def raster(net, width, layer):
    mask = bytearray(AREA)
    edge = 0.5 + width / 2 + MARGIN
    for row in range(NY):
        yy = row * STEP
        if yy < edge or yy > 40 - edge:
            mask[row*NX:(row+1)*NX] = bytes([1])*NX
        else:
            for col in range(NX):
                xx = col * STEP
                if xx < edge or xx > 60 - edge:
                    mask[row*NX+col] = 1
    for obj in obstacles[layer]:
        if obj[1] == net:
            continue
        typ, _, x, y, a, b, hole = obj
        extra = (0.25 if hole else CLEARANCE) + width / 2 + MARGIN
        if typ == "segment":
            x2, y2, old_width = a, b, hole
            radius = old_width / 2 + CLEARANCE + width / 2 + MARGIN
            minx, maxx = min(x,x2)-radius, max(x,x2)+radius
            miny, maxy = min(y,y2)-radius, max(y,y2)+radius
        else:
            minx, maxx = x-a-extra, x+a+extra
            miny, maxy = y-b-extra, y+b+extra
        c0=max(0,int(math.floor((minx-ORIGIN[0])/STEP)))
        c1=min(NX-1,int(math.ceil((maxx-ORIGIN[0])/STEP)))
        r0=max(0,int(math.floor((miny-ORIGIN[1])/STEP)))
        r1=min(NY-1,int(math.ceil((maxy-ORIGIN[1])/STEP)))
        for row in range(r0,r1+1):
            py=ORIGIN[1]+row*STEP
            for col in range(c0,c1+1):
                px=ORIGIN[0]+col*STEP
                if typ == "rect":
                    dx=max(abs(px-x)-a,0); dy=max(abs(py-y)-b,0)
                    blocked=dx*dx+dy*dy <= extra*extra
                elif typ == "circle":
                    blocked=(px-x)**2+(py-y)**2 <= (a+extra)**2
                else:
                    vx=x2-x; vy=y2-y
                    t=max(0,min(1,((px-x)*vx+(py-y)*vy)/(vx*vx+vy*vy or 1)))
                    blocked=(px-x-t*vx)**2+(py-y-t*vy)**2 <= radius*radius
                if blocked:
                    mask[row*NX+col]=1
    # A rounded grid point inside existing copper of this net remains usable.
    # Otherwise rounding next to an already-connected via can falsely cage it.
    for obj in obstacles[layer]:
        if obj[1] != net or obj[0] != "circle":
            continue
        _,_,x,y,a,b,hole=obj
        radius=max(0,a-width/2+0.04)
        c0=max(0,int(math.floor((x-radius-ORIGIN[0])/STEP)))
        c1=min(NX-1,int(math.ceil((x+radius-ORIGIN[0])/STEP)))
        r0=max(0,int(math.floor((y-radius-ORIGIN[1])/STEP)))
        r1=min(NY-1,int(math.ceil((y+radius-ORIGIN[1])/STEP)))
        for row in range(r0,r1+1):
            for col in range(c0,c1+1):
                if (ORIGIN[0]+col*STEP-x)**2+(ORIGIN[1]+row*STEP-y)**2<=radius*radius:
                    mask[row*NX+col]=0
    return mask


def index(x, y):
    return round((y-ORIGIN[1])/STEP)*NX + round((x-ORIGIN[0])/STEP)


def coordinates(state):
    xy = state % AREA
    return (ORIGIN[0] + (xy % NX)*STEP, ORIGIN[1] + (xy//NX)*STEP)


def find_path(start, target, masks, via_masks, prefer_back=False):
    source = index(*start[:2]); goal = index(*target[:2])
    gx,gy = goal%NX,goal//NX
    def heuristic(pos):
        dx=abs(pos%NX-gx); dy=abs(pos//NX-gy)
        return max(dx,dy) + 0.41421356237*min(dx,dy)
    queue=[]; counter=itertools.count(); parents={}; costs={}
    for layer in range(2):
        state=source+layer*AREA
        if not masks[layer][source]:
            initial=0 if layer == int(prefer_back) else 2
            costs[state]=initial
            heapq.heappush(queue,(initial+heuristic(source),next(counter),state))
    moves=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),
           (1,1,math.sqrt(2)),(1,-1,math.sqrt(2)),
           (-1,1,math.sqrt(2)),(-1,-1,math.sqrt(2))]
    settled=set()
    while queue:
        _,_,state=heapq.heappop(queue)
        if state in settled: continue
        settled.add(state)
        layer=state//AREA; pos=state%AREA
        if pos == goal:
            path=[state]
            while state in parents:
                state=parents[state]; path.append(state)
            return path[::-1]
        x,y=pos%NX,pos//NX; current_cost=costs[state]
        for dx,dy,cost in moves:
            xx=x+dx; yy=y+dy
            if not (0 <= xx < NX and 0 <= yy < NY): continue
            newpos=yy*NX+xx
            if masks[layer][newpos]: continue
            if dx and dy and (masks[layer][y*NX+xx] or masks[layer][yy*NX+x]): continue
            neighbor=newpos+layer*AREA
            newcost=current_cost+cost
            if newcost < costs.get(neighbor,math.inf):
                costs[neighbor]=newcost; parents[neighbor]=state
                heapq.heappush(queue,(newcost+heuristic(newpos),next(counter),neighbor))
        if not via_masks[0][pos] and not via_masks[1][pos]:
            neighbor=pos+(1-layer)*AREA; newcost=current_cost+24
            if newcost < costs.get(neighbor,math.inf):
                costs[neighbor]=newcost; parents[neighbor]=state
                heapq.heappush(queue,(newcost+heuristic(pos),next(counter),neighbor))
    return None


def add_segment(net, netcode, start, end, width, layer):
    if math.dist(start,end) < 1e-7: return 0
    item=k.PCB_TRACK(board)
    item.SetStart(pt(*start)); item.SetEnd(pt(*end))
    item.SetWidth(k.FromMM(width))
    item.SetLayer(k.F_Cu if layer == 0 else k.B_Cu)
    item.SetNetCode(netcode)
    board.Add(item)
    obstacles[layer].append(("segment",net,*start,*end,width))
    return math.dist(start,end)


def add_path(net, start, target, path, width):
    netcode=start[2]; total=0; vias=0
    layers=[]; group=[]; current_layer=path[0]//AREA
    for state in path:
        layer=state//AREA
        if layer != current_layer:
            layers.append((current_layer,group)); group=[]
            x,y=coordinates(state)
            key=(x,y,netcode)
            if key not in existing_vias:
                via=k.PCB_VIA(board)
                via.SetPosition(pt(x,y)); via.SetWidth(k.FromMM(0.7))
                via.SetDrill(k.FromMM(0.3)); via.SetViaType(k.VIATYPE_THROUGH)
                via.SetLayerPair(k.F_Cu,k.B_Cu); via.SetNetCode(netcode)
                board.Add(via)
                for ll in range(2):
                    obstacles[ll].append(("circle",net,x,y,0.35,0.35,False))
                existing_vias.add(key)
                vias+=1
            current_layer=layer
        group.append(coordinates(state))
    layers.append((current_layer,group))
    layers[0][1].insert(0,start[:2]); layers[-1][1].append(target[:2])
    for layer, points in layers:
        condensed=[]
        for point in points:
            if condensed and math.dist(condensed[-1],point)<1e-7: continue
            while len(condensed)>1:
                a,b=condensed[-2],condensed[-1]
                if abs((b[0]-a[0])*(point[1]-b[1])-(b[1]-a[1])*(point[0]-b[0]))<1e-7:
                    condensed.pop()
                else: break
            condensed.append(point)
        for a,b in zip(condensed,condensed[1:]):
            total+=add_segment(net,netcode,a,b,width,layer)
    return total,vias


# Give every connected header pad a short escape and a layer transition.
# This keeps later traces from trapping a pin between two routed buses.
for net, nodes in list(pad_nodes.items()):
    escaped=[]
    width=0.4 if net in ("/3V3","/5V_USB","/GPS_VCC") else 0.25
    for x,y,netcode,ref,number in nodes:
        if ref == "J1":
            target=(x+3 if x < 118.5 else x-3,y)
        elif ref == "J2":
            target=(x-3,y)
        elif ref in ("J3","J4","J5"):
            target=(x,y+3)
        elif ref.startswith("SW"):
            target=(x,y-2)
        else:
            target=(x,y-3)
        layer=1 if width>0.25 else 0
        add_segment(net,netcode,(x,y),target,width,layer)
        via=k.PCB_VIA(board)
        via.SetPosition(pt(*target)); via.SetWidth(k.FromMM(0.7))
        via.SetDrill(k.FromMM(0.3)); via.SetViaType(k.VIATYPE_THROUGH)
        via.SetLayerPair(k.F_Cu,k.B_Cu); via.SetNetCode(netcode)
        board.Add(via)
        for ll in range(2):
            obstacles[ll].append(("circle",net,*target,0.35,0.35,False))
        existing_vias.add((*target,netcode))
        escaped.append((*target,netcode,ref,number))
    pad_nodes[net]=escaped

priority=["/BUTTON_1","/BUTTON_2","/AUX_SCL","/AUX_SDA","/IMU_SDA","/IMU_SCL","/3V3","/5V_USB","/GPS_VCC",
          "/TFT_DC","/TFT_MOSI","/TFT_SCK","/GPS_RX","/GPS_TX","/GND"]
order=sorted(pad_nodes,key=lambda n:priority.index(n))
report=[]
for net in order:
    if net == "/GND":
        continue
    width=0.4 if net in ("/3V3","/5V_USB","/GPS_VCC") else 0.25
    nodes=pad_nodes[net]
    tree=[nodes[0]]; todo=list(nodes[1:]); length=0; via_count=0
    while todo:
        start,target=min(((a,b) for a in tree for b in todo),key=lambda pair:math.dist(pair[0][:2],pair[1][:2]))
        masks=[raster(net,width,ll) for ll in range(2)]
        via_masks=[raster(net,0.7,ll) for ll in range(2)]
        path=find_path(start,target,masks,via_masks,prefer_back=width>0.25)
        if path is None:
            raise RuntimeError("Cannot route "+net+" "+str(start)+" -> "+str(target))
        ll,vv=add_path(net,start,target,path,width); length+=ll; via_count+=vv
        tree.append(target); todo.remove(target)
    report.append({"net":net,"pins":len(nodes),"length_mm":round(length,2),"vias":via_count,"width_mm":width})
    print(net, f"{length:.1f} mm, {via_count} vias", flush=True)
for layer in (k.F_Cu,k.B_Cu):
    zone=k.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNetCode(pad_nodes["/GND"][0][2])
    zone.SetLocalClearance(k.FromMM(0.25))
    zone.SetMinThickness(k.FromMM(0.25))
    zone.SetPadConnection(k.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(k.FromMM(0.25))
    zone.SetThermalReliefSpokeWidth(k.FromMM(0.3))
    outline=zone.Outline(); outline.NewOutline()
    for x,y in ((100.6,100.6),(159.4,100.6),(159.4,139.4),(100.6,139.4)):
        outline.Append(k.FromMM(x),k.FromMM(y))
    board.Add(zone)
report.append({"net":"/GND","pins":len(pad_nodes["/GND"]),"connection":"front and back ground planes"})
k.SaveBoard(str(ROOT/(NAME+".kicad_pcb")),board)
(ROOT/"routing_report.json").write_text(json.dumps(report,indent=2)+"\n")
print("Routed",len(report),"nets")
