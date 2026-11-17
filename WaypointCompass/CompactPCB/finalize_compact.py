from build_compact import k,ROOT,NAME,project
import re
b=k.LoadBoard(str(ROOT/(NAME+'.kicad_pcb')))
for f in b.GetFootprints():
 if f.GetReference()=='J2':
  for p in f.Pads():
   if p.GetNumber()=='1':p.SetNet(b.FindNet('/GPS_5V'))
b.GetDesignSettings().SetAuxOrigin(k.VECTOR2I(k.FromMM(100),k.FromMM(140)))
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(ROOT/(NAME+'.kicad_pcb')),b);project()
p=ROOT/(NAME+'.kicad_pcb');s=re.sub(r'\(layers "\*\.Cu"(?: "[^"]+")*\)','(layers "*.Cu" "*.Mask")',p.read_text())
stack='''(stackup
 (layer "F.SilkS" (type "Top Silk Screen") (color "White"))
 (layer "F.Mask" (type "Top Solder Mask") (color "Green"))
 (layer "F.Cu" (type "copper") (thickness 0.035))
 (layer "dielectric 1" (type "prepreg") (thickness 0.11) (material "FR4") (epsilon_r 4.2) (loss_tangent 0.02))
 (layer "In1.Cu" (type "copper") (thickness 0.035))
 (layer "dielectric 2" (type "core") (thickness 0.64) (material "FR4") (epsilon_r 4.2) (loss_tangent 0.02))
 (layer "In2.Cu" (type "copper") (thickness 0.035))
 (layer "dielectric 3" (type "prepreg") (thickness 0.11) (material "FR4") (epsilon_r 4.2) (loss_tangent 0.02))
 (layer "B.Cu" (type "copper") (thickness 0.035))
 (layer "B.Mask" (type "Bottom Solder Mask") (color "Green"))
 (layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
 (copper_finish "ENIG") (dielectric_constraints yes)
)'''
# Replace native generated stackup when present, otherwise add it to setup.
start=s.find('\t\t(stackup')
if start>=0:
 i=start;depth=0;quote=False;escape=False
 while i<len(s):
  ch=s[i]
  if quote:
   if escape:escape=False
   elif ch=='\\':escape=True
   elif ch=='"':quote=False
  elif ch=='"':quote=True
  elif ch=='(':depth+=1
  elif ch==')':
   depth-=1
   if depth==0:break
  i+=1
 s=s[:start]+stack+s[i+1:]
else:s=s.replace('\t(setup\n','\t(setup\n'+stack+'\n',1)
p.write_text(s)
