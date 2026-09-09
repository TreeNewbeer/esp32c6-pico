"""Independent schematic/PCB parity, RF-layer, fabrication, and USB length audit."""
import argparse,csv,heapq,json,math,hashlib,itertools,collections
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as pcb
from build_pcb import ROOT,OUTPUT,BOARD_FILE,MM,xy,point,POWER_NETS
from verify_schematic_wiring import audit as audit_wiring

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--board",type=Path,default=BOARD_FILE)
parser.add_argument("--output-dir",type=Path,default=OUTPUT)
args=parser.parse_args()
BOARD_FILE=args.board.resolve();OUTPUT=args.output_dir.resolve()
PROJECT_FILE=BOARD_FILE.with_suffix(".kicad_pro")
project=json.loads(PROJECT_FILE.read_text(encoding='utf-8'))
b=pcb.LoadBoard(str(BOARD_FILE))
outline=[g for g in b.GetDrawings() if g.GetLayer()==pcb.Edge_Cuts]
outline_points=[point(p) for g in outline for p in [g.GetStart(),g.GetEnd()]]
dimensions=[round(max(p[i] for p in outline_points)-min(p[i] for p in outline_points),6) for i in [0,1]]
antenna_zone=next(z for z in b.Zones() if z.GetZoneName()=='ANTENNA_NO_COPPER')
antenna_box=antenna_zone.GetBoundingBox()
antenna_clearance=[pcb.ToMM(antenna_box.GetWidth()),pcb.ToMM(antenna_box.GetHeight())]
fps={f.GetReference():f for f in b.GetFootprints()}
xml=ET.parse(OUTPUT/'netlist.xml').getroot()
expected={(n.attrib['ref'],n.attrib['pin']):net.attrib['name']
          for net in xml.findall('./nets/net') for n in net.findall('node')}
checks=[]
def check(label,ok,detail=None):
    checks.append(dict(check=label,passed=bool(ok),detail=detail))

mismatch=[]
for ref,f in fps.items():
    for pd in f.Pads():
        if not pd.GetNumber() or not pd.IsOnCopperLayer():continue
        key=(ref,pd.GetNumber())
        if key not in expected or expected[key]!=pd.GetNetname():
            mismatch.append([*key,expected.get(key),pd.GetNetname()])
check('Every PCB copper pad matches the schematic netlist',not mismatch,mismatch)
components={c.attrib['ref']:c for c in xml.findall('./components/comp')}
check('Schematic and PCB component references match',set(fps)==set(components))
fp_mismatch=[]
for ref,c in components.items():
    if fps[ref].GetFPID().GetUniStringLibId()!=c.findtext('footprint'):
        fp_mismatch.append([ref,c.findtext('footprint'),fps[ref].GetFPID().GetUniStringLibId()])
check('Assigned footprint IDs match',not fp_mismatch,fp_mismatch)
field_mismatch=[]
for ref,c in components.items():
    if ref not in fps:continue
    expected_fields={n.attrib['name']:n.text or '' for n in c.findall('./fields/field')
                     if n.attrib['name']!='Footprint'}
    expected_fields['Value']=c.findtext('value') or ''
    actual_fields={field.GetName():field.GetText() for field in fps[ref].GetFields()}
    for name,value in expected_fields.items():
        if actual_fields.get(name)!=value:
            field_mismatch.append([ref,name,value,actual_fields.get(name)])
check('PCB values and schematic instance fields match the netlist',not field_mismatch,field_mismatch)
# RF matching R/C parts are the only 0201 exceptions.
power_passives={ref for ref,fp in fps.items() if ref.startswith(('R','C'))
                and any(pd.GetNetname() in POWER_NETS for pd in fp.Pads())}|{'C21','R10','R11'}
rf_passives={'C2','C3','C16','C17','C18','R6'}
rc_passives={ref for ref in fps if ref.startswith(('R','C'))}
passive_footprints={ref:(('Capacitor_SMD:C_' if ref.startswith('C') else 'Resistor_SMD:R_')+
                            ('0201_0603Metric' if ref in rf_passives else '0402_1005Metric')) for ref in rc_passives}
power_passive_footprints={ref:passive_footprints[ref] for ref in power_passives}
package_errors=[[ref,fps[ref].GetFPID().GetUniStringLibId(),expected_fp]
                for ref,expected_fp in sorted(passive_footprints.items())
                if fps[ref].GetFPID().GetUniStringLibId()!=expected_fp]
check('Six RF resistors/capacitors remain 0201; all 39 non-RF resistors/capacitors are 0402',
      len(rc_passives)==45 and rf_passives<=rc_passives and not package_errors,package_errors)
# The WROOM module diagram uses R4 = 0R at XTAL_P; its local reference is R18.
crystal_series=components.get('R18')
check('XTAL_P uses a populated 0R resistor matching the WROOM module reference',
      'L4' not in fps and 'R18' in fps and not fps['R18'].IsDNP()
      and crystal_series is not None and crystal_series.findtext('value')=='0R'
      and crystal_series.find('libsource') is not None
      and crystal_series.find('libsource').get('part')=='Device__R_Small'
      and expected.get(('R18','1'))==expected.get(('U1','39'))=='XTAL_P'
      and expected.get(('R18','2'))==expected.get(('Y1','1'))==expected.get(('C4','1'))=='XTAL_LOAD_P')
wiring_audit=audit_wiring(BOARD_FILE.parent)
check('MCU peripherals connect by visible wires without relying on labels',wiring_audit['all_passed'],wiring_audit)
spec={c['ref']:c for c in json.loads((BOARD_FILE.parent/'design-spec.json').read_text())}
path_errors=[[ref,f.GetPath().AsString(),spec[ref]['path']] for ref,f in fps.items() if f.GetPath().AsString()!=spec[ref]['path']]
check('PCB symbol paths match the reorganized schematic sheets',not path_errors,path_errors)

widths_by_net=collections.defaultdict(collections.Counter)
signal_width_errors=[];power_width_errors=[];class_errors=[]
for track in b.GetTracks():
    if isinstance(track,pcb.PCB_VIA):continue
    name=track.GetNetname();width=round(pcb.ToMM(track.GetWidth()),6)
    widths_by_net[name][width]+=1
    if name=='GND':continue
    expected_width=.2 if name in POWER_NETS else .15
    if not math.isclose(width,expected_width,abs_tol=.000001):
        (power_width_errors if name in POWER_NETS else signal_width_errors).append(
            dict(net=name,width_mm=width,position_mm=point(track.GetStart()),uuid=track.m_Uuid.AsString()))
    expected_class='Power' if name in POWER_NETS else 'Default'
    if track.GetNetClassName()!=expected_class:class_errors.append([name,track.GetNetClassName(),expected_class])
check('Every signal track and arc is exactly 0.15 mm',not signal_width_errors,signal_width_errors)
check('Every non-GND power track and arc is exactly 0.20 mm',not power_width_errors,power_width_errors)
check('Actual signal and power net-class assignments match the width policy',not class_errors,class_errors)
netclasses={c['name']:c for c in project['net_settings']['classes']}
check('Routing defaults use 0.15 mm signals and 0.20 mm power',
      netclasses.get('Default',{}).get('track_width')==.15
      and netclasses.get('Default',{}).get('diff_pair_width')==.15
      and netclasses.get('Power',{}).get('track_width')==.2)
width_policy=dict(signal_mm=.15,power_mm=.2,power_nets=sorted(POWER_NETS),ground='Existing widths retained; excluded from the exact-width rules',
                  widths_by_net={name:{str(width):count for width,count in sorted(counts.items())}
                                 for name,counts in sorted(widths_by_net.items())})
check('No signal routing on L2 GND',not any(not isinstance(t,pcb.PCB_VIA) and t.GetLayer()==pcb.In1_Cu and t.GetNetname()!='GND' for t in b.GetTracks()))
critical=['RF_CHIP','RF_MID','RF_50','ANT_FEED','XTAL_P','XTAL_N','XTAL_LOAD_P']
check('RF and crystal nets stay on front copper without vias',all(not isinstance(t,pcb.PCB_VIA) and t.GetLayer()==pcb.F_Cu for t in b.GetTracks() if t.GetNetname() in critical))
vias=[t for t in b.GetTracks() if isinstance(t,pcb.PCB_VIA)]
epad=[v for v in vias if v.GetNetname()=='GND' and 107.2<point(v.GetPosition())[0]<110.8 and 115.2<point(v.GetPosition())[1]<118.8]
check('At least nine ground vias under the MCU EPAD',len(epad)>=9,len(epad))
check('Antenna open termination is not grounded',all(pd.GetNetname()!='GND' for pd in fps['AE1'].Pads() if pd.GetNumber()=='2'))
endpads=[p for p in fps['AE1'].Pads() if p.GetNumber()=='2']
endboxes=[p.GetBoundingBox() for p in endpads]
seen={0}
while True:
    connected=seen|{j for i in seen for j in range(len(endboxes))
                   if min(endboxes[i].GetRight(),endboxes[j].GetRight())>max(endboxes[i].GetLeft(),endboxes[j].GetLeft())
                   and min(endboxes[i].GetBottom(),endboxes[j].GetBottom())>max(endboxes[i].GetTop(),endboxes[j].GetTop())}
    if connected==seen:break
    seen=connected
check('Open-end rectangular copper pieces overlap into one continuous shape',
      all(p.GetShape()==pcb.PAD_SHAPE_RECT and math.isclose(p.GetOrientationDegrees()%90,0,abs_tol=.001) for p in endpads)
      and len(seen)==len(endpads))
endplate=max(endpads,key=lambda p:p.GetSize().x*p.GetSize().y)
platebox=endplate.GetBoundingBox()
end_copper=dict(plate_size_board_axes_mm=[pcb.ToMM(platebox.GetWidth()),pcb.ToMM(platebox.GetHeight())],
                plate_area_mm2=round(pcb.ToMM(endplate.GetSize().x)*pcb.ToMM(endplate.GetSize().y),6),
                RF_status='Geometric starting point; not tuned or proven RF-equivalent to the reference')
check('PCB outline is 20 x 29 mm',dimensions==[20,29],dimensions)
check('Flash and USB TVS are on the back; both buttons are on the front',
      all(fps[r].GetLayer()==pcb.B_Cu for r in ['U3','D4']) and
      all(fps[r].GetLayer()==pcb.F_Cu for r in ['SW1','SW2']))
header_geometry={}
for ref in ['J2','J3']:
    pp=sorted((pd for pd in fps[ref].Pads() if pd.GetNumber()),key=lambda pd:int(pd.GetNumber()))
    header_geometry[ref]=dict(side=pcb.LayerName(fps[ref].GetLayer()),
        numbered_pad_positions_mm=[point(pd.GetPosition()) for pd in pp])
check('Headers are mounted on the back with pin 1 toward the antenna and 2 mm pitch',
      all(fps[ref].GetLayer()==pcb.B_Cu and len(d['numbered_pad_positions_mm'])==12
          and all(math.isclose(c[0],a[0],abs_tol=.001) and math.isclose(c[1]-a[1],2,abs_tol=.001)
                  for a,c in zip(d['numbered_pad_positions_mm'],d['numbered_pad_positions_mm'][1:]))
          for ref,d in header_geometry.items()),header_geometry)
header_column_spacing=point(fps['J3'].GetPosition())[0]-point(fps['J2'].GetPosition())[0]
check('Header column center spacing is 18.1 mm',math.isclose(header_column_spacing,18.1,abs_tol=.001),header_column_spacing)
center_x=(min(p[0] for p in outline_points)+max(p[0] for p in outline_points))/2
antenna_feed=next(p for p in fps['AE1'].Pads() if p.GetNumber()=='1')
matching_feed=next(p for p in fps['R6'].Pads() if p.GetNumber()=='2')
check('Antenna sits on the right with its feed aligned to R6',
      point(fps['AE1'].GetPosition())[0]>center_x and
      math.isclose(point(antenna_feed.GetPosition())[0],point(matching_feed.GetPosition())[0],abs_tol=.001))
series_x=[point(p.GetPosition())[0] for ref in ['C16','R6','AE1'] for p in fps[ref].Pads() if p.GetNumber()=='1']
check('Antenna-side series components share a straight axis',max(series_x)-min(series_x)<.001,series_x)
usb_vias={name:[v for v in vias if v.GetNetname()==name] for name in ['USB_D+','USB_D-']}
check('Each USB data net has two matched front/back transitions',all(len(v)==2 for v in usb_vias.values()),{n:len(v) for n,v in usb_vias.items()})
check('USB routing uses only the two outer layers',all(isinstance(t,pcb.PCB_VIA) or t.GetLayer() in [pcb.F_Cu,pcb.B_Cu] for t in b.GetTracks() if t.GetNetname().startswith('USB_')))
check('Antenna is mounted horizontally',math.isclose(fps['AE1'].GetOrientationDegrees()%180,90,abs_tol=.001))
check('Prototype antenna clearance is 20 x 3.8 mm on all copper layers',
      antenna_clearance==[20,3.8] and antenna_zone.GetDoNotAllowZoneFills()
      and all(antenna_zone.IsOnLayer(layer) for layer in [pcb.F_Cu,pcb.In1_Cu,pcb.In2_Cu,pcb.B_Cu]),antenna_clearance)
check('No vias in the antenna clearance',not any(antenna_zone.Outline().Contains(v.GetPosition()) for v in vias))

# Nominal package-body edges, excluding the courtyard and silkscreen stroke.
def body_box(fp,size):
    a=math.radians(fp.GetOrientationDegrees());c=abs(math.cos(a));s=abs(math.sin(a))
    hx=(size[0]*c+size[1]*s)/2;hy=(size[0]*s+size[1]*c)/2;x,y=point(fp.GetPosition())
    return [x-hx,y-hy,x+hx,y+hy]

def box_gap(a,c):
    return math.hypot(max(0,a[0]-c[2],c[0]-a[2]),max(0,a[1]-c[3],c[1]-a[3]))

def bounds(item):
    r=item.GetBoundingBox()
    return [pcb.ToMM(v) for v in [r.GetLeft(),r.GetTop(),r.GetRight(),r.GetBottom()]]

logo_groups={g.GetName():g for g in b.Groups()}
logo_layers={'LOGO_CODEX':pcb.F_SilkS,'LOGO_KZL':pcb.B_SilkS}
silkscreen_logos={}
for name,layer in logo_layers.items():
    items=list(logo_groups[name].GetItems()) if name in logo_groups else []
    if items:
        boxes=[bounds(item) for item in items]
        silkscreen_logos[name]=dict(layer=pcb.LayerName(layer),shapes=len(items),
            bounds_mm=[min(bb[0] for bb in boxes),min(bb[1] for bb in boxes),
                       max(bb[2] for bb in boxes),max(bb[3] for bb in boxes)])
check('Codex and personal logos are native graphics on front and back silkscreen respectively',
      set(silkscreen_logos)==set(logo_layers) and all(
          isinstance(item,pcb.PCB_SHAPE) and item.GetLayer()==layer
          for name,layer in logo_layers.items() for item in logo_groups[name].GetItems()),silkscreen_logos)
check('The replaced antenna text labels are absent',not any(
      isinstance(g,pcb.PCB_TEXT) and g.GetLayer()==pcb.F_SilkS and g.GetText() in ['2.4 GHz','NO COPPER']
      for g in b.GetDrawings()))
board_box=[min(q[0] for q in outline_points),min(q[1] for q in outline_points),
           max(q[0] for q in outline_points),max(q[1] for q in outline_points)]
check('Both logos keep at least 0.25 mm from the board edge',len(silkscreen_logos)==2 and all(
      min(d['bounds_mm'][0]-board_box[0],d['bounds_mm'][1]-board_box[1],
          board_box[2]-d['bounds_mm'][2],board_box[3]-d['bounds_mm'][3])>=.25
      for d in silkscreen_logos.values()))

ant_body=body_box(fps['AE1'],(2,5.2));xtal_body=body_box(fps['Y1'],(2,1.6))
body_gap=box_gap(ant_body,xtal_body)
clock_pin_gap=min(box_gap(bounds(pd),xtal_body) for pd in fps['U1'].Pads() if pd.GetNumber() in ['38','39'])
check('Antenna-to-crystal body gap meets the 8.5 mm project target',body_gap>=8.5,round(body_gap,6))
check('Crystal body clears MCU clock-pin land edges by at least 2.4 mm',clock_pin_gap>=2.4,round(clock_pin_gap,6))
check('Crystal and load capacitors are on the front beside the MCU',
      all(fps[r].GetLayer()==pcb.F_Cu for r in ['Y1','C4','C5'])
      and abs(point(fps['Y1'].GetPosition())[1]-point(fps['U1'].GetPosition())[1])<=.5)
isolation=next((z for z in b.Zones() if z.GetZoneName()=='XTAL_REFERENCE'),None)
band=bounds(isolation) if isolation else None
band_vias=[v for v in vias if isolation and isolation.Outline().Contains(v.GetPosition())]
check('Crystal underside excludes routing and pads on the back and both inner layers',
      isolation is not None and band==[114.45,115.65,116.85,118.15]
      and isolation.GetDoNotAllowTracks() and isolation.GetDoNotAllowPads()
      and not isolation.GetDoNotAllowZoneFills()
      and not isolation.IsOnLayer(pcb.F_Cu)
      and all(isolation.IsOnLayer(l) for l in [pcb.In1_Cu,pcb.In2_Cu,pcb.B_Cu]),band)
ground_returns={}
for ref,num in [('Y1','2'),('Y1','4'),('C4','2'),('C5','2')]:
    pd=next(pd for pd in fps[ref].Pads() if pd.GetNumber()==num)
    ground_returns[ref+'.'+num]=round(min(math.dist(point(pd.GetPosition()),point(v.GetPosition())) for v in vias if v.GetNetname()=='GND'),6)
check('Crystal and load-capacitor ground pads have a ground via within 1 mm',all(d<=1 for d in ground_returns.values()),ground_returns)
check('No signal vias enter the crystal reference area',isolation is not None and all(v.GetNetname()=='GND' for v in band_vias))
l2_ground=pcb.SHAPE_POLY_SET()
for z in b.Zones():
    if not z.GetIsRuleArea() and z.GetNetname()=='GND' and z.IsOnLayer(pcb.In1_Cu):
        l2_ground.BooleanAdd(z.GetFilledPolysList(pcb.In1_Cu))

def uncovered_ground_area(box):
    region=pcb.SHAPE_POLY_SET();region.NewOutline()
    for x,y in [(box[0],box[1]),(box[2],box[1]),(box[2],box[3]),(box[0],box[3])]:region.Append(MM(x),MM(y))
    region.BooleanSubtract(l2_ground)
    return region.Area()/1e12

band_uncovered=uncovered_ground_area([band[0]+.15,band[1]+.15,band[2]-.15,band[3]-.15]) if band else None
body_uncovered=uncovered_ground_area(xtal_body)
check('L2 ground fully covers the crystal reference area interior',band_uncovered==0,band_uncovered)
check('L2 ground fully covers the crystal body projection',body_uncovered==0,body_uncovered)
crystal_isolation=dict(antenna_body_bounds_mm=ant_body,crystal_body_bounds_mm=xtal_body,
    body_clearance_mm=round(body_gap,6),clock_pin_land_to_body_mm=round(clock_pin_gap,6),
    reference_area_bounds_mm=band,nearest_ground_via_distances_mm=ground_returns,
    l2_uncovered_reference_mm2=band_uncovered,l2_uncovered_crystal_mm2=body_uncovered,
    clock_copper_total_mm=round(sum(pcb.ToMM(t.GetLength()) for t in b.GetTracks() if t.GetNetname() in ['XTAL_P','XTAL_N','XTAL_LOAD_P'] and not isinstance(t,pcb.PCB_VIA)),6),
    body_clearance_target_mm=8.5,target_note='The 8.5 mm antenna separation target is a project choice, not a manufacturer guarantee')
rules=project['board']['design_settings']['rules']
vippo=[]
mask_violations=[]
thermal_positions={
    ('U1','41'):{(float(x),float(y)) for x in (108,109,110) for y in (116,117,118)},
    ('U3','9'):{(107.3,125.0),(108.58,123.2)},
}
retained_thermal=set()
thermal_via_ids=set()
for v in vias:
    for ref,f in fps.items():
        for pd in f.Pads():
            if not pd.GetNumber() or pd.GetAttribute()!=pcb.PAD_ATTRIB_SMD or not pd.IsOnCopperLayer():continue
            # The footprint side is authoritative; PAD.GetLayer() can report
            # F.Cu for a bottom-side SMD pad in the legacy Python API.
            layer=f.GetLayer();shape=pd.GetEffectiveShape(layer)
            radius=pcb.ToMM(v.GetDrill())/2
            position=point(v.GetPosition());key=(ref,pd.GetNumber())
            thermal=(position in thermal_positions.get(key,set()) and pd.GetNetname()==v.GetNetname()=='GND')
            if shape.Collide(v.GetPosition(),MM(radius)):
                vippo.append(dict(reference=ref,pad=pd.GetNumber(),net=v.GetNetname(),x_mm=point(v.GetPosition())[0],
                                  y_mm=point(v.GetPosition())[1],drill_mm=pcb.ToMM(v.GetDrill()),diameter_mm=pcb.ToMM(v.GetWidth(pcb.F_Cu))))
                if thermal:
                    retained_thermal.add((ref,pd.GetNumber(),position))
                    thermal_via_ids.add(v.m_Uuid.AsString())
            mask_margin=pcb.ToMM(pd.GetSolderMaskExpansion(layer))
            if not thermal and shape.Collide(v.GetPosition(),MM(radius+mask_margin+.1)-1):
                mask_violations.append(dict(reference=ref,pad=pd.GetNumber(),pad_net=pd.GetNetname(),
                                            via_net=v.GetNetname(),position_mm=position,layer=pcb.LayerName(layer)))
check('Non-thermal via holes clear all SMD mask openings by at least 0.10 mm',not mask_violations,mask_violations)
expected_thermal={(ref,num,pos) for (ref,num),positions in thermal_positions.items() for pos in positions}
check('Only the original 11 filled/capped thermal vias remain in SMD pads',
      len(vippo)==11 and retained_thermal==expected_thermal,len(vippo))
check('Retained thermal vias explicitly specify filling and copper capping',
      all(v.GetFillingMode()==pcb.FILLING_MODE_FILLED and v.GetCappingMode()==pcb.CAPPING_MODE_CAPPED
          for v in vias if v.m_Uuid.AsString() in thermal_via_ids))
tenting_errors=[dict(uuid=v.m_Uuid.AsString(),position_mm=point(v.GetPosition()),
                     front_mode=v.GetFrontTentingMode(),back_mode=v.GetBackTentingMode())
                for v in vias if v.m_Uuid.AsString() not in thermal_via_ids
                and (v.GetFrontTentingMode()!=pcb.TENTING_MODE_TENTED or v.GetBackTentingMode()!=pcb.TENTING_MODE_TENTED)]
check('Ordinary vias explicitly specify tenting on both sides',not tenting_errors,tenting_errors)
with (OUTPUT/'via-in-pad.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['reference','pad','net','x_mm','y_mm','drill_mm','diameter_mm'],lineterminator='\n');w.writeheader();w.writerows(vippo)

# Shortest copper path through the series resistors, with explicit layer nodes.
# Vias connect F/B with the nominal board thickness; same-XY traces on separate
# layers do not connect without a via or a plated pad.
graph={}
def key(x,y,net,layer):return (round(x,3),round(y,3),net,layer)
def edge(a,c,w):
    graph.setdefault(a,[]).append((c,w));graph.setdefault(c,[]).append((a,w))
all_usb=['USB_D+','USB_D-','USB_MCU_D+','USB_MCU_D-']
for net in all_usb:
    net_vias=[v for v in vias if v.GetNetname()==net]
    for layer in [pcb.F_Cu,pcb.B_Cu]:
        tracks=[t for t in b.GetTracks() if t.GetNetname()==net and not isinstance(t,pcb.PCB_VIA) and t.GetLayer()==layer]
        points={point(t.GetStart()) for t in tracks}|{point(t.GetEnd()) for t in tracks}|{point(v.GetPosition()) for v in net_vias}
        for t in tracks:
            a=point(t.GetStart());c=point(t.GetEnd());dx,dy=c[0]-a[0],c[1]-a[1];length=math.hypot(dx,dy)
            if length<1e-8:continue
            chain=[]
            for pt in points:
                u=((pt[0]-a[0])*dx+(pt[1]-a[1])*dy)/(length*length)
                dist=math.hypot(pt[0]-a[0]-u*dx,pt[1]-a[1]-u*dy)
                if -.0005<=u<=1.0005 and dist<.001:chain.append((u,pt))
            chain.sort()
            for (_,pa),(_,pc) in zip(chain,chain[1:]):edge(key(*pa,net,layer),key(*pc,net,layer),math.dist(pa,pc))
        for ref,f in fps.items():
            for pd in f.Pads():
                if pd.GetNetname()!=net or not pd.GetNumber() or not pd.IsOnLayer(layer):continue
                for pp in points:
                    if pd.GetEffectiveShape(layer).Collide(xy(*pp),MM(.001)):
                        edge((ref,pd.GetNumber()),key(*pp,net,layer),math.dist(point(pd.GetPosition()),pp))
    for v in net_vias:
        q=point(v.GetPosition())
        edge(key(*q,net,pcb.F_Cu),key(*q,net,pcb.B_Cu),pcb.ToMM(b.GetDesignSettings().GetBoardThickness()))
for ref in ['R12','R13']:
    ps={p.GetNumber():p for p in fps[ref].Pads() if p.GetNumber()}
    edge((ref,'1'),(ref,'2'),math.dist(point(ps['1'].GetPosition()),point(ps['2'].GetPosition())))
def shortest(a,c):
    serial=itertools.count();q=[(0,next(serial),a)];cost={a:0}
    while q:
        dist,_,n=heapq.heappop(q)
        if n==c:return round(dist,4)
        if dist!=cost[n]:continue
        for nn,w in graph.get(n,[]):
            nd=dist+w
            if nd<cost.get(nn,math.inf):cost[nn]=nd;heapq.heappush(q,(nd,next(serial),nn))
    return None
usb={side:{'D+_mm':shortest(('U1','19'),('J1',side+'6')),
           'D-_mm':shortest(('U1','18'),('J1',side+'7'))} for side in ['A','B']}
for values in usb.values():
    values['skew_mm']=round(abs(values['D+_mm']-values['D-_mm']),4) if all(v is not None for v in values.values()) else None
check('Both USB-C orientations have continuous data paths through their series resistors',all(v is not None for values in usb.values() for v in values.values()),usb)
erc=json.loads((OUTPUT/'erc.json').read_text(encoding='utf-8'))
drc=json.loads((OUTPUT/'drc-final.json').read_text(encoding='utf-8'))
erc_count=sum(len(s['violations'])for s in erc['sheets'])
check('KiCad ERC has no errors or warnings',erc_count==0,erc_count)
check('KiCad DRC has no violations',len(drc['violations'])==0,len(drc['violations']))
check('KiCad PCB has no unconnected items',len(drc['unconnected_items'])==0,len(drc['unconnected_items']))
check('KiCad schematic parity report has no mismatches',drc.get('schematic_parity')==[],drc.get('schematic_parity'))
result=dict(checks=checks,all_passed=all(x['passed']for x in checks),footprints=len(fps),
            populated=sum(not f.IsDNP()for f in fps.values()),tracks=sum(not isinstance(t,pcb.PCB_VIA)for t in b.GetTracks()),
            vias=len(vias),via_in_pad_entries=len(vippo),dimensions_mm=dimensions,nominal_thickness_mm=.8,
            antenna_clearance_mm=antenna_clearance,antenna_orientation_degrees=fps['AE1'].GetOrientationDegrees(),
            antenna_end_copper=end_copper,
            crystal_isolation=crystal_isolation,silkscreen_logos=silkscreen_logos,
            component_sides={r:pcb.LayerName(fps[r].GetLayer()) for r in ['U3','D4','SW1','SW2','J2','J3','Y1','C4','C5','C26']},
            header_geometry=header_geometry,header_column_spacing_mm=round(header_column_spacing,6),
            antenna_center_x_mm=point(fps['AE1'].GetPosition())[0],
            usb_length_method='Copper centerline plus resistor pad spacing and nominal via barrel; excludes device internals and cable',
            copper_layers=4,usb_path_lengths=usb,fabrication_rules=rules,track_width_policy=width_policy,power_passive_references=sorted(power_passives),
            power_passive_footprints=power_passive_footprints,
            resistor_capacitor_footprints=passive_footprints,schematic_wiring=wiring_audit,
            board_sha256=hashlib.sha256(BOARD_FILE.read_bytes()).hexdigest(),
            project_sha256=hashlib.sha256(PROJECT_FILE.read_bytes()).hexdigest(),
            custom_rules_sha256=hashlib.sha256(BOARD_FILE.with_suffix('.kicad_dru').read_bytes()).hexdigest(),
            nonthermal_hole_to_mask_minimum_mm=.1,retained_filled_capped_vias=len(retained_thermal),
            erc_kicad_version=erc.get('kicad_version'),drc_kicad_version=drc.get('kicad_version'),
            limitations=['Axial end copper and 20 x 3.8 mm antenna clearance deviate from the manufacturer reference; RF performance is unmeasured',
                         'RF matching values and antenna efficiency require hardware tuning',
                         'Nominal RF/USB impedance requires manufacturer stackup confirmation',
                         'The 11 retained thermal vias require filling and copper capping; dual-sided SMT assembly required; no physical power or thermal tests performed'])
(OUTPUT/'qa.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:result[k]for k in ['all_passed','footprints','populated','tracks','vias','via_in_pad_entries','usb_path_lengths']},indent=2))
for c in checks:
    if not c['passed']:print('FAILED',c)
if not result['all_passed']:raise SystemExit(1)
