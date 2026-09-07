"""Add local ground returns and supply fan-out, then export a local router job."""
from __future__ import annotations

import json
import math
from pathlib import Path
import pcbnew as pcb
from build_pcb import ROOT,OUTPUT,BOARD_FILE,MM,xy,point,trace,via,box_zone

board=pcb.LoadBoard(str(BOARD_FILE))
fps={f.GetReference():f for f in board.GetFootprints()}
nets={n.GetNetname():n for n in board.GetNetsByNetcode().values()}


def pad(ref,num):
    return next(p for p in fps[ref].Pads() if p.GetNumber()==str(num))


def p(ref,num):
    return point(pad(ref,num).GetPosition())


def route(net,points,width=.2,layer=pcb.F_Cu):
    trace(board,nets[net],points,width,layer)


def forbidden(point_,net,radius,segment_to=None,layer=None):
    pt=xy(*point_)
    shape_arg=pcb.SEG(xy(*segment_to),pt) if segment_to else pt
    extra=MM(radius+.11)
    for f in board.GetFootprints():
        for pd in f.Pads():
            if not pd.IsOnCopperLayer() or pd.GetNetname()==net:
                continue
            for l in ([layer] if layer is not None else [pcb.F_Cu,pcb.In1_Cu,pcb.In2_Cu,pcb.B_Cu]):
                if pd.IsOnLayer(l) and pd.GetEffectiveShape(l).Collide(shape_arg,extra):
                    return True
    for item in board.GetTracks():
        if segment_to is None and isinstance(item,pcb.PCB_VIA) and math.dist(point_,point(item.GetPosition()))<.41:
            return True
        if item.GetNetname()==net:
            continue
        if layer is not None and not item.IsOnLayer(layer):
            continue
        if item.GetEffectiveShape().Collide(shape_arg,extra):
            return True
    return False


def attach_via(pd,required=False):
    net=pd.GetNetname();origin=point(pd.GetPosition());layer=pd.GetLayer()
    # Via drills must stay out of solderable pads. Tent ordinary vias on both sides.
    offsets=[(1,0),(0,1),(-1,0),(0,-1),(.707,.707),(-.707,.707),(-.707,-.707),(.707,-.707)]
    for distance in [.55,.65,.8,1.0,1.2,1.5]:
        for dx,dy in offsets:
            dest=(round(origin[0]+distance*dx,3),round(origin[1]+distance*dy,3))
            if not (100.5<dest[0]<117.5 and 109.25<dest[1]<138.5):
                continue
            if pd.GetEffectiveShape(layer).Collide(xy(*dest),MM(.12)):
                continue
            if forbidden(dest,net,.225) or forbidden(dest,net,.1,origin,layer):
                continue
            via(board,nets[net],dest)
            route(net,[origin,dest],.2,layer)
            return dest
    if required:
        raise RuntimeError(f'No legal local via for {pd.GetParent().GetReference()}.{pd.GetNumber()}')
    return None


# First RF shunt: 0.38 mm extension after the pad edge; L3 is its reference plane.
route('GND',[p('C3',2),(112.05,113.4)],.2)
via(board,nets['GND'],(112.05,113.4))
z=box_zone(board,'RF_GND_STUB_L2_CLEAR',None,111.65,113.22,111.91,113.58,[pcb.In1_Cu],True)
z.SetDoNotAllowVias(False)

# Flash exposed pad: four vias outside the signal pads.
for pos in [(108.7,123.5),(110.3,123.5),(108.7,125.0),(110.3,125.0)]:
    if not forbidden(pos,'GND',.225):
        via(board,nets['GND'],pos)

# Reserve the power paths before choosing the nearby ground-return via positions.
power_fanouts=[(5,(109.3,113.86),[(109.2,114.11),(109.3,114.01)]),
               (28,(110.4,120.25),[(110,119.98),(110.27,120.25)]),
               (37,(112.25,116.6),[(112.05,116.4)]),
               (40,(112.35,114.95),[(112.1,115.2)])]
for pin_no,dest,mids in power_fanouts:
    via(board,nets['+3V3'],dest)
    route('+3V3',[p('U1',pin_no)]+mids+[dest],.2)
route('V3A',[p('L2',2),(105.2,109.9),(105.6,110.3),(107.575,110.3),p('C19',1),p('C20',1)],.5)
route('V3A',[p('C20',1),(108.1,112.85),(108.8,112.15),(109.78,112.15),p('C11',1)],.5)

# Ground returns for every decoupling capacitor and protection device.
ground_omissions=[]
for ref,f in fps.items():
    done=set()
    for pd in f.Pads():
        if pd.GetNetname()!='GND' or not pd.GetNumber() or pd.GetAttribute()==pcb.PAD_ATTRIB_PTH:
            continue
        if (ref,pd.GetNumber()) in [('U1','41'),('U3','9'),('C3','2')]:
            continue
        key=point(pd.GetPosition())
        if key in done:
            continue
        done.add(key)
        if attach_via(pd) is None:
            ground_omissions.append(ref+'.'+pd.GetNumber())

# Ground stitching along the board edges and RF boundary; candidate collision checks
# include both component sides, signal tracks, connector alignment holes and all vias.
for xx,yy in ([(x,109.3) for x in [100.7,102.0,103.3,113.0,116.9]]+
              [(100.5,y) for y in [110.8,112,115,119,123,127,131,135,137.8]]+
              [(117.5,y) for y in [110.8,112,115,119,123,127,131,135,137.8]]+
              [(x,138.45) for x in [101.8,104.4,106,112,113.6,116.2]]):
    if not forbidden((xx,yy),'GND',.225):
        via(board,nets['GND'],(xx,yy))

# Set explicit routable classes. GND, RF, clock and USB are handled by fixed tracks
# and planes; the router completes the remaining nets locally on this machine.
settings=board.GetDesignSettings().m_NetSettings
class_map={}
for name,width in [('GND',.2),('RF',.15),('USB',.14),('Clock',.125),('Power',.5),('Flash',.15)]:
    nc=pcb.NETCLASS(name)
    nc.SetClearance(MM(.1));nc.SetTrackWidth(MM(width));nc.SetViaDiameter(MM(.45));nc.SetViaDrill(MM(.2))
    nc.SetDiffPairWidth(MM(.14));nc.SetDiffPairGap(MM(.15));nc.SetPriority(1)
    settings.SetNetclass(name,nc)
    class_map[name]=nc
for name,net in nets.items():
    group=('GND' if name=='GND' else 'RF' if name.startswith('RF_') or name=='ANT_FEED'
           else 'USB' if name.startswith('USB_') else 'Clock' if name.startswith('XTAL_')
           else 'Power' if name in ['+3V3','+5V','VBUS_USB','VBUS_FUSED','V3A']
           else 'Flash' if name.startswith('SPI_') or name=='VDD_SPI' else None)
    if group:
        net.SetNetClass(class_map[group])
        settings.SetNetclassPatternAssignment(name,group)

board.BuildConnectivity()
pcb.ZONE_FILLER(board).Fill(board.Zones())
pcb.SaveBoard(str(BOARD_FILE),board)
# Export only the solid reference plane. Outer and L3 ground fills are restored by
# KiCad after routing, otherwise the router treats L3 as an unroutable full plane.
router_board=pcb.LoadBoard(str(BOARD_FILE))
for zone in list(router_board.Zones()):
    if not zone.GetIsRuleArea() and zone.GetLayer()!=pcb.In1_Cu:
        router_board.Remove(zone)
pcb.ExportSpecctraDSN(router_board,str(OUTPUT/'routing.dsn'))
(OUTPUT/'local-via-review.json').write_text(json.dumps({'ground_via_not_added':ground_omissions},indent=2)+'\n',encoding='utf-8',newline='\n')
print(f'Prepared {len(board.GetTracks())} tracks/vias. Local ground-via exceptions: {ground_omissions}')
