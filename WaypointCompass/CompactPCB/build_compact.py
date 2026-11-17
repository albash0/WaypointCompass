"""Generate the self-contained KiCad compact prototype (uses bundled KiCad Python)."""
import json,re,uuid,shutil,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import pcbnew as k
import wx
APP=wx.App(False)
ROOT=Path(__file__).resolve().parent; BASE=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport'); NAME='WaypointCompassCompact'
config=json.loads((ROOT/'design.json').read_text()); parts=config['parts']
NS=uuid.UUID('c1791462-feca-4539-8f68-c345ee892eed')
def uid(x):return str(uuid.uuid5(NS,x))
def q(x):return json.dumps(str(x))
def pt(x,y):return k.VECTOR2I(k.FromMM(x),k.FromMM(y))
def eff(size=1.0,extra=''):return f'(effects (font (size {size} {size})) {extra})'

def schematic():
    origins={'mcu':(65,70),'sensors':(195,70),'usb':(325,70),'protection':(455,70),'charger':(65,250),'3v3':(195,250),'gpspower':(325,250),'display':(455,250),'test':(565,70)}
    definitions=[];instances=[];wires=[];labels=[];markers=[]
    layout={}; counters={}
    for block in origins:
        group=[p for p in parts if p['block']==block]
        core=[p for p in group if p['ref'].startswith('U') or p['ref'] in ('J1','J2')]
        small=[p for p in group if p not in core]
        x,y=origins[block]
        for i,p in enumerate(core):layout[p['ref']]=(x+(i%2)*55,y+(i//2)*50)
        yy=y+(70 if block=='mcu' else 52)
        for i,p in enumerate(small):layout[p['ref']]=(x,y+i*14) if block=='test' else (x-30+(i%3)*40,yy+(i//3)*17)
        markers.append(f'(text {q(block.upper())} (at {x-40} {y-25} 0) {eff(2,"(justify left)")} (uuid {uid("heading-"+block)}))')
    for p in parts:
        ref=p['ref'];sym='D_'+ref; pinlayout={}; groups=[]
        # Stack only identically named ground pins on ICs; retain every pin number.
        for pin in p['pins']:
            key='GND' if pin['name'] in ('GND','VSS','PGND') and p['nets'][pin['number']]=='GND' else pin['number']
            group=next((g for g in groups if g[0]==key),None)
            if group:group[1].append(pin)
            else:groups.append([key,[pin]])
        simple=ref.startswith(('R','C','L','D','TP','SW','JP')) or ref in ('Q1','Q2')
        defs=[]; rows=(len(groups)+1)//2
        half=5.08 if simple and len(groups)<=3 else 12.7
        bodyhalf=half-2.54
        for i,(_,pp) in enumerate(groups):
            side=-1 if i<rows else 1;row=i if i<rows else i-rows
            yy=-row*2.54; xx=side*half;ang=0 if side==-1 else 180
            for j,pin in enumerate(pp):
                number=pin['number'];pinlayout[number]=(xx,yy,side)
                pin_length=3.81 if ref.startswith('R') else 4.58 if ref.startswith('C') else 2.54
                ptype='passive' if j and pin['type']=='power_in' else pin['type']
                defs.append(f'(pin {ptype} line (at {xx} {yy} {ang}) (length {pin_length}) '+('(hide yes)' if j else '')+f'(name {q(pin["name"])} {eff(.85)}) (number {q(number)} {eff(.85)}))')
        height=(rows-1)*2.54
        graphic=f'(rectangle (start {-bodyhalf} 1.27) (end {bodyhalf} {-height-1.27}) (stroke (width .2) (type default)) (fill (type background)))'
        if ref.startswith('R'):
            graphic='(rectangle (start -1.27 .762) (end 1.27 -.762) (stroke (width .2) (type default)) (fill (type none)))'
        elif ref.startswith('C'):
            graphic='(polyline (pts (xy -.5 -1.27) (xy -.5 1.27)) (stroke (width .2) (type default)) (fill (type none))) (polyline (pts (xy .5 -1.27) (xy .5 1.27)) (stroke (width .2) (type default)) (fill (type none)))'
        definitions.append(f'''(symbol "Compact:{sym}" (pin_names (offset .508)) (exclude_from_sim no) (in_bom yes) (on_board yes)
          (property "Reference" {q(ref)} (at 0 3.81 0) {eff()})
          (property "Value" {q(p['value'])} (at 0 1.27 0) {eff()})
          (property "Footprint" {q('Compact:'+p['footprint'].split(':')[1])} (at 0 0 0) {eff(extra='(hide yes)')})
          (symbol "{sym}_0_1" {graphic}) (symbol "{sym}_1_1" {' '.join(defs)}))''')
        x,y=layout[ref];x=round(x/1.27)*1.27;y=round(y/1.27)*1.27;iid=uid('symbol-'+ref)
        instance_pins=' '.join(f'(pin {q(pin["number"])} (uuid {uid(ref+"-pin-"+pin["number"])}))' for pin in p['pins'])
        instances.append(f'''(symbol (lib_id "Compact:{sym}") (at {x} {y} 0) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
          (uuid {iid}) (property "Reference" {q(ref)} (at {x} {y-4.3} 0) {eff()})
          (property "Value" {q(p['value'])} (at {x} {y-2.5} 0) {eff(.85)})
          (property "Footprint" {q('Compact:'+p['footprint'].split(':')[1])} (at {x} {y} 0) {eff(extra='(hide yes)')})
          {instance_pins} (instances (project "{NAME}" (path "/{uid('schematic')}" (reference {q(ref)}) (unit 1)))))''')
        seen=set()
        for pin in p['pins']:
            xx,yy,side=pinlayout[pin['number']];px=x+xx;py=y-yy;net=p['nets'][pin['number']]
            if (px,py,net) in seen:continue
            seen.add((px,py,net))
            if net:
                ex=px+side*5.08
                wires.append(f'(wire (pts (xy {px} {py}) (xy {ex} {py})) (stroke (width 0) (type default)) (uuid {uid(ref+"-wire-"+pin["number"])}))')
                labels.append(f'(label {q(net)} (at {ex} {py} 0) {eff(.85,"(justify "+("right" if side==-1 else "left")+" bottom)")} (uuid {uid(ref+"-label-"+pin["number"])}))')
            else:markers.append(f'(no_connect (at {px} {py}) (uuid {uid(ref+"-nc-"+pin["number"])}))')
    # Explicit power-source flags for externally supplied VBUS and the two ground references.
    for i,net in enumerate(('VBUS','GND','CELL_NEG')):
        s='PWR_'+str(i);x=round(565/1.27)*1.27;y=round((245+i*10)/1.27)*1.27;ref='#FLG0'+str(i+1)
        definitions.append(f'(symbol "Compact:{s}" (power) (pin_names (offset 0) (hide yes)) (exclude_from_sim no) (in_bom no) (on_board no) (property "Reference" "#FLG" (at 0 2 0) {eff(extra="(hide yes)")}) (property "Value" "PWR_FLAG" (at 0 2 0) {eff(.85)}) (symbol "{s}_1_1" (pin power_out line (at 0 0 90) (length 0) (name "pwr" {eff()}) (number "1" {eff()}))))')
        instances.append(f'(symbol (lib_id "Compact:{s}") (at {x} {y} 0) (unit 1) (exclude_from_sim no) (in_bom no) (on_board no) (uuid {uid(ref)}) (property "Reference" "{ref}" (at {x} {y} 0) {eff(extra="(hide yes)")}) (property "Value" "PWR_FLAG" (at {x} {y-2} 0) {eff(.85)}) (pin "1" (uuid {uid(ref+"pin")})) (instances (project "{NAME}" (path "/{uid("schematic")}" (reference "{ref}") (unit 1)))))')
        labels.append(f'(label "{net}" (at {x} {y} 0) {eff(.85,"(justify left bottom)")} (uuid {uid(ref+"label")}))')
    notes=['1S Li-ion/LiPo only, 4.2 V charge. J3 pin1 + / pin2 cell negative.','JP2 open:100 mA for 300-500 mAh. Bridge:251 mA for 500-1000 mAh rated cells.','J5: external 10k 103AT-2 NTC taped to cell. No NTC means charging inhibited.','GPS JP1: bridge 2-3 for 5 V; bridge 1-2 only for a 3.3 V-rated breakout.','BQ29700 isolates CELL_NEG from GND through Q1/Q2 common drains.','MCU MINI-1U external antenna optional; compass uses no radio.','TFT VCC is 5 V, shared with the GPS boost; SPI logic remains 3.3 V.',
      'Prototype C1: bench validation required before relying on battery charging.']
    for i,t in enumerate(notes):markers.append(f'(text {q(t)} (at 20 {385+i*2.54} 0) {eff(.95,"(justify left)")} (uuid {uid("note"+str(i))}))')
    content=f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {uid('schematic')}) (paper "A2")
      (title_block (title "Compact Waypoint Compass / USB-C Li-ion") (date "2026-10-02") (rev "C1 PROTOTYPE"))
      (lib_symbols {' '.join(definitions)}) {' '.join(wires+labels+markers+instances)} (embedded_fonts no))'''
    (ROOT/(NAME+'.kicad_sch')).write_text(content)
    (ROOT/'Compact.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor") '+ ' '.join(definitions).replace('(symbol "Compact:','(symbol "')+')')
    (ROOT/'sym-lib-table').write_text('(sym_lib_table (lib (name "Compact") (type "KiCad") (uri "${KIPRJMOD}/Compact.kicad_sym") (options "") (descr "Compact local symbols")))')

def project():
    data={'meta':{'filename':NAME+'.kicad_pro','version':3},'board':{'design_settings':{'rules':{'min_clearance':.10,'min_track_width':.12,'min_via_diameter':.4,'min_through_hole_diameter':.2,'min_copper_edge_clearance':.25,'min_hole_clearance':.2,'min_silk_clearance':.0},'defaults':{'board_outline_line_width':.05,'silk_line_width':.12}}},'net_settings':{'meta':{'version':5},'classes':[{'name':'Default','description':'4-layer compact prototype','clearance':.10,'track_width':.15,'via_diameter':.4,'via_drill':.2,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.15,'diff_pair_gap':.15,'diff_pair_via_gap':.2}]},'schematic':{'legacy_lib_dir':'','legacy_lib_list':[]}}
    (ROOT/(NAME+'.kicad_pro')).write_text(json.dumps(data,indent=2)+'\n')

def line(owner,a,b,layer=k.Edge_Cuts,width=.05):
    g=k.PCB_SHAPE(owner);g.SetShape(k.SHAPE_T_SEGMENT);g.SetStart(pt(*a));g.SetEnd(pt(*b));g.SetLayer(layer);g.SetWidth(k.FromMM(width));owner.Add(g)
def text(board,t,x,y,layer=k.B_SilkS,size=.85):
    a=k.PCB_TEXT(board);a.SetText(t);a.SetPosition(pt(x+100,y+100));a.SetTextSize(pt(size,size));a.SetTextThickness(k.FromMM(.10));a.SetLayer(layer);a.SetMirrored(layer==k.B_SilkS);board.Add(a)

def board():
    netlist=ET.parse(ROOT/'netlist.xml').getroot();pn={}; netnames=[]
    for n in netlist.find('nets'):
        netnames.append(n.attrib['name'])
        for node in n.findall('node'):pn[(node.attrib['ref'],node.attrib['pin'])]=n.attrib['name']
    print('Create board',flush=True)
    b=k.BOARD();b.SetCopperLayerCount(4);b.GetDesignSettings().SetBoardThickness(k.FromMM(1.0))
    for layer in [k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu]:b.SetLayerName(layer,k.LayerName(layer))
    nets={}
    for name in netnames:
        n=k.NETINFO_ITEM(b,name);b.Add(n);nets[name]=n
    libdir=ROOT/'Compact.pretty';libdir.mkdir(exist_ok=True);md=ROOT/'3dmodels';md.mkdir(exist_ok=True)
    for p in parts:
        print('Footprint',p['ref'],flush=True)
        lib,fpname=p['footprint'].split(':')
        library=ROOT.parent/'PCB/CompassCarrier.pretty' if lib=='CompassCarrier' else BASE/'footprints'/(lib+'.pretty')
        f=k.FootprintLoad(str(library),fpname);assert f is not None,p['footprint']
        # Replace copied reference designator/value; reduce silk clutter on dense SMT.
        f.SetAttributes(f.GetAttributes() & ~k.FP_EXCLUDE_FROM_BOM & ~k.FP_EXCLUDE_FROM_POS_FILES)
        f.SetReference(p['ref']);f.SetValue(p['value']);f.Reference().SetVisible(False);f.Value().SetVisible(False)
        f.SetFPID(k.LIB_ID('Compact',fpname));path=k.KIID_PATH();path.push_back(k.KIID(uid('schematic')));path.push_back(k.KIID(uid('symbol-'+p['ref'])));f.SetPath(path)
        for pad in f.Pads():
            number=pad.GetNumber()
            if number and (p['ref'],number) in pn:pad.SetNet(nets[pn[(p['ref'],number)]])
            elif number and pad.GetAttribute()!=k.PAD_ATTRIB_NPTH:
                assert number not in p['nets'] or p['nets'][number] is None,(p['ref'],number)
        for m in f.Models():
            original=m.m_Filename
            if '${KIPRJMOD}' in original:
                src=ROOT.parent/'PCB'/original.replace('${KIPRJMOD}/','')
            else:
                suffix=re.sub(r'^\$\{[^}]+\}/','',original);src=BASE/'3dmodels'/suffix
            if src.is_file():
                target=md/src.name;shutil.copy2(src,target);m.m_Filename='${KIPRJMOD}/3dmodels/'+src.name
                # Copy the STEP counterpart for export substitution.
                if src.suffix.lower()=='.wrl' and src.with_suffix('.step').is_file():shutil.copy2(src.with_suffix('.step'),md/src.with_suffix('.step').name)
        if p['ref']=='J1':
            for g in list(f.GraphicalItems()):
                if g.GetLayer()==k.F_SilkS:f.Remove(g)
        standalone=k.Cast_to_FOOTPRINT(f.Duplicate(False));standalone.Reference().SetText('REF**')
        k.PCB_IO_KICAD_SEXPR().FootprintSave(str(libdir),standalone)
        b.Add(f)
        if p['side']=='back':f.Flip(pt(0,0),k.FLIP_DIRECTION_LEFT_RIGHT)
        f.SetOrientationDegrees(p['angle']);f.SetPosition(pt(p['at'][0]+100,p['at'][1]+100))
    # Four NPTH support/case holes. Left corners are reserved for the buttons.
    for i,(x,y,d) in enumerate([(47.67,10.37,2),(47.67,29.63,2),(50.5,3,2.2),(50.5,37,2.2)],1):
        f=k.FOOTPRINT(b);f.SetReference('H'+str(i));f.SetValue('MOUNT');f.SetAttributes(k.FP_BOARD_ONLY|k.FP_EXCLUDE_FROM_BOM|k.FP_EXCLUDE_FROM_POS_FILES);f.Reference().SetVisible(False);f.Value().SetVisible(False)
        pad=k.PAD(f);pad.SetAttribute(k.PAD_ATTRIB_NPTH);pad.SetShape(k.PAD_SHAPE_CIRCLE);pad.SetSize(pt(d,d));pad.SetDrillSize(pt(d,d));pad.SetLayerSet(k.LSET.AllCuMask());f.Add(pad);f.SetPosition(pt(x+100,y+100));b.Add(f)
    for a,c in [((100,100),(154,100)),((154,100),(154,140)),((154,140),(100,140)),((100,140),(100,100))]:line(b,a,c)
    # Explicit assembly labels remain readable; references are present on Fab layers.
    for t,x,y,layer in [('CAL',5,1.8,k.F_SilkS),('ACTION',5,38.2,k.F_SilkS),('WAYPOINT C1',27,3,k.F_SilkS),('100/250',44.5,1,k.B_SilkS),('FRONT <',13,1,k.B_SilkS)]:text(b,t,x,y,layer)
    (ROOT/'fp-lib-table').write_text('(fp_lib_table (lib (name "Compact") (type "KiCad") (uri "${KIPRJMOD}/Compact.pretty") (options "") (descr "Local verified library copies")))')
    path=ROOT/(NAME+'.kicad_pcb');k.SaveBoard(str(path),b)
    # KiCad 10 native mask token repair for PTH/NPTH.
    for path in [path]+list(libdir.glob('*.kicad_mod')):
        path.write_text(re.sub(r'\(layers "\*\.Cu"(?: "[^"]+")*\)','(layers "*.Cu" "*.Mask")',path.read_text()))
    return b
if __name__=='__main__':
    import sys
    if '--schematic' in sys.argv:project();schematic()
    elif '--board' in sys.argv:board();project()
