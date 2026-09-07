"""Give C11 a direct ground return, then detour the two underlying digital traces."""
import pcbnew as pcb
from build_pcb import BOARD_FILE,MM,point,via

board=pcb.LoadBoard(str(BOARD_FILE))
f=next(f for f in board.GetFootprints() if f.GetReference()=='C11')
pd=next(p for p in f.Pads() if p.GetNumber()=='2')
pos=pd.GetPosition()
removed=[]
for t in list(board.GetTracks()):
    if isinstance(t,pcb.PCB_VIA) or t.GetNetname()=='GND':continue
    if t.GetEffectiveShape().Collide(pos,MM(.15+.11)):
        removed.append(t.GetNetname());board.RemoveNative(t)
via(board,pd.GetNet(),point(pos),.3,.15)
board.BuildConnectivity();pcb.ZONE_FILLER(board).Fill(board.Zones());pcb.SaveBoard(str(BOARD_FILE),board)
print('Re-route:',removed)
