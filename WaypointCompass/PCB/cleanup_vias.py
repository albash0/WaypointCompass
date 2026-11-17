"""Remove only vias identified as unused by the supplied KiCad DRC report."""
import json
import re
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
report=json.loads(Path(sys.argv[1]).read_text())
unused={item["uuid"] for violation in report["violations"]
        if violation["type"]=="via_dangling" for item in violation["items"]}
path=root/"WaypointCompassCarrier.kicad_pcb"
source=path.read_text()
ranges=[]
for match in re.finditer(r'\(via\s',source):
    start=match.start(); depth=0; quoted=False; escaped=False
    for i in range(start,len(source)):
        c=source[i]
        if escaped: escaped=False; continue
        if quoted and c=='\\': escaped=True; continue
        if c=='"': quoted=not quoted
        elif not quoted:
            if c=='(':depth+=1
            elif c==')':
                depth-=1
                if not depth:
                    chunk=source[start:i+1]
                    if any(u in chunk for u in unused):ranges.append((start,i+1))
                    break
if len(ranges)!=len(unused):
    raise RuntimeError(f"Found {len(ranges)} vias, expected {len(unused)}")
for start,end in reversed(ranges):source=source[:start]+source[end:]
path.write_text(source)
print("Removed",len(ranges),"unused vias")
