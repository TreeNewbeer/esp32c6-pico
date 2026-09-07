"""Generate the completed, portable KiCad schematic and its explicit pin/net map.

Run using the Python shipped with KiCad. Original CAD files are preserved in backups.
All circuit connectivity is declared here; PCB generation consumes KiCad's exported
XML netlist, never a second independently maintained connectivity definition.
"""
from __future__ import annotations

import copy
import csv
import json
import math
import uuid
from pathlib import Path

from kicad_sexpr import Atom as A, child, children, dumps, parse, prop, read, symbol_from_library

ROOT = Path(__file__).resolve().parents[1]
LIB = Path('C:/Program Files/KiCad/10.0/share/kicad/symbols')
BASE = ROOT / 'backups/before-foundation-20260906/esp32-c6-pico.kicad_sch'
ORIGINAL = read(BASE)
OLD_LIBS = {s[1]: s for s in children(child(ORIGINAL, 'lib_symbols'), 'symbol')}
OLD_IDS = {prop(s, 'Reference'): child(s, 'uuid')[1] for s in children(ORIGINAL, 'symbol')}
ROOT_ID = child(ORIGINAL, 'uuid')[1]


def uid(key):
    return str(uuid.uuid5(uuid.UUID(ROOT_ID), key))


def form(text):
    return parse(text)


def grid(value):
    return round(round(value / 1.27) * 1.27, 4)


LIBRARIES = {}
USED = {}
PARTS = []
SHEETS = {'core': [], 'io': []}
SHEET_ID = {'core': ROOT_ID, 'io': uid('power-io-sheet')}
SHEET_INSTANCE = uid('power-io-instance')


def get_symbol(lib_id):
    if lib_id in USED:
        return USED[lib_id]
    if lib_id == 'Pico_Custom:SN74LV1T125':
        library = read(LIB/'74xGxx.kicad_sym')
        sym = symbol_from_library(library, '74AHCT1G125')
        sym[1] = lib_id
        for field in children(sym,'property'):
            if field[1]=='Value':field[2]='SN74LV1T125'
            if field[1]=='Datasheet':field[2]='https://www.ti.com/lit/ds/symlink/sn74lv1t125.pdf'
            if field[1]=='Description':field[2]='Single-supply logic-level translating buffer, active-low OE, 1.6-5.5 V supply'
    elif lib_id in OLD_LIBS:
        sym = copy.deepcopy(OLD_LIBS[lib_id])
    else:
        lib, name = lib_id.split(':')
        if lib not in LIBRARIES:
            LIBRARIES[lib] = read(LIB / (lib + '.kicad_sym'))
        sym = symbol_from_library(LIBRARIES[lib], name)
        sym[1] = lib_id
    # Ship a local copy of every used symbol, removing reliance on add-ons.
    if lib_id == 'espressif-kicad-addon:ESP32-C6':
        for unit in children(sym, 'symbol'):
            for pin in children(unit, 'pin'):
                if child(pin, 'number')[1] == '23':
                    pin[1] = A('power_out')
                    child(pin, 'name')[1] = 'VDD_SPI'
    USED[lib_id] = sym
    return sym


def note(sheet, text, x, y, size=1.27):
    SHEETS[sheet].append(form(f'(text {json.dumps(text)} (at {grid(x)} {grid(y)} 0) '
                              f'(effects (font (size {size} {size})) (justify left bottom)) '
                              f'(uuid "{uid(sheet+text)}"))'))


def wire(sheet, p, q, key):
    if p == q:
        return
    SHEETS[sheet].append(form(f'(wire (pts (xy {p[0]} {p[1]}) (xy {q[0]} {q[1]})) '
                              f'(stroke (width 0) (type default)) (uuid "{uid(key)}"))'))


def label(sheet, net, x, y, angle, key):
    # Net names are global because the supply / interfaces occupy a second sheet.
    justification = 'left' if angle in (0, 90) else 'right'
    SHEETS[sheet].append(form(f'(global_label {json.dumps(net)} (shape input) '
                              f'(at {x} {y} {angle}) (effects (font (size 0.9 0.9)) '
                              f'(justify {justification})) (uuid "{uid(key)}") '
                              f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" '
                              f'(at {x} {y} {angle}) (effects (font (size 1 1)) (hide yes))))'))


def part(ref, lib_id, value, footprint, nets, x, y, angle=0, sheet='core', dnp=False, mpn='', detail='', datasheet=None):
    sym = get_symbol(lib_id)
    x, y = grid(x), grid(y)
    path = '/' + ROOT_ID + ('/' + SHEET_INSTANCE if sheet == 'io' else '')
    instance_id = OLD_IDS.get(ref, uid(ref))
    pins = [p for u in children(sym, 'symbol') for p in children(u, 'pin')]
    nets = {str(k): v for k, v in nets.items()}
    assert {child(p, 'number')[1] for p in pins} == set(nets), (ref, nets)
    local_name = lib_id.replace(':', '__')
    # Every instance uses a shipped library with a stable definition.
    instance = form(f'(symbol (lib_id "Pico_Design:{local_name}") (at {x} {y} {angle}) '
                    f'(unit 1) (in_bom {"no" if ref.startswith("#") else "yes"}) '
                    f'(on_board {"no" if ref.startswith("#") else "yes"}) '
                    f'(dnp {"yes" if dnp else "no"}) (uuid "{instance_id}"))')
    # Passives get labels alongside their bodies; ICs above their outlines.
    if len(pins) <= 2:
        positions = [(x + 2.54, y - 1.27), (x + 2.54, y + 1.27)] if angle == 0 else [(x, y - 3.81), (x, y + 3.81)]
    else:
        ymax = max(float(child(p, 'at')[2]) for p in pins)
        positions = [(x, y - ymax - 6.35), (x, y - ymax - 3.81)]
    for i, (name, val) in enumerate([('Reference', ref), ('Value', value), ('Footprint', footprint),
                                    ('Datasheet', datasheet or prop(sym, 'Datasheet')), ('MPN', mpn or value), ('AssemblyNote', detail)]):
        px, py = positions[i] if i < 2 else (x, y)
        hidden = i >= 2 or ref.startswith('#')
        instance.append(form(f'(property {json.dumps(name)} {json.dumps(val)} (at {px} {py} 0) '
                             f'(effects (font (size {1.0 if i==0 else 0.9} {1.0 if i==0 else 0.9})) '
                             f'{"(hide yes)" if hidden else ""}))'))
    seen = set()
    for pin in pins:
        num = child(pin, 'number')[1]
        instance.append(form(f'(pin "{num}" (uuid "{uid(ref+"/"+num)}"))'))
        px, py, pa = map(float, child(pin, 'at')[1:4])
        rad = math.radians(angle)
        rx, ry = px*math.cos(rad)-py*math.sin(rad), px*math.sin(rad)+py*math.cos(rad)
        end = (round(x+rx, 4), round(y-ry, 4))
        if end in seen:
            continue
        seen.add(end)
        net = nets[num]
        if net is None:
            SHEETS[sheet].append(form(f'(no_connect (at {end[0]} {end[1]}) (uuid "{uid(ref+num+"nc")}"))'))
            continue
        direction = (pa + angle) % 360
        # Extend away from the component, then attach the global label facing inward.
        er = math.radians(direction)
        outer = (round(end[0] - 2.54*math.cos(er), 4), round(end[1] + 2.54*math.sin(er), 4))
        wire(sheet, end, outer, ref+num+'wire')
        label(sheet, net, *outer, int((direction + 180) % 360), ref+num+'label')
    instance.append(form(f'(instances (project "esp32-c6-pico" '
                         f'(path "{path}" (reference "{ref}") (unit 1))))'))
    SHEETS[sheet].append(instance)
    if not ref.startswith('#'):
        PARTS.append(dict(ref=ref, value=value, footprint=footprint, nets=nets, uuid=instance_id,
                          sheet=sheet, path=path+'/'+instance_id, dnp=dnp, mpn=mpn or value, note=detail))


C0402 = 'Capacitor_SMD:C_0402_1005Metric'
C0201 = 'Capacitor_SMD:C_0201_0603Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
R0402 = 'Resistor_SMD:R_0402_1005Metric'
R0201 = 'Resistor_SMD:R_0201_0603Metric'
L0201 = 'Inductor_SMD:L_0201_0603Metric'


def passive(ref, value, net1, net2, x, y, sheet='core', angle=0, fp=None, dnp=False, note=''):
    kind = ref[0]
    default = {'C': C0402, 'R': R0402, 'L': L0201}[kind]
    part(ref, 'Device:'+kind+'_Small', value, fp or default, {1: net1, 2: net2},
         x, y, angle, sheet, dnp, detail=note)


def build():
    note('core', 'ESP32-C6 PICO | CORE, RF & FLASH | REV A', 20, 20, 2.54)
    note('core', '01  ESP32-C6 QFN40 - external 4 MB flash', 20, 42, 1.8)
    main = {1:'RF_CHIP',2:'V3A',3:'V3A',4:'CHIP_EN',5:'+3V3',6:'GPIO0',7:'GPIO1',8:'GPIO2',9:'GPIO3',
            10:'GPIO4',11:'GPIO5',12:'GPIO6',13:'GPIO7',14:'GPIO8',15:'GPIO9_BOOT',16:'GPIO10',17:'GPIO11',
            18:'USB_MCU_D-',19:'USB_MCU_D+',20:'SPI_CS_MCU',21:'SPI_Q_MCU',22:'SPI_WP_MCU',23:'VDD_SPI',
            24:'SPI_HD_MCU',25:'SPI_CLK_MCU',26:'SPI_D_MCU',27:'GPIO15',28:'+3V3',29:'U0TXD_MCU',30:'U0RXD',
            31:'GPIO18',32:'GPIO19',33:'GPIO20',34:'GPIO21_LED',35:'GPIO22',36:'GPIO23',37:'+3V3',38:'XTAL_N',39:'XTAL_P',40:'+3V3',41:'GND'}
    part('U1','espressif-kicad-addon:ESP32-C6','ESP32-C6',
         'Pico:QFN40_ESP32_C6_Compact',main,88.9,105.41,detail='QFN40, NOT the pin-incompatible C6FH4 QFN32')
    note('core', '02  RF chip CLCCL filter + antenna pi network', 162, 42, 1.8)
    passive('C3','1.5pF','RF_CHIP','GND',172,65,fp=C0201,note='C0G; RF initial value, VNA tuning required')
    passive('L1','2.4nH','RF_CHIP','RF_MID',191,55,angle=90,note='High-Q RF; initial value')
    passive('C2','1.5pF','RF_MID','GND',210,65,fp=C0201,note='C0G; RF initial value')
    passive('C16','10pF','RF_MID','RF_50',229,55,angle=90,fp=C0201,note='C0G DC-block / tuning initial value')
    passive('L3','DNP','RF_50','GND',248,65,dnp=True,note='Shunt RF tuning option')
    passive('C17','DNP','RF_50','GND',273,65,fp=C0201,dnp=True,note='Antenna pi input shunt')
    passive('R6','0R','RF_50','ANT_FEED',292,55,angle=90,fp=R0201,note='Antenna pi series tuning option')
    passive('C18','DNP','ANT_FEED','GND',312,65,fp=C0201,dnp=True,note='Antenna pi output shunt')
    part('AE1','Walsin_Antenna:RFANT5220110A0T','RFANT5220110A0T',
         'Walsin_Antenna:RFANT5220110A0T',{1:'ANT_FEED',2:None},360,54,
         detail='Pad 2 has open tuning copper, never connect to ground; 18x9 mm RF clearance')
    part('D1','Diode:ESD9B5.0ST5G','PESD5V0F1BL-Q','Diode_SMD:D_SOD-882',
         {1:'GND',2:'ANT_FEED'},341,77,90,dnp=True,detail='0.4 pF antenna ESD option; original 15 pF ESD9B is unsuitable',
         datasheet='https://assets.nexperia.com/documents/data-sheet/PESD5V0F1BL-Q.pdf')
    note('core','RF values are starting points only. Tune with the assembled PCB and final enclosure.\n0201 RF filter; 50 ohm feed referenced to L2 GND. Keep all layers clear in antenna area.',163,92)
    note('core','03  Power decoupling - fit at the named pins',162,111,1.8)
    caps = [('C8','10uF','+3V3',C0603,'Main bulk'),('C9','1uF','+3V3',C0402,'Main bulk'),
            ('C10','100nF','+3V3',C0402,'Main HF'),('C12','100nF','+3V3',C0402,'U1 pin 5'),
            ('C13','100nF','+3V3',C0402,'U1 pin 28'),('C14','100nF','+3V3',C0402,'U1 pin 37'),
            ('C15','100nF','+3V3',C0402,'U1 pin 40')]
    for i,(ref,val,net,fp,msg) in enumerate(caps):
        passive(ref,val,net,'GND',171+i*30,132,fp=fp,note=msg+'; X7R 10 V minimum')
    passive('L2','2.0nH','+3V3','V3A',177,166,angle=90,fp='Inductor_SMD:L_0402_1005Metric',note='RF supply filter; Irated >= 500 mA, low DCR')
    passive('C11','1uF','V3A','GND',214,166,note='U1 pins 2/3 local bypass')
    passive('C19','10uF','V3A','GND',246,166,fp=C0603,note='U1 pin 2 local bulk')
    passive('C20','10uF','V3A','GND',278,166,fp=C0603,note='U1 pin 3 local bulk')
    note('core','04  Quad-SPI flash, powered from U1 VDD_SPI',20,158,1.8)
    flashnets={1:'SPI_CS',2:'SPI_Q',3:'SPI_WP',4:'GND',5:'SPI_D',6:'SPI_CLK',7:'SPI_HD',8:'VDD_SPI'}
    flashnets[9]='GND'
    part('U3','Memory_Flash:W25Q32JVZP','W25Q32JVZPIQ','Package_SON:WSON-8-1EP_6x5mm_P1.27mm_EP3.4x4mm',flashnets,106.68,209.55)
    for i,(ref,key) in enumerate([('R17','CS'),('R1','Q'),('R2','WP'),('R3','HD'),('R4','CLK'),('R5','D')]):
        passive(ref,'0R','SPI_'+key+'_MCU','SPI_'+key,44,178+i*13,angle=90,fp=R0201,note='Place at U1; SPI clock defaults to 40 MHz for bring-up')
    passive('C6','100nF','VDD_SPI','GND',127,198,note='At flash VCC')
    passive('C7','1uF','VDD_SPI','GND',147,198,note='At U1 VDD_SPI pin')
    note('core','05  40 MHz crystal',170,199,1.8)
    passive('L4','24nH','XTAL_P','XTAL_LOAD_P',181,219,angle=90,fp='Inductor_SMD:L_0402_1005Metric',note='Crystal harmonic suppression; initial value')
    part('Y1','Device:Crystal_GND24_Small','40MHz / CL=8pF','Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm',
         {1:'XTAL_LOAD_P',2:'GND',3:'XTAL_N',4:'GND'},227,219,mpn='E9X400081G08',
         detail='Eaton E9X; 40 MHz, CL 8 pF, initial tolerance 10 ppm, ESR <=50 ohm; verify assembled frequency',
         datasheet='https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-e9x-crystal-resonator-mhz-data-sheet-elx1389-en.pdf')
    passive('C4','12pF','XTAL_LOAD_P','GND',201,244,note='C0G; assumes about 2 pF stray; trim frequency on hardware')
    passive('C5','12pF','XTAL_N','GND',253,244,note='C0G; crystal load tuning')
    note('core','All GPIO signals are 3.3 V only.\nGPIO4/5/8/9/15 are strapping pins.\nDo not force strap levels during reset.\nGPIO21 drives the RGB LED.',293,203)
    # The sheet is referenced here; named global nets connect both sheets.
    SHEETS['core'].append(form(f'(sheet (at 298.45 220.98) (size 78.74 25.4) '
                              f'(stroke (width 0.1524) (type default)) (fill (color 0 0 0 0)) '
                              f'(uuid "{SHEET_INSTANCE}") '
                              f'(property "Sheetname" "Power, USB and interfaces" (at 298.45 219.71 0) (effects (font (size 1.27 1.27)) (justify left bottom))) '
                              f'(property "Sheetfile" "power-io.kicad_sch" (at 298.45 247.65 0) (effects (font (size 1.27 1.27)) (justify left top))) '
                              f'(instances (project "esp32-c6-pico" (path "/{ROOT_ID}" (page "2")))))'))

    note('io','ESP32-C6 PICO | POWER, USB & INTERFACES | REV A',20,20,2.54)
    note('io','06  USB-C native USB Serial/JTAG',20,39,1.8)
    usb={p:'VBUS_USB' for p in ['A4','A9','B4','B9']}
    usb.update({p:'GND' for p in ['A1','A12','B1','B12','SH']})
    usb.update(A5='CC1',B5='CC2',A6='USB_D+',B6='USB_D+',A7='USB_D-',B7='USB_D-',A8=None,B8=None)
    part('J1','Connector:USB_C_Receptacle_USB2.0_16P','USB4105-GF-A',
         'Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal',usb,40,83,sheet='io')
    passive('R10','5.1k','CC1','GND',80,56,sheet='io',note='1%; one Rd per CC pin')
    passive('R11','5.1k','CC2','GND',104,56,sheet='io',note='1%; USB-C sink, no PD')
    part('D4','Power_Protection:USBLC6-2SC6','USBLC6-2SC6','Package_TO_SOT_SMD:SOT-23-6',
         {1:'USB_D+',2:'GND',3:'USB_D-',4:'USB_D-',5:'VBUS_USB',6:'USB_D+'},103,93,sheet='io')
    passive('R12','22R','USB_D-','USB_MCU_D-',150,81,angle=90,sheet='io')
    passive('R13','22R','USB_D+','USB_MCU_D+',150,102,angle=90,sheet='io')
    passive('C27','DNP','USB_MCU_D-','GND',187,81,sheet='io',dnp=True,note='EMI tuning option; leave open')
    passive('C28','DNP','USB_MCU_D+','GND',210,102,sheet='io',dnp=True,note='EMI tuning option; leave open')
    note('io','D- = GPIO12; D+ = GPIO13.\nUse BOOT + RESET for recovery.\n90 ohm differential routing; 22R at U1.',20,124)

    note('io','07  USB 5 V to 3.3 V supply',237,39,1.8)
    part('F1','Device:Polyfuse_Small','0.75A hold','Fuse:Fuse_1206_3216Metric',
         {1:'VBUS_USB',2:'VBUS_FUSED'},246,57,90,'io',mpn='1206L075/6',detail='Check thermal derating; input source >=500 mA')
    part('D3','Diode:ESD9B5.0ST5G','ESD9B5.0ST5G','Diode_SMD:D_SOD-923',
         {1:'GND',2:'VBUS_USB'},244,82,90,'io',detail='Move original 15 pF TVS to USB power rail')
    part('D5','Device:D_Schottky','SS14FL','Diode_SMD:D_SOD-123F',
         {1:'+5V',2:'VBUS_FUSED'},279,57,180,'io',detail='Blocks USB backfeed; +5V is about VBUS minus diode drop',
         datasheet='https://www.onsemi.com/download/data-sheet/pdf/ss14fl-d.pdf')
    part('U2','Regulator_Linear:AP2112K-3.3','AP2112K-3.3','Package_TO_SOT_SMD:SOT-23-5',
         {1:'+5V',2:'GND',3:'+5V',4:None,5:'+3V3'},331,77,sheet='io',mpn='AP2112K-3.3TRG1',
         detail='600 mA peak rating; continuous load limited by SOT25 dissipation')
    passive('C22','10uF','+5V','GND',282,92,sheet='io',fp=C0603,note='10 V X7R; regulator input')
    passive('C23','22uF','+3V3','GND',374,82,sheet='io',fp=C0603,note='10 V X5R/X7R; verify DC-bias effective capacitance')
    passive('C24','100nF','VBUS_USB','GND',375,113,sheet='io')
    note('io','USB supplies the board. 3V3 / 5V headers are outputs.\nDo not power 3V3 externally while USB is attached.\nRegulator current rating is NOT an external load budget.\nValidate 3V3 droop and LDO temperature during Wi-Fi TX.',235,139)

    note('io','08  Reset, boot and UART recovery',20,152,1.8)
    passive('R7','10k','+3V3','CHIP_EN',28,174,sheet='io')
    passive('C21','1uF','CHIP_EN','GND',54,174,sheet='io')
    part('SW1','Switch:SW_Push','RESET','Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2',
         {1:'CHIP_EN',2:'GND'},86,180,sheet='io',mpn='KMR221GLFS')
    passive('R8','10k','+3V3','GPIO9_BOOT',119,174,sheet='io')
    part('SW2','Switch:SW_Push','BOOT','Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2',
         {1:'GPIO9_BOOT',2:'GND'},151,180,sheet='io',mpn='KMR221GLFS')
    passive('R9','10k','+3V3','GPIO8',188,174,sheet='io')
    passive('R14','499R','U0TXD_MCU','U0TXD',71,207,angle=90,sheet='io',note='UART0 harmonic damping at U1')
    note('io','Download strap: GPIO8=1, GPIO9=0.\nHold BOOT, tap RESET, release BOOT.\nUART adapter: 3.3 V logic only; TX/RX cross-connect.',20,237)

    note('io','09  2 mm pitch GPIO headers',242,155,1.8)
    left=['GND','+3V3','GPIO0','GPIO1','GPIO2','GPIO3','GPIO4','GPIO5','GPIO6','GPIO7','GPIO8','GPIO9_BOOT']
    right=['+5V','GND','GPIO10','GPIO11','GPIO15','U0TXD','U0RXD','GPIO18','GPIO19','GPIO20','GPIO22','GPIO23']
    for ref,nets,x in [('J2',left,274),('J3',right,371)]:
        part(ref,'Connector_Generic:Conn_01x12',ref+' GPIO / 2.00mm',
             'Pico:PinHeader_1x12_P2.00mm_Compact',
             {str(i+1): n for i,n in enumerate(nets)},x,196,sheet='io',mpn='1x12 P2.00 vertical header')

    note('io','10  RGB indicator - 5 V logic buffer',20,260,1.8)
    # Use a third sheet-sized row on A3; enough horizontal spacing for buffer symbol.
    part('U4','Pico_Custom:SN74LV1T125','SN74LV1T125','Package_TO_SOT_SMD:SOT-23-5',
         {1:'GND',2:'GPIO21_LED',3:'GND',4:'LED_DATA_5V',5:'VBUS_USB'},89,278,sheet='io',mpn='SN74LV1T125DBVR')
    passive('R16','100k','GPIO21_LED','GND',37,279,sheet='io',note='Keep LED data low at reset')
    passive('R15','330R','LED_DATA_5V','LED_DIN',145,273,angle=90,sheet='io')
    part('D2','LED:WS2812B-2020','WS2812B-2020','Pico:WS2812B_2020_Compact',
         {1:None,2:'GND',3:'LED_DIN',4:'VBUS_USB'},198,278,sheet='io')
    passive('C25','1uF','VBUS_USB','GND',231,274,sheet='io',note='At RGB VDD')
    passive('C26','100nF','VBUS_USB','GND',264,274,sheet='io',note='At LV1T125 VCC')

    # Explicit power-source assertions: passive filters do not propagate ERC drive.
    for i,net in enumerate(['GND','VBUS_USB','VBUS_FUSED','+5V','V3A']):
        part('#FLG%02d'%i,'power:PWR_FLAG','PWR_FLAG','',{1:net},303+i*16,268,sheet='io')

    # Increase the IO sheet to A2 to keep the last row away from the title block.
    for sheet, filename in [('core','esp32-c6-pico.kicad_sch'),('io','power-io.kicad_sch')]:
        cache = [A('lib_symbols')]
        for original_id, sym in USED.items():
            s = copy.deepcopy(sym)
            s[1] = 'Pico_Design:'+original_id.replace(':','__')
            for unit in children(s, 'symbol'):
                unit[1] = original_id.replace(':','__') + '_' + '_'.join(unit[1].split('_')[-2:])
            cache.append(s)
        paper = '(paper "A3")' if sheet == 'core' else '(paper "User" 420 330)'
        doc = form(f'(kicad_sch (version 20260306) (generator "eeschema") (generator_version "10.0") '
                   f'(uuid "{SHEET_ID[sheet]}") {paper} '
                   '(title_block (title "ESP32-C6 PICO - prototype Rev A") (date "2026-09-06") '
                   '(rev "A") (company "KZL") (comment 1 "RF and thermal validation required before production")))')
        doc.append(cache)
        doc.extend(SHEETS[sheet])
        doc.append(form('(embedded_fonts no)'))
        if sheet == 'core':
            doc.append(form('(sheet_instances (path "/" (page "1")))'))
        data = dumps(doc)+'\n'
        # Preserve the original root file's CRLF format; newly authored text uses LF.
        with (ROOT/filename).open('w',encoding='utf-8',newline='\r\n' if sheet=='core' else '\n') as f:
            f.write(data)

    local = form('(kicad_symbol_lib (version 20251024) (generator "kicad_symbol_editor"))')
    for old_id,sym in USED.items():
        s=copy.deepcopy(sym)
        s[1]=old_id.replace(':','__')
        for unit in children(s, 'symbol'):
            unit[1] = s[1] + '_' + '_'.join(unit[1].split('_')[-2:])
        local.append(s)
    (ROOT/'libs/Pico_Design.kicad_sym').write_text(dumps(local)+'\n',encoding='utf-8',newline='\n')
    (ROOT/'design-spec.json').write_text(json.dumps(PARTS,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    out=ROOT/'output'
    out.mkdir(exist_ok=True)
    with (out/'bom.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f,lineterminator='\n')
        writer.writerow(['Reference','Value','MPN','Footprint','Populate','Note'])
        for p in PARTS:
            writer.writerow([p['ref'],p['value'],p['mpn'],p['footprint'],'NO' if p['dnp'] else 'YES',p['note']])
    print(f'Generated {len(PARTS)} board components across two schematic sheets.')


if __name__ == '__main__':
    build()
