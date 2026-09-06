"""Regular OKHWB lattice: 48*21 colored samples + 16 shared grays.
Run with Python/NumPy/Pillow and Node. No pruning, fitting or palette fillers.
"""
from pathlib import Path
import hashlib,html,importlib.util,json,math,subprocess,zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/palettes'
STEM='okhwb-triangle-1024';KEY='okhwbTriangle1024'
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-random-strata.py')
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)

def point(w,b):
    # Equilateral coordinate triangle: white upper left, black lower left.
    return np.array([20+(1-w-b)*80*math.sqrt(3),40*w+200*b+120*(1-w-b)])

def cells(points):
    """Exact planar nearest-sample regions clipped to the coordinate triangle."""
    result=[]
    for i,p in enumerate(points):
        poly=[point(1,0),point(0,1),point(0,0)]
        for j,q in enumerate(points):
            if i==j:continue
            n=q-p;k=(q@q-p@p)/2;out=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                fa=a@n-k;fb=b@n-k
                if fa<=1e-9:out.append(a)
                if (fa<0<fb) or (fb<0<fa):out.append(a+(b-a)*fa/(fa-fb))
            poly=out
            if not poly:break
        result.append(poly)
    return result

def main():
    lattice=[(i/6,j/6) for j in range(6) for i in range(6-j)]
    grays=[(i/15,1-i/15) for i in range(16)]
    samples=[dict(kind='hue',h=h*7.5,w=w,b=b) for h in range(48) for w,b in lattice]
    samples += [dict(kind='gray',h=0,w=w,b=b) for w,b in grays]
    js="""const fs=require('fs'),vm=require('vm'),c={};vm.createContext(c);
vm.runInContext(fs.readFileSync('dist/vendor/ottosson-colorconversion.js','utf8'),c);
process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(p=>p.b===1?[0,0,0]:c.okhsv_to_srgb(p.h/360,Math.max(0,1-p.w/(1-p.b)),1-p.b))));"""
    raw=np.array(json.loads(subprocess.check_output(['node','-e',js],input=json.dumps(samples).encode(),cwd=ROOT)))
    assert np.isfinite(raw).all()
    rgb=np.floor(np.clip(raw,0,255)+.5).astype(np.uint8)
    assert len(rgb)==len(set(map(tuple,rgb)))==1024
    assert tuple(rgb[-16])==(0,0,0) and tuple(rgb[-1])==(255,255,255)
    report=dict(method='48 OKHWB hue slices at 7.5 degrees. W=i/6 and B=j/6 for nonnegative integers i+j<6: 21 chromatic points per hue. Sixteen shared grays at W=i/15, B=1-i/15 complete 1024 colors.',
        hue_step_degrees=7.5,hue_count=48,points_per_hue=21,white_black_step=1/6,
        lattice=[dict(w=w,b=b) for w,b in lattice],grayscale=[dict(w=w,b=b) for w,b in grays],
        conversion='OKHSV V=1-B; S=1-W/(1-B). B=1 is explicitly black. Use Ottosson reference conversion, clamp small numerical boundary excursions, round nearest sRGB byte half up.',
        source='https://bottosson.github.io/posts/colorpicker/#okhwb',
        reference_sha256=hashlib.sha256((ROOT/'dist/vendor/ottosson-colorconversion.js').read_bytes()).hexdigest(),
        maximum_boundary_excursion_bytes=float(max(0,-raw.min(),raw.max()-255)),
        perceptual_pruning=False,minimum_separation_requirement=None,fillers=0,individual_rgb_adjustments=0,
        diagram='Equilateral OKHWB coordinate triangles. White, black and the vivid hue are the vertices. Polygons are nearest-sample regions in the drawn triangle, not measured perceptual distances or gamut volumes. Shared grayscale is repeated visually but stored once.',
        grayscale_axis='Even steps in W along W+B=1, equivalent to even OKHSV V steps.')
    js=base.export(rgb,STEM,KEY,'OKHWB · regular triangles · 1024',report)
    (ROOT/'dist/okhwb-triangle.js').write_text(js)
    path=OUT/f'{STEM}.json';data=json.loads(path.read_text())
    for p,c in zip(samples,data['colors']):p['hex']=c
    data['samples']=samples;path.write_text(json.dumps(data,indent=2)+'\n')
    geometry=cells([point(w,b) for w,b in lattice+grays])
    areas=[abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))/2) for poly in geometry]
    assert abs(sum(areas)-6400*math.sqrt(3))<1e-6 and min(areas)>0
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1320" height="1940" viewBox="0 0 1320 1940" role="img" aria-labelledby="title desc">',
        '<title id="title">OKHWB regular triangle palette: 1024 colors</title>',
        '<desc id="desc">48 hue triangles with 21 colored samples and a repeated shared 16-gray boundary. Cells indicate coordinate regions, not perceptual distance.</desc>',
        '<rect width="1320" height="1940" fill="#121018"/>',
        '<g font-family="sans-serif" fill="#eae5f0"><text x="24" y="36" font-size="25">OKHWB · regular triangles · 1024</text><text x="24" y="62" font-size="15">48 hues × 21 colored samples + 16 shared grays · W / B increments of 1/6</text></g>']
    for hue in range(48):
        svg.append(f'<g data-hue="{hue*7.5}" transform="translate({hue%6*220},{80+hue//6*230})">')
        svg.append(f'<text x="20" y="23" fill="#eae5f0" font-family="sans-serif" font-size="16">{hue*7.5:g}°</text>')
        entries=samples[hue*21:(hue+1)*21]+samples[-16:]
        for poly,p in zip(geometry,entries):
            label=f'{p["hex"]} · H {hue*7.5:g}° · W {p["w"]:.4f} · B {p["b"]:.4f}'+(' · shared gray' if p['kind']=='gray' else '')
            points=' '.join(f'{a:.5f},{b:.5f}' for a,b in poly)
            svg.append(f'<polygon points="{points}" fill="{p["hex"]}" stroke="#121018" stroke-width="0.45"><title>{html.escape(label)}</title></polygon>')
        svg.append('<g fill="#bfb6cc" font-family="sans-serif" font-size="12"><text x="4" y="38">W</text><text x="4" y="213">B</text><text x="167" y="124">Hue</text></g></g>')
    svg.append('<text x="24" y="1930" fill="#bfb6cc" font-family="sans-serif" font-size="14">Gray edge shown on each slice for orientation; its colors occur only once in the palette.</text></svg>')
    (OUT/f'{STEM}-atlas.svg').write_text('\n'.join(svg)+'\n')
    with zipfile.ZipFile(OUT/f'{STEM}-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for ext in ['txt','gpl','kpl','json','png']:z.write(OUT/f'{STEM}.{ext}',f'{STEM}.{ext}')
        z.write(OUT/f'{STEM}-atlas.svg',f'{STEM}-atlas.svg')
    print('Atlas cell areas cover the triangle exactly; 1024 unique colors exported.')

if __name__=='__main__':main()
