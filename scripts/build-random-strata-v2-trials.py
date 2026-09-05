"""Import Try 5–8; preserve their union, add RGB3 grays and older random colors.
Usage: python scripts/build-random-strata-v2-trials.py /path/to/uploads
NumPy/Pillow required. No new RGB colors are synthesized beyond the gray ramp.
"""
import sys,re,json,hashlib,importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/palettes'
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-random-strata.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base);m=base.m

def geometry_audit(rgb):
 labs=m.lab(rgb.astype(float));kinds=[];gray=[];vivid=[];quadrants=[];grid_matches=True
 import colorsys
 for i,c in enumerate(rgb):
  y,x=divmod(i,32);block=y//8*4+x//8;cell=y%8*8+x%8
  neutral=int(max(c))-int(min(c))<=4
  if neutral:gray.append(i);kinds.append('gray')
  elif min(c)==0 and max(c)==255:vivid.append(i);kinds.append('vivid')
  else:quadrants.append(i);kinds.append('quadrant')
  if block==0:grid_matches &= neutral
  else:
   h,s,v=colorsys.rgb_to_hsv(*(int(x)/255 for x in c));grid_matches &= not neutral and int(h*15)==block-1
   if cell<8:grid_matches &= s==v==1
   else:grid_matches &= (int(s>=.5),int(v>=.5))==((1,1),(0,1),(1,0),(0,0))[(cell-8)//14]
 assert (0,0,0) in map(tuple,rgb) and (255,255,255) in map(tuple,rgb)
 assert len(gray)==64
 minima={}
 for i in range(1,len(rgb)):
  distances=m.de(labs[:i],labs[i])
  for j,d in enumerate(distances):
   key=' / '.join(sorted([kinds[i],kinds[j]]));minima[key]=min(float(d),minima.get(key,float('inf')))
 return dict(near_gray_count=len(gray),vivid_count=len(vivid),quadrant_count=len(quadrants),black_present=True,white_present=True,order_matches_generator_grid=bool(grid_matches),minimum_by_pair_class=minima,seed='Not supplied; no seed inferred from RGB output.',classification='Pair classes inferred from actual byte RGB, independent of file ordering.')


def main(folder):
 source=[];hashes={};output=[]
 for i in range(5,9):
  path=folder/f'try{i}.gpl';raw=path.read_bytes();hashes[path.name]=hashlib.sha256(raw).hexdigest()
  a=np.array([tuple(map(int,c)) for c in re.findall(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s',raw.decode(),re.M)],dtype=int)
  assert a.shape==(1024,3) and a.min()>=0 and a.max()<=255 and len(set(map(tuple,a)))==1024
  a=a.astype(np.uint8);source.append(a)
  report=dict(source_file=path.name,source_sha256=hashes[path.name],method='Verbatim user-supplied v2 trial; RGB values and row-major order preserved.',modified_colors=False,layout='32x32 swatches in supplied file order; an exported image palette may reorder generator cells.',**geometry_audit(a))
  output.append(base.export(a,f'random-strata-try{i}',f'randomStrataTry{i}',f'Random Strata v2 · Try {i} · 1024',report))
 union=np.array(list(dict.fromkeys(map(tuple,np.concatenate(source)))),dtype=np.uint8);existing=set(map(tuple,union));n_source=len(union)
 levels=[int(i*255/7+.5) for i in range(8)];grays=np.array([(v,v,v) for v in levels if (v,v,v) not in existing],dtype=np.uint8)
 retained=np.concatenate([union,grays]);existing=set(map(tuple,retained));needed=4096-len(retained)
 old={};old_hashes={}
 for i in range(1,5):
  path=OUT/f'random-strata-try{i}.json';old_hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
  for c in json.loads(path.read_text())['colors']:old.setdefault(tuple(bytes.fromhex(c[1:])),[]).append(i)
 candidates=np.array(sorted(set(old)-existing),dtype=np.uint8);labs=m.lab(candidates.astype(float));nearest=np.full(len(candidates),np.inf)
 for lab in m.lab(retained.astype(float)):nearest=np.minimum(nearest,m.de(labs,lab))
 additions=[];distances=[]
 for _ in range(needed):
  idx=int(np.argmax(nearest));assert nearest[idx]>0;additions.append(candidates[idx]);distances.append(float(nearest[idx]));nearest=np.minimum(nearest,m.de(labs,labs[idx]));nearest[idx]=-1
 seen=set();blocks=[];replacements=[];gi=ci=0
 for trial,src in enumerate(source,5):
  block=src.copy()
  for pos,c in enumerate(src):
   if tuple(c) in seen:
    if tuple(c) in [(0,0,0),(255,255,255)]:
     replacement=grays[gi];gi+=1;origin=dict(kind='3-bit gray',level=int(replacement[0]))
    else:
     replacement=additions[ci];origin=dict(kind='earlier random trial',trials=old[tuple(replacement)],insertion_delta_e_2000=distances[ci]);ci+=1
    block[pos]=replacement;replacements.append(dict(trial=trial,source_index=pos,original='#'+bytes(c).hex(),replacement='#'+bytes(replacement).hex(),**origin))
   seen.add(tuple(c))
  blocks.append(block.reshape(32,32,3))
 assert gi==len(grays) and ci==needed
 combined=np.concatenate([np.concatenate(blocks[:2],axis=1),np.concatenate(blocks[2:],axis=1)],axis=0).reshape(-1,3)
 assert set(map(tuple,union))<=set(map(tuple,combined));assert len(set(map(tuple,combined)))==4096
 report=dict(method='Preserve exact union of Try 5–8. Replace repeated black/white occurrences with missing full-range RGB3 gray levels. Fill other duplicates by deterministic CIEDE2000 farthest-point selection from Try 1–4 only.',source_sha256=hashes,earlier_export_sha256=old_hashes,source_entries=4096,source_unique_colors=n_source,exact_duplicate_occurrences=4096-n_source,gray_levels=levels,added_grays=len(grays),earlier_random_fillers=needed,eligible_earlier_random_candidates=len(candidates),minimum_earlier_filler_separation=min(distances),replacements=replacements,layout='64x64, Try 5 upper left, Try 6 upper right, Try 7 lower left, Try 8 lower right; only repeated occurrences replaced.',separation_note='Existing cross-trial close pairs and the requested gray ramp are retained. The union does not inherit each individual trial\'s pairwise thresholds.',global_optimality_claim=False)
 output.append(base.export(combined,'random-strata-v2-combined-4096','randomStrataV2Combined4096','Random Strata v2 · combined 5–8 · 4096',report))
 (ROOT/'dist/random-strata-v2-trials.js').write_text(''.join(output));print(json.dumps(dict(source_unique=n_source,gray_fillers=len(grays),older_fillers=needed,minimum_filler_separation=min(distances))),flush=True)
if __name__=='__main__':main(Path(sys.argv[1]))
