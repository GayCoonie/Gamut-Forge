"""Check the six traversal cycles, exact mirrors, hue steps, and lossless exports."""
from pathlib import Path
from collections import Counter
from xml.etree import ElementTree as ET
import json, math, re, subprocess, zipfile
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/palettes';STEM='okhwb-walks-1024'
d=json.loads((OUT/f'{STEM}.json').read_text());old=json.loads((OUT/'okhwb-triangle-1024.json').read_text())
colors=d['colors'];samples=d['samples'];patterns=d['report']['traversal_patterns']
assert len(colors)==len(samples)==len(set(colors))==1024
assert colors[-16:]==old['colors'][-16:] and colors[-16]=='#000000' and colors[-1]=='#ffffff'
assert sum(c[1:3]==c[3:5]==c[5:7] for c in colors)==16
lattice={(i,j) for j in range(6) for i in range(6-j)}
assert len(patterns)==6 and len({tuple(map(tuple,p['path'])) for p in patterns})==6
for n,p in enumerate(patterns):
 path=list(map(tuple,p['path']));assert len(path)==21 and set(path)==lattice and path[0]==(0,0)
 assert all((c-a,d-b) in {(1,0),(-1,0),(0,1),(0,-1),(1,-1),(-1,1)} for (a,b),(c,d) in zip(path,path[1:]))
 if n%2:assert path==[(j,i) for i,j in patterns[n-1]['path']]
 assert p['mirrored']==bool(n%2)
for sector in range(48):
 block=samples[sector*21:(sector+1)*21]
 assert {p['pattern_index'] for p in block}=={sector%6}
 ordered=sorted(block,key=lambda p:p['walk_rank'])
 assert [p['walk_rank'] for p in ordered]==list(range(21))
 assert [(round(p['w']*6),round(p['b']*6)) for p in ordered]==list(map(tuple,patterns[sector%6]['path']))
 assert sum(p['h']==sector*7.5 for p in block)==1
 assert ordered[0]['w']==ordered[0]['b']==0 and ordered[0]['hex']==old['colors'][sector*21]
 for rank,p in enumerate(ordered):
  assert p['h']==(sector*7.5+rank*7.5/21)%360
  assert 0<=p['hue_offset']<7.5
assert Counter(p['pattern_index'] for p in samples[:1008])=={i:8*21 for i in range(6)}
hues=sorted(p['h'] for p in samples[:1008]);assert len(set(hues))==1008
assert all(abs((b-a)%360-360/1008)<1e-12 for a,b in zip(hues,hues[1:]+hues[:1]))
assert all((p['w'],p['b'])==(q['w'],q['b']) for p,q in zip(samples,old['samples']))
assert [p['hex'] for p in samples]==colors
js="""const fs=require('fs'),vm=require('vm'),c={};vm.createContext(c);vm.runInContext(fs.readFileSync('dist/vendor/ottosson-colorconversion.js','utf8'),c);const d=JSON.parse(fs.readFileSync('dist/palettes/okhwb-walks-1024.json'));console.log(JSON.stringify(d.samples.map(p=>{const rgb=p.b===1?[0,0,0]:c.okhsv_to_srgb(p.h/360,1-p.w/(1-p.b),1-p.b);return '#'+rgb.map(v=>Math.round(Math.max(0,Math.min(255,v))).toString(16).padStart(2,'0')).join('')})));"""
assert json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT))==colors
rgb=[tuple(bytes.fromhex(c[1:])) for c in colors]
assert (OUT/f'{STEM}.txt').read_text().splitlines()==colors
assert [tuple(map(int,m)) for m in re.findall(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s',(OUT/f'{STEM}.gpl').read_text(),re.M)]==rgb
with zipfile.ZipFile(OUT/f'{STEM}.kpl') as z:
 entries=ET.fromstring(z.read('colorset.xml')).findall('ColorSetEntry')
 assert [tuple(round(float(e.find('sRGB').attrib[c])*255) for c in 'rgb') for e in entries]==rgb
im=Image.open(OUT/f'{STEM}.png');assert im.size==(512,512)
assert [im.getpixel((i%32*16+8,i//32*16+8)) for i in range(1024)]==rgb
with zipfile.ZipFile(OUT/f'{STEM}-package.zip') as z:
 for name in z.namelist():assert z.read(name)==(OUT/name).read_bytes()
ns={'s':'http://www.w3.org/2000/svg'};groups=ET.parse(OUT/f'{STEM}-atlas.svg').findall('.//s:g[@data-hue]',ns)
assert len(groups)==48
for sector,g in enumerate(groups):
 polys=g.findall('s:polygon',ns);assert len(polys)==37
 assert [p.attrib['fill'] for p in polys]==colors[sector*21:(sector+1)*21]+colors[-16:]
 ranks=g.findall('s:g[@class="walk-overlay"]/s:text',ns)
 assert [int(p.text) for p in ranks]==list(range(21))
 walk=g.find('s:g[@class="walk-overlay"]/s:polyline',ns)
 assert len(walk.attrib['points'].split())==21
print('Passed: six unique adjacent-cell walks; exact mirror pairs; eight cycles; 1008 evenly spaced hues; unchanged anchors/grays; lossless exports and 48 complete diagrams.')
