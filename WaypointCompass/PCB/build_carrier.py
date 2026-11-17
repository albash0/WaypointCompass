#!/usr/bin/env python3
"""Generate the editable KiCad carrier from module_config.json.

Run with KiCad's bundled Python so pcbnew is available. The modules are
represented by their through-hole header landing patterns; no bare ICs are assembled here.
"""
import json
import math
import re
import uuid
import subprocess
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew as k
import wx

APP = wx.App(False)

ROOT = Path(__file__).resolve().parent
NAME = "WaypointCompassCarrier"
NAMESPACE = uuid.UUID("01cc7ca6-f0de-4462-bf52-982b83b7f35b")


def uid(name):
    return str(uuid.uuid5(NAMESPACE, name))


def q(value):
    return json.dumps(str(value))


def pt(x, y):
    return k.VECTOR2I(k.FromMM(x), k.FromMM(y))


def through_layers():
    layers = k.LSET.AllCuMask()
    layers.AddLayer(k.F_Mask)
    layers.AddLayer(k.B_Mask)
    return layers


def effect(size=1.27, extra=""):
    return f"(effects (font (size {size} {size})) {extra})"


def make_schematic(config):
    root_id = uid("schematic")
    definitions, instances, wires, labels, marks = [], [], [], [], []
    for module in config["modules"]:
        ref, value = module["ref"], module["value"]
        pins = module["pins"]
        symbol_name = "Socket_" + ref
        symbol_id = "CompassCarrier:" + symbol_name
        is_button = module.get("kind") == "button"
        height = (len(pins) - 1) * 2.54 + 5.08
        pin_defs = []
        for i, pin in enumerate(pins):
            y = -i * 2.54
            pin_defs.append(f'''(pin passive line (at -12.7 {y} 0) (length 2.54)
                (name {q(pin['name'])} {effect()})
                (number {q(pin['number'])} {effect()}))''')
        definitions.append(f'''(symbol {q(symbol_id)} (pin_names (offset 0.508))
            (exclude_from_sim no) (in_bom yes) (on_board yes)
            (property "Reference" "J" (at 0 5.08 0) {effect()})
            (property "Value" {q(value)} (at 0 2.54 0) {effect()})
            (property "Footprint" {q('CompassCarrier:'+module['footprint'])}
                (at 0 0 0) {effect(extra='(hide yes)')})
            (property "Datasheet" "" (at 0 0 0) {effect(extra='(hide yes)')})
            (symbol {q(symbol_name+'_0_1')}
                (rectangle (start -10.16 2.54) (end 12.7 {-height+2.54})
                    (stroke (width 0.254) (type default)) (fill (type background))))
            (symbol {q(symbol_name+'_1_1')} {' '.join(pin_defs)}))''')
        if is_button:
            definitions[-1] = f'''(symbol {q(symbol_id)} (pin_names (offset 0) (hide yes))
                (pin_numbers (hide yes)) (exclude_from_sim no) (in_bom yes) (on_board yes)
                (property "Reference" "SW" (at 0 5.08 0) {effect()})
                (property "Value" "6x6 tactile" (at 0 -5.08 0) {effect()})
                (property "Footprint" {q('CompassCarrier:'+module['footprint'])} (at 0 0 0) {effect(extra='(hide yes)')})
                (symbol {q(symbol_name+'_0_1')}
                    (circle (center -2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
                    (circle (center 2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
                    (polyline (pts (xy -2.54 1.27) (xy 2.54 1.27)) (stroke (width 0) (type default)) (fill (type none)))
                    (polyline (pts (xy 0 1.27) (xy 0 3.048)) (stroke (width 0) (type default)) (fill (type none))))
                (symbol {q(symbol_name+'_1_1')}
                    (pin passive line (at -5.08 0 0) (length 2.54) (name "1" {effect()}) (number "1" {effect()}))
                    (pin passive line (at 5.08 0 180) (length 2.54) (name "2" {effect()}) (number "2" {effect()}))))'''
        sx, sy = module["schematic_at"]
        instance_id = uid("symbol-" + ref)
        instance_pins = " ".join(
            f'(pin {q(p["number"])} (uuid {uid(ref+"-pin-"+str(p["number"]))}))'
            for p in pins
        )
        instances.append(f'''(symbol (lib_id {q(symbol_id)}) (at {sx} {sy} 0) (unit 1)
            (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
            (uuid {instance_id})
            (property "Reference" {q(ref)} (at {sx} {sy-5.08} 0) {effect()})
            (property "Value" {q(value)} (at {sx} {sy+5.08 if is_button else sy-2.54} 0) {effect()})
            (property "Footprint" {q('CompassCarrier:'+module['footprint'])}
                (at {sx} {sy} 0) {effect(extra='(hide yes)')})
            (property "Datasheet" "" (at {sx} {sy} 0) {effect(extra='(hide yes)')})
            {instance_pins}
            (instances (project {q(NAME)}
                (path {q('/'+root_id)} (reference {q(ref)}) (unit 1)))))''')
        for i, pin in enumerate(pins):
            px, py = (sx + (-5.08 if i == 0 else 5.08), sy) if is_button else (sx - 12.7, sy + i * 2.54)
            if pin.get("net"):
                end_x = px + (7.62 if is_button and i == 1 else -7.62)
                wires.append(f'''(wire (pts (xy {end_x} {py}) (xy {px} {py}))
                    (stroke (width 0) (type default)) (uuid {uid(ref+'-wire-'+str(i))}))''')
                labels.append(f'''(label {q(pin['net'])} (at {end_x} {py} 0)
                    {effect(extra='(justify left bottom)')}
                    (uuid {uid(ref+'-label-'+str(i))}))''')
            else:
                marks.append(f'(no_connect (at {px} {py}) (uuid {uid(ref+"-nc-"+str(i))}))')
    notes = [
        (25.4, 15.24, "WAYPOINT COMPASS / HEADER CARRIER", 2.0),
        (25.4, 22.86, "Power: USB on the SuperMini. All signal levels are 3.3 V.", 1.27),
        (25.4, 175.26, "GY-271 SDA/SCL connect to GY-521 XDA/XCL; firmware enables bypass.", 1.27),
        (25.4, 182.88, "TFT: CS = GND, RST = 3V3; matches the working firmware.", 1.27),
        (25.4, 190.50, "JP1: fit ONE shunt for GPS voltage. Confirm the GPS board's VCC rating.", 1.27),
        (25.4, 165.1, "SW1 = GPIO1; SW2 = GPIO2. Active LOW; configure INPUT_PULLUP in firmware.", 1.27),
    ]
    for i, (x, y, text, size) in enumerate(notes):
        marks.append(f'(text {q(text)} (at {x} {y} 0) {effect(size, "(justify left)")} (uuid {uid("note-"+str(i))}))')
    content = f'''(kicad_sch (version 20250114) (generator "eeschema")
        (uuid {root_id}) (paper "A4")
        (title_block (title "Waypoint Compass Header Carrier")
            (date "2026-10-01") (rev "B")
            (comment 1 "Direct soldered headers and tactile buttons; USB-powered"))
        (lib_symbols {' '.join(definitions)})
        {' '.join(wires)} {' '.join(labels)} {' '.join(marks)} {' '.join(instances)}
        (embedded_fonts no))'''
    (ROOT / (NAME + ".kicad_sch")).write_text(content)
    library_definitions = ' '.join(definitions).replace('(symbol "CompassCarrier:', '(symbol "')
    library = f'''(kicad_symbol_lib (version 20250114) (generator "kicad_symbol_editor")
        {library_definitions})'''
    (ROOT / "CompassCarrier.kicad_sym").write_text(library)
    (ROOT / "sym-lib-table").write_text('''(sym_lib_table
        (lib (name "CompassCarrier") (type "KiCad")
            (uri "${KIPRJMOD}/CompassCarrier.kicad_sym") (options "") (descr "Carrier headers")))''')


def line(board_or_fp, x1, y1, x2, y2, layer, width=0.15):
    item = k.PCB_SHAPE(board_or_fp)
    item.SetShape(k.SHAPE_T_SEGMENT)
    item.SetStart(pt(x1, y1))
    item.SetEnd(pt(x2, y2))
    item.SetWidth(k.FromMM(width))
    item.SetLayer(layer)
    board_or_fp.Add(item)


def rectangle(board_or_fp, bounds, layer, width=0.15):
    x1, y1, x2, y2 = bounds
    for a, b in [((x1,y1),(x2,y1)), ((x2,y1),(x2,y2)),
                 ((x2,y2),(x1,y2)), ((x1,y2),(x1,y1))]:
        line(board_or_fp, *a, *b, layer, width)


def board_text(board, text, x, y, size=1.0, layer=k.F_SilkS, align=None):
    item = k.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(pt(x, y))
    item.SetTextSize(pt(size, size))
    item.SetTextThickness(k.FromMM(0.15 if size >= 1 else 0.12))
    item.SetLayer(layer)
    if layer == k.B_SilkS:
        item.SetMirrored(True)
    if align is not None:
        item.SetHorizJustify(align)
    board.Add(item)


def footprint_for(board, module, nets):
    is_button = module.get("kind") == "button"
    if is_button:
        library = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Button_Switch_THT.pretty"
        fp = k.FootprintLoad(library, module["footprint"])
        model_file = module["footprint"] + ".step"
        model_source = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels/Button_Switch_THT.3dshapes") / model_file
        (ROOT / "3dmodels").mkdir(exist_ok=True)
        shutil.copy2(model_source, ROOT / "3dmodels" / model_file)
        for model in fp.Models():
            model.m_Filename = "${KIPRJMOD}/3dmodels/" + model_file
        for pad in fp.Pads():
            pad.SetNet(nets[module["actual_nets"][pad.GetNumber()]])
    else:
        fp = k.FOOTPRINT(board)
    fp.SetReference(module["ref"])
    fp.SetValue(module["value"])
    fp.SetAttributes(k.FP_THROUGH_HOLE)
    fp.SetFPID(k.LIB_ID("CompassCarrier", module["footprint"]))
    path = k.KIID_PATH()
    path.push_back(k.KIID(uid("schematic")))
    path.push_back(k.KIID(uid("symbol-"+module["ref"])))
    fp.SetPath(path)
    for i, pin in enumerate([] if is_button else module["pins"]):
        pad = k.PAD(fp)
        pad.SetNumber(str(pin["number"]))
        pad.SetAttribute(k.PAD_ATTRIB_PTH)
        pad.SetShape(k.PAD_SHAPE_RECT if pin["number"] == "1" else k.PAD_SHAPE_CIRCLE)
        pad.SetSize(pt(1.8, 1.8))
        pad.SetDrillSize(pt(1, 1))
        pad.SetLayerSet(through_layers())
        pad.SetPosition(pt(*pin["at"]))
        net_name = module["actual_nets"].get(str(pin["number"]))
        if net_name:
            pad.SetNet(nets[net_name])
        fp.Add(pad)
    if "courtyard" in module:
        rectangle(fp, module["courtyard"], k.F_CrtYd, 0.05)
    for box in module.get("socket_outlines", []):
        rectangle(fp, box, k.F_SilkS, 0.12)
    if "body" in module:
        rectangle(fp, module["body"], k.F_Fab, 0.1)
    for cx,cy,radius in module.get("circles", []):
        item = k.PCB_SHAPE(fp)
        item.SetShape(k.SHAPE_T_CIRCLE)
        item.SetCenter(pt(cx,cy))
        item.SetEnd(pt(cx+radius,cy))
        item.SetWidth(k.FromMM(0.1))
        item.SetLayer(k.F_Fab)
        fp.Add(item)
    fp.Reference().SetPosition(pt(*module.get("ref_at", [0,-3])))
    fp.Reference().SetTextSize(pt(1,1))
    fp.Reference().SetTextThickness(k.FromMM(0.15))
    fp.Reference().SetVisible(False)
    fp.Value().SetLayer(k.F_Fab)
    fp.Value().SetVisible(False)
    fp.SetPosition(pt(*module["pcb_at"]))
    fp.SetOrientationDegrees(module.get("rotation", 0))
    if module.get("side") == "back":
        fp.Flip(fp.GetPosition(), k.FLIP_DIRECTION_LEFT_RIGHT)
    board.Add(fp)
    return fp


def make_board(config):
    board = k.BOARD()
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(k.FromMM(1.6))
    ds.m_MinClearance = k.FromMM(0.2)
    ds.m_TrackMinWidth = k.FromMM(0.25)
    ds.m_ViasMinSize = k.FromMM(0.7)
    ds.m_MinThroughDrill = k.FromMM(0.3)
    ds.m_CopperEdgeClearance = k.FromMM(0.5)
    nets = {}
    for name in sorted({name for m in config["modules"] for name in m["actual_nets"].values()}):
        net = k.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net
    libdir = ROOT / "CompassCarrier.pretty"
    libdir.mkdir(exist_ok=True)
    for module in config["modules"]:
        fp = footprint_for(board, module, nets)
        standalone = k.Cast_to_FOOTPRINT(fp.Duplicate(False))
        if standalone.GetLayer() == k.B_Cu:
            standalone.Flip(standalone.GetPosition(), k.FLIP_DIRECTION_LEFT_RIGHT)
        standalone.SetPosition(pt(0,0))
        standalone.SetOrientationDegrees(0)
        standalone.Reference().SetText("REF**")
        for pad in standalone.Pads():
            pad.SetNetCode(0)
        k.PCB_IO_KICAD_SEXPR().FootprintSave(str(libdir), standalone)
        for text in module.get("labels", []):
            x, y = module["pcb_at"]
            back = module.get("side") == "back"
            board_text(board, text[0], x+(-text[1] if back else text[1]), y+text[2],
                       text[3] if len(text)>3 else 0.8, k.B_SilkS if back else k.F_SilkS)
    (ROOT / "fp-lib-table").write_text('''(fp_lib_table
        (lib (name "CompassCarrier") (type "KiCad")
            (uri "${KIPRJMOD}/CompassCarrier.pretty") (options "") (descr "Through-hole module headers")))''')
    x, y, width, height = config["board"]
    rectangle(board, (x,y,x+width,y+height), k.Edge_Cuts, 0.05)
    holes = [(x,y,2.2) for x,y in config.get("mounting_holes", [])]
    holes += [(x,y,2.0) for x,y in config.get("tft_holes", [])]
    for i,(hx,hy,diameter) in enumerate(holes):
        fp = k.FOOTPRINT(board)
        fp.SetReference("H"+str(i+1))
        fp.SetValue(f"MountingHole_{diameter:.1f}mm")
        fp.SetAttributes(k.FP_BOARD_ONLY | k.FP_EXCLUDE_FROM_BOM | k.FP_EXCLUDE_FROM_POS_FILES)
        fp.SetFPID(k.LIB_ID("CompassCarrier", f"MountingHole_{diameter:.1f}mm_Carrier"))
        pad = k.PAD(fp)
        pad.SetNumber("")
        pad.SetAttribute(k.PAD_ATTRIB_NPTH)
        pad.SetShape(k.PAD_SHAPE_CIRCLE)
        pad.SetSize(pt(diameter,diameter))
        pad.SetDrillSize(pt(diameter,diameter))
        pad.SetLayerSet(through_layers())
        fp.Add(pad)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetPosition(pt(hx,hy))
        board.Add(fp)
        standalone = k.Cast_to_FOOTPRINT(fp.Duplicate(False))
        standalone.SetPosition(pt(0,0))
        standalone.Reference().SetText("REF**")
        k.PCB_IO_KICAD_SEXPR().FootprintSave(str(libdir), standalone)
    for text in config.get("board_text", []):
        board_text(board, *text)
    board_path = ROOT / (NAME + ".kicad_pcb")
    k.SaveBoard(str(board_path), board)
    # Native pad tokens also initialize KiCad 10's outer mask properties.
    for path in [board_path] + list(libdir.glob("*.kicad_mod")):
        source = re.sub(r'\(layers "\*\.Cu"(?: "[^"]+")*\)',
                        '(layers "*.Cu" "*.Mask")', path.read_text())
        path.write_text(source)
    return board


def make_project():
    project = {
        "meta": {"filename":NAME+".kicad_pro", "version":3},
        "board": {"design_settings": {
            "rules": {"min_clearance":0.2, "min_track_width":0.25,
                      "min_via_diameter":0.7, "min_through_hole_diameter":0.3,
                      "min_copper_edge_clearance":0.5,
                      "min_hole_clearance":0.25, "min_silk_clearance":0.15},
            "defaults": {"board_outline_line_width":0.05,
                         "copper_line_width":0.25,
                         "silk_line_width":0.15},
        }},
        "net_settings": {"meta":{"version":4}, "classes":[{
            "name":"Default", "description":"2-layer header carrier",
            "clearance":0.2, "track_width":0.25,
            "via_diameter":0.7, "via_drill":0.3,
            "microvia_diameter":0.3, "microvia_drill":0.1,
            "diff_pair_width":0.25, "diff_pair_gap":0.25,
            "diff_pair_via_gap":0.25,
        }]},
        "schematic": {"legacy_lib_dir":"", "legacy_lib_list":[]},
    }
    (ROOT/(NAME+".kicad_pro")).write_text(json.dumps(project, indent=2)+"\n")


if __name__ == "__main__":
    config = json.loads((ROOT/"module_config.json").read_text())
    make_project()
    make_schematic(config)
    subprocess.run([
        "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli", "sch", "export", "netlist",
        "--format", "kicadxml", "-o", str(ROOT/"netlist.xml"),
        str(ROOT/(NAME+".kicad_sch"))], check=True)
    net_map = {m["ref"]: {} for m in config["modules"]}
    for net in ET.parse(ROOT/"netlist.xml").findall("./nets/net"):
        for node in net.findall("node"):
            net_map[node.attrib["ref"]][node.attrib["pin"]] = net.attrib["name"]
    for module in config["modules"]:
        module["actual_nets"] = net_map[module["ref"]]
    make_board(config)
    print("Generated", ROOT/NAME)
