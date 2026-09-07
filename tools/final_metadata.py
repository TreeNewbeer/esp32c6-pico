"""Synchronize non-electrical metadata and the antenna's dimension-only 3D model."""
import copy,json
import pcbnew as pcb
from build_pcb import ROOT,BOARD_FILE,MM,xy
from kicad_sexpr import child,children,dumps,read,prop

doc=read(BOARD_FILE)
antlib=read(ROOT/'libs/Walsin_Antenna.pretty/RFANT5220110A0T.kicad_mod')
for fp in children(doc,'footprint'):
    if prop(fp,'Reference')!='AE1':continue
    fp[:]=[n for n in fp if not(isinstance(n,list) and n and (n[0]=='model' or (n[0]=='fp_rect' and child(n,'layer')[1]=='F.CrtYd')))]
    fp.append(copy.deepcopy(child(antlib,'model')))
    fp.extend(copy.deepcopy(n)for n in children(antlib,'fp_rect')if child(n,'layer')[1]=='F.CrtYd')
    for text in children(fp,'fp_text'):
        if text[2].startswith('GND PLANE >='):text[2]='REFERENCE TEST GND 30 x 18 mm on feed side (pad 1)'
BOARD_FILE.write_text(dumps(doc)+'\n',encoding='utf-8',newline='\n')
board=pcb.LoadBoard(str(BOARD_FILE))
board.GetDesignSettings().SetAuxOrigin(xy(100,139))
board.GetDesignSettings().SetGridOrigin(xy(100,139))
title=board.GetTitleBlock();title.SetTitle('ESP32-C6 PICO - Rev A prototype');title.SetRevision('A');title.SetDate('2026-09-06')
board.SetTitleBlock(title)
for t in board.GetTracks():
    if isinstance(t,pcb.PCB_VIA):
        t.SetFrontTentingMode(pcb.TENTING_MODE_TENTED);t.SetBackTentingMode(pcb.TENTING_MODE_TENTED)
for fp in board.GetFootprints():
    if fp.GetReference()=='U4':fp.SetValue('SN74LV1T125')
board.BuildConnectivity();pcb.ZONE_FILLER(board).Fill(board.Zones());pcb.SaveBoard(str(BOARD_FILE),board)
