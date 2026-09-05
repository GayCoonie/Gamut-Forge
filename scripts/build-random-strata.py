"""Import four user/Gemini palettes verbatim; combine and fill exact duplicates.
Usage: python scripts/build-random-strata.py /path/to/gpl/files
NumPy + Pillow required. No reference game images are published.
"""
import sys,re,json,hashlib,colorsys,importlib.util,zipfile
from pathlib import Path
from collections import Counter
from xml.etree import ElementTree as ET
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/palettes'
spec=importlib.util.spec_from_file_location('maths',ROOT/'scripts/build-critter-palettes.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def audit(rgb):
 report=m.audit(rgb);labs=m.lab(rgb.astype(float));report['pairs_below_2_5']=sum(int(np.count_nonzero(m.de(labs[i+1:],labs[i])<2.5)) for i in range(len(rgb)-1))
 report.update(count=len(rgb),unique_colors=len(set(map(tuple,rgb))),gray_count=sum(int(r==g==b) for r,g,b in rgb),metric='CIEDE2000; CIELAB D65/2 degrees; kL=kC=kH=1')
 return report

def export(rgb,stem,key,name,report):
 colors=['#'+bytes(c).hex() for c in rgb];side=int(len(rgb)**.5);assert side*side==len(rgb)==len(set(colors))
 report=dict(report,**audit(rgb));(OUT/f'{stem}.json').write_text(json.dumps(dict(report=report,colors=colors),indent=2)+'\n')
 (OUT/f'{stem}.txt').write_text('\n'.join(colors)+'\n')
 (OUT/f'{stem}.gpl').write_text('\n'.join(['GIMP Palette',f'Name: {name}',f'Columns: {side}','#']+[f'{r:3} {g:3} {b:3}\t{c}' for (r,g,b),c in zip(rgb,colors)])+'\n')
 root=ET.Element('Colorset',name=name,columns=str(side),rows=str(side),readonly='false',version='1.0')
 for i,(c,channels) in enumerate(zip(colors,rgb)):
  sw=ET.SubElement(root,'ColorSetEntry',name=c,id=f'color-{i+1}',bitdepth='U8',spot='false');ET.SubElement(sw,'sRGB',**{k:f'{int(v)/255:.10f}' for k,v in zip('rgb',channels)});ET.SubElement(sw,'Position',row=str(i//side),column=str(i%side))
 with zipfile.ZipFile(OUT/f'{stem}.kpl','w') as z:
  z.writestr('mimetype','application/x-krita-palette');z.writestr('colorset.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True),compress_type=zipfile.ZIP_DEFLATED);z.writestr('profiles.xml','<?xml version="1.0" encoding="UTF-8"?><Profiles/>')
 im=Image.fromarray(rgb.reshape(side,side,3));im.resize((512,512),Image.Resampling.NEAREST).save(OUT/f'{stem}.png')
 with zipfile.ZipFile(OUT/f'{stem}-package.zip','w',zipfile.ZIP_DEFLATED) as z:
  for ext in ['txt','gpl','kpl','json','png']:z.write(OUT/f'{stem}.{ext}',f'{stem}.{ext}')
 print(json.dumps(dict(key=key,minimum=report['minimum_delta_e_2000'],pairs_below_2_5=report['pairs_below_2_5'],gray_count=report['gray_count'])),flush=True)
 return f'window.GAMUT_PALETTES.{key}='+json.dumps(dict(name=name,colors=colors),separators=(',',':'))+';\n'

def main(folder):
 source=[];hashes={};output=[]
 for i in range(1,5):
  path=folder/f'try{i}.gpl';raw=path.read_bytes();hashes[path.name]=hashlib.sha256(raw).hexdigest();a=np.array([list(map(int,x)) for x in re.findall(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s',raw.decode(),re.M)],dtype=int)
  assert a.shape==(1024,3) and a.min()>=0 and a.max()<=255 and len(set(map(tuple,a)))==1024
  a=a.astype(np.uint8);source.append(a)
  output.append(export(a,f'random-strata-try{i}',f'randomStrataTry{i}',f'Random Strata Beta · Try {i} · 1024',dict(source_file=path.name,source_sha256=hashes[path.name],method='Verbatim RGB entries from the user-supplied GPL, in original order. User supplied the Gemini generator prompt, not its implementation.',release_status='beta',intended_design='15 non-overlapping 24-degree HSV hue sectors: 8 vivid plus 14 samples per S/V quadrant each; 64 random grays. Requested global 2.5 CIEDE2000 separation is not met by these files.',modified_colors=False,layout='32 by 32, preserving supplied row-major order.')))
 allrgb=np.concatenate(source);union=np.array(list(dict.fromkeys(map(tuple,allrgb))),dtype=np.uint8);missing=4096-len(union)
 (OUT/'random-strata-exact-union.txt').write_text('\n'.join('#'+bytes(c).hex() for c in union)+'\n')
 print(f'Exact union {len(union)}; filling {missing} repeated entries.',flush=True)
 gray_missing=np.array([(i,i,i) for i in range(256) if (i,i,i) not in set(map(tuple,union))],dtype=np.uint8)
 union_with_grays=np.concatenate([union,gray_missing]);colored_missing=4096-len(union_with_grays)
 rng=np.random.default_rng(20260905);candidates=[]
 for sector in range(15):
  for sh,vh in [(0,0),(0,1),(1,0),(1,1)]:
   for h,s,v in rng.random((512,3)):
    candidates.append([int(x*255+.5) for x in colorsys.hsv_to_rgb((sector+h)/15,(sh+s)/2,(vh+v)/2)])
  for h in rng.random(128):candidates.append([int(x*255+.5) for x in colorsys.hsv_to_rgb((sector+h)/15,1,1)])
 candidates=np.unique(np.array(candidates,dtype=np.uint8),axis=0);labs=m.lab(candidates.astype(float));ulab=m.lab(union_with_grays.astype(float));nearest=np.full(len(candidates),np.inf)
 for i,l in enumerate(ulab):
  nearest=np.minimum(nearest,m.de(labs,l))
  if i%1000==0:print(f'Coverage initialization {i}/{len(union)}',flush=True)
 additions=list(gray_missing);distances=[None]*len(gray_missing)
 for _ in range(colored_missing):
  idx=int(np.argmax(nearest));assert nearest[idx]>0;additions.append(candidates[idx]);distances.append(float(nearest[idx]));nearest=np.minimum(nearest,m.de(labs,labs[idx]));nearest[idx]=-1
 # Keep each original 32x32 quadrant, replacing only repeated occurrences.
 seen=set();blocks=[];replacements=[];gray_j=0;colored_j=len(gray_missing)
 for trial,src in enumerate(source,1):
  block=src.copy()
  for pos,c in enumerate(src):
   if tuple(c) in seen:
    j=gray_j if c[0]==c[1]==c[2] else colored_j
    block[pos]=additions[j];replacements.append(dict(trial=trial,source_index=pos,original='#'+bytes(c).hex(),replacement='#'+bytes(additions[j]).hex(),insertion_delta_e_2000=distances[j]))
    if c[0]==c[1]==c[2]:gray_j+=1
    else:colored_j+=1
   seen.add(tuple(c))
  blocks.append(block.reshape(32,32,3))
 combined=np.concatenate([np.concatenate(blocks[:2],axis=1),np.concatenate(blocks[2:],axis=1)],axis=0).reshape(-1,3)
 assert set(map(tuple,union))<=set(map(tuple,combined));assert len(set(map(tuple,combined)))==4096
 report=dict(release_status='beta',method='Exact four-palette union plus all 256 sRGB grays retained; replace duplicate occurrences with deterministic farthest-point CIEDE2000 samples from a stratified HSV candidate pool. No source color is removed from the union.',source_sha256=hashes,source_entries=4096,source_unique_colors=len(union),exact_duplicates=missing,added_colors=missing,seed=20260905,candidate_count=len(candidates),added_grays=len(gray_missing),added_chromatic_colors=colored_missing,minimum_added_chromatic_separation=min(d for d in distances if d is not None),added_chromatic_colors_all_at_least_2_5=min(d for d in distances if d is not None)>=2.5,layout='64x64: Try 1 top left, Try 2 top right, Try 3 bottom left, Try 4 bottom right. Repeated occurrences are replaced at their original positions.',replacements=replacements,global_optimality_claim=False,separation_note='Source palettes do not meet 2.5 ΔE00. Existing close source pairs are preserved; all 256 grays are intentionally included regardless of distance; chromatic additions are selected for maximum available distance.')
 output.append(export(combined,'random-strata-combined-4096','randomStrataCombined4096','Random Strata Beta · combined + gap fill · 4096',report))
 (ROOT/'dist/random-strata.js').write_text(''.join(output));print('Minimum added separation:',min(d for d in distances if d is not None),flush=True)
if __name__=='__main__':main(Path(sys.argv[1]))
