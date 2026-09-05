"""Publish a complete catalog and lossless downloads of every shipped built-in.
Run with Python + Pillow and Node. Existing palette files are never overwritten.
"""
import json, subprocess, math, zipfile, html
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]; DIST=ROOT/'dist'; OUT=DIST/'palettes'
scripts=['palettes.js','retro-source-union-4096.js','retro-source-union-1024.js','critter-palettes.js','hsv-three-tier-64.js','hsv-three-tier-10.js','hsv-three-tier-sketch.js','random-strata.js','random-strata-v2-trials.js']
js="const fs=require('fs'),vm=require('vm'),c={window:{}};vm.createContext(c);for(const f of "+json.dumps(scripts)+")vm.runInContext(fs.readFileSync('dist/'+f,'utf8'),c);process.stdout.write(JSON.stringify(c.window.GAMUT_PALETTES));"
palettes=json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT))
# Descriptions document the shipped profiles, not a regeneration of their colors.
rows=[
('randomStrataTry5', 'random-strata-try5', 'Random Strata v2', 'Try 5, supplied from the adaptive generator. All 1,024 RGB entries and their grid positions are preserved. Includes 64 near-grays with black and white, 120 vivid entries and 840 quadrant samples. Per-hue vivid spacing varies; the download JSON records measured pair-class distances.', None),
('randomStrataTry6', 'random-strata-try6', 'Random Strata v2', 'Try 6, supplied from the adaptive generator. All 1,024 RGB entries and their grid positions are preserved. Includes 64 near-grays with black and white, 120 vivid entries and 840 quadrant samples. Per-hue vivid spacing varies; the download JSON records measured pair-class distances.', None),
('randomStrataTry7', 'random-strata-try7', 'Random Strata v2', 'Try 7, supplied from the adaptive generator. All 1,024 RGB entries and their grid positions are preserved. Includes 64 near-grays with black and white, 120 vivid entries and 840 quadrant samples. Per-hue vivid spacing varies; the download JSON records measured pair-class distances.', None),
('randomStrataTry8', 'random-strata-try8', 'Random Strata v2', 'Try 8, supplied from the adaptive generator. All 1,024 RGB entries and their grid positions are preserved. Includes 64 near-grays with black and white, 120 vivid entries and 840 quadrant samples. Per-hue vivid spacing varies; the download JSON records measured pair-class distances.', None),
('randomStrataV2Combined4096', 'random-strata-v2-combined-4096', 'Random Strata v2', 'All 4,001 unique colors from Try 5–8, six missing 3-bit gray levels replacing repeated black/white entries, and 89 well-separated fillers chosen only from Try 1–4. The complete eight-level ramp is included. Existing close cross-trial pairs remain; individual trial thresholds do not carry over to the union.', None),

('randomStrataTry1', 'random-strata-try1', 'Random Strata Beta', 'User/Gemini random HSV experiment, Try 1. The 1,024 supplied RGB colors and their 32×32 order are preserved exactly. Intended design: fifteen hue sectors with vivid rows and four S/V quadrants, plus 64 grays. Beta: the files do not meet the requested global 2.5 ΔE00 separation; the JSON contains the measured audit.', None),
('randomStrataTry2', 'random-strata-try2', 'Random Strata Beta', 'User/Gemini random HSV experiment, Try 2. The 1,024 supplied RGB colors and their 32×32 order are preserved exactly. Intended design: fifteen hue sectors with vivid rows and four S/V quadrants, plus 64 grays. Beta: the files do not meet the requested global 2.5 ΔE00 separation; the JSON contains the measured audit.', None),
('randomStrataTry3', 'random-strata-try3', 'Random Strata Beta', 'User/Gemini random HSV experiment, Try 3. The 1,024 supplied RGB colors and their 32×32 order are preserved exactly. Intended design: fifteen hue sectors with vivid rows and four S/V quadrants, plus 64 grays. Beta: the files do not meet the requested global 2.5 ΔE00 separation; the JSON contains the measured audit.', None),
('randomStrataTry4', 'random-strata-try4', 'Random Strata Beta', 'User/Gemini random HSV experiment, Try 4. The 1,024 supplied RGB colors and their 32×32 order are preserved exactly. Intended design: fifteen hue sectors with vivid rows and four S/V quadrants, plus 64 grays. Beta: the files do not meet the requested global 2.5 ΔE00 separation; the JSON contains the measured audit.', None),
('randomStrataCombined4096', 'random-strata-combined-4096', 'Random Strata Beta', 'All 3,777 unique colored entries from the four trials, all 256 true sRGB grays, and 63 gap-filling colors. The added colored samples are at least 4.669 ΔE00 from every other final color. Existing close pairs are preserved; this beta does not promise global separation. The four source grids occupy four quadrants; only duplicate occurrences are replaced.', None),

('hsvThreeTierSketch','hsv-three-tier-sketch','HSV experiments','A 64-hue bright 3×3 core, with 32-hue middle rows and 16-hue outer rows spread through the square. The green 3×3, purple 2/2/5 and yellow 3/2/4 sketch becomes 1,008 colors plus 16 grays. HSV geometry is retained without perceptual pruning.','hsv-three-tier.html?version=sketch'),
('hsvThreeTier64','hsv-three-tier-64','HSV experiments','64 hues at 5.625° intervals. A bright 3×3 core is extended by three three-point Ls for 32 hues, then three more for 16 hues. The bands reach 14% saturation/value; 16 grays complete the palette. No perceptual pruning.','hsv-three-tier.html?version=thirds'),
('hsvThreeTier10','hsv-three-tier-10','HSV experiments','The 64/32/16 hue comparison on a 10% saturation/value lattice. A bright 80/90/100% core is extended through the middle and outer bands down to 10%. Sixteen grays retain their separate, evenly spaced HSV values.','hsv-three-tier.html?version=grid'),
('staticBloom1024','static-bloom-1024','Game and artist palettes','Stepped lightness and hue-shifting material ramps informed by Coonie Critters terrain and sprite atlases. Designed for pronounced palette crushing, with every pair more than 2 CIEDE2000 apart. Contained in Static Bloom 4096.',None),
('staticBloom4096','static-bloom-4096','Game and artist palettes','More material variations around the same game-derived core. Includes every Static Bloom 1024 color and keeps every pair more than 2 CIEDE2000 apart.',None),
('lospec19MaxFit','lospec-19-max-fit','Game and artist palettes','1,024 verbatim colors selected from the 1,420 unique colors in the original 19 supplied palettes. Eight RGB corners are fixed; weighted farthest-point selection in OKLab fills the remaining slots.',None),
('lospecMachineMaxFit','lospec-machine-max-fit','Game and artist palettes','A fresh selection from all 1,420 Lospec colors plus RGB333, RGB332 and RGB222: 2,076 unique candidates. Weighted OKLab selection preserves eight RGB corners. Contains 680 artist-only, 328 machine-only and 16 shared colors.',None),
('retroSourceUnion1024','retro-source-union-1024','Retro source unions','A literal subset of the 4,096-color retro source union. CIEDE2000 farthest-point selection and bottleneck-improving swaps prioritize minimum separation. Audited minimum: 4.203 ΔE00. This is a heuristic, not a global optimality proof.',None),
('retroSourceUnion4096','retro-source-union-4096','Retro source unions','29 supplied palettes plus low-bit hardware and software vocabularies, web-safe colors and 1994 X11 rgb.txt. From 5,576 candidates, 3,175 mutually separated colors meet ΔE00 ≥ 2; 921 closer additions reach 4,096. Final minimum is about 1.226 ΔE00. X11-only provenance is deweighted at distance ties.',None),
('rgb9Fusion','rgb9-fusion','Retro source unions','All RGB333, RGB332 and RGB222 colors remain anchored: 688 unique colors after overlap. The remaining 336 are selected in OKLab from RGB444, web-safe and 1994 X11 colors.',None),
('rgb9Retro','rgb9-retro','Retro source unions','The RGB333 cube supplemented from RGB222, RGB332, web-safe colors and X11. A restricted digital vocabulary around the 512-color base.',None),
('rgb9Rgb444','rgb9-rgb444','Retro source unions','The RGB333 base supplemented only with colors from the RGB444 cube. Every entry belongs to the union of these two machine vocabularies.',None),
('retroArtistWheel','retro-artist-wheel','Retro source unions','816 unique anchors from RGB333, RGB332, RGB233, RGB222 and Windows-16, with 208 new artist accents. The supplied 60-color vocabulary expands to interstitial hues and darker companions, replacing the web-safe contribution.',None),
('rgb343Control','rgb343-control','Cubes and coverage','The complete 10-bit RGB343 cube: 8 red × 16 green × 8 blue levels, expanded to full-range sRGB. A hardware-style control with no perceptual pruning.',None),
('rgbCube','rgb-cube','Cubes and coverage','A 10×10×10 RGB color cube plus 24 additional grays. Regular channel steps create a deliberately visible digital structure.',None),
('rgb9Hybrid','rgb9-hybrid','Cubes and coverage','512 RGB333 cube colors combined with 512 coverage colors. Keeps the 9-bit lattice while filling gaps with a broader color vocabulary.',None),
('maxCoverage','maximum-coverage','Cubes and coverage','A broad-coverage palette built around 48 vivid hue anchors. Useful as a fidelity-oriented comparison against the more constrained pixel-art and machine palettes.',None),
('original','original-96-48','Early tier experiments','The original shipped 96/48-hue profile from the earlier palette experiments. This download preserves its exact built-in RGB values and order.',None),
('twoTier','two-tier-48-24','Early tier experiments','The earlier 48/24-hue two-tier experiment, preserved for direct comparison with the later redesigned HSV profiles.',None),
('threeTier','three-tier-48-24-12','Early tier experiments','The earlier 48/24/12-hue three-tier experiment, preserved for direct comparison with the later redesigned HSV profiles.',None),
]
assert {r[0] for r in rows}==set(palettes)
catalog=[]
for key,stem,group,description,diagram in rows:
 p=palettes[key];colors=p['colors'];n=len(colors);assert len(set(colors))==n
 side=math.isqrt(n);assert side*side==n
 item=dict(key=key,stem=stem,group=group,name=p['name'],count=n,description=description)
 if diagram:item['diagram']=diagram
 catalog.append(item)
 # Reuse audited existing exports intact. Only missing sets need packaging.
 if not (OUT/f'{stem}.txt').exists():
  rgb=[tuple(bytes.fromhex(c[1:])) for c in colors]
  (OUT/f'{stem}.txt').write_text('\n'.join(colors)+'\n')
  (OUT/f'{stem}.json').write_text(json.dumps(dict(name=p['name'],description=description,colors=colors),indent=2)+'\n')
  (OUT/f'{stem}.gpl').write_text('\n'.join(['GIMP Palette',f'Name: {p["name"]}',f'Columns: {side}','#']+[f'{r:3} {g:3} {b:3}\t{c}' for (r,g,b),c in zip(rgb,colors)])+'\n')
  root=ET.Element('Colorset',name=p['name'],columns=str(side),rows=str(side),readonly='false',version='1.0')
  for i,(c,channels) in enumerate(zip(colors,rgb)):
   sw=ET.SubElement(root,'ColorSetEntry',name=c,id=f'color-{i+1}',bitdepth='U8',spot='false')
   ET.SubElement(sw,'sRGB',**{k:f'{v/255:.10f}' for k,v in zip('rgb',channels)})
   ET.SubElement(sw,'Position',row=str(i//side),column=str(i%side))
  with zipfile.ZipFile(OUT/f'{stem}.kpl','w') as z:
   z.writestr('mimetype','application/x-krita-palette')
   z.writestr('colorset.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True),compress_type=zipfile.ZIP_DEFLATED)
   z.writestr('profiles.xml','<?xml version="1.0" encoding="UTF-8"?><Profiles/>')
  im=Image.new('RGB',(side,side));im.putdata(rgb);im.resize((512,512),Image.Resampling.NEAREST).save(OUT/f'{stem}.png')
  with zipfile.ZipFile(OUT/f'{stem}-package.zip','w',zipfile.ZIP_DEFLATED) as z:
   for ext in ('txt','gpl','kpl','json','png'):z.write(OUT/f'{stem}.{ext}',f'{stem}.{ext}')
 for ext in ('txt','gpl','kpl','json','png'):assert (OUT/f'{stem}.{ext}').exists()
 assert [c if isinstance(c,str) else c['hex'] for c in json.loads((OUT/f'{stem}.json').read_text())['colors']]==colors
(DIST/'palette-catalog.js').write_text('window.GAMUT_CATALOG='+json.dumps(catalog,indent=2)+';\n')
# The catalog is static HTML: descriptions and downloads work without JavaScript.
esc=html.escape
parts=['''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Palette library · Gamut Forge</title><meta name="description" content="Explore all __COUNT__ Gamut Forge palettes: information, color-space atlases, sampling diagrams and Krita, GIMP, hex, JSON and PNG downloads."><link rel="stylesheet" href="./styles.css"><link rel="stylesheet" href="./palette-library.css"></head><body>
<header class="topbar"><a class="site-name" href="./">Gamut Forge</a><nav aria-label="Main navigation"><a href="./">Image quantizer</a><a href="./palette-library.html" aria-current="page">Palette library</a></nav></header>
<main class="library"><p class="eyebrow">THE FULL COLLECTION</p><h1>Find your color vocabulary.</h1><p class="intro">All __COUNT__ built-in palettes, from machine cubes to game-derived material ramps and HSV experiments. Explore their construction, inspect every color, or take them into your editor.</p><p class="library-stats">__COUNTS__</p>
<p class="format-note">Every palette includes Krita (KPL), GIMP (GPL), hex text, JSON and a swatch PNG. ZIP packages gather those formats; audited profiles also retain their reports. Downloads contain the exact colors used by the quantizer.</p><nav class="jump-links" aria-label="Palette families">''']
groups=list(dict.fromkeys(r[2] for r in rows));slug=lambda s:s.lower().replace(' ','-')
for g in groups:parts.append(f'<a href="#{slug(g)}">{esc(g)}</a>')
parts.append('</nav>')
for g in groups:
 parts.append(f'<section id="{slug(g)}" class="family"><h2>{esc(g)}</h2><div class="palette-grid">')
 for p in [p for p in catalog if p['group']==g]:
  key,stem=p['key'],p['stem'];info='./palette-guide.html?palette='+key
  parts.append(f'<article id="{key}" class="palette-entry"><a href="{info}" tabindex="-1" aria-hidden="true"><img loading="lazy" width="512" height="512" src="./palettes/{stem}.png" alt=""></a><div class="entry-body"><p class="count">{p["count"]:,} unique colors</p><h3><a href="{info}">{esc(p["name"])}</a></h3><p>{esc(p["description"])}</p><div class="entry-actions"><a href="{info}">Info &amp; color atlas →</a><a href="./?palette={key}">Use palette →</a>')
  if p.get('diagram'):parts.append(f'<a href="./{p["diagram"]}">HSV sampling diagram →</a>')
  parts.append(f'</div><div class="palette-downloads" aria-label="Downloads for {esc(p["name"])}">')
  for ext,label in [('kpl','Krita'),('gpl','GIMP'),('txt','Hex'),('json','JSON'),('png','PNG'),('-package.zip','All formats ↓')]:
   suffix=ext if ext.startswith('-') else '.'+ext
   parts.append(f'<a href="./palettes/{stem}{suffix}" download>{label}</a>')
  parts.append('</div></div></article>')
 if g=='Random Strata v2':parts.append('<p class="format-note"><a href="./random-strata.html#v2-trials">Try 5–8 reports and combination details →</a></p>')
 if g=='Random Strata Beta':parts.append('<p class="format-note"><a href="./random-strata.html">Beta audit, overlap counts and corrected generator →</a></p>')
 parts.append('</div></section>')
parts.append('<p class="format-note">Color-space plots share CIELAB lightness/chroma axes for comparison. Construction and perceptual separation are different properties: a regular HSV or RGB grid does not promise a minimum ΔE00. Choose an info page for the available audit and construction details.</p></main><footer><a href="./">Back to image quantizer</a><span>Gamut Forge · Palette library</span></footer></body></html>')
(DIST/'palette-library.html').write_text(('\n'.join(parts)+'\n').replace('__COUNT__',str(len(catalog))).replace('__COUNTS__',f'{sum(p["count"]==1024 for p in catalog)} palettes of 1,024 colors · {sum(p["count"]==4096 for p in catalog)} palettes of 4,096 colors'))
print(f'Built library: {len(catalog)} palettes, all downloads present.')
