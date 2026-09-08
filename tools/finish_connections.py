"""Conservative three-layer grid router for the final short escape connections.

This only adds copper. KiCad DRC remains authoritative; existing tracks and all
foreign pads/vias are obstacles, and L2 GND is never used for signal routing.
"""
from __future__ import annotations
import heapq
import math
import sys
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import pcbnew as pcb
from build_pcb import ROOT,OUTPUT,BOARD_FILE,MM,xy,point,trace,via

STEP=.025
X0,Y0=99.5,108.5
NX,NY=761,1241
LAYERS=[pcb.F_Cu,pcb.In2_Cu,pcb.B_Cu]
board=pcb.LoadBoard(str(BOARD_FILE))
fps={f.GetReference():f for f in board.GetFootprints()}


def cell(pt):
    return (round((pt[0]-X0)/STEP),round((pt[1]-Y0)/STEP))


def mm(pt):
    return (round(X0+pt[0]*STEP,6),round(Y0+pt[1]*STEP,6))


def rect(draw,bb,pad,color):
    a=point(bb.GetOrigin());b=point(bb.GetEnd())
    draw.rectangle([cell((a[0]-pad,a[1]-pad)),cell((b[0]+pad,b[1]+pad))],fill=color)


def draw_pad(draw,pd,extra,color):
    if pd.GetShape()==pcb.PAD_SHAPE_CIRCLE:
        ctr=point(pd.GetPosition());r=pcb.ToMM(pd.GetSize().x)/2+extra
        draw.ellipse([cell((ctr[0]-r,ctr[1]-r)),cell((ctr[0]+r,ctr[1]+r))],fill=color)
    else:
        rect(draw,pd.GetBoundingBox(),extra,color)


def draw_track(draw,t,extra,color):
    if isinstance(t,pcb.PCB_VIA):
        ctr=point(t.GetPosition());r=pcb.ToMM(t.GetWidth(pcb.F_Cu))/2+extra
        draw.ellipse([cell((ctr[0]-r,ctr[1]-r)),cell((ctr[0]+r,ctr[1]+r))],fill=color)
    else:
        a,b=cell(point(t.GetStart())),cell(point(t.GetEnd()))
        w=max(1,math.ceil((pcb.ToMM(t.GetWidth())+2*extra)/STEP))
        draw.line([a,b],fill=color,width=w)
        r=w/2
        for c in [a,b]:
            draw.ellipse([(c[0]-r,c[1]-r),(c[0]+r,c[1]+r)],fill=color)


def route_one(ref,num,width=.1,fanout=False):
    source=next(p for p in fps[ref].Pads() if p.GetNumber()==str(num))
    name=source.GetNetname();net=source.GetNet();start_xy=point(source.GetPosition())
    start=(*cell(start_xy),LAYERS.index(source.GetParent().GetLayer()))
    obstacles=[Image.new('1',(NX,NY),0) for _ in LAYERS]
    own=[Image.new('1',(NX,NY),0) for _ in LAYERS]
    via_block=Image.new('1',(NX,NY),0)
    own_via=Image.new('1',(NX,NY),0)
    od=[ImageDraw.Draw(im) for im in obstacles];gd=[ImageDraw.Draw(im) for im in own]
    vd=ImageDraw.Draw(via_block);vown=ImageDraw.Draw(own_via)
    targets=[]
    for f in board.GetFootprints():
        for pd in f.Pads():
            npth=pd.GetAttribute()==pcb.PAD_ATTRIB_NPTH
            if not pd.IsOnCopperLayer() and not npth:
                continue
            same=pd.GetNetname()==name
            # Do not drill into an SMT solderable land, even when it is this net.
            via_margin=.10 if same else .15+(.19 if npth else .115)
            if pd.GetAttribute()==pcb.PAD_ATTRIB_SMD:
                mask=pcb.ToMM(pd.GetSolderMaskExpansion(f.GetLayer()))
                via_margin=max(via_margin,.075+.10+mask+.02)
            draw_pad(vd,pd,via_margin,1)
            for li,layer in enumerate(LAYERS):
                if not pd.IsOnLayer(layer):
                    continue
                draw_pad(gd[li] if same else od[li],pd,-.04 if same else width/2+(.19 if npth else .115),1)
            if same:
                if pd.GetAttribute()==pcb.PAD_ATTRIB_PTH:
                    draw_pad(vown,pd,-.05,1)
                if f.GetReference()!=ref or pd.GetNumber()!=str(num):
                    targets.append(cell(point(pd.GetPosition())))
    for t in board.GetTracks():
        same=t.GetNetname()==name
        draw_track(vd,t,.15 if same else .15+.115,1)
        for li,layer in enumerate(LAYERS):
            if t.IsOnLayer(layer):
                draw_track(gd[li] if same else od[li],t,-.03 if same else width/2+.115,1)
        if same:
            targets.extend([cell(point(t.GetStart())),cell(point(t.GetEnd()))])
            if isinstance(t,pcb.PCB_VIA):
                draw_track(vown,t,-.04,1)
    # Restrict the board boundary and preserve all rule-area routing constraints.
    for li in range(3):
        od[li].rectangle([(0,0),(NX-1,round((109.05-Y0)/STEP))],fill=1)
        od[li].rectangle([(0,0),(round((100.4-X0)/STEP),NY-1)],fill=1)
        od[li].rectangle([(round((117.6-X0)/STEP),0),(NX-1,NY-1)],fill=1)
        od[li].rectangle([(0,round((138.6-Y0)/STEP)),(NX-1,NY-1)],fill=1)
    vd.rectangle([(0,0),(NX-1,round((109.35-Y0)/STEP))],fill=1)
    for z in board.Zones():
        if not z.GetIsRuleArea():
            continue
        if z.GetDoNotAllowVias():
            rect(vd,z.GetBoundingBox(),.25,1)
        if z.GetDoNotAllowTracks():
            for li,l in enumerate(LAYERS):
                if z.IsOnLayer(l):
                    rect(od[li],z.GetBoundingBox(),width/2+.02,1)
    blocked=np.stack([np.array(i,dtype=bool) for i in obstacles])
    copper=np.stack([np.array(i,dtype=bool) for i in own])
    via_blocked=np.array(via_block,dtype=bool)
    connection_vias=np.array(own_via,dtype=bool)
    # Remove the source's existing connected copper component from the goal set.
    queue=deque([start]);seen={start}
    while queue:
        x,y,l=queue.popleft()
        for nx,ny,nl in [(x+1,y,l),(x-1,y,l),(x,y+1,l),(x,y-1,l)]+([(x,y,k) for k in range(3)] if connection_vias[y,x] else []):
            if 0<=nx<NX and 0<=ny<NY and copper[nl,ny,nx] and (nx,ny,nl) not in seen:
                seen.add((nx,ny,nl));queue.append((nx,ny,nl))
    for x,y,l in seen:
        copper[l,y,x]=False
    targets=[(x,y) for x,y in targets if any(copper[l,y,x] for l in range(3))]
    if fanout:
        copper=np.stack([~via_blocked & ~blocked[k] for k in range(3)])
    if not targets and not fanout:
        print(name,'already connected / no remaining target',flush=True)
        return False
    targets=list(dict.fromkeys(targets))
    # Weighted A* prioritizes short escapes. All candidate geometry still goes
    # through the conservative obstacle map and the final KiCad DRC.
    def heuristic(x,y):
        return 0 if fanout else min(math.hypot(x-a,y-b) for a,b in targets)
    heap=[(heuristic(start[0],start[1]),0,start)]
    cost={start:0};parent={};end=None;iterations=0
    dirs=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)]
    while heap and iterations<650000:
        _,g,cur=heapq.heappop(heap)
        if g!=cost.get(cur):
            continue
        x,y,l=cur;iterations+=1
        if copper[l,y,x]:
            end=cur;break
        neighbors=[]
        for dx,dy,move in dirs:
            nx,ny=x+dx,y+dy
            if not (0<nx<NX-1 and 0<ny<NY-1) or blocked[l,ny,nx]:
                continue
            if dx and dy and (blocked[l,y,nx] or blocked[l,ny,x]):
                continue
            neighbors.append(((nx,ny,l),move))
        if not via_blocked[y,x] or connection_vias[y,x]:
            neighbors.extend(((x,y,nl),32) for nl in range(3) if nl!=l and not blocked[nl,y,x])
        for nxt,move in neighbors:
            ng=g+move
            if ng<cost.get(nxt,float('inf')):
                cost[nxt]=ng;parent[nxt]=cur
                heapq.heappush(heap,(ng+1.3*heuristic(nxt[0],nxt[1]),ng,nxt))
    if end is None:
        if name in ['GPIO0','CHIP_EN','GPIO11','GPIO23']:
            rgb=np.full((NY,NX,3),245,dtype=np.uint8)
            rgb[~via_blocked]=(100,195,115)
            rgb[blocked[start[2]]]=(45,45,45)
            for (cx,cy,cl) in cost:
                if cl==start[2]:rgb[cy,cx]=(75,160,235)
            rgb[start[1]-2:start[1]+3,start[0]-2:start[0]+3]=(240,40,60)
            im=Image.fromarray(rgb)
            a=cell((start_xy[0]-2,start_xy[1]-2));b=cell((start_xy[0]+2,start_xy[1]+1))
            im.crop((*a,*b)).resize((800,600)).save(str(OUTPUT/('debug-'+name+'.png')))
        print(name,'FAILED',iterations,flush=True)
        return False
    chain=[end]
    while chain[-1]!=start:
        chain.append(parent[chain[-1]])
    chain.reverse()
    # Remove collinear grid vertices while preserving every bend and layer change.
    simplified=[chain[0]]
    for i in range(1,len(chain)-1):
        a,b,c=chain[i-1],chain[i],chain[i+1]
        if a[2]!=b[2] or b[2]!=c[2] or (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):
            simplified.append(b)
    simplified.append(chain[-1])
    if math.dist(start_xy,mm(start))>1e-6:
        trace(board,net,[start_xy,mm(start)],width,LAYERS[start[2]],False)
    for a,b in zip(simplified,simplified[1:]):
        if a[2]!=b[2]:
            if not connection_vias[a[1],a[0]]:
                via(board,net,mm(a),.3,.15)
        else:
            trace(board,net,[mm(a),mm(b)],width,LAYERS[a[2]],False)
    if fanout:
        via(board,net,mm(end),.3,.15)
    print(name,'connected',len(simplified),'vertices;',iterations,'searched',flush=True)
    return True


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='local_ground':
        route_one('C11',2,.15,True)
        board.BuildConnectivity();pcb.ZONE_FILLER(board).Fill(board.Zones());pcb.SaveBoard(str(BOARD_FILE),board)
        sys.exit(0)
    if len(sys.argv)>1 and sys.argv[1]=='fanout':
        for num in [4,6,7,8,9,10,11,12,13,14,15,16,17,27,29,30,36,35,34,33,32,31]:
            route_one('U1',num,.1,True)
        route_one('J1','A4',.25,True)
        route_one('J1','A9',.25,True)
        board.BuildConnectivity()
        pcb.ZONE_FILLER(board).Fill(board.Zones())
        pcb.SaveBoard(str(BOARD_FILE),board)
        sys.exit(0)
    tasks=[('C14','1',.2),('C15','1',.2),('J1','A4',.3),
           ('U1','4',.1),('U1','6',.1),('U1','7',.1),('U1','12',.1),('U1','15',.1),('U1','17',.1),
           ('U1','23',.1),('U1','27',.1),('U1','29',.1),('U1','35',.1),('U1','36',.1)]
    if len(sys.argv)>1:
        tasks=[(sys.argv[1],sys.argv[2],float(sys.argv[3]) if len(sys.argv)>3 else .1)]
    for ref,num,width in tasks:
        route_one(ref,num,width)
        board.BuildConnectivity()
        pcb.SaveBoard(str(BOARD_FILE),board)
    pcb.ZONE_FILLER(board).Fill(board.Zones())
    pcb.SaveBoard(str(BOARD_FILE),board)
