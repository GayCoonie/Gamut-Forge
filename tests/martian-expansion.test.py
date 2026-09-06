"""Verify source provenance, exact anchors, extension rules and shipped exports."""
from pathlib import Path
from xml.etree import ElementTree as ET
import importlib.util,json,re,zipfile
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/palettes';STEM='martian-expansion-1024'
s=importlib.util.spec_from_file_location('build',ROOT/'scripts/build-martian-expansion.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
source,families,expected=m.build();data=json.loads((OUT/f'{STEM}.json').read_text())
assert data['samples']==expected and data['families']==families
colors=data['colors'];samples=data['samples'];anchors=source['colors']
assert len(colors)==len(set(colors))==1024 and [p['hex'] for p in samples]==colors
assert len(anchors)==len({p['hex'] for p in anchors})==120
assert {p['hex'] for p in anchors}=={p['hex'] for p in samples if p['kind']=='source-anchor'}
assert sum(p['kind']=='source-anchor' for p in samples)==120
assert sum(p['kind']=='muted-companion' for p in samples)==384
assert sum(p['kind']=='gray' for p in samples)==16
assert sum(p['kind']=='new-vivid-exemplar' for p in samples)==24
assert len({f['vivid_hex'] for f in families})==48
for family in families:
 c=bytes.fromhex(family['vivid_hex'][1:]);assert min(c)==0 and max(c)==255
 assert family['vivid_hex'] in colors
assert colors[-16]=='#000000' and colors[-1]=='#ffffff'
assert sum(c[1:3]==c[3:5]==c[5:7] for c in colors)==16
for f in range(48):
 block=samples[f*21:(f+1)*21]
 assert all(p['family']==f for p in block)
 assert [p['cell'] for p in block]==list(range(21))
 if not f%2:assert [p['hex'] for p in block[2:11:2]]==[a['hex'] for a in anchors[f//2*5:f//2*5+5]][::-1]
 for p in block[13:]:
  Y=m.luminance(m.rgb_float(p['hsv']))
  assert abs(Y-p['target_relative_luminance'])<1e-11
  assert p['saturation_scale'] in [.4,.7]
 if f%2:
  a=f//2;b=(a+1)%24
  for ring,cell in enumerate(range(2,11,2)):
   left=m.hsv(anchors[a*5+4-ring]['rgb']);right=m.hsv(anchors[b*5+4-ring]['rgb'])
   if ring==families[f]['vivid_ring']:
    assert block[cell]['kind']=='new-vivid-exemplar' and block[cell]['hsv'][1:]==[1.,1.]
   else:assert np.allclose(block[cell]['hsv'],m.blend(left,right,.5),atol=1e-10)
rgb=[tuple(bytes.fromhex(c[1:])) for c in colors]
assert (OUT/f'{STEM}.txt').read_text().splitlines()==colors
assert [tuple(map(int,v)) for v in re.findall(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s',(OUT/f'{STEM}.gpl').read_text(),re.M)]==rgb
with zipfile.ZipFile(OUT/f'{STEM}.kpl') as z:
 entries=ET.fromstring(z.read('colorset.xml')).findall('ColorSetEntry')
 assert [tuple(round(float(e.find('sRGB').attrib[c])*255) for c in 'rgb') for e in entries]==rgb
im=Image.open(OUT/f'{STEM}.png');assert [im.getpixel((i%32*16+8,i//32*16+8)) for i in range(1024)]==rgb
with zipfile.ZipFile(OUT/f'{STEM}-package.zip') as z:
 for name in z.namelist():assert z.read(name)==(OUT/name).read_bytes()
svg=ET.parse(OUT/f'{STEM}-atlas.svg');cells=[p for p in svg.iter() if 'data-index' in p.attrib]
assert len(cells)==1024 and {int(p.attrib['data-index']) for p in cells}==set(range(1024))
assert all(p.attrib['fill']==colors[int(p.attrib['data-index'])] for p in cells)
assert sum(p.attrib.get('stroke')=='#ffffff' for p in cells)==120
print('Passed: 120 exact source anchors, 48 ring-specific hue families, 384 luminance-preserving companions, 16 grays, all exports, and all 1024 atlas cells.')
