"""Add a conservative front-layer length correction to the USB D- trunk, if space permits."""
import math
import pcbnew as pcb
from build_pcb import BOARD_FILE,MM,point,xy,trace

b=pcb.LoadBoard(str(BOARD_FILE))
trunk=next((t for t in b.GetTracks() if not isinstance(t,pcb.PCB_VIA) and t.GetNetname()=='USB_D-'
            and abs(point(t.GetStart())[0]-103.35)<.005 and abs(point(t.GetEnd())[0]-103.35)<.005
            and abs(pcb.ToMM(t.GetLength())-6.44)<.01),None)
if trunk is None:
    print('No original USB trunk remains; nothing changed.');raise SystemExit(0)
foreign=[pd.GetEffectiveShape(pcb.F_Cu) for f in b.GetFootprints() for pd in f.Pads()
         if pd.IsOnLayer(pcb.F_Cu) and pd.GetNetname()!='USB_D-']
foreign += [t.GetEffectiveShape() for t in b.GetTracks() if t.IsOnLayer(pcb.F_Cu) and t.GetNetname()!='USB_D-']
amplitude=(4.0087/2+4*.125*(2-math.sqrt(2)))/2
left=103.35-amplitude
def bump(y,h):
    return [(103.35,y),(103.225,y+.125),(left+.125,y+.125),(left,y+.25),
            (left,y+h-.25),(left+.125,y+h-.125),(103.225,y+h-.125),(103.35,y+h)]
chosen=None
for ystep in range(1185,1211):
    for h in [.75,1.,1.25,1.5]:
        for gap in [.4,.6,.8,1.]:
            y=ystep/10
            if y+2*h+gap>124.5:continue
            pts=[(103.35,118.2)]+bump(y,h)+bump(y+h+gap,h)+[(103.35,124.64)]
            if all(not any(s.Collide(pcb.SEG(xy(*a),xy(*c)),MM(.185)) for s in foreign)
                   for a,c in zip(pts,pts[1:])):
                chosen=pts;break
        if chosen:break
    if chosen:break
if not chosen:
    print('No clearance-safe tuning pocket found; existing USB geometry retained.');raise SystemExit(0)
net=trunk.GetNet();b.RemoveNative(trunk);trace(b,net,chosen,.14)
b.BuildConnectivity();pcb.ZONE_FILLER(b).Fill(b.Zones());pcb.SaveBoard(str(BOARD_FILE),b)
print('USB D- length correction: +4.0087 mm; two chamfered loops at',chosen[1],chosen[9])
