"""Reserve QFN escapes before routing GPIO traces around the MCU."""
import math
import pcbnew as pcb
from build_pcb import BOARD_FILE,OUTPUT,MM,xy,point,trace,via

board=pcb.LoadBoard(str(BOARD_FILE))
fps={f.GetReference():f for f in board.GetFootprints()}
board.GetDesignSettings().m_ViasMinSize=MM(.4)
# Clear ground-only escape congestion; the solid L2 plane and nine EPAD vias stay.
for item in list(board.GetTracks()):
    if item.GetNetname()!='GND':
        continue
    bb=item.GetBoundingBox();a=point(bb.GetOrigin());b=point(bb.GetEnd())
    def intersects(x1,y1,x2,y2):
        return a[0]<x2 and b[0]>x1 and a[1]<y2 and b[1]>y1
    if intersects(106,113.35,111,114.4) or intersects(111.8,116,114,119.2):
        board.RemoveNative(item)
for item in list(board.GetTracks()):
    if item.GetNetname()=='+3V3' and isinstance(item,pcb.PCB_VIA) and math.dist(point(item.GetPosition()),(109.3,113.86))<.01:
        item.SetPosition(xy(109.0,113.86));item.SetWidth(MM(.4))
        trace(board,item.GetNet(),[(109.3,113.86),(109.0,113.86)],.15)
# Shift the VDDPST2 landing away from the adjacent UART TX escape.
net28=None
for item in list(board.GetTracks()):
    if item.GetNetname()!='+3V3':
        continue
    bb=item.GetBoundingBox();a=point(bb.GetOrigin());b=point(bb.GetEnd())
    if a[0]>109.8 and b[0]<110.7 and a[1]>119.1 and b[1]<120.6:
        net28=item.GetNet();board.RemoveNative(item)
if net28:
    via(board,net28,(111.0,120.55),.4,.2)
    trace(board,net28,[(110,119.4375),(110,119.98),(110.05,120.03),(110.05,120.5),(110.1,120.55),(111,120.55)],.2)
for item in board.GetTracks():
    if isinstance(item,pcb.PCB_VIA) and item.GetNetname()=='+3V3':
        xx,yy=point(item.GetPosition())
        if 108<xx<113 and 113<yy<121:
            item.SetWidth(MM(.3));item.SetDrill(MM(.15))


def pad(r,n):
    return next(p for p in fps[r].Pads() if p.GetNumber()==str(n))


def p(r,n):
    return point(pad(r,n).GetPosition())


for pin,ref,mids in [(20,'R17',[(106.5625,119.4),(106.2,119.7625)]),
                     (21,'R1',[(107.2,119.8),(106.9,120.1)]),(22,'R2',[]),
                     (24,'R3',[(108.4,119.9),(108.3,120.0)]),
                     (25,'R4',[(108.8,119.9),(109,120.1)]),
                     (26,'R5',[(109.225,120.1),(109.425,120.3),(109.425,120.645)])]:
    trace(board,pad('U1',pin).GetNet(),[p('U1',pin)]+mids+[p(ref,1)],.1)
net=pad('U1',23).GetNet()
trace(board,net,[p('U1',23),(108,119.9),(107.95,119.95),(107.95,121.95)],.1)
via(board,net,(107.95,121.95))
trace(board,net,[(107.95,121.95),p('C7',1)],.15,pcb.B_Cu)
for ref,pts in [('C14',[(112.2,118.2)]),('C15',[(112.35,114.67),(112.35,114.95)])]:
    trace(board,pad(ref,1).GetNet(),[p(ref,1)]+pts,.2)
via(board,pad('C14',1).GetNet(),(112.2,118.2),.4,.2)
board.BuildConnectivity()
pcb.SaveBoard(str(BOARD_FILE),board)
