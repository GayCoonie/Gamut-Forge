"""Martian expansion v2: HSLuv ramps around 120 exact Warren Mars anchors.
Use the official HSLuv conversion; retain the source's ring-specific hue bends.
"""
from pathlib import Path
import hashlib,html,importlib.util,json,math,zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/palettes'
STEM='martian-expansion-1024';KEY='martianExpansion1024'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=module('base',ROOT/'scripts/build-random-strata.py')
uv=module('hsluv',ROOT/'scripts/vendor/hsluv.py')
SOURCE=ROOT/'scripts/sources/martian-step7.json'

def hsluv(rgb):return np.array(uv.rgb_to_hsluv([x/255 for x in rgb]))
def blend(a,b,t):
    d=(b[0]-a[0]+180)%360-180
    return np.array([(a[0]+d*t)%360,(1-t)*a[1]+t*b[1],(1-t)*a[2]+t*b[2]])
def rgb_float(p):return np.array(uv.hsluv_to_rgb(p))
def encode(p):
    rgb=rgb_float(p)
    assert np.all(rgb>=-1e-8) and np.all(rgb<=1+1e-8),rgb
    return np.floor(np.clip(rgb,0,1)*255+.5).astype(np.uint8)
def muted(p,tint_h,factor):
    q=p.copy();q[0]=(p[0]+((tint_h-p[0]+180)%360-180)*(1-factor))%360
    q[1]*=factor
    return q

def vivid(h):
    # Find the gamut cusp: greatest available CIELUV chroma at this hue.
    # A coarse global scan brackets the maximum; golden-section refines it.
    levels=np.linspace(.01,99.99,1001)
    i=max(range(len(levels)),key=lambda i:uv._max_chroma_for_lh(levels[i],h))
    lo,hi=levels[max(0,i-1)],levels[min(len(levels)-1,i+1)]
    ratio=(math.sqrt(5)-1)/2
    for _ in range(80):
        a=hi-ratio*(hi-lo);b=lo+ratio*(hi-lo)
        if uv._max_chroma_for_lh(a,h)<uv._max_chroma_for_lh(b,h):lo=a
        else:hi=b
    return np.array([h,100.,(lo+hi)/2])

def build():
    source=json.loads(SOURCE.read_text());anchors=source['colors']
    original=[list(reversed(anchors[i*5:i*5+5])) for i in range(24)]
    families=[];samples=[]
    for f in range(48):
        a=f//2;b=(a+1)%24;t=.5 if f%2 else 0
        nodes=[blend(hsluv(p['rgb']),hsluv(q['rgb']),t) for p,q in zip(original[a],original[b])]
        peaks=[next(p for p in original[index] if p['primary_exemplar']) for index in [a,b]]
        if f%2:
            peak=vivid(blend(hsluv(peaks[0]['rgb']),hsluv(peaks[1]['rgb']),t)[0])
            peak_ring=min(range(5),key=lambda r:abs(nodes[r][2]-peak[2]))
            nodes[peak_ring]=peak
        else:
            peak_ring=next(i for i,p in enumerate(original[a]) if p['primary_exemplar'])
            peak=nodes[peak_ring]
        def ramp(r):
            j=min(int(r),3);return blend(nodes[j],nodes[j+1],r-j)
        label_a=next(p['name'] for p in original[a] if p['primary_exemplar'])
        label_b=next(p['name'] for p in original[b] if p['primary_exemplar'])
        label=label_a if f%2==0 else label_a+' / '+label_b
        families.append(dict(index=f,label=label,source_spokes=[a] if f%2==0 else [a,b],interstitial=bool(f%2),vivid_ring=peak_ring,vivid_hex='#'+bytes(encode(peak)).hex()))
        entries=[]
        # Relocate one former outer tint between the two added inner shades.
        for scale in [.35,.5,.65]:
            p=nodes[0].copy();p[2]*=scale;entries.append(dict(hsluv=p,kind='deeper-shade',lightness_scale=scale))
        for r in np.arange(0,4.01,.5):
            p=ramp(r);entry=dict(hsluv=p,kind='ramp-interpolation',ring_position=float(r))
            if f%2==0 and r.is_integer():entry.update(kind='source-anchor',source_name=original[a][int(r)]['name'],source_hex=original[a][int(r)]['hex'])
            if f%2 and r==peak_ring:entry['kind']='new-vivid-exemplar'
            entries.append(entry)
        p=nodes[-1].copy();p[2]+=(100-p[2])*.5
        entries.append(dict(hsluv=p,kind='lighter-tint',white_lightness_fraction=.5))
        for r in [.5,1.5,2.5,3.5]:
            p=ramp(r)
            for factor in [.4,.7]:
                q=muted(p,nodes[-1][0],factor)
                entries.append(dict(hsluv=q,kind='muted-companion',ring_position=r,saturation_scale=factor,target_lightness=float(p[2])))
        assert len(entries)==21
        for cell,entry in enumerate(entries):
            p=entry.pop('hsluv');color='#'+bytes(encode(p)).hex()
            if entry['kind']=='source-anchor':assert color==entry['source_hex']
            samples.append(dict(family=f,cell=cell,hex=color,hsluv=list(map(float,p)),**entry))
    for i in range(16):
        L=i*100/15;color='#'+bytes(encode([0,0,L])).hex()
        samples.append(dict(family=None,cell=i,kind='gray',target_lab_lightness=L,hsluv=[0.,0.,L],hex=color))
    colors=[p['hex'] for p in samples]
    assert len(colors)==len(set(colors))==1024, f'{len(set(colors))} unique colors'
    assert {p['hex'] for p in anchors}<=set(colors)
    return source,families,samples

def main():
    source,families,samples=build();rgb=np.array([list(bytes.fromhex(p['hex'][1:])) for p in samples],dtype=np.uint8)
    report=dict(version=2,interpolation_space='HSLuv',
        method='HSLuv expansion of the final Step 7 RGB table, retaining all 120 exact anchors. Interpolate 24 intermediate families in ring-specific HSLuv; add gamut-cusp exemplars, perceptual shade/tint subdivisions and constant-lightness muted companions. Three added inner shades and one outer tint replace the v1 two-inner/two-outer allocation.',
        attribution='Source wheel and 120 named RGB anchors: Warren Mars. HSLuv: Alexei Boronine and contributors. Expansion and interpolation rules: Gamut Forge. Independent extension, not an official Martian wheel.',
        source_url=source['source'],source_section=source['source_section'],source_data_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        color_space_reference='https://www.hsluv.org/math/',conversion_implementation='https://github.com/hsluv/hsluv-python',conversion_version=uv.__version__,conversion_sha256=hashlib.sha256((ROOT/'scripts/vendor/hsluv.py').read_bytes()).hexdigest(),
        new_vivid_exemplar_count=24,total_vivid_exemplar_count=48,
        vivid_rule='Interpolate source exemplar HSLuv hue by the shortest arc, find the maximum CIELUV chroma over lightness at that hue, and place this gamut cusp at the closest of the five ring lightnesses before subdivision. Original exemplars are retained exactly.',
        source_anchor_count=120,source_anchor_count_retained=120,hue_family_count=48,colors_per_family=21,
        ramp_samples_per_family=13,muted_samples_per_family=8,source_value_policy=source['value_policy'],
        ramp_rule='Interpolate shortest-arc HSLuv hue, relative-gamut saturation and CIELUV lightness between the five source rings and at their four midpoints. Three inner shades use 0.35, 0.50 and 0.65 times the darkest L*. One outer tint is halfway from the lightest L* to 100. Extensions retain the endpoint hue and HSLuv saturation.',
        muted_rule='At ring coordinates 0.5, 1.5, 2.5 and 3.5, multiply HSLuv S by 0.4 and 0.7 at unchanged L*. Bend H toward the lightest-tint H by 1 minus the saturation multiplier. This continuation of source hue bends is our extension.',
        gray_rule='16 neutrals evenly spaced in L*: 0,100/15,...,100, using HSLuv conversion and nearest-byte rounding.',
        perceptual_pruning=False,minimum_separation_requirement=None,fillers=0,individual_rgb_adjustments=0,
        diagram='Ring position follows the authored shade/tint sequence, not globally constant lightness. Three added dark rings, nine source/interpolated rings, one added light ring. Outlined cells are exact source anchors.')
    bundle=base.export(rgb,STEM,KEY,'Martian expansion v2 · HSLuv ramps · 1024',report)
    (ROOT/'dist/martian-expansion.js').write_text(bundle)
    data=json.loads((OUT/f'{STEM}.json').read_text());data.update(families=families,samples=samples,source_anchors=source['colors'])
    (OUT/f'{STEM}.json').write_text(json.dumps(data,indent=2)+'\n')
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1380" viewBox="0 0 1440 1380" role="img" aria-labelledby="title desc">',
        '<title id="title">Martian expansion: 1024 colors</title><desc id="desc">48 artist-derived hue families: 13 shades and tints each, eight muted companions each, and sixteen neutral grays. White outlines identify Warren Mars’s 120 original RGB anchors.</desc>',
        '<rect width="1440" height="1380" fill="#121018"/>',
        '<g fill="#eae5f0" font-family="sans-serif"><text x="40" y="42" font-size="28">Martian expansion v2 · HSLuv ramps · 1024</text><text x="40" y="72" font-size="16">120 original anchors preserved · 24 original + 24 intermediate hue families</text></g>']
    def point(r,a):return (720+r*math.cos(a),550+r*math.sin(a))
    for family in families:
        f=family['index'];a=(f/48-.25)*2*math.pi-math.pi/48;b=a+2*math.pi/48
        for ring in range(13):
            p=samples[f*21+ring];r0=110+ring*25;r1=r0+25
            x0,y0=point(r0,a);x1,y1=point(r1,a);x2,y2=point(r1,b);x3,y3=point(r0,b)
            label=f'{p["hex"]} · {family["label"]} · {p.get("source_name",p["kind"])}'
            path=f'M{x0:.5f},{y0:.5f} L{x1:.5f},{y1:.5f} A{r1},{r1} 0 0 1 {x2:.5f},{y2:.5f} L{x3:.5f},{y3:.5f} A{r0},{r0} 0 0 0 {x0:.5f},{y0:.5f} Z'
            svg.append(f'<path data-index="{f*21+ring}" d="{path}" fill="{p["hex"]}" stroke="{"#ffffff" if p["kind"]=="source-anchor" else "#121018"}" stroke-width="{1.1 if p["kind"]=="source-anchor" else .5}"><title>{html.escape(label)}</title></path>')
        if not family['interstitial']:
            x,y=point(460,(a+b)/2);anchor='start' if math.cos((a+b)/2)>.15 else 'end' if math.cos((a+b)/2)<-.15 else 'middle';svg.append(f'<text x="{x:.4f}" y="{y:.4f}" text-anchor="{anchor}" dominant-baseline="middle" fill="#d3c7dc" font-family="sans-serif" font-size="12">{html.escape(family["label"])}</text>')
    svg.append('<g fill="#d3c7dc" text-anchor="middle" font-family="sans-serif"><text x="720" y="534" font-size="19">48 × 13</text><text x="720" y="560" font-size="14">shade / tint ramps</text><text x="720" y="583" font-size="12">white outlines: source</text></g>')
    svg.append('<text x="48" y="1060" fill="#eae5f0" font-family="sans-serif" font-size="20">Muted companions · four tones, two saturation levels · same 48-family order</text>')
    for row in range(8):
        for f in range(48):
            index=f*21+13+row;p=samples[index]
            label=f'{p["hex"]} · {families[f]["label"]} · ring {p["ring_position"]} · saturation ×{p["saturation_scale"]}'
            svg.append(f'<rect data-index="{index}" x="{48+f*28}" y="{1080+row*27}" width="27" height="26" fill="{p["hex"]}"><title>{html.escape(label)}</title></rect>')
    for i,p in enumerate(samples[-16:]):svg.append(f'<rect data-index="{1008+i}" x="{48+i*84}" y="1320" width="83" height="28" fill="{p["hex"]}"><title>{p["hex"]} · shared gray</title></rect>')
    svg.append('<text x="48" y="1370" fill="#bfb6cc" font-family="sans-serif" font-size="12">Original anchors: Warren Mars · New interpolation and muted companions: Gamut Forge · ring position is not constant lightness</text></svg>')
    (OUT/f'{STEM}-atlas.svg').write_text('\n'.join(svg)+'\n')
    with zipfile.ZipFile(OUT/f'{STEM}-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for ext in ['txt','gpl','kpl','json','png']:z.write(OUT/f'{STEM}.{ext}',f'{STEM}.{ext}')
        z.write(OUT/f'{STEM}-atlas.svg',f'{STEM}-atlas.svg')
    print('120 published anchors retained; 624 ramp colors + 384 muted companions + 16 grays.')
if __name__=='__main__':main()
