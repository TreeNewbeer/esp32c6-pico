"""Filled/capped via-in-pad escapes for the remaining QFN pins.

These eight vias REQUIRE VIPPO (filled and copper-capped) fabrication. Do not
substitute ordinary open or tented-through vias under the solderable QFN lands.
"""
import pcbnew as pcb
from build_pcb import BOARD_FILE,OUTPUT,MM,point,via

board=pcb.LoadBoard(str(BOARD_FILE))
chip=next(f for f in board.GetFootprints() if f.GetReference()=='U1')
for num in [4,6,13,17,27,35,33,32]:
    pd=next(p for p in chip.Pads() if p.GetNumber()==str(num))
    x,y=point(pd.GetPosition())
    if num<=10:y-=.26
    elif num<=20:x-=.26
    elif num<=30:y+=.26
    else:x+=.26
    via(board,pd.GetNet(),(x,y),.3,.15)
board.BuildConnectivity()
pcb.ZONE_FILLER(board).Fill(board.Zones())
pcb.SaveBoard(str(BOARD_FILE),board)
# Strip only ground pours from the router copy; maintain their board-side zones.
for zone in list(board.Zones()):
    if not zone.GetIsRuleArea() and zone.GetLayer()!=pcb.In1_Cu:
        board.RemoveNative(zone)
pcb.ExportSpecctraDSN(board,str(OUTPUT/'routing-final.dsn'))
print('Added 8 filled/capped QFN pad escapes; exported routing-final.dsn')
