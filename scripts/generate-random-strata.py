#!/usr/bin/env python3
"""Random HSV strata v2. Python 3.10+, standard library only.

  python generate-random-strata.py palette.gpl
  python generate-random-strata.py palette.png --seed 42 --vivid-margin 0.2

64 near-grays (max RGB - min RGB <= 4), including black and white.
15 hue sectors: eight vivid colors + fourteen samples per S/V quadrant each.
Vivid spacing adapts per sector using exact eight-clique feasibility searches;
all other pairs retain 2.5 by default. No silent retry-based relaxation.
Output: GPL, TXT/HEX, JSON or RGB PNG, plus an all-pairs audit sidecar.
"""
import argparse,colorsys,json,math,random,secrets,struct,sys,zlib
from pathlib import Path


def rgb_to_lab(rgb):
    c=[v/255 for v in rgb];c=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]
    x,y,z=[sum(a*b for a,b in zip(row,c))/white for row,white in zip(((.4124564,.3575761,.1804375),(.2126729,.7151522,.0721750),(.0193339,.1191920,.9503041)),(.95047,1,1.08883))]
    f=lambda t:t**(1/3) if t>216/24389 else (24389/27*t+16)/116
    x,y,z=map(f,(x,y,z));return (116*y-16,500*(x-y),200*(y-z))


def delta_e(lab1,lab2):
    """CIEDE2000, Sharma/Wu/Dalal, kL=kC=kH=1."""
    L1,a1,b1=lab1;L2,a2,b2=lab2;C1=math.hypot(a1,b1);C2=math.hypot(a2,b2)
    c7=((C1+C2)/2)**7;G=.5*(1-math.sqrt(c7/(c7+25**7)))
    ap1,ap2=(1+G)*a1,(1+G)*a2;c1,c2=math.hypot(ap1,b1),math.hypot(ap2,b2)
    h1=math.degrees(math.atan2(b1,ap1))%360 if c1 else 0;h2=math.degrees(math.atan2(b2,ap2))%360 if c2 else 0
    dh=h2-h1
    if c1*c2==0:dh=0
    elif dh>180:dh-=360
    elif dh< -180:dh+=360
    dH=2*math.sqrt(c1*c2)*math.sin(math.radians(dh/2));C=(c1+c2)/2
    if c1*c2==0:H=h1+h2
    elif abs(h1-h2)<=180:H=(h1+h2)/2
    elif h1+h2<360:H=(h1+h2+360)/2
    else:H=(h1+h2-360)/2
    cos=lambda x:math.cos(math.radians(x))
    T=1-.17*cos(H-30)+.24*cos(2*H)+.32*cos(3*H+6)-.20*cos(4*H-63)
    t=(L1+L2)/2-50;dl=(L2-L1)/(1+.015*t*t/math.sqrt(20+t*t));dc=(c2-c1)/(1+.045*C);dht=dH/(1+.015*C*T)
    rt=-2*math.sqrt(C**7/(C**7+25**7))*math.sin(math.radians(60*math.exp(-((H-275)/25)**2)))
    return math.sqrt(max(0,dl*dl+dc*dc+dht*dht+rt*dc*dht))


def vivid_pools():
    pools=[set() for _ in range(15)]
    # Every possible full-saturation, full-value byte RGB lies on these six edges.
    for n in range(256):
        for rgb in [(255,n,0),(n,255,0),(0,255,n),(0,n,255),(n,0,255),(255,0,n)]:
            h=colorsys.rgb_to_hsv(*(v/255 for v in rgb))[0];pools[min(14,int(h*15))].add(rgb)
    return [sorted(p) for p in pools]


def packing_upper_bound(colors,threshold):
    """Partition into pairwise-conflicting cliques: at most one per clique.
    This is a rigorous upper bound, not necessarily the exact packing number.
    """
    if threshold<=0:return len(colors)
    cliques=[]
    for rgb in colors:
        lab=rgb_to_lab(rgb)
        for clique in cliques:
            if all(delta_e(lab,other)<threshold for other in clique):clique.append(lab);break
        else:cliques.append([lab])
    return len(cliques)


def is_gray(rgb):
    return max(rgb)-min(rgb)<=4


def gray_pool():
    return [(r,g,b) for r in range(256)
            for g in range(max(0,r-4),min(255,r+4)+1)
            for b in range(max(0,max(r,g)-4),min(255,min(r,g)+4)+1)]


def distance_matrix(pool):
    labs=list(map(rgb_to_lab,pool));matrix=[[0.0]*len(pool) for _ in pool]
    for i in range(len(pool)):
        for j in range(i):matrix[i][j]=matrix[j][i]=delta_e(labs[i],labs[j])
    return matrix


def clique_eight(matrix,minimum,rng=None,allowed=None):
    """Exact size-eight clique search with a greedy-coloring upper bound.
    Vertices are actual byte RGB colors; edges satisfy the distance threshold.
    Returns a witness or None after exhaustive exclusion. No metric assumption.
    """
    n=len(matrix);order=list(range(n)) if allowed is None else list(allowed)
    if rng is not None:rng.shuffle(order)
    adj=[]
    for i in order:
        mask=0
        for j,k in enumerate(order):
            if i!=k and matrix[i][k]>=minimum:mask|=1<<j
        adj.append(mask)
    def color_sort(mask):
        order_out=[];bounds=[];color=0;uncolored=mask
        while uncolored:
            color+=1;available=uncolored
            while available:
                bit=available & -available;v=bit.bit_length()-1
                order_out.append(v);bounds.append(color);uncolored^=bit
                available &= ~bit;available &= ~adj[v]
        return order_out,bounds
    def expand(mask,chosen):
        if len(chosen)==8:return chosen
        if mask.bit_count()<8-len(chosen):return None
        vertices,bounds=color_sort(mask)
        for pos in range(len(vertices)-1,-1,-1):
            if len(chosen)+bounds[pos]<8:return None
            v=vertices[pos];result=expand(mask & adj[v],chosen+[v])
            if result is not None:return result
            mask &= ~(1<<v)
        return None
    chosen=expand((1<<len(order))-1,[])
    return None if chosen is None else [order[i] for i in chosen]


def sector_plan(pool,cap,margin,matrix=None,ceilings=None):
    if matrix is None:matrix=distance_matrix(pool)
    if ceilings is None:ceilings=[cap]*len(pool)
    def feasible(d):return clique_eight(matrix,d,allowed=[i for i,c in enumerate(ceilings) if c>=d])
    if feasible(0) is None:raise RuntimeError('Fewer than eight compatible vivid candidates.')
    if feasible(cap) is not None:
        return matrix,dict(target=cap,capacity_at_least=cap,maximum_computed=False)
    values=sorted({d for row in matrix for d in row if d<cap}|{c for c in ceilings if 0<=c<cap})
    lo,hi=0,len(values)-1
    while lo<hi:
        mid=(lo+hi+1)//2
        if feasible(values[mid]) is not None:lo=mid
        else:hi=mid-1
    maximum=values[lo];slack=min(margin,maximum/2)
    return matrix,dict(target=maximum-slack,maximum_eight_point_distance=maximum,
                       maximum_computed=True,variation_margin=slack)


def threshold(a,b,args):
    if a==b=='gray':return args.gray_distance
    if a.startswith('vivid:') and b.startswith('vivid:'):
        return min(args.sector_targets[int(a.split(':')[1])],args.sector_targets[int(b.split(':')[1])])
    return args.min_distance


def preflight(args):
    plans=[];matrices=[]
    cap=args.min_distance if args.vivid_distance is None else min(args.min_distance,args.vivid_distance)
    for sector,pool in enumerate(vivid_pools()):
        matrix,plan=sector_plan(pool,cap,args.vivid_margin);plan.update(sector=sector,hue_start=24*sector,hue_end=24*(sector+1))
        matrices.append(matrix);plans.append(plan)
    args.independent_sector_plans=plans;args.sector_plans=plans;args.sector_targets=[p['target'] for p in plans];args.vivid_matrices=matrices
    return []


def generate(args):
    rng=random.Random(args.seed);pools=vivid_pools();last=''
    for restart in range(args.restarts):
        selected=[];seen=set();cells={};attempts=0
        args.sector_plans=[dict(p) for p in args.independent_sector_plans]
        def accept(rgb,kind,cell):
            nonlocal attempts
            attempts+=1
            if rgb in seen:return False
            lab=rgb_to_lab(rgb)
            if any(delta_e(lab,l)<threshold(kind,k,args) for _,l,k in selected):return False
            seen.add(rgb);selected.append((rgb,lab,kind));cells[cell]=(rgb,kind);return True
        accept((0,0,0),'gray',(0,0));accept((255,255,255),'gray',(0,1))
        if len(cells)!=2:raise RuntimeError('Black and white cannot meet the configured gray distance.')
        grays=gray_pool();rng.shuffle(grays)
        for c in grays:
            if len(cells)==64:break
            accept(c,'gray',(0,len(cells)))
        if len(cells)<64:last='Gray packing failed.';continue
        # Place constrained vivid colors before the much larger quadrant pools.
        failed=False
        sector_order=list(range(15));rng.shuffle(sector_order)
        for sector in sector_order:
            pool=pools[sector];kind=f'vivid:{sector}'
            cap=args.min_distance if args.vivid_distance is None else min(args.min_distance,args.vivid_distance)
            ceilings=[]
            for rgb in pool:
                lab=rgb_to_lab(rgb);ceiling=cap
                for _,l,k in selected:
                    d=delta_e(lab,l)
                    if k=='gray':
                        if d<args.min_distance:ceiling=-1;break
                    elif d<args.sector_targets[int(k.split(':')[1])]:ceiling=min(ceiling,d)
                ceilings.append(ceiling)
            matrix,plan=sector_plan(pool,cap,args.vivid_margin,args.vivid_matrices[sector],ceilings)
            plan.update(sector=sector,hue_start=24*sector,hue_end=24*(sector+1),conditional_on_preceding_sectors=sector_order[:sector_order.index(sector)])
            args.sector_plans[sector]=plan;args.sector_targets[sector]=plan['target']
            chosen=clique_eight(matrix,plan['target'],rng,[i for i,c in enumerate(ceilings) if c>=plan['target']])
            if chosen is None:raise AssertionError('Exact sector witness disappeared.')
            rng.shuffle(chosen)
            for n,idx in enumerate(chosen):
                if not accept(pool[idx],kind,(sector+1,n)):raise AssertionError('Vivid witness failed final RGB check.')
        if failed:continue
        # Interleave sectors and S/V quadrants so one region cannot fill first.
        for rank in range(14):
            slots=[(sector,q) for sector in range(15) for q in range(4)];rng.shuffle(slots)
            for sector,q in slots:
                sh,vh=((1,1),(0,1),(1,0),(0,0))[q]
                for _ in range(args.attempts_per_slot):
                    h=(sector+rng.random())/15;s=(sh+rng.random())/2;v=(vh+rng.random())/2
                    rgb=tuple(int(c*255+.5) for c in colorsys.hsv_to_rgb(h,s,v))
                    hh,ss,vv=colorsys.rgb_to_hsv(*(c/255 for c in rgb))
                    # Validate hue sector and quadrant AFTER byte rounding.
                    if is_gray(rgb) or int(hh*15)!=sector or int(ss>=.5)!=sh or int(vv>=.5)!=vh:continue
                    if accept(rgb,'quadrant',(sector+1,8+q*14+rank)):break
                else:last=f'Sector {sector}, S/V quadrant {q}, sample {rank+1}: retry limit.';failed=True;break
            if failed:break
        if failed:continue
        grid=[];tags=[]
        for y in range(32):
            for x in range(32):
                block=(y//8)*4+x//8;cell=(y%8)*8+x%8;rgb,tag=cells[(block,cell)];grid.append(rgb);tags.append(tag)
        return grid,tags,dict(restart=restart,candidates_tested_in_successful_restart=attempts)
    raise RuntimeError(f'Bounded search exhausted {args.restarts} restarts. {last} No constraints were relaxed. Try another seed, a larger retry budget, or explicitly smaller distances.')


def audit(colors,tags,args):
    labs=list(map(rgb_to_lab,colors));minimum=math.inf;closest=None;below=0;violations=0;by_class={};sector_minima={}
    for i in range(len(colors)):
        for j in range(i):
            d=delta_e(labs[i],labs[j]);pair=' / '.join(sorted((tags[i].split(':')[0],tags[j].split(':')[0])))
            by_class[pair]=min(d,by_class.get(pair,math.inf))
            if tags[i]==tags[j] and tags[i].startswith('vivid:'):
                sector=tags[i].split(':')[1];sector_minima[sector]=min(d,sector_minima.get(sector,math.inf))
            if d<minimum:minimum=d;closest=[i,j]
            below+=d<args.min_distance;violations+=d<threshold(tags[i],tags[j],args)
    assert len(colors)==len(set(colors))==1024 and violations==0
    return dict(count=1024,unique_colors=1024,minimum_delta_e_2000=minimum,closest_pair_indices=closest,pairs_below_requested_global_distance=below,configured_constraint_violations=violations,minimum_by_pair_class=by_class,vivid_sector_minima=sector_minima,near_gray_count=sum(is_gray(c) for c in colors),black_present=(0,0,0) in colors,white_present=(255,255,255) in colors)


def write_output(path,colors,report):
    hexes=['#'+bytes(c).hex() for c in colors];ext=path.suffix.lower()
    if ext=='.png':
        def chunk(tag,data):return struct.pack('!I',len(data))+tag+data+struct.pack('!I',zlib.crc32(tag+data)&0xffffffff)
        raw=b''.join(b'\x00'+b''.join(bytes(c) for c in colors[y*32:(y+1)*32]) for y in range(32))
        data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',32,32,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'');path.write_bytes(data)
    elif ext=='.json':path.write_text(json.dumps(dict(colors=hexes,report=report),indent=2)+'\n')
    elif ext=='.gpl':path.write_text('\n'.join(['GIMP Palette','Name: Random Strata (audited)','Columns: 32','#']+[f'{r} {g} {b}\t{c}' for (r,g,b),c in zip(colors,hexes)])+'\n')
    else:path.write_text('\n'.join(hexes)+'\n')
    path.with_name(path.name+'.audit.json').write_text(json.dumps(report,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('output',type=Path);p.add_argument('--seed',type=int,help='Reproducible seed; omitted means a fresh random seed recorded in the audit.');p.add_argument('--min-distance',type=float,default=2.5)
    p.add_argument('--gray-distance',type=float,help='Gray–gray target; default follows --min-distance. Search never silently lowers it.')
    p.add_argument('--vivid-distance',type=float,help='Optional lower cap for adaptive vivid spacing; never exceeds --min-distance.')
    p.add_argument('--vivid-margin',type=float,default=.2,help='Slack below a sector maximum when it cannot reach the cap (default 0.2; limited to half its maximum).')
    p.add_argument('--attempts-per-slot',type=int,default=2000);p.add_argument('--restarts',type=int,default=5);p.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    if args.gray_distance is None:args.gray_distance=args.min_distance
    if args.seed is None:args.seed=secrets.randbits(64)
    if any(not math.isfinite(v) or v<0 for v in (args.min_distance,args.gray_distance,args.vivid_margin,*([args.vivid_distance] if args.vivid_distance is not None else []))):p.error('Distances must be finite and nonnegative.')
    if args.attempts_per_slot<1 or args.restarts<1:p.error('Retry budgets must be positive.')
    if args.output.suffix.lower() not in ('.gpl','.txt','.hex','.json','.png'):p.error('Output extension must be .gpl, .txt, .hex, .json or .png.')
    errors=preflight(args)
    if errors:
        print('INFEASIBLE REQUEST:\n'+'\n'.join(errors)+'\nNo palette written. Gray/vivid exceptions require explicit flags.',file=sys.stderr);return 2
    if args.check_only:print(json.dumps(dict(near_gray_pool_size=len(gray_pool()),sector_plans=args.sector_plans,notes='Per-sector exact capacities do not guarantee a jointly compatible random construction.'),indent=2));return 0
    try:colors,tags,search=generate(args)
    except RuntimeError as e:print(str(e),file=sys.stderr);return 3
    report=audit(colors,tags,args);report.update(generator_version=2,sector_plans=args.sector_plans,search=search,seed=args.seed,thresholds=dict(global_distance=args.min_distance,gray_gray=args.gray_distance,vivid_sector_targets=args.sector_targets),metric='CIEDE2000, CIELAB D65/2 degrees, kL=kC=kH=1',layout='32x32 grid, 4x4 blocks of 8x8; first block gray, remaining blocks hue sectors 0–24 through 336–360 degrees',notes='Near-gray means max(R,G,B)-min(R,G,B)<=4; exactly 64 including black and white occupy the first block and none enter hue blocks. Vivid pairs use the smaller of their two sector targets, including across sector boundaries; all other pairs use the global target except an explicitly configured gray-gray target. Sector maxima are exact when computed, conditional on already selected vivid colors. Processing order and witnesses are seeded random; this is not a globally optimal joint allocation. Other stages use bounded restarts.')
    write_output(args.output,colors,report);print(f'Wrote {args.output}: 1024 unique colors, minimum ΔE00 {report["minimum_delta_e_2000"]:.6f}, zero configured violations. Audit: {args.output}.audit.json');return 0
if __name__=='__main__':sys.exit(main())
