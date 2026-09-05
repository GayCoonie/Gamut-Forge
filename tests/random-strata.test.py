"""Numerical reference, byte-space geometry, and source-preservation regression checks."""
import colorsys,importlib.util,itertools,json,random,re,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('generator',ROOT/'scripts/generate-random-strata.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
class RandomStrataTests(unittest.TestCase):
 def test_reference_vectors(self):
  vectors=[list(map(float,l.split())) for l in (ROOT/'tests/ciede2000-reference.txt').read_text().splitlines() if l.strip()]
  self.assertEqual(len(vectors),34)
  for v in vectors:self.assertLess(abs(g.delta_e(v[:3],v[3:6])-v[6]),.00005)
 def test_exact_solver_against_exhaustive_search(self):
  for seed in range(12):
   rng=random.Random(seed);n=10;matrix=[[0.0]*n for _ in range(n)]
   for i in range(n):
    for j in range(i):matrix[i][j]=matrix[j][i]=rng.random()*5
   maxima=[min(matrix[i][j] for i,j in itertools.combinations(c,2)) for c in itertools.combinations(range(n),8)]
   best=max(maxima)
   self.assertIsNotNone(g.clique_eight(matrix,best))
   self.assertIsNone(g.clique_eight(matrix,best+1e-9))
   _,plan=g.sector_plan([None]*n,5,.2,matrix)
   self.assertAlmostEqual(plan['maximum_eight_point_distance'],best)
 def test_seeded_default_succeeds_reproducibly(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'palette.gpl';r=subprocess.run([sys.executable,str(ROOT/'scripts/generate-random-strata.py'),str(out),'--seed','42'],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr)
   self.assertEqual(out.read_bytes(),(ROOT/'dist/downloads/random-strata-corrected-example.gpl').read_bytes())
   report=json.loads(out.with_name('palette.gpl.audit.json').read_text());self.assertEqual(report['configured_constraint_violations'],0)
 def test_gray_pool_definition(self):
  pool=g.gray_pool();self.assertEqual(len(pool),15436);self.assertEqual(len(set(pool)),15436)
  self.assertTrue(all(max(c)-min(c)<=4 for c in pool));self.assertTrue(all((i,i,i) in pool for i in range(256)))
 def test_tested_example_byte_geometry(self):
  colors=[tuple(map(int,c)) for c in re.findall(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s',(ROOT/'dist/downloads/random-strata-corrected-example.gpl').read_text(),re.M)]
  self.assertEqual(len(colors),1024);self.assertEqual(len(set(colors)),1024)
  self.assertIn((0,0,0),colors);self.assertIn((255,255,255),colors)
  for i,c in enumerate(colors):
   y,x=divmod(i,32);block=(y//8)*4+x//8;cell=(y%8)*8+x%8
   if block==0:self.assertTrue(g.is_gray(c));continue
   self.assertFalse(g.is_gray(c))
   h,s,v=colorsys.rgb_to_hsv(*(c/255 for c in c));self.assertEqual(int(h*15),block-1)
   if cell<8:self.assertEqual((s,v),(1,1))
   else:self.assertEqual((int(s>=.5),int(v>=.5)),((1,1),(0,1),(1,0),(0,0))[(cell-8)//14])
 def test_beta_union(self):
  load=lambda stem:json.loads((ROOT/f'dist/palettes/{stem}.json').read_text())['colors']
  source=set().union(*(set(load(f'random-strata-try{i}')) for i in range(1,5)));combined=set(load('random-strata-combined-4096'))
  self.assertEqual(len(source),3949);self.assertEqual(len(combined),4096);self.assertTrue(source<=combined)
  self.assertTrue({'#'+bytes([i]*3).hex() for i in range(256)}<=combined)
if __name__=='__main__':unittest.main()
