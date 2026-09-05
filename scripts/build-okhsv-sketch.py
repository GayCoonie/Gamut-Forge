"""Build the 48-hue OKHSV sketch using Ottosson's vendored reference JavaScript.

Run: python scripts/build-okhsv-sketch.py (Node, NumPy and Pillow required).
The supplied geometry yields 1024 colors: 48*20 + 16 + 12*4. No fillers.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import zipfile
from xml.etree import ElementTree as ET
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist/palettes'
STEM = 'okhsv-sketch-1024'
KEY = 'okhsvSketch1024'
NAME = 'OKHSV · sketch sampling · 1024'
# Yellow and purple are one shared pattern; the stray exterior dot is omitted.
# Sketch interpretation: five-percent grid; the upper row is on V=1.
MAIN = [[40,100],[70,100],[100,100],[45,85],[70,85],
        [30,75],[60,70],[80,70],[45,60],[90,55],
        [75,50],[35,45],[60,45],[85,40],[25,30],
        [50,25],[70,20],[15,15],[40,15],[85,15]]
# Gently bow the pattern toward high S/high V, rather than a diagonal cutoff.
# f(x)=x+0.35*x*(1-x), then nearest 5%; endpoints remain fixed.
MAIN = [[int(np.floor((x/100+.35*(x/100)*(1-x/100))*20+.5))*5
         for x in point] for point in MAIN]
# Use the opened lower-left pocket; 15/15 collapsed adjacent hues in byte RGB.
MAIN[17] = [25,25]
GREEN = [[5,75],[15,65],[5,35],[60,10]]

def main():
    samples = [dict(kind='main',h=i*7.5,s=s/100,v=v/100,point=j+1)
               for i in range(48) for j,(s,v) in enumerate(MAIN)]
    samples += [dict(kind='gray',h=0,s=0,v=i/15,point=i+1) for i in range(16)]
    samples += [dict(kind='tinted',h=h,s=s/100,v=v/100,point=j+1)
                for h in range(0,360,30) for j,(s,v) in enumerate(GREEN)]
    js = """const fs=require('fs'),vm=require('vm'),c={};vm.createContext(c);
vm.runInContext(fs.readFileSync('dist/vendor/ottosson-colorconversion.js','utf8'),c);
const samples=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(samples.map(p=>p.v===0?[0,0,0]:c.okhsv_to_srgb(p.h/360,p.s,p.v))));"""
    raw = np.array(json.loads(subprocess.check_output(['node','-e',js],input=json.dumps(samples).encode(),cwd=ROOT)))
    assert np.isfinite(raw).all()
    # Reference gamut approximation can produce tiny excursions at the boundary.
    rgb = np.floor(np.clip(raw,0,255)+.5).astype(np.uint8)
    spec=importlib.util.spec_from_file_location('audit',ROOT/'scripts/build-random-strata.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    colors = ['#'+bytes(c).hex() for c in rgb]
    assert len(samples)==len(set(colors))==1024
    assert np.all(rgb[960:976,0]==rgb[960:976,1]) and np.all(rgb[960:976,1]==rgb[960:976,2])
    assert colors[960]=='#000000' and colors[975]=='#ffffff'
    report=dict(method='48 OKHSV hues at 7.5 degree intervals; the same 20 S/V points at every hue; 16 evenly spaced OKHSV V grays; four tinted samples at each of twelve 30 degree marks.',
        sketch_interpretation='Freehand pattern bowed toward top right with f(x)=x+0.35*x*(1-x), snapped to five percent. Upper row remains V=1; lower-left main point is S=25%, V=25% to avoid byte collisions. Yellow and purple are one pattern. Four green points applied at 0,30,60,...,330 degrees. The exterior yellow dot is omitted.',
        count_arithmetic='48 * 20 + 16 + 12 * 4 = 1024; no unrequested fillers.',
        main_points_percent=MAIN,tinted_points_percent=GREEN,tinted_hues=list(range(0,360,30)),
        grayscale_values=[i/15 for i in range(16)],grayscale_bytes=rgb[960:976,0].tolist(),
        source='https://bottosson.github.io/posts/colorpicker/',
        reference_js='https://bottosson.github.io/misc/colorpicker/colorconversion.js',
        reference_sha256=hashlib.sha256((ROOT/'dist/vendor/ottosson-colorconversion.js').read_bytes()).hexdigest(),
        channel_encoding='Reference OKHSV to encoded sRGB; clamp numerical gamut excursions then round nearest half up. V=0 handled explicitly as black.',
        duplicate_rounding_resolutions=[],
        maximum_channel_error_from_clamped_target=float(np.abs(rgb.astype(float)-np.clip(raw,0,255)).max()),
        raw_channel_range=[float(raw.min()),float(raw.max())],
        maximum_boundary_excursion_bytes=float(max(0,-raw.min(),raw.max()-255)),
        perceptual_pruning=False,minimum_separation_requirement=None,
        separation_note='Geometry retained exactly; equal coordinate steps do not guarantee equal perceptual distances.',
        **audit.audit(rgb))
    for p,c in zip(samples,colors):p['hex']=c
    (OUT/f'{STEM}.json').write_text(json.dumps(dict(name=NAME,report=report,colors=colors,samples=samples),indent=2)+'\n')
    (OUT/f'{STEM}.txt').write_text('\n'.join(colors)+'\n')
    columns,rows=32,32
    (OUT/f'{STEM}.gpl').write_text('\n'.join(['GIMP Palette',f'Name: {NAME}',f'Columns: {columns}','#']+[f'{r:3} {g:3} {b:3}\t{c}' for (r,g,b),c in zip(rgb,colors)])+'\n')
    root=ET.Element('Colorset',name=NAME,columns=str(columns),rows=str(rows),readonly='false',version='1.0')
    for i,(c,channels) in enumerate(zip(colors,rgb)):
        sw=ET.SubElement(root,'ColorSetEntry',name=c,id=f'color-{i+1}',bitdepth='U8',spot='false')
        ET.SubElement(sw,'sRGB',**{k:f'{int(v)/255:.10f}' for k,v in zip('rgb',channels)})
        ET.SubElement(sw,'Position',row=str(i//columns),column=str(i%columns))
    with zipfile.ZipFile(OUT/f'{STEM}.kpl','w') as z:
        z.writestr('mimetype','application/x-krita-palette')
        z.writestr('colorset.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True),compress_type=zipfile.ZIP_DEFLATED)
        z.writestr('profiles.xml','<?xml version="1.0" encoding="UTF-8"?><Profiles/>')
    Image.fromarray(rgb.reshape(rows,columns,3)).resize((640,640),Image.Resampling.NEAREST).save(OUT/f'{STEM}.png')
    with zipfile.ZipFile(OUT/f'{STEM}-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for ext in ['txt','gpl','kpl','json','png']:z.write(OUT/f'{STEM}.{ext}',f'{STEM}.{ext}')
    (ROOT/'dist/okhsv-sketch.js').write_text(f'window.GAMUT_PALETTES.{KEY}='+json.dumps(dict(name=NAME,colors=colors),separators=(',',':'))+';\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
