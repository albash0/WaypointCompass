"""Create charger supply fanout before the two neighboring control traces."""
from build_compact import k,ROOT,NAME,pt,project
import re
board=k.LoadBoard(str(ROOT/(NAME+'.kicad_pcb')))
for name,a,b in (
 ('/VBUS',(39.75,8.5625),(39.65,7.65)), ('/VBUS',(40.75,11.4375),(41,12.3)),
 ('/PGOOD_N',(40.25,8.5625),(40.25,7.25)), ('/CHG_TMR',(40.25,11.4375),(40.05,12.3)),
 ('/CHG_ISET',(39.25,11.4375),(39.05,12.15)), ('/CHG_ILIM',(41.4375,10.75),(42.2,11.2)), ('/SYS',(41.4375,10.25),(42.1,10)) ):
 t=k.PCB_TRACK(board);t.SetStart(pt(a[0]+100,a[1]+100));t.SetEnd(pt(b[0]+100,b[1]+100));t.SetWidth(k.FromMM(.2 if name=='/VBUS' else .15));t.SetLayer(k.B_Cu);t.SetNetCode(board.FindNet(name).GetNetCode());board.Add(t)
 v=k.PCB_VIA(board);v.SetPosition(pt(b[0]+100,b[1]+100));v.SetWidth(k.FromMM(.4));v.SetDrill(k.FromMM(.2));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNetCode(board.FindNet(name).GetNetCode());board.Add(v)
def power(points,width=.35):
 for a,b in zip(points,points[1:]):
  t=k.PCB_TRACK(board);t.SetStart(pt(a[0]+100,a[1]+100));t.SetEnd(pt(b[0]+100,b[1]+100));t.SetWidth(k.FromMM(width));t.SetLayer(k.B_Cu);t.SetNetCode(board.FindNet('/SYS').GetNetCode());board.Add(t)
power([(41.4375,9.75),(41.4375,10.25)],.2)
power([(37.74,22),(35.5,21.95)])
power([(37.74,23),(36.55,23),(35.5,21.95)])
power([(35.5,21.95),(34.2,23.25),(34.2,24.85),(35.5,25.325)])
power([(47.787,21),(46.85,21),(46.85,19.5),(47.15,18.5)],.3)
power([(47.15,18.5),(46,17.35),(46,14.45)],.45)
board.BuildConnectivity();k.ZONE_FILLER(board).Fill(board.Zones());k.SaveBoard(str(ROOT/(NAME+'.kicad_pcb')),board);project()
p=ROOT/(NAME+'.kicad_pcb');p.write_text(re.sub(r'\(layers "\*\.Cu"(?: "[^"]+")*\)','(layers "*.Cu" "*.Mask")',p.read_text()))
