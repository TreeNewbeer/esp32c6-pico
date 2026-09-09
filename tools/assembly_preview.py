"""Make a plotting-only copy with one legible reference per component."""
import pcbnew as pcb
from build_pcb import BOARD_FILE,ROOT,MM,xy

b=pcb.LoadBoard(str(BOARD_FILE))
for fp in b.GetFootprints():
    ref=fp.GetReference()
    # Keep connector references clear of the plated hole at pin 1.
    label_position=fp.GetPosition()+xy(0,-2) if ref in ['J2','J3'] else fp.GetPosition()
    if ref=='D5':label_position=fp.GetPosition()+xy(0,.9)
    if ref=='L2':label_position=fp.GetPosition()+xy(0,-.8)
    # Suppress labels that collide with the reference in the plotting-only copy.
    for pd in fp.Pads():
        if ref.startswith(('R','L','C')) or (ref,pd.GetNumber()) == ('U1','41'):
            pd.SetNumber('')
    size=.30 if ref in ['R1','R2','R3','R4','R5','R6','R17','C2','C3','C16','C17','C18','L1','L3'] else .38
    if ref.startswith(('U','J','SW')) or ref=='AE1':size=.7
    fp.Reference().SetVisible(False)
    found=False
    for g in fp.GraphicalItems():
        if (ref.startswith(('R','L','C')) or ref in ['D1','D3']) and not isinstance(g,pcb.PCB_TEXT) and g.GetLayer() in [pcb.F_Fab,pcb.B_Fab]:
            g.SetLayer(pcb.Dwgs_User)
        if isinstance(g,pcb.PCB_TEXT) and 'REFERENCE' in g.GetText():
            g.SetText(ref);g.SetPosition(label_position);g.SetTextSize(xy(size,size));g.SetTextThickness(MM(.06))
            g.SetTextAngle(pcb.EDA_ANGLE(0,pcb.DEGREES_T));g.SetLayer(pcb.B_Fab if fp.GetLayer()==pcb.B_Cu else pcb.F_Fab)
            g.SetMirrored(fp.GetLayer()==pcb.B_Cu);found=True
    if not found:
        text=fp.Reference();text.SetVisible(True);text.SetPosition(label_position);text.SetTextSize(xy(size,size));text.SetTextThickness(MM(.06))
        text.SetTextAngle(pcb.EDA_ANGLE(0,pcb.DEGREES_T))
pcb.SaveBoard(str(ROOT/'tmp/inspection/assembly-view.kicad_pcb'),b)
