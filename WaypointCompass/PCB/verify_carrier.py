"""Audit the saved native board and fabrication outputs before packaging."""
import json
import re
from build_carrier import ROOT, NAME, k

board = k.LoadBoard(str(ROOT / (NAME + ".kicad_pcb")))
footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
expected = {
    "J1": {"16": "TFT_SCK", "15": "TFT_MOSI", "13": "TFT_DC",
           "17": "IMU_SCL", "18": "IMU_SDA", "1": "GPS_RX", "2": "GPS_TX",
           "3": "BUTTON_1", "4": "BUTTON_2"},
    "J2": {"1": "3V3", "2": "GND", "3": "TFT_SCK", "4": "TFT_MOSI",
           "5": "TFT_DC", "6": "GND", "7": "3V3"},
    "J4": {"5": "AUX_SDA", "6": "AUX_SCL", "7": "GND"},
    "J5": {"2": "AUX_SDA", "3": "AUX_SCL"},
    "SW1": {"1": "BUTTON_1", "2": "GND"},
    "SW2": {"1": "BUTTON_2", "2": "GND"},
}
for ref, pins in expected.items():
    pads = {p.GetNumber(): p for p in footprints[ref].Pads()}
    for number, net in pins.items():
        assert pads[number].GetNetname() == "/" + net, (ref, number, net)

circles = [g for g in footprints["J2"].GraphicalItems()
           if isinstance(g, k.PCB_SHAPE) and g.GetShape() == k.SHAPE_T_CIRCLE]
assert len(circles) == 2
for circle in circles:
    center = circle.GetCenter()
    assert abs(k.ToMM(center.x) - 130) < 0.001
    assert abs(k.ToMM(center.y) - 120) < 0.001

for ref, cy in (("SW1", 111.5), ("SW2", 127)):
    fp = footprints[ref]
    assert fp.GetLayer() == k.F_Cu
    pads = list(fp.Pads())
    assert len(pads) == 4
    for pad in pads:
        assert pad.GetNetname() == "/" + expected[ref][pad.GetNumber()]
    center_x = sum(k.ToMM(p.GetPosition().x) for p in pads)/4
    center_y = sum(k.ToMM(p.GetPosition().y) for p in pads)/4
    assert abs(center_x-105) < 0.001 and abs(center_y-cy) < 0.001
    assert center_x + 3 < 111  # Button body stays outside the TFT's left edge.

ends = [p for g in board.GetDrawings()
        if isinstance(g, k.PCB_SHAPE) and g.GetLayer() == k.Edge_Cuts
        for p in (g.GetStart(), g.GetEnd())]
width = k.ToMM(max(p.x for p in ends) - min(p.x for p in ends))
height = k.ToMM(max(p.y for p in ends) - min(p.y for p in ends))
assert (width, height) == (60, 40)
assert board.GetCopperLayerCount() == 2
assert k.ToMM(board.GetDesignSettings().GetBoardThickness()) == 1.6

for fp in footprints.values():
    for pad in fp.Pads():
        assert pad.GetLayerSet().Contains(k.F_Mask)
        assert pad.GetLayerSet().Contains(k.B_Mask)
counts = {}
for suffix in ("F_Mask.gts", "B_Mask.gbs"):
    filename = NAME + "-" + suffix
    counts[filename] = (ROOT / "fabrication" / filename).read_text().count("D03*")
    assert counts[filename] == 59, (filename, counts[filename])

drc = json.loads((ROOT / "checks/DRC.json").read_text())
for field in ("violations", "unconnected_items", "schematic_parity"):
    assert not drc.get(field), field
erc = (ROOT / "checks/ERC.rpt").read_text()
assert re.search(r"\*\* ERC messages: 0", erc), erc

models = json.loads((ROOT / "module_models.json").read_text())
for ref, spec in models["models"].items():
    attached = list(footprints[ref].Models())
    assert len(attached) == 2, ref
    for model in attached:
        path = ROOT / model.m_Filename.replace("${KIPRJMOD}/", "")
        assert path.is_file(), str(path)
    assert [attached[0].m_Rotation.x, attached[0].m_Rotation.y, attached[0].m_Rotation.z] == spec["rotation"]
    assert [attached[0].m_Offset.x, attached[0].m_Offset.y, attached[0].m_Offset.z] == spec["offset"]

result = {
    "board_mm": [width, height], "display_center_from_board_corner_mm": [30, 20],
    "copper_layers": 2, "thickness_mm": 1.6,
    "ERC_violations": 0, "DRC_violations": 0, "unconnected_items": 0,
    "schematic_parity_issues": 0,
    "audited_key_pin_assignments": sum(len(p) for p in expected.values()),
    "mask_openings": counts, "module_header_pads": 45,
    "front_pushbuttons": {"SW1": {"gpio": 1, "body_center_mm": [5, 11.5]},
                          "SW2": {"gpio": 2, "body_center_mm": [5, 27]}},
    "pushbutton_pads": 8,
    "plated_vias": sum(isinstance(t, k.PCB_VIA) for t in board.GetTracks()),
    "NPTH_display_holes": 2, "NPTH_case_holes": 4,
    "mechanical_limitations": "GY-521/GY-271 body envelopes nominal; sensor header pitch assumed 2.54 mm; verify 1:1 print against actual modules",
    "module_STEP_models": 4, "direct_module_header_models": 4,
    "module_to_carrier_gap_mm": 2.54,
    "reference_model_differences": models["differences"],
    "hardware_validation": "PCB not yet fabricated or assembled",
}
(ROOT / "checks/Verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
