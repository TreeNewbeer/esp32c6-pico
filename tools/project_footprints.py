"""Derive the compact header footprint without altering the KiCad system library."""
from pathlib import Path
from kicad_sexpr import child,children,dumps,read

root=Path(__file__).resolve().parents[1]
src=Path('C:/Program Files/KiCad/10.0/share/kicad/footprints/Connector_PinHeader_2.00mm.pretty/PinHeader_1x12_P2.00mm_Vertical.kicad_mod')
fp=read(src)
fp[1]='PinHeader_1x12_P2.00mm_Compact'
for item in fp:
    if isinstance(item,list) and item[0] in ['fp_line','fp_rect','fp_poly','fp_circle']:
        layer=child(item,'layer')
        if layer and layer[1]=='F.SilkS':
            layer[1]='F.Fab'
dest=root/'libs/Pico.pretty'
dest.mkdir(exist_ok=True)
(dest/(fp[1]+'.kicad_mod')).write_text(dumps(fp)+'\n',encoding='utf-8',newline='\n')
qfn=read(Path('C:/Program Files/KiCad/10.0/share/kicad/footprints/Package_DFN_QFN.pretty/QFN-40-1EP_5x5mm_P0.4mm_EP3.6x3.6mm.kicad_mod'))
qfn[1]='QFN40_ESP32_C6_Compact'
for item in qfn:
    if isinstance(item,list) and item[0].startswith('fp_'):
        layer=child(item,'layer')
        if layer and layer[1]=='F.SilkS':layer[1]='F.Fab'
(dest/(qfn[1]+'.kicad_mod')).write_text(dumps(qfn)+'\n',encoding='utf-8',newline='\n')
led=read(Path('C:/Program Files/KiCad/10.0/share/kicad/footprints/LED_SMD.pretty/LED_WS2812B-2020_PLCC4_2.0x2.0mm.kicad_mod'))
led[1]='WS2812B_2020_Compact'
for item in led:
    if isinstance(item,list) and item[0].startswith('fp_'):
        layer=child(item,'layer')
        if layer and layer[1]=='F.SilkS':layer[1]='F.Fab'
(dest/(led[1]+'.kicad_mod')).write_text(dumps(led)+'\n',encoding='utf-8',newline='\n')
