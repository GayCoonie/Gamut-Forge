"""Evaluate atlas-level holdouts; publish aggregate metrics, never game images.

Requires the owner's source archive. Same sampler as the design generator.
Run with --source-zip PATH --review-dir PRIVATE_DIRECTORY.
"""
from pathlib import Path
import argparse
import importlib.util
import io
import json
import zipfile
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build',ROOT/'scripts/build-critter-palettes.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


def match(rgb,palette):
    query=b.lab(rgb.astype(float));target=b.lab(palette.astype(float))
    best=np.full(len(rgb),np.inf);ids=np.zeros(len(rgb),dtype=int)
    for i,ref in enumerate(target):
        ds=b.de(query,ref);update=ds<best
        ids[update]=i;best[update]=ds[update]
    return ids,best


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-zip',required=True);p.add_argument('--review-dir',required=True);args=p.parse_args()
    review=Path(args.review_dir);review.mkdir(parents=True,exist_ok=True)
    records=[r for r in b.samples_from_zip(args.source_zip) if r[2]]
    # Independent atlases; 512 of each deterministic 4096-pixel holdout sample.
    rgb=np.concatenate([r[3][::8][:512] for r in records])
    stems=['static-bloom-1024','static-bloom-4096','rgb343-control','retro-source-union-1024','retro-source-union-4096']
    palettes=[]
    for stem in stems:
        path=ROOT/'dist/palettes'/f'{stem}.txt'
        if path.exists(): colors=path.read_text().splitlines()
        else:
            text=(ROOT/'dist'/f'{stem}.js').read_text();colors=json.loads(text.split('=',1)[1].strip().rstrip(';'))['colors']
        palettes.append(np.array([list(bytes.fromhex(c.lstrip('#'))) for c in colors],dtype=np.uint8))
    rows=[]
    for stem,palette in zip(stems,palettes):
        ids,ds=match(rgb,palette);metrics=[];offset=0
        for name,category,_,sample in records:
            n=len(sample[::8][:512]);part=ds[offset:offset+n];offset+=n
            metrics.append(dict(category=category,mean=float(part.mean()),p95=float(np.percentile(part,95))))
        means=[np.mean([m['mean'] for m in metrics if m['category']==cat]) for cat in sorted(set(m['category'] for m in metrics))]
        row=dict(palette=stem,mean_delta_e_2000=float(ds.mean()),p95_delta_e_2000=float(np.percentile(ds,95)),maximum_delta_e_2000=float(ds.max()),category_balanced_mean_delta_e_2000=float(np.mean(means)))
        rows.append(row);print(json.dumps(row),flush=True)
    report=dict(metric='Exact nearest CIEDE2000, no dithering',holdout_atlases=len(records),sample_pixels=len(rgb),
        interpretation='Lower error is fidelity, not a pixel-art quality score. No palette can guarantee coherent spatial clusters.',results=rows)
    (ROOT/'dist/palettes/static-bloom-evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    # Actual full-resolution 128px crops: no smoothing, recoloring or resampling
    # before quantization. Composite alpha only for the final review sheet.
    z=zipfile.ZipFile(args.source_zip)
    crops=[('/tiles/26-',(128,1280,256,1408),'Rock / fallen leaves'),
           ('/tiles/25-',(128,640,256,768),'Wood / interior'),
           ('/tiles/26-',(0,0,128,128),'Snow / cool shadows'),
           ('/critters/class-05',(240,1536,368,1664),'Critter / fabric')]
    ims=[]
    for fragment,box,label in crops:
        name=next(n for n in z.namelist() if fragment in n and n.endswith('.png'))
        im=Image.open(io.BytesIO(z.read(name))).convert('RGBA').crop(box);ims.append(im)
    strip=np.concatenate([np.asarray(im) for im in ims],axis=1)
    visible=strip[:,:,3].ravel()>0
    flat=strip[:,:,:3].reshape(-1,3)
    unique,inverse=np.unique(flat[visible],axis=0,return_inverse=True)
    panels=[Image.fromarray(strip)]
    for stem,palette in zip(stems,palettes):
        ids,_=match(unique,palette)
        # Assign through the full contiguous RGBA buffer, not a strided copy.
        rgba=strip.reshape(-1,4).copy();rgba[visible,:3]=palette[ids[inverse]]
        im=Image.fromarray(rgba.reshape(strip.shape));im.save(review/f'{stem}-crops.png');panels.append(im)
    canvas=Image.new('RGB',(1056,6*290),(20,19,27));draw=ImageDraw.Draw(canvas)
    for i,(label,im) in enumerate(zip(['Original']+stems,panels)):
        draw.text((16,i*290+6),label,fill='white')
        im=im.resize((1024,256),Image.Resampling.NEAREST)
        canvas.paste(im,(16,i*290+28),im)
    canvas.save(review/'static-bloom-comparison.png')
    print('Review: '+str(review/'static-bloom-comparison.png'),flush=True)


if __name__=='__main__':main()
