"""Independent schematic/PCB parity, RF-layer, fabrication, and USB length audit."""
import csv,heapq,json,math,hashlib,itertools
import xml.etree.ElementTree as ET
import pcbnew as pcb
from build_pcb import ROOT,OUTPUT,BOARD_FILE,MM,xy,point

b=pcb.LoadBoard(str(BOARD_FILE))
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
check('No signal routing on L2 GND',not any(not isinstance(t,pcb.PCB_VIA) and t.GetLayer()==pcb.In1_Cu and t.GetNetname()!='GND' for t in b.GetTracks()))
critical=['RF_CHIP','RF_MID','RF_50','ANT_FEED','XTAL_P','XTAL_N','XTAL_LOAD_P','USB_D+','USB_D-']
check('RF, crystal and main USB nets stay on front copper',all(not isinstance(t,pcb.PCB_VIA) and t.GetLayer()==pcb.F_Cu for t in b.GetTracks() if t.GetNetname() in critical))
vias=[t for t in b.GetTracks() if isinstance(t,pcb.PCB_VIA)]
epad=[v for v in vias if v.GetNetname()=='GND' and 107.2<point(v.GetPosition())[0]<110.8 and 115.2<point(v.GetPosition())[1]<118.8]
check('At least nine ground vias under the MCU EPAD',len(epad)>=9,len(epad))
check('Antenna open termination is not grounded',all(pd.GetNetname()!='GND' for pd in fps['AE1'].Pads() if pd.GetNumber()=='2'))
check('No vias in the 18 x 9 mm antenna clearance',not any(point(v.GetPosition())[1]<109 for v in vias))
rules=json.loads((ROOT/'esp32-c6-pico.kicad_pro').read_text(encoding='utf-8'))['board']['design_settings']['rules']
vippo=[]
for v in vias:
    for ref,f in fps.items():
        for pd in f.Pads():
            if not pd.GetNumber() or pd.GetAttribute()!=pcb.PAD_ATTRIB_SMD or pd.GetNetname()!=v.GetNetname():continue
            if pd.GetEffectiveShape(pd.GetLayer()).Collide(v.GetPosition(),MM(pcb.ToMM(v.GetDrill())/2)):
                vippo.append(dict(reference=ref,pad=pd.GetNumber(),net=v.GetNetname(),x_mm=point(v.GetPosition())[0],
                                  y_mm=point(v.GetPosition())[1],drill_mm=pcb.ToMM(v.GetDrill()),diameter_mm=pcb.ToMM(v.GetWidth(pcb.F_Cu))))
with (OUTPUT/'via-in-pad.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['reference','pad','net','x_mm','y_mm','drill_mm','diameter_mm'],lineterminator='\n');w.writeheader();w.writerows(vippo)

# Shortest copper path through the series resistors, including connector branch
# geometry. Capacitor branches are not part of the end-to-end propagation path.
graph={}
def key(x,y,net):return (round(x,3),round(y,3),net)
def edge(a,c,w):
    graph.setdefault(a,[]).append((c,w));graph.setdefault(c,[]).append((a,w))
all_usb=['USB_D+','USB_D-','USB_MCU_D+','USB_MCU_D-']
for net in all_usb:
    tracks=[t for t in b.GetTracks() if t.GetNetname()==net and not isinstance(t,pcb.PCB_VIA)]
    points={point(t.GetStart()) for t in tracks}|{point(t.GetEnd()) for t in tracks}
    for t in tracks:
        a=point(t.GetStart());c=point(t.GetEnd());dx,dy=c[0]-a[0],c[1]-a[1];length=math.hypot(dx,dy)
        if length<1e-8:continue
        chain=[]
        for p in points:
            u=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(length*length)
            dist=math.hypot(p[0]-a[0]-u*dx,p[1]-a[1]-u*dy)
            if -.0005<=u<=1.0005 and dist<.001:chain.append((u,p))
        chain.sort()
        for (_,pa),(_,pc) in zip(chain,chain[1:]):edge(key(*pa,net),key(*pc,net),math.dist(pa,pc))
    for ref,f in fps.items():
        for pd in f.Pads():
            if pd.GetNetname()!=net or not pd.GetNumber():continue
            for pp in points:
                if pd.GetEffectiveShape(pd.GetLayer()).Collide(xy(*pp),MM(.001)):
                    edge((ref,pd.GetNumber()),key(*pp,net),math.dist(point(pd.GetPosition()),pp))
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
erc=json.loads((OUTPUT/'erc.json').read_text(encoding='utf-8'))
drc=json.loads((OUTPUT/'drc-final.json').read_text(encoding='utf-8'))
erc_count=sum(len(s['violations'])for s in erc['sheets'])
check('KiCad ERC has no errors or warnings',erc_count==0,erc_count)
check('KiCad DRC has no violations',len(drc['violations'])==0,len(drc['violations']))
check('KiCad PCB has no unconnected items',len(drc['unconnected_items'])==0,len(drc['unconnected_items']))
result=dict(checks=checks,all_passed=all(x['passed']for x in checks),footprints=len(fps),
            populated=sum(not f.IsDNP()for f in fps.values()),tracks=sum(not isinstance(t,pcb.PCB_VIA)for t in b.GetTracks()),
            vias=len(vias),via_in_pad_entries=len(vippo),dimensions_mm=[18,39],nominal_thickness_mm=.8,
            copper_layers=4,usb_path_lengths=usb,fabrication_rules=rules,
            board_sha256=hashlib.sha256(BOARD_FILE.read_bytes()).hexdigest(),
            limitations=['RF matching values and antenna efficiency require hardware tuning',
                         'Nominal RF/USB impedance requires manufacturer stackup confirmation',
                         'VIPPO and dual-sided SMT assembly required; no physical power or thermal tests performed'])
(OUTPUT/'qa.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:result[k]for k in ['all_passed','footprints','populated','tracks','vias','via_in_pad_entries','usb_path_lengths']},indent=2))
for c in checks:
    if not c['passed']:print('FAILED',c)
if not result['all_passed']:raise SystemExit(1)
