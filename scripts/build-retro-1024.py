"""Reproducible distance-first subset of the shipped Retro Source Union 4096.

Dependencies: numpy, Pillow. No generated colors, centroids or channel edits.
Eight deterministic farthest-point starts, then strict bottleneck-improving swaps.
This is a measured maximin heuristic, NOT a claim of global optimality.
"""
from pathlib import Path
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist' / 'palettes'
OUT.mkdir(exist_ok=True)
STEM = 'retro-source-union-1024'
SIZE = 1024


def deltaE_ciede2000(lab, reference):
    """CIEDE2000 vectorized equations; Sharma, Wu & Dalal (2005)."""
    l1,a1,b1 = lab.T
    l2,a2,b2 = reference
    c1,c2 = np.hypot(a1,b1),np.hypot(a2,b2)
    c7 = ((c1+c2)/2)**7
    g = .5*(1-np.sqrt(c7/(c7+25**7)))
    ap1,ap2 = (1+g)*a1,(1+g)*a2
    cp1,cp2 = np.hypot(ap1,b1),np.hypot(ap2,b2)
    h1 = np.mod(np.degrees(np.arctan2(b1,ap1)),360)
    h2 = np.mod(np.degrees(np.arctan2(b2,ap2)),360)
    h1,h2 = np.where(cp1==0,0,h1),np.where(cp2==0,0,h2)
    dh = h2-h1
    dh = np.where(cp1*cp2==0,0,np.where(dh>180,dh-360,np.where(dh < -180,dh+360,dh)))
    dH = 2*np.sqrt(cp1*cp2)*np.sin(np.radians(dh/2))
    C = (cp1+cp2)/2
    H = np.where(cp1*cp2==0,h1+h2,np.where(np.abs(h1-h2)<=180,(h1+h2)/2,
        np.where(h1+h2<360,(h1+h2+360)/2,(h1+h2-360)/2)))
    T = 1-.17*np.cos(np.radians(H-30))+.24*np.cos(np.radians(2*H))+.32*np.cos(np.radians(3*H+6))-.20*np.cos(np.radians(4*H-63))
    t = (l1+l2)/2-50
    dL = (l2-l1)/(1+.015*t*t/np.sqrt(20+t*t))
    dC = (cp2-cp1)/(1+.045*C)
    dHt = dH/(1+.015*C*T)
    RT = -2*np.sqrt(C**7/(C**7+25**7))*np.sin(np.radians(60*np.exp(-((H-275)/25)**2)))
    return np.sqrt(np.maximum(0,dL*dL+dC*dC+dHt*dHt+RT*dC*dHt))


def rgb_to_lab(rgb):
    v = rgb / 255.0
    lin = np.where(v <= .04045, v/12.92, ((v+.055)/1.055)**2.4)
    xyz = lin @ np.array([[.4124564,.3575761,.1804375],
                          [.2126729,.7151522,.0721750],
                          [.0193339,.1191920,.9503041]]).T
    xyz /= [.95047,1,1.08883]
    f = np.where(xyz > 216/24389,np.cbrt(xyz),(24389/27*xyz+16)/116)
    return np.column_stack((116*f[:,1]-16,500*(f[:,0]-f[:,1]),200*(f[:,1]-f[:,2])))


def grow(D, seeds):
    chosen = list(seeds)
    nearest = D[:,chosen].min(axis=1)
    nearest[chosen] = -1
    while len(chosen) < SIZE:
        i = int(np.argmax(nearest))
        chosen.append(i)
        nearest = np.minimum(nearest,D[:,i])
        nearest[chosen] = -1
    return np.array(chosen)


def improve(D, selected, locked):
    # At a unique bottleneck, any strict improvement must remove an endpoint.
    # Use every legal replacement, without weighting distances or moving colors.
    selected = selected.copy()
    swaps = 0
    while swaps < 512:
        sub = D[np.ix_(selected,selected)].copy()
        np.fill_diagonal(sub,np.inf)
        old = float(sub.min())
        a,b = np.unravel_index(np.argmin(sub),sub.shape)
        choices = []
        for pos in (a,b):
            if int(selected[pos]) in locked:
                continue
            rest = np.delete(selected,pos)
            distances = D[:,rest].min(axis=1)
            distances[selected] = -1
            new_id = int(np.argmax(distances))
            rest_sub = np.delete(np.delete(sub,pos,axis=0),pos,axis=1)
            new_min = min(float(distances[new_id]),float(rest_sub.min()))
            if new_min > old + 1e-10:
                choices.append((new_min,float(distances[new_id]),pos,new_id))
        if not choices:
            break
        _,_,pos,new_id = max(choices)
        selected[pos] = new_id
        swaps += 1
    return selected,swaps


def main():
    source_path = ROOT/'dist'/'retro-source-union-4096.js'
    source_bytes = source_path.read_bytes()
    parent = json.loads(source_bytes.decode().split('=',1)[1].strip().rstrip(';'))
    colors = parent['colors']
    assert len(colors) == len(set(colors)) == 4096
    rgb = np.array([list(bytes.fromhex(c[1:])) for c in colors],dtype=float)
    lab = rgb_to_lab(rgb)
    n = len(lab)
    D = np.empty((n,n),dtype=np.float64)
    for i in range(n):
        D[i] = deltaE_ciede2000(lab,lab[i])
    assert np.allclose(D,D.T,atol=1e-10)
    black,white = colors.index('#000000'),colors.index('#ffffff')
    locks = {black,white}  # Only functional ink/paper endpoints; no inherited anchors.
    seed_hexes = [None,'#ff0000','#00ff00','#0000ff','#00ffff','#ff00ff','#ffff00','#808080']
    trials = []
    for seed_hex in seed_hexes:
        seeds = [black,white]
        if seed_hex is not None:
            target = np.array(list(bytes.fromhex(seed_hex[1:])),dtype=float)
            seed = int(np.argmin(deltaE_ciede2000(lab,rgb_to_lab(target[None,:])[0])))
            if seed not in seeds: seeds.append(seed)
        selected = grow(D,seeds)
        initial = D[np.ix_(selected,selected)].copy()
        np.fill_diagonal(initial,np.inf)
        initial_min = float(initial.min())
        selected,swaps = improve(D,selected,locks)
        sub = D[np.ix_(selected,selected)].copy()
        np.fill_diagonal(sub,np.inf)
        spacing = sub.min(axis=1)
        coverage = D[:,selected].min(axis=1)
        # Compare separation FIRST, then source-pool covering radius, then mean.
        score = (float(spacing.min()),-float(coverage.max()),-float(coverage.mean()))
        trial = dict(seed=seed_hex or 'black+white',initial_minimum=initial_min,
                     minimum=score[0],swaps=swaps,pool_covering_radius=float(coverage.max()),
                     pool_mean_error=float(coverage.mean()))
        trials.append(trial)
        print(json.dumps(trial),flush=True)
        if len(trials) == 1 or score > best_score:
            best_score,best_selected,best_spacing,best_trial = score,selected,spacing,len(trials)-1
    selected = best_selected
    selected_rgb = rgb[selected]
    # Display order only: 32 lightness bands, hue snakes across each row.
    labs = lab[selected]
    h = np.mod(np.arctan2(labs[:,2],labs[:,1]),2*np.pi)
    order = []
    for row,band in enumerate(np.array_split(np.argsort(labs[:,0],kind='stable'),32)):
        band = band[np.argsort(h[band],kind='stable')]
        order.extend(band[::-1] if row%2 else band)
    selected = selected[order]
    selected_rgb = rgb[selected].astype(int)
    sub = D[np.ix_(selected,selected)].copy()
    np.fill_diagonal(sub,np.inf)
    close_a,close_b = np.unravel_index(np.argmin(sub),sub.shape)
    report = dict(name='Retro source union · distance-first · 1024',
        count=SIZE,parent_count=n,parent_sha256=hashlib.sha256(source_bytes).hexdigest(),
        metric='CIEDE2000, CIELAB D65 / 2°, kL=kC=kH=1',
        method='Eight farthest-point starts; strict minimum-distance-improving one-color swaps; best separation wins before pool coverage.',
        global_optimality_claim=False,locked_colors=['#000000','#ffffff'],
        minimum_delta_e_2000=float(sub.min()),pairs_below_2=int(np.count_nonzero(sub<2)//2),
        nearest_neighbor_percentiles=dict(zip(['min','p25','median','p75','max'],map(float,np.percentile(sub.min(axis=1),[0,25,50,75,100])))),
        closest_pair=[colors[selected[close_a]],colors[selected[close_b]]],
        pool_covering_radius=-best_score[1],pool_mean_delta_e_2000=-best_score[2],
        winning_trial=best_trial,trials=trials,
        all_colors_verbatim_from_parent=True)
    entries = [dict(hex=colors[idx],rgb=list(map(int,rgb[idx])),parent_index=int(idx),
                    nearest_delta_e_2000=float(sub[pos].min())) for pos,idx in enumerate(selected)]
    (OUT/f'{STEM}.json').write_text(json.dumps(dict(report=report,colors=entries),indent=2)+'\n')
    (OUT/f'{STEM}.txt').write_text('\n'.join(e['hex'] for e in entries)+'\n')
    (ROOT/'dist'/f'{STEM}.js').write_text('window.GAMUT_PALETTES.retroSourceUnion1024='+json.dumps(dict(name=report['name'],colors=[e['hex'] for e in entries]),separators=(',',':'))+';\n')
    lines=['GIMP Palette','Name: Coonie - Retro Source Union Distance First 1024','Columns: 32','#']
    lines += [f"{e['rgb'][0]:3} {e['rgb'][1]:3} {e['rgb'][2]:3}\t{e['hex']}" for e in entries]
    (OUT/f'{STEM}.gpl').write_text('\n'.join(lines)+'\n')
    root=ET.Element('Colorset',name='Coonie - Retro Source Union Distance First 1024',columns='32',rows='32',readonly='false',version='1.0')
    for i,e in enumerate(entries):
        sw=ET.SubElement(root,'ColorSetEntry',name=e['hex'],id=f'color-{i+1}',bitdepth='U8',spot='false')
        ET.SubElement(sw,'sRGB',**{c:f'{v/255:.10f}' for c,v in zip('rgb',e['rgb'])})
        ET.SubElement(sw,'Position',row=str(i//32),column=str(i%32))
    with zipfile.ZipFile(OUT/f'{STEM}.kpl','w') as z:
        z.writestr('mimetype','application/x-krita-palette')
        z.writestr('colorset.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True),compress_type=zipfile.ZIP_DEFLATED)
        z.writestr('profiles.xml','<?xml version="1.0" encoding="UTF-8"?><Profiles/>')
    # Exact 32×32 swatch chart; no antialiasing or generated imagery.
    from PIL import Image
    im=Image.fromarray(selected_rgb.astype('uint8').reshape(32,32,3))
    im.resize((1024,1024),Image.Resampling.NEAREST).save(OUT/f'{STEM}.png')
    with zipfile.ZipFile(OUT/f'{STEM}-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for ext in ('json','txt','gpl','kpl','png'):
            z.write(OUT/f'{STEM}.{ext}',f'{STEM}.{ext}')
        z.write(Path(__file__),'scripts/build-retro-1024.py')
        z.write(source_path,'dist/'+source_path.name)
    assert len(set(e['hex'] for e in entries))==SIZE and report['pairs_below_2']==0
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
