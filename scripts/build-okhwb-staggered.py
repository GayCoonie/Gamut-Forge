"""OKHWB v2: Coonie's dot-count hue staggering on the unchanged v1 lattice.
Run with Python/NumPy/Pillow and Node. No pruning or color fitting.
"""
from pathlib import Path
import hashlib, html, importlib.util, json, math, subprocess, zipfile
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/palettes'
STEM = 'okhwb-staggered-1024'
KEY = 'okhwbStaggered1024'
spec = importlib.util.spec_from_file_location('triangle', ROOT/'scripts/build-okhwb-triangle.py')
triangle = importlib.util.module_from_spec(spec); spec.loader.exec_module(triangle)
# Each column runs from its white-facing cell to its black-facing cell.
# Columns have constant W+B=(n-1)/6; entries are yellow-dot counts.
# The zero in each column is the sketch's green, unchanged-hue cell.
DOTS = {6: [0,1,2,3,4,5], 5: [0,2,1,3,4], 4: [2,0,1,3],
        3: [1,0,2], 2: [0,1], 1: [0]}

def make_samples():
    samples = []
    for base in range(48):
        source = base*7.5
        # Preserve v1's stored W/B order for direct comparison.
        for j in range(6):
            for i in range(6-j):
                n = i+j+1; step = DOTS[n][j]; offset = step*7.5/n
                samples.append(dict(kind='hue', source_h=source, h=(source+offset)%360,
                    w=i/6, b=j/6, column_size=n, hue_step=step, hue_offset=offset))
    samples += [dict(kind='gray', source_h=0, h=0, w=i/15, b=1-i/15,
                     column_size=None, hue_step=None, hue_offset=0) for i in range(16)]
    return samples

def main():
    samples = make_samples()
    js = """const fs=require('fs'),vm=require('vm'),c={};vm.createContext(c);
vm.runInContext(fs.readFileSync('dist/vendor/ottosson-colorconversion.js','utf8'),c);
process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(p=>p.b===1?[0,0,0]:c.okhsv_to_srgb(p.h/360,Math.max(0,1-p.w/(1-p.b)),1-p.b))));"""
    raw = np.array(json.loads(subprocess.check_output(['node','-e',js],
        input=json.dumps(samples).encode(), cwd=ROOT)))
    assert np.isfinite(raw).all()
    rgb = np.floor(np.clip(raw,0,255)+.5).astype(np.uint8)
    assert len(rgb) == len(set(map(tuple,rgb))) == 1024
    old = json.loads((OUT/'okhwb-triangle-1024.json').read_text())
    colors = ['#'+bytes(c).hex() for c in rgb]
    assert colors[-16:] == old['colors'][-16:]
    assert all(c==old['colors'][i] for i,(c,p) in enumerate(zip(colors,samples))
               if p['kind']=='gray' or p['hue_step']==0)
    report = dict(method='Keep v1 W/B coordinates and 48 vivid anchors. Within each constant-W+B column, assign the sketch dot-count permutation and H=(source H + dot count * 7.5 / column size) modulo 360. Preserve all sixteen grays.',
        source_sketch='User drawing 8b2da0ca-ce5e-4813-b4d8-7e2aa38fa489.png; green cells have zero offset, yellow dots encode positive offset steps. Dot counts are not extra samples.',
        interpretation='Columns are read from the white-facing end toward black. Use all n equally spaced offsets 0..(n-1)*7.5/n in each n-cell column; the next source hue is excluded. The final drawing takes precedence over the earlier tentative row counts.',
        hue_step_degrees=7.5, source_hue_count=48, points_per_source_hue=21,
        sampled_hue_count=len({p['h'] for p in samples if p['kind']=='hue'}),
        offset_columns=[dict(cells=n,white_plus_black=(n-1)/6,
            steps=DOTS[n],degrees_per_step=7.5/n) for n in range(6,0,-1)],
        white_black_step=1/6, base_palette='okhwb-triangle-1024',
        exact_colors_shared_with_v1=len(set(colors)&set(old['colors'])),
        conversion=old['report']['conversion'], source=old['report']['source'],
        reference_sha256=hashlib.sha256((ROOT/'dist/vendor/ottosson-colorconversion.js').read_bytes()).hexdigest(),
        maximum_boundary_excursion_bytes=float(max(0,-raw.min(),raw.max()-255)),
        perceptual_pruning=False, minimum_separation_requirement=None, fillers=0,
        individual_rgb_adjustments=0,
        diagram='Source-hue panels, not constant-actual-hue sections: cells keep v1 W/B coordinates while their hues vary. Polygons indicate nearest-sample regions in the drawn triangle, not perceptual distance or gamut volume.',
        grayscale_axis=old['report']['grayscale_axis'])
    bundle = triangle.base.export(rgb, STEM, KEY, 'OKHWB v2 · staggered hues · 1024', report)
    (ROOT/'dist/okhwb-staggered.js').write_text(bundle)
    data = json.loads((OUT/f'{STEM}.json').read_text())
    for sample,c in zip(samples,colors): sample['hex']=c
    data['samples'] = samples
    (OUT/f'{STEM}.json').write_text(json.dumps(data,indent=2)+'\n')
    geometry = triangle.cells([triangle.point(p['w'],p['b']) for p in samples[:21]+samples[-16:]])
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1320" height="1940" viewBox="0 0 1320 1940" role="img" aria-labelledby="title desc">',
        '<title id="title">OKHWB v2: staggered hue triangles, 1024 colors</title>',
        '<desc id="desc">48 source-hue panels with unchanged W/B geometry and dot-count hue offsets. Each panel contains several actual hues. The 16 grays are stored once.</desc>',
        '<style>.offset-markers{display:none;pointer-events:none}</style>',
        '<rect width="1320" height="1940" fill="#121018"/>',
        '<g font-family="sans-serif" fill="#eae5f0"><text x="24" y="36" font-size="25">OKHWB v2 · staggered hues · 1024</text><text x="24" y="62" font-size="15">48 source hues × 21 colored samples + 16 grays · regular W/B geometry, interleaved hues</text></g>']
    for hue in range(48):
        svg.append(f'<g data-hue="{hue*7.5}" transform="translate({hue%6*220},{80+hue//6*230})">')
        svg.append(f'<text x="20" y="23" fill="#eae5f0" font-family="sans-serif" font-size="16">Source {hue*7.5:g}°</text>')
        entries = samples[hue*21:(hue+1)*21]+samples[-16:]
        for cell,(poly,p) in enumerate(zip(geometry,entries)):
            label = f'{p["hex"]} · source {hue*7.5:g}° · H {p["h"]:g}° · +{p["hue_offset"]:g}° · W {p["w"]:.4f} · B {p["b"]:.4f}' if p['kind']=='hue' else f'{p["hex"]} · shared gray · W {p["w"]:.4f} · B {p["b"]:.4f}'
            points = ' '.join(f'{a:.5f},{b:.5f}' for a,b in poly)
            svg.append(f'<polygon data-cell="{cell}" points="{points}" fill="{p["hex"]}" stroke="#121018" stroke-width="0.45"><title>{html.escape(label)}</title></polygon>')
            if p['kind']=='hue':
                # Position markers inside the clipped cell, including edge vertices.
                cx,cy = np.mean(poly,axis=0)
                count=p['hue_step']; color='#25b57c' if count==0 else '#ffdf28'
                svg.append(f'<g class="offset-markers" data-step="{count}">')
                for dot in range(max(1,count)):
                    angle=2*math.pi*dot/max(1,count)
                    x=cx+(3.2*math.cos(angle) if count>1 else 0)
                    y=cy+(3.2*math.sin(angle) if count>1 else 0)
                    svg.append(f'<circle cx="{x:.5f}" cy="{y:.5f}" r="1.4" fill="{color}" stroke="#19151f" stroke-width="0.25"/>')
                svg.append('</g>')
        svg.append('<g fill="#bfb6cc" font-family="sans-serif" font-size="12"><text x="4" y="38">W</text><text x="4" y="213">B</text><text x="167" y="124">Hue</text></g></g>')
    svg.append('<text x="24" y="1930" fill="#bfb6cc" font-family="sans-serif" font-size="14">Source-hue panels contain shifted hues. Gray edge repeated for orientation; all colors stored once.</text></svg>')
    (OUT/f'{STEM}-atlas.svg').write_text('\n'.join(svg)+'\n')
    with zipfile.ZipFile(OUT/f'{STEM}-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for ext in ['txt','gpl','kpl','json','png']: z.write(OUT/f'{STEM}.{ext}',f'{STEM}.{ext}')
        z.write(OUT/f'{STEM}-atlas.svg',f'{STEM}-atlas.svg')
    print(json.dumps({k:report[k] for k in ['sampled_hue_count','exact_colors_shared_with_v1']}))

if __name__=='__main__':main()
