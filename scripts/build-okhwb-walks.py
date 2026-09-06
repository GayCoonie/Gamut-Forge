"""OKHWB v3: three sketch traversals and their W/B reflections, cycling every six hues."""
from pathlib import Path
import hashlib, html, importlib.util, json, subprocess, zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'dist/palettes'
STEM='okhwb-walks-1024'; KEY='okhwbWalks1024'
spec=importlib.util.spec_from_file_location('triangle',ROOT/'scripts/build-okhwb-triangle.py')
triangle=importlib.util.module_from_spec(spec);spec.loader.exec_module(triangle)
# Coordinates are integer W/B levels, divided by six at conversion time.
# Start at the vivid tip and visit every chromatic lattice point once.
SPIRAL=[(0,0),(1,0),(2,0),(3,0),(4,0),(5,0),(4,1),(3,2),(2,3),(1,4),(0,5),
        (0,4),(0,3),(0,2),(0,1),(1,1),(2,1),(3,1),(2,2),(1,3),(1,2)]
COLUMNS=[(n-1-j,j) for n in range(1,7) for j in (range(n) if n%2 else range(n-1,-1,-1))]
FOLDS=[(0,0),(1,0),(2,0),(3,0),(4,0),(5,0),(4,1),(3,2),(2,3),(1,4),(0,5),
       (0,4),(1,3),(2,2),(3,1),(2,1),(1,2),(0,3),(0,2),(1,1),(0,1)]
PATTERNS=[]
for family,path in [('Spiral',SPIRAL),('Column snake',COLUMNS),('Edge and folds',FOLDS)]:
    for mirror in [False,True]:
        PATTERNS.append(dict(name=family+(' · mirrored' if mirror else ' · original'),
            family=family, mirrored=mirror, path=[(j,i) if mirror else (i,j) for i,j in path]))
LATTICE=[(i,j) for j in range(6) for i in range(6-j)]
for p in PATTERNS:
    assert p['path'][0]==(0,0) and len(p['path'])==21 and set(p['path'])==set(LATTICE)
    assert all((c-a,d-b) in [(1,0),(-1,0),(0,1),(0,-1),(1,-1),(-1,1)]
               for (a,b),(c,d) in zip(p['path'],p['path'][1:]))

def make_samples():
    samples=[]
    for sector in range(48):
        pattern=PATTERNS[sector%6];ranks={point:rank for rank,point in enumerate(pattern['path'])}
        for i,j in LATTICE:
            rank=ranks[i,j];offset=rank*7.5/21
            samples.append(dict(kind='hue',source_h=sector*7.5,h=(sector*7.5+offset)%360,
                w=i/6,b=j/6,walk_rank=rank,hue_offset=offset,pattern_index=sector%6))
    samples.extend(dict(kind='gray',source_h=0,h=0,w=i/15,b=1-i/15,
                        walk_rank=None,hue_offset=0,pattern_index=None) for i in range(16))
    return samples

def main():
    samples=make_samples()
    js="""const fs=require('fs'),vm=require('vm'),c={};vm.createContext(c);
vm.runInContext(fs.readFileSync('dist/vendor/ottosson-colorconversion.js','utf8'),c);
process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(p=>p.b===1?[0,0,0]:c.okhsv_to_srgb(p.h/360,Math.max(0,1-p.w/(1-p.b)),1-p.b))));"""
    raw=np.array(json.loads(subprocess.check_output(['node','-e',js],input=json.dumps(samples).encode(),cwd=ROOT)))
    assert np.isfinite(raw).all()
    rgb=np.floor(np.clip(raw,0,255)+.5).astype(np.uint8)
    assert len(rgb)==len(set(map(tuple,rgb)))==1024
    old=json.loads((OUT/'okhwb-triangle-1024.json').read_text())
    colors=['#'+bytes(c).hex() for c in rgb]
    assert colors[-16:]==old['colors'][-16:]
    assert all(colors[h*21]==old['colors'][h*21] for h in range(48))
    report=dict(method='48 source hues, each assigned one of six cyclic traversals of the same 21 W/B cells. Rank 0 is the vivid tip; H=(source H + rank*7.5/21) modulo 360. The next source hue is excluded. Preserve all sixteen v1 grays.',
        source_sketches=['86f4768e-7ae2-4c43-b330-307852beed27.png','695a620e-c310-4a26-8052-16f7151071a4.png','Screenshot from 2026-09-06 09-19-17.png'],
        interpretation='Translate the freehand curves to three adjacent-cell walks: inward spiral, alternating columns, and outer edge followed by folded columns. Pair each with exact W/B reflection, keeping the vivid tip fixed. Do not reverse hue direction for mirrors.',
        hue_step_degrees=7.5,walk_hue_step_degrees=7.5/21,source_hue_count=48,points_per_source_hue=21,
        sampled_hue_count=len({p['h'] for p in samples[:1008]}),pattern_cycle_length=6,occurrences_per_pattern=8,
        traversal_patterns=PATTERNS,white_black_step=1/6,base_palette='okhwb-triangle-1024',
        exact_colors_shared_with_v1=len(set(colors)&set(old['colors'])),
        conversion=old['report']['conversion'],source=old['report']['source'],
        reference_sha256=hashlib.sha256((ROOT/'dist/vendor/ottosson-colorconversion.js').read_bytes()).hexdigest(),
        maximum_boundary_excursion_bytes=float(max(0,-raw.min(),raw.max()-255)),
        perceptual_pruning=False,minimum_separation_requirement=None,fillers=0,individual_rgb_adjustments=0,
        diagram='Source-hue panels contain shifted hues. Cells retain the same W/B geometry as v1. Optional numbered lines connect cell interiors in traversal order; they do not add colors or indicate perceptual distance.',
        grayscale_axis=old['report']['grayscale_axis'])
    bundle=triangle.base.export(rgb,STEM,KEY,'OKHWB v3 · chiral hue walks · 1024',report)
    (ROOT/'dist/okhwb-walks.js').write_text(bundle)
    data=json.loads((OUT/f'{STEM}.json').read_text())
    for p,c in zip(samples,colors):p['hex']=c
    data['samples']=samples;(OUT/f'{STEM}.json').write_text(json.dumps(data,indent=2)+'\n')
    geometry=triangle.cells([triangle.point(p['w'],p['b']) for p in samples[:21]+samples[-16:]])
    centers=[np.mean(poly,axis=0) for poly in geometry[:21]]
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1320" height="1940" viewBox="0 0 1320 1940" role="img" aria-labelledby="title desc">',
        '<title id="title">OKHWB v3: chiral hue walks, 1024 colors</title>',
        '<desc id="desc">Three traversal families, each with its W/B mirror, repeat eight times around 48 source hues. Each cell advances one of 21 hue steps. Sixteen shared grays complete the palette.</desc>',
        '<style>.walk-overlay{display:none;pointer-events:none}</style>',
        '<rect width="1320" height="1940" fill="#121018"/>',
        '<g font-family="sans-serif" fill="#eae5f0"><text x="24" y="36" font-size="25">OKHWB v3 · chiral hue walks · 1024</text><text x="24" y="62" font-size="15">48 vivid anchors + 960 hue-walk samples + 16 grays · six traversals, eight cycles</text></g>']
    for sector in range(48):
        pattern=PATTERNS[sector%6]
        svg.append(f'<g data-hue="{sector*7.5}" data-pattern="{sector%6}" transform="translate({sector%6*220},{80+sector//6*230})">')
        svg.append(f'<text x="20" y="16" fill="#eae5f0" font-family="sans-serif" font-size="14">Source {sector*7.5:g}°</text><text x="20" y="29" fill="#bfb6cc" font-family="sans-serif" font-size="9">{html.escape(pattern["name"])}</text>')
        entries=samples[sector*21:(sector+1)*21]+samples[-16:]
        for cell,(poly,p) in enumerate(zip(geometry,entries)):
            label=(f'{p["hex"]} · source {sector*7.5:g}° · H {p["h"]:.6f}° · step {p["walk_rank"]}/21 · +{p["hue_offset"]:.6f}° · W {p["w"]:.4f} · B {p["b"]:.4f}' if p['kind']=='hue' else f'{p["hex"]} · shared gray · W {p["w"]:.4f} · B {p["b"]:.4f}')
            points=' '.join(f'{a:.5f},{b:.5f}' for a,b in poly)
            svg.append(f'<polygon data-cell="{cell}" points="{points}" fill="{p["hex"]}" stroke="#121018" stroke-width="0.45"><title>{html.escape(label)}</title></polygon>')
        walk=[centers[LATTICE.index(tuple(p))] for p in pattern['path']]
        walkpoints=' '.join(f'{x:.5f},{y:.5f}' for x,y in walk)
        svg.append(f'<g class="walk-overlay"><polyline points="{walkpoints}" fill="none" stroke="#19151f" stroke-width="2.6"/><polyline points="{walkpoints}" fill="none" stroke="#ffe259" stroke-width="1.2"/>')
        for rank,(x,y) in enumerate(walk):
            svg.append(f'<circle cx="{x:.5f}" cy="{y:.5f}" r="4.4" fill="{"#63ead8" if rank==0 else "#ffe259"}" stroke="#19151f" stroke-width="0.4"/><text x="{x:.5f}" y="{y+1.8:.5f}" fill="#121018" text-anchor="middle" font-family="sans-serif" font-size="5.5">{rank}</text>')
        svg.append('</g><g fill="#bfb6cc" font-family="sans-serif" font-size="12"><text x="4" y="38">W</text><text x="4" y="213">B</text><text x="167" y="124">Hue</text></g></g>')
    svg.append('<text x="24" y="1930" fill="#bfb6cc" font-family="sans-serif" font-size="14">Hue advances by 7.5° / 21 per cell. Shared gray edge repeats visually; palette stores it once.</text></svg>')
    (OUT/f'{STEM}-atlas.svg').write_text('\n'.join(svg)+'\n')
    with zipfile.ZipFile(OUT/f'{STEM}-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for ext in ['txt','gpl','kpl','json','png']:z.write(OUT/f'{STEM}.{ext}',f'{STEM}.{ext}')
        z.write(OUT/f'{STEM}-atlas.svg',f'{STEM}-atlas.svg')
    print(json.dumps({k:report[k] for k in ['sampled_hue_count','exact_colors_shared_with_v1']}))

if __name__=='__main__':main()
