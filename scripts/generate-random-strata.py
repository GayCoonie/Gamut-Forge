#!/usr/bin/env python3
"""Random HSV strata, with honest CIEDE2000 constraints. Python 3.10+, stdlib only.

Strict original request (diagnoses infeasibility and writes no palette):
  python generate-random-strata.py palette.gpl --seed 42
Explicit exceptions for dense gray/vivid rows, retaining 2.5 for other pairs:
  python generate-random-strata.py palette.gpl --seed 42 --gray-distance 0 --vivid-distance 0.25

Outputs: .gpl, .txt/.hex, .json, .png (RGB, no alpha). Always writes an audit
sidecar on success. Constraints apply to the FINAL 8-bit sRGB colors. A bounded
search failure means this search failed, not proof that no solution exists.
"""
import argparse,colorsys,json,math,random,struct,sys,zlib
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


def threshold(a,b,args):
    if a==b=='gray':return args.gray_distance
    if a==b=='vivid':return args.vivid_distance
    return args.min_distance


def preflight(args):
    errors=[];gray_bound=packing_upper_bound([(v,v,v) for v in range(256)],args.gray_distance)
    if gray_bound<64:errors.append(f'64 grays requested, but at most {gray_bound} can fit at gray–gray ΔE00 >= {args.gray_distance:g} (proven upper bound).')
    for sector,pool in enumerate(vivid_pools()):
        bound=packing_upper_bound(pool,args.vivid_distance)
        if bound<8:errors.append(f'Hue sector {24*sector}–{24*(sector+1)}°: eight vivid colors requested, but at most {bound} fit at vivid–vivid ΔE00 >= {args.vivid_distance:g}.')
    return errors


def generate(args):
    rng=random.Random(args.seed);pools=vivid_pools();last=''
    for restart in range(args.restarts):
        selected=[];seen=set();cells={};attempts=0
        def accept(rgb,kind,cell):
            nonlocal attempts
            attempts+=1
            if rgb in seen:return False
            lab=rgb_to_lab(rgb)
            if any(delta_e(lab,l)<threshold(kind,k,args) for _,l,k in selected):return False
            seen.add(rgb);selected.append((rgb,lab,kind));cells[cell]=(rgb,kind);return True
        grays=[(v,v,v) for v in range(256)];rng.shuffle(grays)
        for c in grays:
            if len(cells)==64:break
            accept(c,'gray',(0,len(cells)))
        if len(cells)<64:last='Gray packing failed.';continue
        # Place constrained vivid colors before the much larger quadrant pools.
        failed=False
        for sector,pool in enumerate(pools):
            pool=pool.copy();rng.shuffle(pool);n=0
            for rgb in pool:
                if accept(rgb,'vivid',(sector+1,n)):n+=1
                if n==8:break
            if n<8:last=f'Vivid sector {sector} placed {n}/8.';failed=True;break
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
                    if ss==0 or int(hh*15)!=sector or int(ss>=.5)!=sh or int(vv>=.5)!=vh:continue
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
    labs=list(map(rgb_to_lab,colors));minimum=math.inf;closest=None;below=0;violations=0;by_class={}
    for i in range(len(colors)):
        for j in range(i):
            d=delta_e(labs[i],labs[j]);pair=' / '.join(sorted((tags[i],tags[j])))
            by_class[pair]=min(d,by_class.get(pair,math.inf))
            if d<minimum:minimum=d;closest=[i,j]
            below+=d<args.min_distance;violations+=d<threshold(tags[i],tags[j],args)
    assert len(colors)==len(set(colors))==1024 and violations==0
    return dict(count=1024,unique_colors=1024,minimum_delta_e_2000=minimum,closest_pair_indices=closest,pairs_below_requested_global_distance=below,configured_constraint_violations=violations,minimum_by_pair_class=by_class)


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
    p.add_argument('output',type=Path);p.add_argument('--seed',type=int,default=42);p.add_argument('--min-distance',type=float,default=2.5)
    p.add_argument('--gray-distance',type=float,help='Explicit gray–gray exception; default follows --min-distance.')
    p.add_argument('--vivid-distance',type=float,help='Explicit vivid–vivid exception; default follows --min-distance.')
    p.add_argument('--attempts-per-slot',type=int,default=2000);p.add_argument('--restarts',type=int,default=5);p.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    if args.gray_distance is None:args.gray_distance=args.min_distance
    if args.vivid_distance is None:args.vivid_distance=args.min_distance
    if any(not math.isfinite(v) or v<0 for v in (args.min_distance,args.gray_distance,args.vivid_distance)):p.error('Distances must be finite and nonnegative.')
    if args.attempts_per_slot<1 or args.restarts<1:p.error('Retry budgets must be positive.')
    if args.output.suffix.lower() not in ('.gpl','.txt','.hex','.json','.png'):p.error('Output extension must be .gpl, .txt, .hex, .json or .png.')
    errors=preflight(args)
    if errors:
        print('INFEASIBLE REQUEST:\n'+'\n'.join(errors)+'\nNo palette written. Gray/vivid exceptions require explicit flags.',file=sys.stderr);return 2
    if args.check_only:print('No impossibility detected by the upper-bound checks. This does not guarantee search success.');return 0
    try:colors,tags,search=generate(args)
    except RuntimeError as e:print(str(e),file=sys.stderr);return 3
    report=audit(colors,tags,args);report.update(search=search,seed=args.seed,thresholds=dict(global_distance=args.min_distance,gray_gray=args.gray_distance,vivid_vivid=args.vivid_distance),metric='CIEDE2000, CIELAB D65/2 degrees, kL=kC=kH=1',layout='32x32 grid, 4x4 blocks of 8x8; first block gray, remaining blocks hue sectors 0–24 through 336–360 degrees',notes='Exact duplicates are always rejected. Exceptions affect only the named pair class; all other pairs retain the global threshold.')
    write_output(args.output,colors,report);print(f'Wrote {args.output}: 1024 unique colors, minimum ΔE00 {report["minimum_delta_e_2000"]:.6f}, zero configured violations. Audit: {args.output}.audit.json');return 0
if __name__=='__main__':sys.exit(main())
