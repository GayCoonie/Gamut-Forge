"""Static Bloom material palettes and full-range RGB343 control.

Optional --source-zip learns a compact design manifest from the private game.
Normal rebuild uses that manifest: no game images are required or distributed.
Dependencies: NumPy, Pillow. Selection is a deterministic maximin heuristic.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import io
import json
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist' / 'palettes'
MANIFEST = ROOT / 'scripts' / 'critter-material-design.json'
spec = importlib.util.spec_from_file_location('distance', ROOT/'scripts/build-retro-1024.py')
distance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distance)
lab = distance.rgb_to_lab
de = distance.deltaE_ciede2000


def rgb_ok(rgb):
    v = np.asarray(rgb, dtype=float)/255
    v = np.where(v <= .04045, v/12.92, ((v+.055)/1.055)**2.4)
    lms = v @ np.array([[.4122214708,.5363325363,.0514459929],
                        [.2119034982,.6806995451,.1073969566],
                        [.0883024619,.2817188376,.6299787005]]).T
    return np.cbrt(lms) @ np.array([[.2104542553,.7936177850,-.0040720468],
                                   [1.9779984951,-2.4285922050,.4505937099],
                                   [.0259040371,.7827717662,-.8086757660]]).T


def lch_linear(L, C, H):
    a, b = C*np.cos(np.radians(H)), C*np.sin(np.radians(H))
    l, m, s = (L+.3963377774*a+.2158037573*b)**3, (L-.1055613458*a-.0638541728*b)**3, (L-.0894841775*a-1.2914855480*b)**3
    return np.column_stack((4.0767416621*l-3.3077115913*m+.2309699292*s,
                           -1.2684380046*l+2.6097574011*m-.3413193965*s,
                           -.0041960863*l-.7034186147*m+1.7076147010*s))


def chroma_limit(L, H):
    lo, hi = np.zeros_like(L), np.full_like(L, .45)
    for _ in range(24):
        mid = (lo+hi)/2
        rgb = lch_linear(L, mid, H)
        ok = ((rgb >= 0) & (rgb <= 1)).all(axis=1)
        lo, hi = np.where(ok, mid, lo), np.where(ok, hi, mid)
    return lo


def encode(rgb):
    v = np.where(rgb <= .0031308, 12.92*rgb, 1.055*np.maximum(rgb,0)**(1/2.4)-.055)
    return np.floor(np.clip(v,0,1)*255+.5).astype(np.uint8)


def samples_from_zip(path):
    """Equal sample cap per atlas, with an atlas-level holdout split."""
    z = zipfile.ZipFile(path)
    names = sorted(n for n in z.namelist() if '/assets/visual-v11/' in n and n.endswith('.png'))
    records = []
    for number, name in enumerate(names):
        arr = np.asarray(Image.open(io.BytesIO(z.read(name))).convert('RGBA'))
        pix = arr.reshape(-1,4)
        # Some delivered sprites cap alpha at 254. Exclude translucent fringes,
        # without accidentally dropping those entire sprite atlases.
        opaque = pix[pix[:,3] >= 192,:3]
        if len(opaque) == 0: raise ValueError(f'No usable foreground samples: {name}')
        rng = np.random.default_rng(343000+number)
        sample = opaque[rng.choice(len(opaque), min(4096,len(opaque)),replace=False)]
        category = 'tiles' if '/tiles/' in name else name.split('/sprites/')[1].split('/')[0]
        holdout = ('/tiles/25-' in name or '/tiles/26-' in name or
                   '/critters/class-05' in name or number % 7 == 3)
        records.append((name, category, holdout, sample))
    return records


def learn(path):
    records = samples_from_zip(path)
    train = [r for r in records if not r[2]]
    cats = sorted(set(r[1] for r in train))
    points, weights = [], []
    for _, category, _, sample in train:
        points.append(rgb_ok(sample))
        # A tile bank cannot outweigh an entire sprite category.
        weights.extend([1/(len(cats)*sum(r[1]==category for r in train)*len(sample))]*len(sample))
    ok, weights = np.concatenate(points), np.array(weights)
    order = np.argsort(ok[:,0], kind='stable')
    quantiles = np.interp(np.linspace(0,1,19), np.cumsum(weights[order]), ok[order,0])
    tones = .65*np.linspace(.035,.985,19) + .35*quantiles
    tones[0], tones[-1] = .035,.985
    H, C = np.mod(np.degrees(np.arctan2(ok[:,2],ok[:,1])),360), np.hypot(ok[:,1],ok[:,2])
    bins = (H//7.5).astype(int)*12 + np.minimum((C/.025).astype(int),11)
    candidates = []
    for key in np.unique(bins):
        mask = (bins == key) & (C > .018)
        if not mask.any(): continue
        w = weights[mask]
        center = np.average(ok[mask],axis=0,weights=w)
        candidates.append((float(w.sum()),int(key//12),float(np.degrees(np.arctan2(center[2],center[1]))%360),float(np.hypot(center[1],center[2]))))
    families, per_hue = [], {}
    for weight, hb, h, c in sorted(candidates,reverse=True):
        if per_hue.get(hb,0) == 2: continue
        families.append(dict(hue=round(h,6),chroma=round(c,6),balanced_mass=round(weight,8)))
        per_hue[hb] = per_hue.get(hb,0)+1
        if len(families) == 64: break
    manifest = dict(version=1, source='Coonie Critters: Static Bloom v11.1.0 runtime atlases',
        archive_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        training_atlases=len(train), holdout_atlases=len(records)-len(train),
        training_samples=sum(len(r[3]) for r in train),sample_rule='Up to 4096 pixels with alpha >= 192 per atlas; RNG 343000 + sorted atlas index.',
        category_balance='Equal total weight per category, then equal per atlas within category.',
        categories=cats,coarse_oklab_lightness=list(map(float,tones)),material_families=families,
        holdout_names=[r[0].split('/assets/visual-v11/')[1] for r in records if r[2]],
        artistic_intent='Shared lightness steps; warm highlights and cool shadows; muted material ramps alongside vivid full-hue accents. Separation takes priority over coverage.')
    MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def shifted_hue(h, L):
    # Gently bend shadows toward indigo, highlights toward warm gold.
    toward = np.where(L < .55, 285., 85.)
    turn = (toward-h+180)%360-180
    return (h+np.clip(turn,-35,35)*np.minimum(np.abs(L-.55)*1.15,.48))%360


def pool(design, fine=False):
    tones = np.array(design['coarse_oklab_lightness'])
    if fine:
        tones = np.interp(np.linspace(0,18,55),np.arange(19),tones)
    hues = np.arange(0,360,3.75 if fine else 7.5)
    L, H = np.meshgrid(tones,hues,indexing='ij')
    L, H = L.ravel(), shifted_hue(H.ravel(),L.ravel())
    cmax = chroma_limit(L,H)
    fractions = [.18,.30,.43,.56,.69,.82,.92,1] if fine else [.24,.43,.64,.83,1]
    chunks = [encode(lch_linear(L,cmax*f,H)) for f in fractions]
    for family in design['material_families']:
        H = shifted_hue(np.full_like(tones,family['hue']),tones)
        cmax = chroma_limit(tones,H)
        envelope = np.sin(np.pi*tones)**.65
        for scale in ([.55,.7,.85,1,1.15,1.35,1.6] if fine else [.6,.85,1,1.2,1.5]):
            C = np.minimum(cmax,family['chroma']*scale*envelope)
            chunks.append(encode(lch_linear(tones,C,H)))
    # A single neutral spine, never separate near-gray copies at every hue.
    chunks.append(encode(lch_linear(tones,np.zeros_like(tones),np.zeros_like(tones))))
    chunks.append(np.array([[0,0,0],[255,255,255]],dtype=np.uint8))
    return np.unique(np.concatenate(chunks),axis=0)


def select(rgb, size, seeds=None):
    labs = lab(rgb.astype(float))
    if seeds is None: seeds = np.array([[0,0,0],[255,255,255]],dtype=np.uint8)
    lookup = {tuple(c): i for i,c in enumerate(rgb)}
    ids = [lookup[tuple(c)] for c in seeds]
    nearest = np.full(len(rgb),np.inf)
    for idx in ids: nearest = np.minimum(nearest,de(labs,labs[idx]))
    nearest[ids] = -1
    insertion = []
    while len(ids) < size:
        idx = int(np.argmax(nearest))
        insertion.append(float(nearest[idx]))
        ids.append(idx)
        nearest = np.minimum(nearest,de(labs,labs[idx]))
        nearest[ids] = -1
        if len(ids)%512 == 0: print(f'{size}: {len(ids)} selected; insertion ΔE00 {insertion[-1]:.6f}',flush=True)
    return rgb[ids],dict(candidate_count=len(rgb),last_insertion_delta_e_2000=insertion[-1],candidate_covering_radius=float(nearest.max()))


def audit(rgb):
    labs = lab(rgb.astype(float))
    nn = np.full(len(rgb),np.inf)
    closest, below = None, 0
    for i in range(len(rgb)-1):
        ds = de(labs[i+1:],labs[i])
        j = int(np.argmin(ds))
        if closest is None or ds[j] < closest[0]: closest = float(ds[j]),i,i+j+1
        nn[i] = min(nn[i],ds[j])
        nn[i+1:] = np.minimum(nn[i+1:],ds)
        below += int(np.count_nonzero(ds < 2))
    return dict(minimum_delta_e_2000=closest[0],pairs_below_2=below,
                closest_pair=['#'+bytes(rgb[i]).hex() for i in closest[1:]],
                nearest_neighbor_percentiles=dict(zip(['min','p25','median','p75','max'],map(float,np.percentile(nn,[0,25,50,75,100])))))


def export(rgb, stem, key, name, report):
    size, side = len(rgb), int(np.sqrt(len(rgb)))
    ok = rgb_ok(rgb)
    hue = np.mod(np.arctan2(ok[:,2],ok[:,1]),2*np.pi)
    order = []
    for row, band in enumerate(np.array_split(np.argsort(ok[:,0],kind='stable'),side)):
        band = band[np.argsort(hue[band],kind='stable')]
        order.extend(band[::-1] if row%2 else band)
    rgb = rgb[order]
    colors = ['#'+bytes(c).hex() for c in rgb]
    report.update(name=name,count=size,unique_colors=len(set(colors)),metric='CIEDE2000; CIELAB D65/2 degrees; kL=kC=kH=1',**audit(rgb))
    (OUT/f'{stem}.txt').write_text('\n'.join(colors)+'\n')
    (OUT/f'{stem}.json').write_text(json.dumps(dict(report=report,colors=colors),indent=2)+'\n')
    (OUT/f'{stem}.gpl').write_text('\n'.join(['GIMP Palette',f'Name: {name}',f'Columns: {side}','#']+[f'{r:3} {g:3} {b:3}\t{c}' for (r,g,b),c in zip(rgb,colors)])+'\n')
    root = ET.Element('Colorset',name=name,columns=str(side),rows=str(side),readonly='false',version='1.0')
    for i,(c,channels) in enumerate(zip(colors,rgb)):
        sw = ET.SubElement(root,'ColorSetEntry',name=c,id=f'color-{i+1}',bitdepth='U8',spot='false')
        ET.SubElement(sw,'sRGB',**{k:f'{v/255:.10f}' for k,v in zip('rgb',channels)})
        ET.SubElement(sw,'Position',row=str(i//side),column=str(i%side))
    with zipfile.ZipFile(OUT/f'{stem}.kpl','w') as z:
        z.writestr('mimetype','application/x-krita-palette')
        z.writestr('colorset.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True),compress_type=zipfile.ZIP_DEFLATED)
        z.writestr('profiles.xml','<?xml version="1.0" encoding="UTF-8"?><Profiles/>')
    Image.fromarray(rgb.reshape(side,side,3)).resize((1024,1024),Image.Resampling.NEAREST).save(OUT/f'{stem}.png')
    with zipfile.ZipFile(OUT/f'{stem}-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for ext in ('txt','json','gpl','kpl','png'): z.write(OUT/f'{stem}.{ext}',f'{stem}.{ext}')
    print(json.dumps(report),flush=True)
    return f'window.GAMUT_PALETTES.{key}='+json.dumps(dict(name=name,colors=colors),separators=(',',':'))+';\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-zip')
    args = parser.parse_args()
    design = learn(args.source_zip) if args.source_zip else json.loads(MANIFEST.read_text())
    coarse_pool = pool(design)
    coarse, coarse_report = select(coarse_pool,1024)
    fine_pool = np.unique(np.concatenate((pool(design,True),coarse)),axis=0)
    fine, fine_report = select(fine_pool,4096,coarse)
    for rgb in (coarse,fine):
        assert len(np.unique(rgb,axis=0)) == len(rgb)
        assert audit(rgb)['minimum_delta_e_2000'] >= 2, 'Do not silently relax separation.'
    common = dict(method='Deterministic CIEDE2000 farthest-point selection from game-derived, hue-shifted material ramps on shared OKLab lightness steps.',
        global_optimality_claim=False,design_manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        minimum_separation_requirement=2,relaxed_separation=False,
        training_atlases=design['training_atlases'],holdout_atlases=design['holdout_atlases'])
    js = export(coarse,'static-bloom-1024','staticBloom1024','Static Bloom · material ramps · 1024',dict(common,**coarse_report,role='Strong palette crushing; nested in Static Bloom 4096.'))
    js += export(fine,'static-bloom-4096','staticBloom4096','Static Bloom · material ramps · 4096',dict(common,**fine_report,role='Extended material vocabulary; contains every Static Bloom 1024 color.'))
    r = np.floor(np.arange(8)*255/7+.5).astype(np.uint8)
    g = np.arange(16,dtype=np.uint8)*17
    cube = np.array(np.meshgrid(r,g,r,indexing='ij')).reshape(3,-1).T
    js += export(cube,'rgb343-control','rgb343Control','RGB343 · 10-bit control · 1024',dict(method='Cartesian product of 8 red × 16 green × 8 blue full-range sRGB code levels; nearest-integer expansion.',
        red_blue_levels=r.tolist(),green_levels=g.tolist(),bit_allocation=[3,4,3],separation_requirement_applied=False))
    (ROOT/'dist/critter-palettes.js').write_text(js)


if __name__ == '__main__': main()
