"""Audit visible pin-to-peripheral wires without resolving net or power labels."""
from pathlib import Path
import math
from kicad_sexpr import read,child,children,prop

def audit(root):
    doc=read(Path(root)/'esp32-c6-pico.kicad_sch')
    libraries={s[1]:s for s in children(child(doc,'lib_symbols'),'symbol')}
    pins={};wires=[];points=set();parents={}
    def point(q):return tuple(round(float(v),4) for v in q)
    for instance in children(doc,'symbol'):
        ref=prop(instance,'Reference')
        if ref.startswith('#'):continue
        x,y,angle=map(float,child(instance,'at')[1:]);a=math.radians(angle)
        for unit in children(libraries[child(instance,'lib_id')[1]],'symbol'):
            for pin in children(unit,'pin'):
                px,py=map(float,child(pin,'at')[1:3])
                q=point((x+px*math.cos(a)-py*math.sin(a),y-px*math.sin(a)-py*math.cos(a)))
                pins[(ref,child(pin,'number')[1])]=q;points.add(q)
    for wire in children(doc,'wire'):
        a,b=[point(q[1:]) for q in children(child(wire,'pts'),'xy')]
        wires.append((a,b));points.update((a,b))
    def find(q):
        parents.setdefault(q,q)
        if parents[q]!=q:parents[q]=find(parents[q])
        return parents[q]
    def join(a,b):parents[find(a)]=find(b)
    def lies(q,a,b):
        return min(a[0],b[0])<=q[0]<=max(a[0],b[0]) and min(a[1],b[1])<=q[1]<=max(a[1],b[1]) and abs((q[0]-a[0])*(b[1]-a[1])-(q[1]-a[1])*(b[0]-a[0]))<1e-7
    for a,b in wires:
        for q in points:
            if lies(q,a,b):join(a,q)
    required=[('C19','1','U1','2'),('C20','1','U1','3'),('C11','1','U1','2'),('L2','2','U1','2'),
              ('C12','1','U1','5'),('C13','1','U1','28'),('C14','1','U1','37'),('C15','1','U1','40'),
              ('R7','2','U1','4'),('C21','1','U1','4'),('SW1','1','U1','4'),
              ('R8','2','U1','15'),('SW2','1','U1','15'),('R9','2','U1','14'),
              ('C7','1','U1','23'),('U3','8','U1','23'),('C6','1','U3','8'),
              ('Y1','1','R18','2'),('Y1','3','U1','38'),('R18','1','U1','39'),('C5','1','U1','38'),
              ('R12','2','U1','18'),('C27','1','U1','18'),('R13','2','U1','19'),('C28','1','U1','19'),
              ('R14','1','U1','29'),('R16','1','U1','34'),('U4','2','U1','34'),('R15','2','D2','3'),('R15','1','U4','4'),
              ('C3','1','U1','1'),('L1','1','U1','1')]
    for ref,mcu,flash in [('R17','20','1'),('R1','21','2'),('R2','22','3'),('R3','24','7'),('R4','25','6'),('R5','26','5')]:
        required.extend([(ref,'1','U1',mcu),(ref,'2','U3',flash)])
    checks=[dict(from_pin=f'{r}.{n}',to_pin=f'{s}.{m}',connected=(r,n) in pins and (s,m) in pins and find(pins[r,n])==find(pins[s,m])) for r,n,s,m in required]
    return dict(all_passed=all(c['connected'] for c in checks),connections=checks,
                method='Visible wires only; labels and power-symbol aliases are not electrical edges')

if __name__=='__main__':
    import json
    result=audit(Path(__file__).resolve().parents[1]);print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['all_passed'] else 1)
