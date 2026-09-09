"""Redraw existing components with explicit wires; preserve electrical pin assignments.

The component specification and embedded symbols are the inputs. This does not
rebuild the PCB or choose component values. The shipped symbol library is updated
with readable pin grouping for the MCU, flash, TVS and logic buffer.
"""
from pathlib import Path
import copy,json,math,uuid,collections
from kicad_sexpr import Atom as A,child,children,parse,dumps,prop,read

ROOT=Path(__file__).resolve().parents[1]
DOCS={s:read(ROOT/f) for s,f in [('core','esp32-c6-pico.kicad_sch'),('io','power-io.kicad_sch')]}
SPEC=json.loads((ROOT/'design-spec.json').read_text())
PARTS={x['ref']:x for x in SPEC}
INST={prop(x,'Reference'):copy.deepcopy(x) for d in DOCS.values() for x in children(d,'symbol')}
LIBS={x[1]:copy.deepcopy(x) for d in DOCS.values() for x in children(child(d,'lib_symbols'),'symbol')}
RID=child(DOCS['core'],'uuid')[1]
SHEET=copy.deepcopy(children(DOCS['core'],'sheet')[0]);SID=child(SHEET,'uuid')[1]
ITEMS={'core':[],'io':[]};WIRES={'core':[],'io':[]};PINS={};PLACED=set();COUNTER=0

def uid(key):return str(uuid.uuid5(uuid.UUID(RID),'direct-wired:'+key))
def fmt(x):return f'{x:.4f}'.rstrip('0').rstrip('.')
def grid(x):return round(round(x/1.27)*1.27,4)
def point(x,y):return (grid(x),grid(y))
def form(s):return parse(s)
def put(sheet,kind,body):
    global COUNTER
    COUNTER+=1
    node=form(f'({kind} {body} (uuid "{uid(str(COUNTER))}"))');ITEMS[sheet].append(node);return node
def text(sheet,value,x,y,size=1.27):
    put(sheet,'text',f'{json.dumps(value)} (at {grid(x)} {grid(y)} 0) (effects (font (size {size} {size})) (justify left bottom))')
def line(sheet,net,*points):
    points=[point(*q) for q in points]
    for a,b in zip(points,points[1:]):
        if a==b:continue
        assert a[0]==b[0] or a[1]==b[1],(net,a,b)
        WIRES[sheet].append((net,a,b))
def glabel(sheet,net,x,y,angle=0):
    x,y=point(x,y);justify='left' if angle in (0,90) else 'right'
    put(sheet,'global_label',f'{json.dumps(net)} (shape input) (at {x} {y} {angle}) '
        f'(effects (font (size 1.016 1.016)) (justify {justify})) '
        f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x} {y} {angle}) (effects (font (size 1 1)) (hide yes)))')
def netlabel(sheet,net,x,y):
    # A global name keeps the existing PCB net names stable across sheets.
    line(sheet,net,(x,y),(x,y-3.81));glabel(sheet,net,x,y-3.81,90)
def nc(sheet,q):put(sheet,'no_connect',f'(at {q[0]} {q[1]})')

def update_property(node,name,value=None,at=None,size=None):
    p=next(x for x in children(node,'property') if x[1]==name)
    if value is not None:p[2]=value
    if at is not None:child(p,'at')[1:]=[A(fmt(at[0])),A(fmt(at[1])),A('0')]
    if size is not None:child(child(child(p,'effects'),'font'),'size')[1:]=[A(fmt(size)),A(fmt(size))]
    return p

def reshape(ref,center,box,positions,aliases=None):
    """Change only symbol graphics and pin positions, retaining pin types/numbers."""
    key=child(INST[ref],'lib_id')[1];sym=LIBS[key]
    pins={child(p,'number')[1]:copy.deepcopy(p) for u in children(sym,'symbol') for p in children(u,'pin')}
    assert set(pins)==set(positions),(ref,set(pins)^set(positions))
    for u in list(children(sym,'symbol')):sym.remove(u)
    name=key.split(':',1)[1]
    x0,y0,x1,y1=box;cx,cy=center
    graphics=form(f'(symbol "{name}_0_1" (rectangle (start {fmt(x0-cx)} {fmt(cy-y0)}) '
        f'(end {fmt(x1-cx)} {fmt(cy-y1)}) (stroke (width 0.254) (type default)) (fill (type background))))')
    unit=[A('symbol'),name+'_1_1']
    for number,pin in pins.items():
        x,y,angle=positions[number]
        child(pin,'at')[1:]=[A(fmt(x-cx)),A(fmt(cy-y)),A(str(angle))]
        child(pin,'length')[1]=A('5.08')
        if ref=='U1':
            for hidden in list(children(pin,'hide')):pin.remove(hidden)
        if ref=='D4' and number in ['4','6'] and child(pin,'hide') is None:pin.append(form('(hide yes)'))
        if aliases and number in aliases:child(pin,'name')[1]=aliases[number]
        for field in ['name','number']:
            child(child(child(pin,field),'effects'),'font')[1]=form('(size 1.016 1.016)')
        unit.append(pin)
    sym.extend([graphics,unit])

MC=(260.35,223.52);MB=(223.52,97.79,297.18,349.25)
mp={str(n):(218.44,y,0) for n,y in [(2,121.92),(3,132.08),(5,157.48),(28,177.8),(37,198.12),(40,218.44),(4,241.3),(14,261.62),(15,281.94),(39,309.88),(38,330.2)]}
spi=[('R17','20','1','CS'),('R1','21','2','Q'),('R2','22','3','WP'),('R3','24','7','HD'),('R4','25','6','CLK'),('R5','26','5','D')]
for i,(_,n,_,_) in enumerate(spi):mp[n]=(302.26,114.3+i*5.08,180)
for n,y in [(18,165.1),(19,185.42),(29,213.36),(30,223.52),(34,241.3)]:mp[str(n)]=(302.26,y,180)
gpio=[6,7,8,9,10,11,12,13,16,17,27,31,32,33,35,36]
for i,n in enumerate(gpio):mp[str(n)]=(302.26,266.7+i*5.08,180)
mp.update({'1':(241.3,92.71,270),'23':(279.4,92.71,270),'41':(260.35,354.33,90)})
oldnames={child(p,'number')[1]:child(p,'name')[1] for u in children(LIBS[child(INST['U1'],'lib_id')[1]],'symbol') for p in children(u,'pin')}
aliases={n:('/'.join(v.split('/')[:2]) if not v.startswith('GPIO') else v.split('/')[0]) for n,v in oldnames.items()}
aliases.update({'18':'GPIO12 / USB_D-','19':'GPIO13 / USB_D+','4':'CHIP_PU / EN'})
reshape('U1',MC,MB,mp,aliases)
fp={n:(414.02,114.3+i*5.08,0) for i,(_,_,n,_) in enumerate(spi)}
fp.update({'8':(467.36,114.3,180),'4':(438.15,156.21,90)})
reshape('U3',(440.69,127),(419.1,102.87,462.28,151.13),fp,
        {'1':'~{CS}','2':'DO / IO1','3':'~{WP} / IO2','7':'~{HOLD} / IO3','5':'DI / IO0','6':'CLK'})
# The USBLC6 channel pins are paired on the same nets in this design.
reshape('D4',(134.62,87.63),(125.73,77.47,144.78,97.79),
        {'1':(120.65,90.17,0),'6':(120.65,90.17,0),'3':(120.65,82.55,0),'4':(120.65,82.55,0),'5':(137.16,72.39,270),'2':(137.16,102.87,90)},
        {'1':'D+ (1,6)','6':'D+','3':'D- (3,4)','4':'D-'})
reshape('U4',(416.56,241.3),(408.94,233.68,424.18,248.92),
        {'1':(419.1,254,90),'2':(403.86,241.3,0),'3':(414.02,254,90),'4':(429.26,241.3,180),'5':(416.56,228.6,270)},
        {'1':'~{OE}','2':'A','3':'GND','4':'Y','5':'VCC'})

def symbol(ref,x,y,angle=0,sheet='core'):
    assert ref not in PLACED,ref
    PLACED.add(ref);x,y=point(x,y);node=copy.deepcopy(INST[ref]);key=child(node,'lib_id')[1]
    child(node,'at')[1:]=[A(fmt(x)),A(fmt(y)),A(str(angle))]
    for m in list(children(node,'mirror')):node.remove(m)
    path='/'+RID+('/'+SID if sheet=='io' else '')
    project=child(child(node,'instances'),'project');child(project,'path')[1]=path
    if ref in PARTS:PARTS[ref]['sheet']=sheet;PARTS[ref]['path']=path+'/'+child(node,'uuid')[1]
    definition=LIBS[key]
    pins=[p for u in children(definition,'symbol') for p in children(u,'pin')]
    for field in children(node,'property'):
        child(field,'at')[1:]=[A(fmt(x)),A(fmt(y)),A('0')]
    if len(pins)<=2 and ref[0] in 'RCL':
        if angle%180==0:
            update_property(node,'Reference',at=(x+4.445,y-1.27),size=1.27)
            update_property(node,'Value',at=(x+4.445,y+1.27),size=1.016)
        else:
            update_property(node,'Reference',at=(x-3.81,y-2.54),size=1.016)
            update_property(node,'Value',at=(x+3.81,y-2.54),size=1.016)
    elif ref=='U1':
        update_property(node,'Reference',at=(260.35,82.55),size=1.778)
        update_property(node,'Value',at=(260.35,86.36),size=2.032)
    else:
        top=max(float(child(p,'at')[2]) for p in pins)
        update_property(node,'Reference',at=(x,y-top-5.08),size=1.27)
        update_property(node,'Value',at=(x,y-top-2.54),size=1.016)
    if ref in ['D4','U4']:
        update_property(node,'Reference',at=(x+17.78,y-5.08),size=1.27)
        update_property(node,'Value',at=(x+17.78,y-2.54),size=1.016)
    if ref in ['SW1','SW2']:
        update_property(node,'Reference',at=(x-5.08,y-1.27),size=1.27)
        update_property(node,'Value',at=(x-7.62,y+1.27),size=1.016)
    if ref in ['D1','D3']:
        update_property(node,'Reference',at=(x+6.35,y-1.27),size=1.016)
        update_property(node,'Value',at=(x+10.16,y+1.27),size=1.016)
    if ref=='AE1':
        update_property(node,'Reference',at=(x+15.24,y-2.54),size=1.27)
        update_property(node,'Value',at=(x+22.86,y),size=1.016)
    if ref=='U3':
        update_property(node,'Reference',at=(x,96.52),size=1.27)
        update_property(node,'Value',at=(x,99.06),size=1.016)
    if ref in ['J1','U2']:
        for field in children(node,'property'):
            if field[1] in ['Reference','Value']:
                at=child(field,'at');at[2]=A(fmt(float(at[2])-2.54))
    if ref=='Y1':
        update_property(node,'Reference',at=(x,y-7.62),size=1.27)
        update_property(node,'Value',at=(x,y-5.08),size=1.016)
    if angle%180:
        for field in children(node,'property'):
            if field[1] in ['Reference','Value']:child(field,'at')[3]=A('90')
    for pin in pins:
        number=child(pin,'number')[1];px,py,pa=map(float,child(pin,'at')[1:4]);a=math.radians(angle)
        q=(round(x+px*math.cos(a)-py*math.sin(a),4),round(y-px*math.sin(a)-py*math.cos(a),4))
        PINS[(ref,number)]=q
        if ref in PARTS and PARTS[ref]['nets'][number] is None:nc(sheet,q)
    ITEMS[sheet].append(node);return node
def P(ref,n):return PINS[(ref,str(n))]

# Package the two standard power symbols locally; their values define global nets.
for name in ['GND','+3V3']:
    path=ROOT/'libs'/('power-'+name+'.kicad_sym')
    node=copy.deepcopy(children(read(path),'symbol')[0]);node[1]='Pico_Design:power__'+name
    for unit in children(node,'symbol'):unit[1]='power__'+unit[1]
    LIBS[node[1]]=node
POWER_COUNT=0
def power(sheet,net,q):
    global POWER_COUNT
    POWER_COUNT+=1;x,y=point(*q);name='GND' if net=='GND' else '+3V3';key='Pico_Design:power__'+name
    ref=f'#PWR{POWER_COUNT:03d}';ident=uid(ref);path='/'+RID+('/'+SID if sheet=='io' else '')
    node=form(f'(symbol (lib_id "{key}") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid "{ident}"))')
    for k,v,py,hide in [('Reference',ref,y,True),('Value',net,y+3.81 if name=='GND' else y-3.556,False),('Footprint','',y,True)]:
        node.append(form(f'(property "{k}" {json.dumps(v)} (at {x} {py} 0) (effects (font (size 1.016 1.016)) {"(hide yes)" if hide else ""}))'))
    node.append(form(f'(pin "1" (uuid "{uid(ref+"pin")}"))'))
    node.append(form(f'(instances (project "esp32-c6-pico" (path "{path}" (reference "{ref}") (unit 1))))'))
    ITEMS[sheet].append(node)
def ground(sheet,q,dy=5.08):
    end=(q[0],grid(q[1]+dy));line(sheet,'GND',q,end);power(sheet,'GND',end)

text('core','ESP32-C6 PICO | DIRECT-WIRED PERIPHERALS | REV A',20.32,20.32,2.54)
text('core','RF matching / 0201 unchanged',241.3,33.02,1.778)
symbol('U1',*MC)
for ref,x,y,a in [('C3',260.35,63.5,0),('L1',285.75,50.8,90),('C2',311.15,63.5,0),
                 ('C16',336.55,50.8,90),('L3',361.95,63.5,0),('C17',387.35,63.5,0),
                 ('R6',412.75,50.8,90),('C18',438.15,63.5,0),('D1',463.55,63.5,90),('AE1',495.3,43.18,0)]:symbol(ref,x,y,a)
line('core','RF_CHIP',P('U1',1),(241.3,50.8),P('L1',1))
line('core','RF_CHIP',(260.35,50.8),P('C3',1));netlabel('core','RF_CHIP',247.65,50.8)
line('core','RF_MID',P('L1',2),P('C16',1));line('core','RF_MID',(311.15,50.8),P('C2',1));netlabel('core','RF_MID',304.8,50.8)
line('core','RF_50',P('C16',2),P('R6',1))
for ref in ['L3','C17']:line('core','RF_50',(P(ref,1)[0],50.8),P(ref,1))
netlabel('core','RF_50',374.65,50.8)
line('core','ANT_FEED',P('R6',2),P('AE1',1));line('core','ANT_FEED',(438.15,50.8),P('C18',1))
line('core','ANT_FEED',(P('D1',2)[0],50.8),P('D1',2));netlabel('core','ANT_FEED',481.33,50.8)
for ref,n in [('C3',2),('C2',2),('L3',2),('C17',2),('C18',2),('D1',1)]:ground('core',P(ref,n))

text('core','3V3 bulk and VDDA3P3 filtering',53.34,100.33,1.778)
for ref,x in [('C8',63.5),('C9',88.9),('C10',114.3),('C19',165.1),('C20',182.88),('C11',200.66)]:symbol(ref,x,132.08)
symbol('L2',142.24,114.3,90)
line('core','+3V3',(50.8,114.3),P('L2',1));power('core','+3V3',(50.8,114.3))
for ref in ['C8','C9','C10']:line('core','+3V3',(P(ref,1)[0],114.3),P(ref,1));ground('core',P(ref,2))
line('core','V3A',P('L2',2),(210.82,114.3),(210.82,132.08),P('U1',3))
line('core','V3A',(210.82,121.92),P('U1',2))
for ref in ['C19','C20','C11']:line('core','V3A',(P(ref,1)[0],114.3),P(ref,1));ground('core',P(ref,2))
netlabel('core','V3A',190.5,114.3)
for ref,pin,y in [('C12',5,157.48),('C13',28,177.8),('C14',37,198.12),('C15',40,218.44)]:
    symbol(ref,195.58,y+5.08);line('core','+3V3',(175.26,y),P('U1',pin));line('core','+3V3',(195.58,y),P(ref,1))
    line('core','+3V3',(175.26,y),(175.26,y-5.08));power('core','+3V3',(175.26,y-5.08));ground('core',P(ref,2))

text('core','EN delay and RESET',96.52,226.06,1.778)
symbol('R7',175.26,233.68);symbol('C21',187.96,248.92);symbol('SW1',154.94,248.92,270)
line('core','CHIP_EN',P('U1',4),(154.94,241.3),P('SW1',1));line('core','CHIP_EN',P('R7',2),(175.26,241.3));line('core','CHIP_EN',(187.96,241.3),P('C21',1))
power('core','+3V3',P('R7',1));ground('core',P('C21',2));ground('core',P('SW1',2));netlabel('core','CHIP_EN',207.01,241.3)
symbol('R9',207.01,254);line('core','GPIO8',P('R9',2),(207.01,261.62),P('U1',14));power('core','+3V3',P('R9',1));glabel('core','GPIO8',210.82,261.62,180)
text('core','BOOT: GPIO8 high, GPIO9 low at reset',96.52,269.24,1.524)
symbol('R8',175.26,274.32);symbol('SW2',187.96,289.56,270)
line('core','GPIO9_BOOT',P('R8',2),(175.26,281.94),P('U1',15));line('core','GPIO9_BOOT',(187.96,281.94),P('SW2',1))
power('core','+3V3',P('R8',1));ground('core',P('SW2',2));glabel('core','GPIO9_BOOT',210.82,281.94,180)

text('core','40 MHz crystal / local load capacitors',91.44,302.26,1.778)
symbol('R18',193.04,309.88,270);symbol('Y1',160.02,320.04);symbol('C4',139.7,325.12);symbol('C5',187.96,335.28)
line('core','XTAL_P',P('U1',39),P('R18',1));netlabel('core','XTAL_P',210.82,309.88)
line('core','XTAL_LOAD_P',P('R18',2),(147.32,309.88),(147.32,320.04),P('Y1',1))
line('core','XTAL_LOAD_P',(147.32,320.04),(139.7,320.04),P('C4',1));netlabel('core','XTAL_LOAD_P',162.56,309.88)
line('core','XTAL_N',P('U1',38),(177.8,330.2),(177.8,320.04),P('Y1',3));line('core','XTAL_N',(187.96,330.2),P('C5',1));netlabel('core','XTAL_N',210.82,330.2)
ground('core',P('C4',2));ground('core',P('C5',2));ground('core',P('Y1',2));ground('core',P('U1',41))

text('core','4 MB QSPI flash / series resistors at U1',327.66,78.74,1.778)
symbol('U3',440.69,127)
for i,(ref,pin,flash_pin,key) in enumerate(spi):
    y=114.3+i*5.08;symbol(ref,365.76,y,90)
    line('core','SPI_'+key+'_MCU',P('U1',pin),P(ref,1));line('core','SPI_'+key,P(ref,2),P('U3',flash_pin))
    # Label each wire without detached labels at individual resistor pins.
    glabel('core','SPI_'+key+'_MCU',322.58,y,180);glabel('core','SPI_'+key,396.24,y,0)
symbol('C7',345.44,99.06);symbol('C6',499.11,99.06)
line('core','VDD_SPI',P('U1',23),(279.4,86.36),(499.11,86.36),P('C6',1))
line('core','VDD_SPI',(345.44,86.36),P('C7',1));line('core','VDD_SPI',(480.06,86.36),(480.06,114.3),P('U3',8));netlabel('core','VDD_SPI',292.1,86.36)
for ref in ['C6','C7']:ground('core',P(ref,2))
line('core','GND',P('U3',4),(438.15,161.29),(440.69,161.29));ground('core',(440.69,161.29))

text('core','Native USB Serial/JTAG / connector and TVS on sheet 2',327.66,154.94,1.778)
for r,c,n,y,net in [('R12','C27',18,165.1,'USB_D-'),('R13','C28',19,185.42,'USB_D+')]:
    symbol(r,370.84,y,270);symbol(c,342.9,y+5.08)
    m='USB_MCU_D'+net[-1];line('core',m,P('U1',n),P(r,2));line('core',m,(342.9,y),P(c,1));ground('core',P(c,2))
    line('core',net,P(r,1),(400.05,y));glabel('core',net,400.05,y,0);glabel('core',m,322.58,y,180)
symbol('R14',370.84,213.36,90);line('core','U0TXD_MCU',P('U1',29),P('R14',1));line('core','U0TXD',P('R14',2),(400.05,213.36));glabel('core','U0TXD',400.05,213.36,0);glabel('core','U0TXD_MCU',322.58,213.36,180)
line('core','U0RXD',P('U1',30),(400.05,223.52));glabel('core','U0RXD',400.05,223.52,0)
symbol('R16',342.9,248.92);symbol('U4',416.56,241.3);symbol('R15',457.2,241.3,90);symbol('D2',502.92,241.3)
symbol('C26',441.96,228.6);symbol('C25',528.32,228.6)
line('core','GPIO21_LED',P('U1',34),P('U4',2));line('core','GPIO21_LED',(342.9,241.3),P('R16',1));ground('core',P('R16',2));glabel('core','GPIO21_LED',322.58,241.3,180)
line('core','LED_DATA_5V',P('U4',4),P('R15',1));glabel('core','LED_DATA_5V',433.07,241.3,180)
line('core','LED_DIN',P('R15',2),P('D2',3));glabel('core','LED_DIN',482.6,241.3,0)
line('core','VBUS_USB',(416.56,220.98),(528.32,220.98),P('C25',1));line('core','VBUS_USB',(416.56,220.98),P('U4',5))
line('core','VBUS_USB',(441.96,220.98),P('C26',1));line('core','VBUS_USB',(502.92,220.98),P('D2',4));power('core','VBUS_USB',(416.56,220.98))
for ref in ['C25','C26']:ground('core',P(ref,2))
line('core','GND',P('U4',1),(419.1,259.08),(414.02,259.08),P('U4',3));ground('core',(416.56,259.08));ground('core',P('D2',2))
for pin in gpio:
    q=P('U1',pin);net=PARTS['U1']['nets'][str(pin)];line('core',net,q,(345.44,q[1]));glabel('core',net,345.44,q[1],0)
text('core','GPIO headers and USB power input are on sheet 2.\nAll GPIO signals are 3.3 V.\nRF values are initial values; verify matching on the assembled board.',396.24,292.1,1.524)
child(SHEET,'at')[1:]=[A('396.24'),A('307.34')];child(SHEET,'size')[1:]=[A('142.24'),A('25.4')]
update_property(SHEET,'Sheetname',at=(396.24,306.07));update_property(SHEET,'Sheetfile',at=(396.24,334.01));ITEMS['core'].append(SHEET)

text('io','ESP32-C6 PICO | POWER, USB & INTERFACES | REV A',20.32,20.32,2.54)
text('io','USB-C input, CC pull-downs and ESD protection',20.32,30.48,1.778)
symbol('J1',45.72,85.09,sheet='io');symbol('D4',134.62,87.63,sheet='io')
symbol('R10',83.82,48.26,90,'io');symbol('R11',109.22,48.26,90,'io')
line('io','CC1',P('J1','A5'),(73.66,74.93),(73.66,48.26),P('R10',1));line('io','GND',P('R10',2),(88.9,48.26));ground('io',(88.9,48.26))
line('io','CC2',P('J1','B5'),(96.52,77.47),(96.52,48.26),P('R11',1));line('io','GND',P('R11',2),(114.3,48.26));ground('io',(114.3,48.26))
netlabel('io','CC1',73.66,69.85);netlabel('io','CC2',96.52,69.85)
line('io','VBUS_USB',P('J1','A4'),(66.04,69.85),(66.04,35.56),(137.16,35.56),P('D4',5));power('io','VBUS_USB',(137.16,35.56))
line('io','USB_D-',P('J1','A7'),P('D4',3));line('io','USB_D-',P('J1','B7'),(81.28,85.09),(81.28,82.55));glabel('io','USB_D-',110.49,82.55,0)
line('io','USB_D+',P('J1','A6'),(76.2,87.63),(76.2,90.17),P('D4',1));line('io','USB_D+',P('J1','B6'),(76.2,90.17));glabel('io','USB_D+',110.49,90.17,0)
line('io','GND',P('J1','SH'),(38.1,114.3),(45.72,114.3),P('J1','A1'));ground('io',(45.72,114.3));ground('io',P('D4',2))
symbol('C24',172.72,88.9,sheet='io');power('io','VBUS_USB',P('C24',1));ground('io',P('C24',2))

text('io','USB supply, backfeed blocking and 3.3 V regulator',220.98,30.48,1.778)
symbol('D5',271.78,53.34,180,'io');symbol('D3',220.98,71.12,90,'io')
symbol('U2',336.55,71.12,sheet='io');symbol('C22',307.34,83.82,sheet='io');symbol('C23',365.76,83.82,sheet='io')
power('io','VBUS_USB',(218.44,53.34));line('io','VBUS_USB',(218.44,53.34),P('D5',2));line('io','VBUS_USB',(P('D3',2)[0],53.34),P('D3',2));ground('io',P('D3',1))
line('io','+5V',P('D5',1),(307.34,53.34),(307.34,68.58),P('U2',1));line('io','+5V',(307.34,68.58),P('C22',1))
line('io','+5V',P('U2',3),(317.5,71.12),(317.5,68.58));power('io','+5V',(307.34,53.34))
line('io','+3V3',P('U2',5),(365.76,68.58),P('C23',1));power('io','+3V3',(365.76,68.58))
for ref in ['C22','C23']:ground('io',P(ref,2))
ground('io',P('U2',2))
text('io','3V3 / 5V headers are outputs.\nUse a current-limited supply for first power-up.\nVerify Wi-Fi TX droop, LDO temperature and capacitor DC-bias derating.',220.98,119.38,1.524)
text('io','2.00 mm pitch headers / pin 1 toward the antenna',35.56,149.86,1.778)
for ref,x in [('J2',93.98),('J3',187.96)]:
    symbol(ref,x,187.96,sheet='io')
    for n,net in PARTS[ref]['nets'].items():
        q=P(ref,n);end=(q[0]-15.24,q[1]);line('io',net,q,end)
        if net in ['GND','+3V3','+5V']:glabel('io',net,*end,180)
        else:glabel('io',net,*end,180)
text('io','Keep GPIO4/5/8/9/15 strap levels valid during reset.\nHold BOOT, tap RESET, then release BOOT for recovery.\nUART adapter logic must be 3.3 V.',35.56,228.6,1.524)
for i,net in [(0,'GND'),(1,'VBUS_USB'),(3,'+5V'),(4,'V3A')]:
    ref=f'#FLG{i:02d}';symbol(ref,254+i*25.4,175.26,sheet='io');q=P(ref,1);line('io',net,q,(q[0],q[1]+5.08));glabel('io',net,q[0],q[1]+5.08,270)
assert set(PARTS)<=PLACED,set(PARTS)-PLACED

def on_segment(q,a,b):return min(a[0],b[0])<=q[0]<=max(a[0],b[0]) and min(a[1],b[1])<=q[1]<=max(a[1],b[1]) and (a[0]==b[0]==q[0] or a[1]==b[1]==q[1])
for sheet in ['core','io']:
    nodes=collections.defaultdict(set)
    for net,a,b in WIRES[sheet]:nodes[net].update([a,b])
    # Split same-net wire branches, then put visible junctions at electrical tees.
    edges=set()
    for net,a,b in WIRES[sheet]:
        points=sorted([q for q in nodes[net] if on_segment(q,a,b)],key=lambda q:(q[0],q[1]))
        for u,v in zip(points,points[1:]):edges.add((net,u,v))
    degree=collections.Counter()
    for net,a,b in sorted(edges):
        put(sheet,'wire',f'(pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default))')
        degree[(net,a)]+=1;degree[(net,b)]+=1
    for (net,q),count in degree.items():
        if count>=3:put(sheet,'junction',f'(at {q[0]} {q[1]}) (diameter 0) (color 0 0 0 0)')
    doc=copy.deepcopy(DOCS[sheet])
    for kind in ['symbol','wire','global_label','label','junction','no_connect','text','sheet','lib_symbols','polyline','rectangle']:
        for node in list(children(doc,kind)):doc.remove(node)
    child(doc,'paper')[1:]=['A2' if sheet=='core' else 'A3']
    doc.append([A('lib_symbols')]+[copy.deepcopy(v) for v in LIBS.values()]);doc.extend(ITEMS[sheet])
    file=ROOT/('esp32-c6-pico.kicad_sch' if sheet=='core' else 'power-io.kicad_sch')
    file.write_text(dumps(doc)+'\n')
lib=read(ROOT/'libs/Pico_Design.kicad_sym')
for node in list(children(lib,'symbol')):lib.remove(node)
for key,value in LIBS.items():
    if not key.startswith('Pico_Design:'):continue
    node=copy.deepcopy(value);node[1]=key.split(':',1)[1];lib.append(node)
(ROOT/'libs/Pico_Design.kicad_sym').write_text(dumps(lib)+'\n')
(ROOT/'design-spec.json').write_text(json.dumps(list(PARTS.values()),indent=2,ensure_ascii=False)+'\n')
print('Redrew',len(PARTS),'components; core:',sum(x['sheet']=='core' for x in PARTS.values()),'IO:',sum(x['sheet']=='io' for x in PARTS.values()))
