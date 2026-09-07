"""Final geometric fixes and silkscreen placement, after the routed session import."""
import json,math
import pcbnew as pcb
from build_pcb import BOARD_FILE,OUTPUT,MM,xy,point,trace,via

board=pcb.LoadBoard(str(BOARD_FILE))
fps={f.GetReference():f for f in board.GetFootprints()}
def pad(ref,num):return next(p for p in fps[ref].Pads() if p.GetNumber()==str(num))

# Connect the two genuinely isolated shunt-ground copper islands to the solid plane.
for ref in ['C18']:
    pd=pad(ref,2)
    if not any(isinstance(t,pcb.PCB_VIA) and math.dist(point(t.GetPosition()),point(pd.GetPosition()))<.01 for t in board.GetTracks()):
        via(board,pd.GetNet(),point(pd.GetPosition()),.3,.15)

# Stagger adjacent VIPPO lands to preserve the 0.18 mm drill-to-copper rule.
for v in list(board.GetTracks()):
    if isinstance(v,pcb.PCB_VIA) and v.GetNetname()=='GPIO19' and math.dist(point(v.GetPosition()),(111.6975,118.4))<.005:
        old=point(v.GetPosition());new=(111.775,118.4)
        for t in board.GetTracks():
            if isinstance(t,pcb.PCB_VIA) or t.GetNetname()!='GPIO19':continue
            if math.dist(point(t.GetStart()),old)<.005:t.SetStart(xy(*new))
            if math.dist(point(t.GetEnd()),old)<.005:t.SetEnd(xy(*new))
        v.SetPosition(xy(*new))

# Router clearance is copper-based; add 12 um at four drill-to-track pinch points.
report=json.loads((OUTPUT/'drc-near-final.json').read_text(encoding='utf-8'))
by_id={t.m_Uuid.AsString():t for t in board.GetTracks()}
for violation in report['violations']:
    if violation['type']!='hole_clearance':continue
    objs=[by_id.get(i['uuid']) for i in violation['items']]
    ts=[t for t in objs if isinstance(t,pcb.PCB_TRACK) and not isinstance(t,pcb.PCB_VIA)]
    vs=[v for v in objs if isinstance(v,pcb.PCB_VIA)]
    if len(ts)!=1 or len(vs)!=1:continue
    t=ts[0]
    assert pcb.ToMM(t.GetWidth())>=.125
    t.SetWidth(MM(.125))

# Ordinary vias are tented. Solder-pad vias must additionally be filled and capped
# by the fabricator; tenting alone cannot close a via inside a mask opening.
for t in board.GetTracks():
    if isinstance(t,pcb.PCB_VIA):
        t.SetFrontTentingMode(pcb.TENTING_MODE_TENTED)
        t.SetBackTentingMode(pcb.TENTING_MODE_TENTED)

right_labels=['5V','G','10','11','15','TX','RX','18','19','20','22','23']
for text in board.GetDrawings():
    if not isinstance(text,pcb.PCB_TEXT):continue
    xx,yy=point(text.GetPosition())
    if text.GetText() in right_labels and xx>115 and text.GetLayer()==pcb.F_SilkS:
        text.SetPosition(xy(115.68,yy));text.SetTextAngle(pcb.EDA_ANGLE(90,pcb.DEGREES_T))
    if text.GetText()=='C6 PICO':text.SetPosition(xy(109,117.0))
    if text.GetText()=='REV A':text.SetPosition(xy(109,132.8))

# Prune two redundant single-layer landing vias left by the routing pass.
for net,where in [('+3V3',(112.2,118.2)),('GPIO10',(105.575,117.2))]:
    for v in list(board.GetTracks()):
        if not isinstance(v,pcb.PCB_VIA) or v.GetNetname()!=net or math.dist(point(v.GetPosition()),where)>.005:continue
        attached=[t for t in board.GetTracks() if not isinstance(t,pcb.PCB_VIA) and t.GetNetname()==net
                  and min(math.dist(point(t.GetStart()),where),math.dist(point(t.GetEnd()),where))<.005]
        board.RemoveNative(v)
        if len(attached)==1:board.RemoveNative(attached[0])

# The compact local QFN footprint moves the crowded native pin-1 triangle to fab.
fps['U1'].SetFPID(pcb.LIB_ID('Pico','QFN40_ESP32_C6_Compact'))
for g in fps['U1'].GraphicalItems():
    if g.GetLayer()==pcb.F_SilkS:g.SetLayer(pcb.F_Fab)
fps['D2'].SetFPID(pcb.LIB_ID('Pico','WS2812B_2020_Compact'))
for g in fps['D2'].GraphicalItems():
    if g.GetLayer()==pcb.F_SilkS:g.SetLayer(pcb.F_Fab)

board.BuildConnectivity()
pcb.ZONE_FILLER(board).Fill(board.Zones())
pcb.SaveBoard(str(BOARD_FILE),board)
