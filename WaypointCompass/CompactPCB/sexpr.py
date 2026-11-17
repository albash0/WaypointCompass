"""Small S-expression reader used to copy KiCad library data without editing globals."""
import re,json,copy
from functools import lru_cache
from pathlib import Path
BASE=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport')
def parse(text):
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',text); stack=[];root=[];cur=root
    for t in tokens:
        if t=='(':new=[];cur.append(new);stack.append(cur);cur=new
        elif t==')':cur=stack.pop()
        else:cur.append(json.loads(t) if t.startswith('"') else t)
    return root[0]
def children(node,key):return [x for x in node if isinstance(x,list) and x and x[0]==key]
def child(node,key,default=None):return next(iter(children(node,key)),default)
@lru_cache(maxsize=None)
def symbol(lib,name):
    allsym={x[1]:x for x in children(parse((BASE/'symbols'/(lib+'.kicad_sym')).read_text()),'symbol')}
    def flatten(name):
        s=copy.deepcopy(allsym[name]); ext=child(s,'extends')
        if ext:
            parent=flatten(ext[1]); overrides={p[1]:p for p in children(s,'property')}
            parent[1]=name
            parent=[x for x in parent if not(isinstance(x,list) and x and x[0]=='property' and x[1] in overrides)]
            parent.extend(overrides.values());s=parent
        return s
    return flatten(name)
def pins(s):
    result=[]
    for group in children(s,'symbol'):
        for p in children(group,'pin'):
            result.append({'number':child(p,'number')[1],'name':child(p,'name')[1],'type':p[1],'at':child(p,'at')[1:]})
    return result
if __name__=='__main__':
    for lib,name in [('RF_Module','ESP32-S3-MINI-1U'),('Battery_Management','BQ24074RGT'),('Regulator_Switching','TPS63060'),('Sensor_Motion','LIS2DH'),('Sensor_Magnetic','LIS2MDL'),('Connector','USB_C_Receptacle_USB2.0_16P')]:
        s=symbol(lib,name);print(name,child(s,'property'))
        print(next((p[2] for p in children(s,'property') if p[1]=='Footprint'),''))
        print([(p['number'],p['name'],p['type']) for p in pins(s)])
