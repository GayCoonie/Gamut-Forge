"""Interpret the owner's 3/3/3, 2/2/5, 3/2/4 sketch on an exact HSV grid.
No source-image pixel sampling, perceptual optimization, or duplicate filling.
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
STEM='hsv-three-tier-sketch'


def coverage(points):
    """Uniform midpoint sample of the retained S/V square, no color metric."""
    ticks=.14+(np.arange(400)+.5)/400*.86
    cloud=np.array(np.meshgrid(ticks,ticks)).reshape(2,-1).T
    ds=np.full(len(cloud),np.inf)
    for p in points:ds=np.minimum(ds,((cloud-p)**2).sum(axis=1))
    ds=np.sqrt(ds)
    return dict(mean_distance=float(ds.mean()),maximum_sampled_distance=float(ds.max()))


def main():
    a=.14;outer_top=[a,a+(1/3-a)/3,a+2*(1/3-a)/3]
    tiers=[dict(name='Core square',hue_count=64,hue_stride=1,lower=2/3,upper=1.,
                row_counts=[3,3,3],points=[[s,v] for v in [1,5/6,2/3] for s in [2/3,5/6,1]]),
           dict(name='Middle L band',hue_count=32,hue_stride=2,lower=1/3,upper=2/3,
                row_counts=[2,2,5],points=[[s,v] for v in [1,2/3] for s in [1/3,1/2]]+[[s,1/3] for s in [1/3,1/2,2/3,5/6,1]]),
           dict(name='Outer L band',hue_count=16,hue_stride=4,lower=a,upper=1/3,
                row_counts=[3,2,4],points=[[s,1] for s in outer_top]+[[s,1/2] for s in [outer_top[0],outer_top[2]]]+[[s,a] for s in [a,1/3,2/3,1]])]
    colors=[]
    for ti,tier in enumerate(tiers):
        assert len(tier['points'])==9
        for s,v in tier['points']:
            assert tier['lower']<=min(s,v)<=max(s,v)<=1
            assert not ti or min(s,v)<tier['upper']
        for i in range(0,64,tier['hue_stride']):
            for s,v in tier['points']:
                colors.append([int(np.floor(c*255+.5+1e-10)) for c in colorsys.hsv_to_rgb(i/64,s,v)])
    assert len(colors)==1008
    colors += [[i*17]*3 for i in range(16)]
    rgb=np.array(colors,dtype=np.uint8);assert len(np.unique(rgb,axis=0))==1024
    placement='Sketch interpretation: green rows 3/3/3; purple rows 2/2/5 at V=1,2/3,1/3; yellow rows 3/2/4 at V=1,1/2,0.14. Purple uses thirds/sixths; yellow top positions subdivide the retained 14%-to-1/3 band. No perceptual fitting or pruning.'
    geometry=dict(hue_step_degrees=5.625,hue_origin_degrees=0,tiers=tiers,ten_percent_grid=False,
        layout='sketch_rows',grayscale_values=[i/15 for i in range(16)],placement=placement,
        channel_encoding='HSV to sRGB code values; round nearest, half up, with floating tie correction.')
    (ROOT/'dist/palettes'/f'{STEM}-geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
    old=json.loads((ROOT/'dist/palettes/hsv-three-tier-64-geometry.json').read_text())
    comparison=dict(metric='Euclidean S/V coordinate distance on a uniform 400x400 midpoint grid over [0.14,1]^2; hue indices with all three tiers; not perceptual color error.',
        nested_ls=coverage([p for t in old['tiers'] for p in t['points']]),
        sketch_rows=coverage([p for t in tiers for p in t['points']]))
    report=dict(method=placement,hue_step_degrees=5.625,hue_counts=[64,32,16],chromatic_colors_per_tier=[576,288,144],
        gray_count=16,grayscale_rgb_step=17,saturation_value_bounds=[2/3,1/3,.14],
        minimum_separation_requirement=None,perceptual_pruning=False,hsv_coverage_comparison=comparison)
    js=b.export(rgb,STEM,'hsvThreeTierSketch','HSV three-tier · sketch spread · 1024',report)
    (ROOT/'dist'/f'{STEM}.js').write_text(js)
    with zipfile.ZipFile(ROOT/'dist/palettes'/f'{STEM}-package.zip','a',zipfile.ZIP_DEFLATED) as z:
        z.write(ROOT/'dist/palettes'/f'{STEM}-geometry.json',f'{STEM}-geometry.json')


if __name__=='__main__':main()
