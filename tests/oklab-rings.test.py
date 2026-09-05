"""Check the shipped ring palette's geometry, provenance and hard separation."""
from pathlib import Path
import importlib.util
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('m',ROOT/'scripts/build-critter-palettes.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
d=json.loads((ROOT/'dist/palettes/oklab-rings-1024.json').read_text())
rgb=np.array([list(bytes.fromhex(c[1:])) for c in d['colors']],dtype=np.uint8)
assert len(rgb)==len(set(map(tuple,rgb)))==1024
assert '#000000' in d['colors'] and '#ffffff' in d['colors']
samples=d['samples']
assert len(samples)==1344
assert sorted({p['L'] for p in samples})==[.1,.25,.4,.55,.7,.85,1.]
assert {p['h'] for p in samples}==set(range(0,360,15))
assert sorted({p['C'] for p in samples})==[r*.25/7 for r in range(8)]
target=np.array([(p['L'],p['C'],p['h']) for p in samples])
expected=m.encode(m.lch_linear(*target.T))
assert ['#'+bytes(c).hex() for c in expected]==[p['hex'] for p in samples]
grid={p['hex'] for p in samples}
parent=set(json.loads((ROOT/'dist/palettes/okhsv-sketch-1024.json').read_text())['colors'])
chosen=set(d['colors'])
assert len(grid)==1133 and len(grid&chosen)==837 and len(chosen-grid)==187
assert chosen<=grid|parent
assert all(p['selected']==(p['hex'] in chosen) for p in samples)
assert all(p['palette_index'] is None or d['colors'][p['palette_index']]==p['hex'] for p in samples)
assert len(d['palette_entries'])==1024
assert all(e['hex']==c and e['source']==('grid' if c in grid else 'okhsv') for e,c in zip(d['palette_entries'],d['colors']))
report=m.audit(rgb)
assert report['minimum_delta_e_2000']>=2 and report['pairs_below_2']==0
assert abs(report['minimum_delta_e_2000']-d['report']['minimum_delta_e_2000'])<1e-12
# At the end of the grid stage, all omitted grid candidates violate separation.
stage=(grid&chosen)|{'#000000'}
stage_lab=m.lab(np.array([list(bytes.fromhex(c[1:])) for c in stage],dtype=float))
for c in grid-chosen:
    lab=m.lab(np.array([list(bytes.fromhex(c[1:]))],dtype=float))[0]
    assert m.de(stage_lab,lab).min()<2
print('OK: 1344 grid targets; 837 grid + 187 legal borrowed colors; all pairs >= 2 ΔE00.')
