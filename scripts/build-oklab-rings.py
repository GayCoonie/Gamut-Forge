"""Seven Oklab ring slices, distance-pruned and filled only from OKHSV Sketch.

python scripts/build-oklab-rings.py (NumPy/Pillow; no network required).
Screen reference: L=.10,.25,.40,.55,.70,.85,1; 24 hues; 8 rings C=0..0.25.
Clamped RGB reproduces the screenshot readouts; target LCh is not final LCh.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/palettes'
STEM='oklab-rings-1024'
KEY='oklabRings1024'
LEVELS=[.1,.25,.4,.55,.7,.85,1.]
THRESHOLD=2.0
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-random-strata.py')
base=importlib.util.module_from_spec(s);s.loader.exec_module(base);m=base.m

def main():
    coords=np.array([(L,r*.25/7,h) for L in LEVELS for r in range(8) for h in range(0,360,15)])
    linear=m.lch_linear(*coords.T)
    raw_rgb=m.encode(linear)
    outside=np.any((linear < -1e-8)|(linear > 1+1e-8),axis=1)
    grid=np.unique(raw_rgb,axis=0);grid_set=set(map(tuple,grid))
    parent_path=OUT/'okhsv-sketch-1024.json'
    parent=json.loads(parent_path.read_text())
    old=np.array([list(bytes.fromhex(c[1:])) for c in parent['colors']],dtype=np.uint8)
    old_set=set(map(tuple,old))
    pool=np.unique(np.concatenate([grid,old]),axis=0)
    is_grid=np.array([tuple(c) in grid_set for c in pool])
    labs=m.lab(pool.astype(float));near=np.full(len(pool),np.inf);ids=[]
    lookup={tuple(c):i for i,c in enumerate(pool)}
    for color in [(0,0,0),(255,255,255)]:
        i=lookup[color];ids.append(i);near=np.minimum(near,m.de(labs,labs[i]));near[ids]=-1
    # Grid first, but never allow a source preference to override separation.
    while len(ids)<1024:
        scores=np.where(is_grid,near,-1);i=int(np.argmax(scores))
        if scores[i]<THRESHOLD:break
        ids.append(i);near=np.minimum(near,m.de(labs,labs[i]));near[ids]=-1
    grid_stage_count=len(ids)
    fill_distances=[]
    while len(ids)<1024:
        i=int(np.argmax(near))
        if near[i]<THRESHOLD:
            raise RuntimeError(f'Only {len(ids)} colors fit in this search at ΔE00 >= 2. No silent threshold relaxation.')
        assert tuple(pool[i]) in old_set
        fill_distances.append(float(near[i]));ids.append(i)
        near=np.minimum(near,m.de(labs,labs[i]));near[ids]=-1
    selected_set=set(map(tuple,pool[ids]))
    # Store grid colors in original L/ring/hue order, then borrowed colors.
    ordered=list(dict.fromkeys(tuple(c) for c in raw_rgb if tuple(c) in selected_set))
    ordered += [tuple(c) for c in pool[ids] if tuple(c) not in grid_set]
    rgb=np.array(ordered,dtype=np.uint8)
    assert len(rgb)==len(set(ordered))==1024
    assert set(ordered)<=grid_set|old_set
    measured=base.audit(rgb)
    assert measured['minimum_delta_e_2000']>=THRESHOLD
    ok=m.rgb_ok(rgb);selected_lookup={tuple(c):i for i,c in enumerate(rgb)}
    samples=[]
    for i,(L,C,H) in enumerate(coords):
        c=raw_rgb[i];idx=selected_lookup.get(tuple(c));actual=m.rgb_ok(c[None,:])[0]
        samples.append(dict(L=float(L),C=float(C),h=float(H),ring=(i//24)%8,
            hex='#'+bytes(c).hex(),outside_srgb=bool(outside[i]),selected=idx is not None,
            palette_index=idx,actual_oklab=list(map(float,actual))))
    grid_retained=sum(c in grid_set for c in ordered)
    report=dict(method='Seven Oklab lightness slices; 24 hues at 15 degree steps; eight chroma levels 0..0.25 inclusive. Clamp out-of-range sRGB channels to reproduce supplied screenshot colors. Deduplicate byte colors, keep black/white, grow a farthest-point grid subset at ΔE00 >= 2, then fill exclusively from OKHSV Sketch at the same hard threshold.',
        lightness_levels=LEVELS,hue_step_degrees=15,chroma_levels=[r*.25/7 for r in range(8)],
        screenshot_readout_check=dict(target_oklab=[.85,.25,0],clamped_rgb=[255,118,199]),
        nominal_samples=len(coords),grid_unique_colors=len(grid),exact_duplicate_occurrences=len(coords)-len(grid),
        out_of_gamut_sample_positions=int(outside.sum()),pool_unique_colors=len(pool),source_overlap=len(grid_set&old_set),
        grid_colors_retained=grid_retained,grid_colors_omitted=len(grid)-grid_retained,
        okhsv_only_colors_added=len(rgb)-grid_retained,grid_stage_count_including_black=grid_stage_count,
        farthest_fillers=len(fill_distances),minimum_filler_insertion_delta_e_2000=min(fill_distances),
        required_minimum_delta_e_2000=THRESHOLD,threshold_relaxed=False,
        parent_palette='okhsvSketch1024',parent_sha256=hashlib.sha256(parent_path.read_bytes()).hexdigest(),
        black_present=True,white_present=True,global_optimality_claim=False,
        interpretation='Eight rings includes C=0. Every zero-chroma ring repeats the same gray 24 times before deduplication. Requested lightness/chroma/hue are construction coordinates; clipping changes final Oklab values. The unknown viewer implementation is inferred from matching RGB readouts, not claimed recovered.',
        selection_note='Deterministic maximin heuristic with grid priority among eligible colors. A maximal grid subset is not a proof of maximum cardinality or optimal coverage. Every omitted grid color is less than 2 ΔE00 from a retained grid-stage color.',
        **measured)
    js=base.export(rgb,STEM,KEY,'Oklab · seven ring slices · 1024',report)
    (ROOT/'dist/oklab-rings.js').write_text(js)
    output=json.loads((OUT/f'{STEM}.json').read_text())
    output['samples']=samples
    output['palette_entries']=[dict(hex='#'+bytes(c).hex(),source='grid' if tuple(c) in grid_set else 'okhsv',
        actual_oklab=list(map(float,lab))) for c,lab in zip(rgb,ok)]
    (OUT/f'{STEM}.json').write_text(json.dumps(output,indent=2)+'\n')
    (OUT/f'{STEM}-grid-union.txt').write_text('\n'.join('#'+bytes(c).hex() for c in grid)+'\n')
    with zipfile.ZipFile(OUT/f'{STEM}-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for ext in ['txt','gpl','kpl','json','png']:z.write(OUT/f'{STEM}.{ext}',f'{STEM}.{ext}')
        z.write(OUT/f'{STEM}-grid-union.txt',f'{STEM}-grid-union.txt')
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v,(dict,list))},indent=2))

if __name__=='__main__':main()
