"""Place the Rev A PCB from KiCad's authoritative XML netlist.

Critical RF / clock / USB paths are explicitly routed here. Remaining low-speed
connections are exported for the local Freerouting pass. Never route L2 GND.
"""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew as pcb
from kicad_sexpr import Atom as A, child, children, dumps, parse, read

ROOT = Path(__file__).resolve().parents[1]
FPLIB = Path('C:/Program Files/KiCad/10.0/share/kicad/footprints')
OUTPUT = ROOT/'output'
BOARD_FILE = ROOT/'esp32-c6-pico.kicad_pcb'
MM = pcb.FromMM
POWER_NETS = frozenset(['+3V3', '+5V', 'V3A', 'VBUS_FUSED', 'VBUS_USB', 'VDD_SPI'])


def xy(x, y):
    return pcb.VECTOR2I(MM(x), MM(y))


def point(p):
    return (round(pcb.ToMM(p.x), 6), round(pcb.ToMM(p.y), 6))


# Absolute mm; F/B is the component side. Angles are KiCad board rotations.
PLACEMENT = {
    'AE1':(109,107,270,'F'), 'U1':(109,117,270,'F'),
    'U3':(107.8,125,0,'B'), 'J1':(109,134.225,0,'F'),
    'J2':(99.95,114,180,'B'), 'J3':(118.05,114,180,'B'),
    'C3':(111.12,113.4,0,'F'), 'L1':(110.8,112.3,90,'F'),
    'C2':(110.48,111.15,180,'F'), 'C16':(111.7,111.4,90,'F'),
    'L3':(112.85,111,0,'F'), 'C17':(110.5,110.3,180,'F'),
    'R6':(111.7,109.8,90,'F'), 'C18':(110.5,109.35,180,'F'),
    'D1':(112.85,109.7,90,'F'),
    'L2':(104.4,109.9,0,'F'), 'C19':(106.8,111.25,180,'F'),
    'C20':(106.8,112.85,180,'F'), 'C11':(109.3,113.15,180,'F'),
    'C8':(104,113.8,0,'B'), 'C9':(103.8,115.2,90,'F'),
    'C10':(105,115.2,90,'F'), 'C12':(108.8,115,180,'B'),
    'C13':(111.35,121.2,-90,'F'), 'C14':(113.15,117.9,0,'F'),
    'C15':(113.2,114.3,0,'F'), 'C6':(111.7,126.2,90,'B'),
    'C7':(108.45,121,0,'F'),
    'Y1':(115.65,116.9,180,'F'), 'L4':(113.1,115.6,0,'F'),
    'C4':(115.65,114.6,180,'F'), 'C5':(115.65,119,0,'F'),
    'R17':(104.95,121.2,-90,'B'), 'R1':(106.15,121.2,-90,'B'),
    'R2':(107.35,121.2,-90,'B'), 'R3':(108.55,121.2,-90,'B'),
    'R4':(109.75,121.2,-90,'B'), 'R5':(110.95,121.2,-90,'B'),
    'R12':(104.75,117.8,0,'F'), 'R13':(104.75,118.85,0,'F'),
    'C27':(104.75,117.8,180,'B'), 'C28':(103.2,119.3,180,'B'),
    'D4':(108.8,129.949999,90,'B'), 'R10':(105.5,128.5,0,'F'),
    'R11':(107.7,128.5,0,'F'), 'D3':(115,132.9,90,'B'),
    'C24':(111.2,129.1,270,'B'),
    'U2':(114,125.5,90,'B'), 'D5':(109.4,133.2,0,'B'),
    'F1':(109,135.8,0,'B'), 'C22':(114,128.5,0,'B'),
    'C23':(113.7,128.5,0,'F'),
    'SW1':(106.65,125.1,0,'F'), 'SW2':(112.35,125.1,0,'F'),
    'R7':(106.95,115.4,180,'B'), 'C21':(104.2,116.5,0,'B'),
    'R8':(103.15,121.8,0,'B'), 'R9':(104.8,121.7,0,'F'),
    'R14':(111.95,123.25,90,'B'),
    'D2':(113.5,121.8,0,'F'), 'U4':(113.55,120.5,0,'B'),
    'C25':(114.8,122.8,0,'B'), 'C26':(115.65,120.7,90,'F'),
    'R15':(111,122.75,180,'F'), 'R16':(113.45,119.45,0,'F'),
}


def load_board():
    board = pcb.BOARD()
    board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetBoardThickness(MM(.8))
    ds = board.GetDesignSettings()
    ds.SetAuxOrigin(xy(98.75,137.5))
    ds.m_MinClearance=MM(.1)
    ds.m_TrackMinWidth=MM(.1)
    ds.m_ViasMinSize=MM(.4)
    ds.m_MinThroughDrill=MM(.2)
    ds.m_ViasMinAnnularWidth=MM(.1)
    ds.m_HoleToHoleMin=MM(.2)
    ds.m_CopperEdgeClearance=MM(.25)
    ds.m_SilkClearance=MM(.1)
    ds.m_MinSilkTextHeight=MM(.6)
    ds.m_MinSilkTextThickness=MM(.1)
    ds.m_SolderMaskMinWidth=MM(.075)
    nc=ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(MM(.1));nc.SetTrackWidth(MM(.15))
    nc.SetViaDiameter(MM(.45));nc.SetViaDrill(MM(.2))
    nc.SetDiffPairWidth(MM(.15));nc.SetDiffPairGap(MM(.15))
    ds.m_HoleClearance=MM(.18)
    doc = ET.parse(OUTPUT/'netlist.xml').getroot()
    net_map, pad_net, pad_function = {}, {}, {}
    for net in doc.findall('./nets/net'):
        name=net.attrib['name']
        ni=pcb.NETINFO_ITEM(board,name)
        board.Add(ni)
        net_map[name]=ni
        for node in net.findall('node'):
            pad_net[(node.attrib['ref'],node.attrib['pin'])]=ni
            pad_function[(node.attrib['ref'],node.attrib['pin'])]=node.attrib.get('pinfunction','')
    spec={p['ref']:p for p in json.loads((ROOT/'design-spec.json').read_text(encoding='utf-8'))}
    assert set(spec)==set(PLACEMENT), (set(spec)-set(PLACEMENT),set(PLACEMENT)-set(spec))
    footprints={}
    for comp in doc.findall('./components/comp'):
        ref=comp.attrib['ref']
        fp_id=comp.findtext('footprint')
        lib,name=fp_id.split(':')
        folder=ROOT/('libs/'+lib+'.pretty') if lib in ['Walsin_Antenna','Pico'] else FPLIB/(lib+'.pretty')
        fp=pcb.FootprintLoad(str(folder),name)
        assert fp is not None,fp_id
        fp.SetFPID(pcb.LIB_ID(lib,name))
        fp.SetReference(ref)
        fp.SetValue(comp.findtext('value'))
        fp.SetPath(pcb.KIID_PATH(spec[ref]['path']))
        fp.SetDNP(spec[ref]['dnp'])
        board.Add(fp)
        x,y,angle,side=PLACEMENT[ref]
        fp.SetPosition(xy(x,y))
        if side=='B':
            fp.Flip(fp.GetPosition(),False)
        fp.SetOrientationDegrees(angle)
        fp.Reference().SetTextSize(xy(.65,.65))
        fp.Reference().SetTextThickness(MM(.1))
        fp.Reference().SetLayer(pcb.F_Fab if side=='F' else pcb.B_Fab)
        fp.Value().SetVisible(False)
        for pad in fp.Pads():
            key=(ref,pad.GetNumber())
            if key in pad_net:
                pad.SetNet(pad_net[key])
                pad.SetPinFunction(pad_function[key])
        footprints[ref]=fp
    return board,footprints,net_map


def segment(board,net,p,q,width=.15,layer=pcb.F_Cu,locked=True):
    if math.dist(p,q)<1e-6:
        return
    # Keep generated signal and supply traces consistent with the project rules.
    if net.GetNetname()!='GND':
        width=.2 if net.GetNetname() in POWER_NETS else .15
    t=pcb.PCB_TRACK(board)
    t.SetStart(xy(*p));t.SetEnd(xy(*q));t.SetWidth(MM(width));t.SetLayer(layer);t.SetNet(net)
    t.SetLocked(locked)
    board.Add(t)
    return t


def trace(board,net,points,width=.15,layer=pcb.F_Cu,locked=True):
    for a,b in zip(points,points[1:]):
        segment(board,net,a,b,width,layer,locked)


def via(board,net,p,size=.45,drill=.2):
    v=pcb.PCB_VIA(board)
    v.SetPosition(xy(*p));v.SetWidth(MM(size));v.SetDrill(MM(drill))
    v.SetViaType(pcb.VIATYPE_THROUGH);v.SetLayerPair(pcb.F_Cu,pcb.B_Cu);v.SetNet(net)
    v.SetLocked(True)
    board.Add(v)
    return v


def box_zone(board,name,net,x1,y1,x2,y2,layers,keepout=False):
    zone=pcb.ZONE(board)
    zone.SetZoneName(name)
    ls=pcb.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    zone.SetLayerSet(ls)
    zone.SetLocalClearance(MM(.15));zone.SetThermalReliefGap(MM(.2));zone.SetThermalReliefSpokeWidth(MM(.25))
    zone.SetPadConnection(pcb.ZONE_CONNECTION_FULL)
    zone.SetMinThickness(MM(.1))
    if keepout:
        zone.SetIsRuleArea(True)
        zone.SetDoNotAllowTracks(False);zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowPads(False);zone.SetDoNotAllowFootprints(False)
        zone.SetDoNotAllowZoneFills(True)
    else:
        zone.SetNet(net)
    poly=zone.Outline();poly.NewOutline()
    for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:
        poly.Append(MM(x),MM(y))
    board.Add(zone)
    return zone


def text(board,value,x,y,layer=pcb.F_SilkS,size=.7,angle=0):
    t=pcb.PCB_TEXT(board)
    t.SetText(value);t.SetPosition(xy(x,y));t.SetTextSize(xy(size,size));t.SetTextThickness(MM(.1))
    t.SetLayer(layer);t.SetTextAngle(pcb.EDA_ANGLE(angle,pcb.DEGREES_T))
    if layer==pcb.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def main():
    board,fps,nets=load_board()
    def pad(ref,num):
        return next(p for p in fps[ref].Pads() if p.GetNumber()==str(num))
    def p(ref,num):
        return point(pad(ref,num).GetPosition())
    def route(net,points,width=.15,layer=pcb.F_Cu):
        trace(board,nets[net],points,width,layer)
    # Bottom-mounted headers provide front-side room for the crystal beside the MCU.
    for a,b in [((98.75,105.5),(119.25,105.5)),((119.25,105.5),(119.25,137.5)),((119.25,137.5),(98.75,137.5)),((98.75,137.5),(98.75,105.5))]:
        edge=pcb.PCB_SHAPE(board);edge.SetShape(pcb.SHAPE_T_SEGMENT)
        edge.SetStart(xy(*a));edge.SetEnd(xy(*b));edge.SetLayer(pcb.Edge_Cuts);edge.SetWidth(MM(.05));board.Add(edge)
    allcu=[pcb.F_Cu,pcb.In1_Cu,pcb.In2_Cu,pcb.B_Cu]
    box_zone(board,'ANTENNA_NO_COPPER',None,98.75,105.5,119.25,109,allcu,True)
    # Reject signal routing in the antenna clearance except the dedicated feed.
    for name,rect in [('ANT_LEFT',(98.75,105.5,110.65,109)),('ANT_RIGHT',(112.45,105.5,119.25,109)),('ANT_TIP',(110.65,105.5,112.45,105.9))]:
        z=box_zone(board,name,None,*rect,allcu,True)
        z.SetDoNotAllowTracks(True)
    for layer in allcu:
        box_zone(board,'GND_'+board.GetLayerName(layer),nets['GND'],99,109,119,137.25,[layer])
    # No autorouted digital tracks under the crystal or RF matching chain.
    for name,rect in [('RF_REFERENCE',(110.4,109,113.4,114.25)),('ANT_REFERENCE',(110.0,109,112.4,111.6)),('XTAL_REFERENCE',(114.45,115.65,116.85,118.15))]:
        z=box_zone(board,name,None,*rect,[pcb.In1_Cu,pcb.In2_Cu,pcb.B_Cu],True)
        z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(False);z.SetDoNotAllowZoneFills(False)
        if name=='XTAL_REFERENCE':z.SetDoNotAllowPads(True)

    # RF chip CLCCL and antenna pi network; no layer changes in the RF signal.
    route('RF_CHIP',[p('U1',1),p('C3',1),p('L1',1)])
    route('RF_MID',[p('L1',2),(111.1,111.98),(111.36,111.72),p('C16',1)])
    route('RF_MID',[p('L1',2),p('C2',1)])
    route('RF_50',[p('C16',2),p('R6',1)])
    route('RF_50',[(111.7,111.08),(112.45,111.08),p('L3',1)])
    route('RF_50',[p('C17',1),(111.4,110.3),(111.7,110.6)])
    route('ANT_FEED',[p('R6',2),p('AE1',1)])
    route('ANT_FEED',[p('C18',1),(111.57,109.35),p('R6',2)])
    route('ANT_FEED',[p('R6',2),(112.77,109.48),p('D1',2)])
    # Crystal: every signal stays on the front copper.
    route('XTAL_P',[p('U1',39),p('L4',1)],.15)
    route('XTAL_LOAD_P',[p('L4',2),(115.6,115.6),p('Y1',1)],.15)
    route('XTAL_LOAD_P',[p('Y1',1),(116.13,116.13),p('C4',1)],.15)
    route('XTAL_N',[p('U1',38),(112.225,116),(112.675,116.45),(113.675,116.45),(114.675,117.45),p('Y1',3)],.15)
    route('XTAL_N',[p('Y1',3),(115.17,117.67),p('C5',1)],.15)

    # RF supply pins get a shared short wide branch after the LC filter.
    route('V3A',[p('U1',2),(110.4,114.05),(110.0,114.05),p('U1',3)],.2)
    route('V3A',[(110.0,114.05),p('C11',1)],.2)
    # Exposed-pad thermal / ground vias, arranged away from the paste windows.
    for dx in [-1.0,0,1.0]:
        for dy in [-1.0,0,1.0]:
            via(board,nets['GND'],(109+dx,117+dy),.45,.2)

    # USB series resistors close to the MCU.
    route('USB_MCU_D-',[p('U1',18),(106.0,118),(105.8,117.8),p('R12',2)],.15)
    route('USB_MCU_D+',[p('U1',19),(106.0,118.4),(105.55,118.85),p('R13',2)],.15)
    # Short DNP EMI-cap branches terminate beside the series resistors on B.Cu.
    for cap,res in [('C27','R12'),('C28','R13')]:
        target=(105.65,p(res,2)[1])
        net=pad(res,2).GetNet()
        trace(board,net,[p(res,2),target],.15)
        via(board,net,target)
        trace(board,net,[target,p(cap,1)],.15,pcb.B_Cu)
    # Two front/back transitions per line; no length-matching meanders.
    route('USB_D-',[p('R12',1),(103.75,117.8),(103.35,118.2),(103.35,121.9),(103.15,122.1)],.15)
    route('USB_D+',[p('R13',1),(104.04,118.85),(103.64,119.25),(103.64,122.6)],.15)
    for net,locations in [('USB_D-',[(103.15,122.1),(108.2,130.7)]),('USB_D+',[(103.64,122.6),(109.75,130.7)])]:
        for location in locations:via(board,nets[net],location,.3,.15)
    route('USB_D-',[(103.15,122.1),(103.15,126.9),(103.85,127.6),(107.85,127.6),p('D4',4),p('D4',3),(108.2,130.7)],.15,pcb.B_Cu)
    route('USB_D+',[(103.64,122.6),(103.64,126.61),(104.18,127.15),(109.75,127.15),p('D4',6),p('D4',1),(109.75,130.7)],.15,pcb.B_Cu)
    route('USB_D-',[(108.2,130.7),p('J1','B7'),(108.25,129.2),(109.25,129.2),p('J1','A7')],.15)
    route('USB_D+',[(109.75,130.7),p('J1','B6')],.15)
    route('USB_D+',[(109.75,130.7),(109.75,131.5),(108.75,131.5),p('J1','A6')],.15)

    # Label the accessible controls and connector pinout on the back silkscreen.
    text(board,'C6 PICO',109,116.8,pcb.B_SilkS,.85)
    text(board,'REV A',109,110.3,pcb.B_SilkS,.6)
    text(board,'RST',106.65,127.35,pcb.F_SilkS,.6)
    text(board,'BOOT',112.35,127.35,pcb.F_SilkS,.6)
    # Final silkscreen logos are editable board groups; see docs/logo/README.md.
    text(board,'RFANT5220110A0T: axial end copper, 20.5 x 3.5 mm prototype clearance; RF validation required.',109,102.8,pcb.Dwgs_User,.8)
    text(board,'20.5 x 32 mm | 4 layers | 0.8 mm nominal | 0.20 mm drilled vias',109,141.5,pcb.Dwgs_User,.8)
    text(board,'L1 signal / L2 solid GND / L3 power+GND / L4 signal+GND. Fab to confirm 50R RF / 90R USB.',109,143.0,pcb.Dwgs_User,.8)
    for ref,labels in [('J2',['G','3V3','0','1','2','3','4','5','6','7','8','9']),
                       ('J3',['5V','G','10','11','15','TX','RX','18','19','20','22','23'])]:
        for i,lab in enumerate(labels):
            if ref=='J2':
                text(board,lab,101.75,114+i*2,pcb.B_SilkS,.6)
            else:text(board,lab,116.25,114+i*2,pcb.B_SilkS,.6,90)

    board.BuildConnectivity()
    pcb.SaveBoard(str(BOARD_FILE),board)
    # Store manufacturing constraints and the intended stackup explicitly.
    doc=read(BOARD_FILE)
    setup=child(doc,'setup')
    stack=parse('(stackup (layer "F.Cu" (type "copper") (thickness 0.035)) '
                '(layer "dielectric 1" (type "prepreg") (thickness 0.1) (material "FR4") (epsilon_r 4.2) (loss_tangent 0.02)) '
                '(layer "In1.Cu" (type "copper") (thickness 0.0175)) '
                '(layer "dielectric 2" (type "core") (thickness 0.495) (material "FR4") (epsilon_r 4.2) (loss_tangent 0.02)) '
                '(layer "In2.Cu" (type "copper") (thickness 0.0175)) '
                '(layer "dielectric 3" (type "prepreg") (thickness 0.1) (material "FR4") (epsilon_r 4.2) (loss_tangent 0.02)) '
                '(layer "B.Cu" (type "copper") (thickness 0.035)) (copper_finish "ENIG") '
                '(dielectric_constraints yes))')
    old=child(setup,'stackup')
    if old:
        setup.remove(old)
    setup.insert(1,stack)
    BOARD_FILE.write_text(dumps(doc)+'\n',encoding='utf-8',newline='\n')
    positions={ref:{n:point(pad(ref,n).GetPosition()) for n in {pp.GetNumber() for pp in fp.Pads()} if n}
               for ref,fp in fps.items()}
    (OUTPUT/'pad-positions.json').write_text(json.dumps(positions,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'Placed {len(fps)} components; {len(board.GetTracks())} critical track/via objects.')


if __name__=='__main__':
    main()
