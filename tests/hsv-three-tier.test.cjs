const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path'),root=path.join(__dirname,'..');require('../dist/color-math.js');
const C=global.GamutColor,ctx={window:{GAMUT_PALETTES:{}}};vm.createContext(ctx);
function hex(h,s,v){
 const c=v*s,x=c*(1-Math.abs(h/60%2-1)),m=v-c;
 const sector=Math.floor(h/60),parts=[[c,x,0],[x,c,0],[0,c,x],[0,x,c],[x,0,c],[c,0,x]][sector];
 return '#'+parts.map(a=>Math.floor((a+m)*255+.5+1e-12).toString(16).padStart(2,'0')).join('');
}
for(const suffix of ['64','10','sketch']){
 const stem='hsv-three-tier-'+suffix,read=ext=>fs.readFileSync(path.join(root,'dist/palettes',stem+ext),'utf8');
 vm.runInContext(fs.readFileSync(path.join(root,'dist',stem+'.js'),'utf8'),ctx);
 const geometry=JSON.parse(read('-geometry.json')),data=JSON.parse(read('.json'));
 const palette=new Set(data.colors),expected=[];
 assert.equal(palette.size,1024);assert.equal(data.colors.length,1024);
 assert.equal(geometry.hue_step_degrees,5.625);
 for(const [t,tier] of geometry.tiers.entries()){
  assert.equal(tier.points.length,9);assert.equal(tier.hue_count,[64,32,16][t]);
  for(const [s,v] of tier.points){
   assert.ok(s>=tier.lower&&v>=tier.lower&&s<=1&&v<=1);
   if(t)assert.ok(Math.min(s,v)<tier.upper);
   if(suffix==='10')for(const a of [s,v])assert.ok(Math.abs(a*10-Math.round(a*10))<1e-10);
  }
  if(t&&suffix==='64')for(let j=0;j<3;j++){
   const q=tier.upper+(tier.lower-tier.upper)*(j+1)/3;
   assert.deepEqual(tier.points.slice(j*3,j*3+3),[[q,1],[q,q],[1,q]]);
  }
  if(suffix==='sketch'){
   const rows=new Map();for(const [s,v] of tier.points)rows.set(v,(rows.get(v)||0)+1);
   assert.deepEqual([...rows.values()],[[3,3,3],[2,2,5],[3,2,4]][t]);
   if(t===0)assert.ok(tier.points.every(([s,v])=>[2/3,5/6,1].includes(s)&&[2/3,5/6,1].includes(v)));
   if(t===1)assert.ok(tier.points.every(([s,v])=>Math.abs(s*6-Math.round(s*6))<1e-10));
  }
  for(let i=0;i<64;i+=tier.hue_stride)for(const [s,v]of tier.points)expected.push(hex(i*5.625,s,v));
 }
 assert.equal(expected.length,1008);
 for(let i=0;i<16;i++)expected.push('#'+(i*17).toString(16).padStart(2,'0').repeat(3));
 assert.equal(new Set(expected).size,1024);assert.ok(expected.every(c=>palette.has(c)));
 const key={64:'hsvThreeTier64',10:'hsvThreeTier10',sketch:'hsvThreeTierSketch'}[suffix];assert.deepEqual(Array.from(ctx.window.GAMUT_PALETTES[key].colors),data.colors);
 assert.deepEqual(read('.txt').trim().split(/\r?\n/),data.colors);
 const labs=data.colors.map(h=>C.rgbToLab(...[1,3,5].map(p=>parseInt(h.slice(p,p+2),16))));
 let min=Infinity,below=0;
 for(let i=0;i<1024;i++)for(let j=i+1;j<1024;j++){const d=C.deltaE00(labs[i],labs[j]);min=Math.min(min,d);if(d<2)below++;}
 assert.ok(Math.abs(min-data.report.minimum_delta_e_2000)<1e-9);assert.equal(below,data.report.pairs_below_2);
 console.log(`${stem}: 1024 unique; exact HSV reconstruction, bands, nesting, gray ramp, exports and all-pairs audit pass.`);
}
