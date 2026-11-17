"""Ensure all through-hole pads have mask openings on both board faces."""
import re
from build_carrier import ROOT, NAME, k

path = ROOT / (NAME + ".kicad_pcb")
count = 0
# KiCad 10's pad mask properties are separate from the copper layer set.
# Write the native pad-layer tokens so KiCad's parser sets both properties.
for item in [path] + list((ROOT / "CompassCarrier.pretty").glob("*.kicad_mod")):
    source, edits = re.subn(r'\(layers "\*\.Cu"(?: "[^"]+")*\)',
                           '(layers "*.Cu" "*.Mask")', item.read_text())
    item.write_text(source)
    if item == path:
        count = edits
board = k.LoadBoard(str(ROOT / (NAME + ".kicad_pcb")))
for fp in board.GetFootprints():
    for pad in fp.Pads():
        assert pad.GetLayerSet().Contains(k.F_Mask), fp.GetReference()
        assert pad.GetLayerSet().Contains(k.B_Mask), fp.GetReference()
print("Verified both mask layers on", count, "pads")
