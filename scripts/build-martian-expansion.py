"""An attributed 1024-color extension of Warren Mars's final 120 RGB anchors.
Preserve source anchors; interpolate their ring-specific HSV corrections.
The extra shades, tints, and equal-luminance muted companions are our extension.
"""
from pathlib import Path
import colorsys,hashlib,html,importlib.util,json,math,zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/palettes'
STEM='martian-expansion-1024';KEY='martianExpansion1024'
spec=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-random-strata.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
SOURCE=ROOT/'scripts/sources/martian-step7.json'

def hsv(rgb):
    h,s,v=colorsys.rgb_to_hsv(*(x/255 for x in rgb));return np.array([h*360,s,v])
def blend(a,b,t):
    d=(b[0]-a[0]+180)%360-180
    return np.array([(a[0]+d*t)%360,(1-t)*a[1]+t*b[1],(1-t)*a[2]+t*b[2]])
def rgb_float(hsv):return np.array(colorsys.hsv_to_rgb(hsv[0]/360,hsv[1],hsv[2]))
def encode(hsv):return np.floor(np.clip(rgb_float(hsv),0,1)*255+.5).astype(np.uint8)
def luminance(rgb):
    rgb=np.array(rgb);lin=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    return float(lin@np.array([.2126,.7152,.0722]))
def muted(p,tint_h,factor):
    h=(p[0]+((tint_h-p[0]+180)%360-180)*(1-factor))%360
    s=p[1]*factor;target=luminance(rgb_float(p));lo,hi=0.,1.
    assert luminance(rgb_float([h,s,hi]))>=target-1e-10
    for _ in range(40):
        mid=(lo+hi)/2
        if luminance(rgb_float([h,s,mid]))<target:lo=mid
        else:hi=mid
    return np.array([h,s,(lo+hi)/2]),target

def lightness(Y):return 116*Y**(1/3)-16 if Y>216/24389 else (24389/27)*Y

def build():
    source=json.loads(SOURCE.read_text());anchors=source['colors']
    # Reorder the published light-to-dark table to dark-to-light ramps.
    original=[list(reversed(anchors[i*5:i*5+5])) for i in range(24)]
    families=[];samples=[]
    for f in range(48):
        a=f//2;b=(a+1)%24;t=.5 if f%2 else 0
        nodes=[blend(hsv(p['rgb']),hsv(q['rgb']),t) for p,q in zip(original[a],original[b])]
        peaks=[next(p for p in original[index] if p['primary_exemplar']) for index in [a,b]]
        peak_h=blend(hsv(peaks[0]['rgb']),hsv(peaks[1]['rgb']),t)[0]
        peak=np.array([peak_h,1.,1.])
        if f%2:
            target_L=lightness(luminance(rgb_float(peak)))
            peak_ring=min(range(5),key=lambda r:abs(lightness(luminance(rgb_float(nodes[r])))-target_L))
            nodes[peak_ring]=peak
        else:peak_ring=next(i for i,p in enumerate(original[a]) if p['primary_exemplar'])
        def ramp(r):
            j=min(int(r),3);return blend(nodes[j],nodes[j+1],r-j)
        label_a=next(p['name'] for p in original[a] if p['primary_exemplar'])
        label_b=next(p['name'] for p in original[b] if p['primary_exemplar'])
        label=label_a if f%2==0 else label_a+' / '+label_b
        families.append(dict(index=f,label=label,source_spokes=[a] if f%2==0 else [a,b],interstitial=bool(f%2),vivid_ring=peak_ring,vivid_hex='#'+bytes(encode(peak)).hex()))
        entries=[]
        for scale in [.35,.65]:
            p=nodes[0].copy();p[2]*=scale;entries.append(dict(hsv=p,kind='deeper-shade',value_scale=scale))
        for r in np.arange(0,4.01,.5):
            p=ramp(r);entry=dict(hsv=p,kind='ramp-interpolation',ring_position=float(r))
            if f%2==0 and r.is_integer():entry.update(kind='source-anchor',source_name=original[a][int(r)]['name'],source_hex=original[a][int(r)]['hex'])
            if f%2 and r==peak_ring:entry['kind']='new-vivid-exemplar'
            entries.append(entry)
        for scale in [.75,.5]:
            p=nodes[-1].copy();p[1]*=scale;entries.append(dict(hsv=p,kind='lighter-tint',saturation_scale=scale))
        for r in [.5,1.5,2.5,3.5]:
            p=ramp(r)
            for factor in [.4,.7]:
                q,target=muted(p,nodes[-1][0],factor)
                entries.append(dict(hsv=q,kind='muted-companion',ring_position=r,saturation_scale=factor,target_relative_luminance=target))
        assert len(entries)==21
        for cell,entry in enumerate(entries):
            p=entry.pop('hsv');rgb=encode(p);color='#'+bytes(rgb).hex()
            if entry['kind']=='source-anchor':assert color==entry['source_hex']
            samples.append(dict(family=f,cell=cell,hex=color,hsv=list(map(float,p)),**entry))
    for i in range(16):
        L=i*100/15;Y=((L+16)/116)**3 if L>8 else L/(24389/27)
        v=12.92*Y if Y<=.0031308 else 1.055*Y**(1/2.4)-.055
        byte=int(math.floor(v*255+.5));samples.append(dict(family=None,cell=i,kind='gray',target_lab_lightness=L,hex='#'+bytes([byte]*3).hex()))
    colors=[p['hex'] for p in samples]
    assert len(colors)==len(set(colors))==1024, f'{len(set(colors))} unique colors'
    assert {p['hex'] for p in anchors}<=set(colors)
    return source,families,samples

def main():
    source,families,samples=build();rgb=np.array([list(bytes.fromhex(p['hex'][1:])) for p in samples],dtype=np.uint8)
    report=dict(method='An independent expansion using the final Step 7 RGB table as 120 exact anchors. Add 24 interstitial hue families by shortest-arc HSV interpolation at each original ring separately. Restore one full-saturation, full-value exemplar per intermediate family at the closest source-ring lightness before interpolation. Build 13 shade/tint levels and eight equal-luminance muted companions per family, plus sixteen neutral grays.',
        attribution='Source wheel and 120 named RGB anchors: Warren Mars. Expansion, interpolation and muted-color rules: Gamut Forge. Not an official Martian wheel or a validated new perceptual color space.',
        source_url=source['source'],source_section=source['source_section'],source_data_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        new_vivid_exemplar_count=24,total_vivid_exemplar_count=48,
        vivid_rule='For each intermediate family, interpolate the two source exemplar hue angles and set S=V=1. Place it at the closest of the five ring lightnesses in CIELAB before interpolating the nine core ramp samples. This is our numerical extension of the final-revision placement principle.',
        source_anchor_count=120,source_anchor_count_retained=120,hue_family_count=48,colors_per_family=21,
        ramp_samples_per_family=13,muted_samples_per_family=8,
        source_value_policy=source['value_policy'],
        ramp_rule='Use the five dark-to-light source rings and their four midpoint interpolations. Add two shades at 0.35 and 0.65 times the darkest V, and two tints at 0.75 and 0.5 times the lightest S. Interpolate shortest-arc H, S and V; retain anchor RGB exactly.',
        muted_rule='At source-ring coordinates 0.5, 1.5, 2.5 and 3.5, multiply S by 0.4 and 0.7. Bend H toward that family’s lightest-tint H by 1 minus the saturation multiplier; solve V to preserve linear-sRGB relative luminance. This extrapolation is our rule, not a correction formula published by Mars.',
        gray_rule='16 neutral sRGB values at target CIELAB D65 L*=0,100/15,...,100; nearest-byte rounding.',
        perceptual_pruning=False,minimum_separation_requirement=None,fillers=0,individual_rgb_adjustments=0,
        diagram='Ring position indicates the authored shade/tint sequence, not constant measured lightness. Muted companions are displayed separately. Outlined wheel cells are exact source anchors.')
    bundle=base.export(rgb,STEM,KEY,'Martian expansion · artist-corrected ramps · 1024',report)
    (ROOT/'dist/martian-expansion.js').write_text(bundle)
    data=json.loads((OUT/f'{STEM}.json').read_text());data.update(families=families,samples=samples,source_anchors=source['colors'])
    (OUT/f'{STEM}.json').write_text(json.dumps(data,indent=2)+'\n')
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1380" viewBox="0 0 1440 1380" role="img" aria-labelledby="title desc">',
        '<title id="title">Martian expansion: 1024 colors</title><desc id="desc">48 artist-derived hue families: 13 shades and tints each, eight muted companions each, and sixteen neutral grays. White outlines identify Warren Mars’s 120 original RGB anchors.</desc>',
        '<rect width="1440" height="1380" fill="#121018"/>',
        '<g fill="#eae5f0" font-family="sans-serif"><text x="40" y="42" font-size="28">Martian expansion · artist-corrected ramps · 1024</text><text x="40" y="72" font-size="16">120 original anchors preserved · 24 original + 24 intermediate hue families</text></g>']
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
