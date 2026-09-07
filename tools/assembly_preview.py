"""Make a plotting-only copy with one legible reference per component."""
import pcbnew as pcb
from build_pcb import BOARD_FILE,ROOT,MM,xy

b=pcb.LoadBoard(str(BOARD_FILE))
for fp in b.GetFootprints():
    ref=fp.GetReference()
    size=.30 if ref in ['R1','R2','R3','R4','R5','R6','R17','C2','C3','C16','C17','C18','L1','L3'] else .38
    if ref.startswith(('U','J','SW')) or ref=='AE1':size=.7
    fp.Reference().SetVisible(False)
    found=False
    for g in fp.GraphicalItems():
        if (ref.startswith(('R','L','C')) or ref in ['D1','D3']) and not isinstance(g,pcb.PCB_TEXT) and g.GetLayer() in [pcb.F_Fab,pcb.B_Fab]:
            g.SetLayer(pcb.Dwgs_User)
        if isinstance(g,pcb.PCB_TEXT) and 'REFERENCE' in g.GetText():
            g.SetText(ref);g.SetPosition(fp.GetPosition());g.SetTextSize(xy(size,size));g.SetTextThickness(MM(.06))
            g.SetTextAngle(pcb.EDA_ANGLE(0,pcb.DEGREES_T));g.SetLayer(pcb.B_Fab if fp.GetLayer()==pcb.B_Cu else pcb.F_Fab)
            g.SetMirrored(fp.GetLayer()==pcb.B_Cu);found=True
    if not found:
        text=fp.Reference();text.SetVisible(True);text.SetPosition(fp.GetPosition());text.SetTextSize(xy(size,size));text.SetTextThickness(MM(.06))
        text.SetTextAngle(pcb.EDA_ANGLE(0,pcb.DEGREES_T))
pcb.SaveBoard(str(ROOT/'tmp/inspection/assembly-view.kicad_pcb'),b)
