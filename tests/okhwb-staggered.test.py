"""Validate the sketch transcription, hue interleaving and exported bytes."""
import json, math, re, subprocess, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];DIST=ROOT/'dist';OUT=DIST/'palettes'
STEM='okhwb-staggered-1024'
d=json.loads((OUT/f'{STEM}.json').read_text());v1=json.loads((OUT/'okhwb-triangle-1024.json').read_text())
colors=d['colors'];samples=d['samples']
assert len(samples)==len(colors)==len(set(colors))==1024
assert colors[-16:]==v1['colors'][-16:]
assert colors[-16]=='#000000' and colors[-1]=='#ffffff'
assert sum(c[1:3]==c[3:5]==c[5:7] for c in colors)==16
# Expected sketch cells: (W level, B level): yellow-dot count.
expected={(5,0):0,(4,1):1,(3,2):2,(2,3):3,(1,4):4,(0,5):5,
 (4,0):0,(3,1):2,(2,2):1,(1,3):3,(0,4):4,
 (3,0):2,(2,1):0,(1,2):1,(0,3):3,
 (2,0):1,(1,1):0,(0,2):2,(1,0):0,(0,1):1,(0,0):0}
for source in range(48):
 block=samples[source*21:(source+1)*21]
 assert len(block)==21
 for p in block:
  i,j=round(p['w']*6),round(p['b']*6);n=i+j+1
  assert p['hue_step']==expected[i,j]
  assert p['source_h']==source*7.5
  assert p['hue_offset']==expected[i,j]*7.5/n
  assert p['h']==(source*7.5+p['hue_offset'])%360
  assert 0<=p['hue_offset']<7.5
 for n in range(1,7):
  column=[p for p in block if p['column_size']==n]
  assert sorted(p['hue_step'] for p in column)==list(range(n))
  assert sum(p['hue_step']==0 for p in column)==1
for i,(p,old) in enumerate(zip(samples,v1['samples'])):
 assert (p['w'],p['b'])==(old['w'],old['b'])
 assert p['hex']==colors[i]
 if p['kind']=='gray' or p['hue_step']==0: assert p['hex']==old['hex']
assert len({p['h'] for p in samples[:1008]})==576
# Independently run the shipped conversion against every coordinate.
js="""const fs=require('fs'),vm=require('vm'),c={};vm.createContext(c);vm.runInContext(fs.readFileSync('dist/vendor/ottosson-colorconversion.js','utf8'),c);const d=JSON.parse(fs.readFileSync('dist/palettes/okhwb-staggered-1024.json'));console.log(JSON.stringify(d.samples.map(p=>{const rgb=p.b===1?[0,0,0]:c.okhsv_to_srgb(p.h/360,1-p.w/(1-p.b),1-p.b);return '#'+rgb.map(v=>Math.round(Math.max(0,Math.min(255,v))).toString(16).padStart(2,'0')).join('')})));"""
assert json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT))==colors
assert (OUT/f'{STEM}.txt').read_text().splitlines()==colors
rgb=[tuple(bytes.fromhex(c[1:])) for c in colors]
gpl=[tuple(map(int,m)) for m in re.findall(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s', (OUT/f'{STEM}.gpl').read_text(),re.M)]
assert gpl==rgb
with zipfile.ZipFile(OUT/f'{STEM}.kpl') as z:
 entries=ET.fromstring(z.read('colorset.xml')).findall('ColorSetEntry')
 assert len(entries)==1024
 assert [tuple(round(float(e.find('sRGB').attrib[c])*255) for c in 'rgb') for e in entries]==rgb
im=Image.open(OUT/f'{STEM}.png');assert im.size==(512,512)
assert [im.getpixel((i%32*16+8,i//32*16+8)) for i in range(1024)]==rgb
with zipfile.ZipFile(OUT/f'{STEM}-package.zip') as z:
 for file in z.namelist():assert z.read(file)==(OUT/file).read_bytes()
ns={'s':'http://www.w3.org/2000/svg'}
svg=ET.parse(OUT/f'{STEM}-atlas.svg')
groups=svg.findall('.//s:g[@data-hue]',ns);assert len(groups)==48
for hue,group in enumerate(groups):
 polygons=group.findall('s:polygon',ns);assert len(polygons)==37
 assert [p.attrib['fill'] for p in polygons]==colors[hue*21:(hue+1)*21]+colors[-16:]
 markers=group.findall('s:g[@class="offset-markers"]',ns)
 assert [int(m.attrib['data-step']) for m in markers]==[p['hue_step'] for p in samples[hue*21:(hue+1)*21]]
 assert all(len(m.findall('s:circle',ns))==max(1,int(m.attrib['data-step'])) for m in markers)
 area=0
 for p in polygons:
  points=[tuple(map(float,pair.split(','))) for pair in p.attrib['points'].split()]
  area+=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1])))/2
 assert abs(area-6400*math.sqrt(3))<.01
print('Passed: sketch offsets, 48 anchors, 16 unchanged grays, 1024 unique colors, conversion, all exports, and 48 complete triangle panels.')
