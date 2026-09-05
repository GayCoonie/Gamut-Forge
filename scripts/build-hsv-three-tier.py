"""64/32/16 hue HSV experiment: square + two filled L bands + 16 grays.

The main version has three three-point Ls per added band, at equally spaced
levels, excluding the previous boundary. All placement uses ordinary S/V
coordinates, never perceptual color fitting.
"""
from pathlib import Path
import colorsys
import importlib.util
import json
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('exports',ROOT/'scripts/build-critter-palettes.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
STEM='hsv-three-tier-64'


def band_points(a,bound):
    levels=[bound+(a-bound)*i/3 for i in (1,2,3)]
    points=np.array([[s,v] for q in levels for s,v in [(q,1),(q,q),(1,q)]])
    assert len(np.unique(points,axis=0))==9
    assert np.all(points>=a) and np.all(points<=1)
    assert np.all(points.min(axis=1)<bound)
    return points.tolist()


def grid_band(a,bound):
    # All eligible S/V pairs on the ten-percent lattice. Select nine by exact
    # Euclidean farthest-point placement, then improve uniform-lattice coverage
    # with medoid swaps. Preserve the three illustrated extreme corners.
    ticks=np.arange(round(a*10),11)/10
    cloud=np.array(np.meshgrid(ticks,ticks)).reshape(2,-1).T
    cloud=cloud[np.minimum(cloud[:,0],cloud[:,1])<bound-1e-9]
    D=((cloud[:,None,:]-cloud[None,:,:])**2).sum(axis=2)
    chosen=[int(np.argmin(((cloud-p)**2).sum(axis=1))) for p in [(a,a),(a,1),(1,a)]]
    while len(chosen)<9:
        near=D[:,chosen].min(axis=1);near[chosen]=-1
        chosen.append(int(np.argmax(near)))
    # Exhaustive one-point swaps optimize geometry only, not image/color fit.
    for _ in range(100):
        old=float(D[:,chosen].min(axis=1).sum());best=None
        for pos in range(3,9):
            for idx in range(len(cloud)):
                if idx in chosen:continue
                trial=chosen.copy();trial[pos]=idx
                score=float(D[:,trial].min(axis=1).sum())
                if score<old-1e-12 and (best is None or score<best[0]-1e-12):best=score,pos,idx
        if best is None:break
        chosen[best[1]]=best[2]
    return cloud[chosen].tolist()


def build(linear=False):
    stem='hsv-three-tier-10' if linear else STEM
    levels=[.8,.9,1.] if linear else [2/3,5/6,1.]
    bounds=[.8,.4,.1] if linear else [2/3,1/3,.14]
    sampler=grid_band if linear else band_points
    tiers=[dict(name='Core square',hue_count=64,hue_stride=1,lower=bounds[0],upper=1.,
                points=[[s,v] for v in levels for s in levels]),
           dict(name='Middle L band',hue_count=32,hue_stride=2,lower=bounds[1],upper=bounds[0],
                points=sampler(bounds[1],bounds[0])),
           dict(name='Outer L band',hue_count=16,hue_stride=4,lower=bounds[2],upper=bounds[1],
                points=sampler(bounds[2],bounds[1]))]
    colors=[]
    for tier in tiers:
        for i in range(0,64,tier['hue_stride']):
            for s,v in tier['points']:
                rgb=colorsys.hsv_to_rgb(i/64,s,v)
                # Resolve floating representations just below an exact .5 tie.
                colors.append([int(np.floor(ch*255+.5+1e-10)) for ch in rgb])
    assert len(colors)==1008
    colors += [[i*17]*3 for i in range(16)]
    rgb=np.array(colors,dtype=np.uint8)
    assert len(np.unique(rgb,axis=0))==1024, 'No silent duplicates or filler colors.'
    placement=('Core: 80/90/100% grid. L bands: nine samples on the 10% HSV lattice, using Euclidean farthest-point initialization and uniform-lattice medoid refinement; three outer corners fixed. Bounds 80/40/10%. No perceptual fitting or pruning.' if linear else
        'Core: exact 3x3 endpoint-inclusive grid. Each added band: three nested Ls, with samples at (q,1), (q,q), (1,q). Levels divide the distance from the previous boundary to the new boundary into thirds, excluding the previous boundary. No perceptual optimization or pruning.')
    geometry=dict(hue_step_degrees=360/64,hue_origin_degrees=0,tiers=tiers,ten_percent_grid=linear,
        grayscale_values=[i/15 for i in range(16)],
        placement=placement,
        channel_encoding='HSV to sRGB code values; round nearest, half up.')
    (ROOT/'dist/palettes'/f'{stem}-geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
    report=dict(method=geometry['placement'],hue_step_degrees=360/64,hue_counts=[64,32,16],
        chromatic_colors_per_tier=[576,288,144],gray_count=16,
        saturation_value_bounds=bounds,grayscale_rgb_step=17,
        minimum_separation_requirement=None,perceptual_pruning=False)
    js=b.export(rgb,stem,'hsvThreeTier10' if linear else 'hsvThreeTier64',
        'HSV three-tier · 10% grid · 1024' if linear else 'HSV three-tier · 64/32/16 hues · 1024',report)
    (ROOT/'dist'/f'{stem}.js').write_text(js)
    with zipfile.ZipFile(ROOT/'dist/palettes'/f'{stem}-package.zip','a',zipfile.ZIP_DEFLATED) as z:
        z.write(ROOT/'dist/palettes'/f'{stem}-geometry.json',f'{stem}-geometry.json')
    return geometry,rgb


if __name__=='__main__':
    build()
    build(linear=True)
