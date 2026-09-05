// Run with: node tests/quantizer.test.cjs
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path'),root=path.join(__dirname,'..');
require('../dist/color-math.js');
const C=global.GamutColor;
const fixture=fs.readFileSync(path.join(__dirname,'ciede2000-reference.txt'),'utf8').trim().split(/\r?\n/).map(l=>l.trim().split(/\s+/).map(Number));
for(const [i,row] of fixture.entries()) {
  assert.equal(row.length,7);
  const a=row.slice(0,3),b=row.slice(3,6);
  assert.ok(Math.abs(C.deltaE00(a,b)-row[6]) < .000051,`Sharma case ${i+1}: ${C.deltaE00(a,b)} != ${row[6]}`);
  assert.ok(Math.abs(C.deltaE00(a,b)-C.deltaE00(b,a)) < 1e-10);
}
assert.equal(fixture.length,34);
assert.ok(C.rgbToLab(0,0,0).every(v=>v===0));
const white=C.rgbToLab(255,255,255);
assert.ok(Math.abs(white[0]-100)<.00001 && Math.hypot(white[1],white[2])<.0001);

const parentContext={window:{GAMUT_PALETTES:{}}};vm.createContext(parentContext);
for(const file of ['retro-source-union-4096.js','retro-source-union-1024.js'])
  vm.runInContext(fs.readFileSync(path.join(root,'dist',file),'utf8'),parentContext);
const parent=parentContext.window.GAMUT_PALETTES.retroSourceUnion4096.colors;
const subset=parentContext.window.GAMUT_PALETTES.retroSourceUnion1024.colors;
assert.equal(subset.length,1024);assert.equal(new Set(subset).size,1024);
assert.ok(subset.every(c=>parent.includes(c)));
assert.ok(subset.includes('#000000') && subset.includes('#ffffff'));
const rgb=hex=>[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16));
const points=subset.map(c=>({cie:C.prepareLab(C.rgbToLab(...rgb(c)))}));
const index=C.makeCiedeIndex(points);
let actualMinimum=Infinity;
for(let i=0;i<points.length;i++) for(let j=i+1;j<points.length;j++)
  actualMinimum=Math.min(actualMinimum,C.deltaE00(points[i].cie,points[j].cie));
const report=JSON.parse(fs.readFileSync(path.join(root,'dist/palettes/retro-source-union-1024.json'),'utf8')).report;
const appText=fs.readFileSync(path.join(root,'dist/app.js'),'utf8');
const parserCode=appText.slice(appText.indexOf('function uniqueColors'),appText.indexOf('function drawPalette'))
  +appText.slice(appText.indexOf('function parseTextPalette'),appText.indexOf('async function paletteFromImage'));
const importJSON=vm.runInNewContext(parserCode+'parseTextPalette(input)',{input:fs.readFileSync(path.join(root,'dist/palettes/retro-source-union-1024.json'),'utf8')});
assert.equal(importJSON.length,1024);
assert.ok(importJSON.every(c=>subset.includes(c)),'Import must ignore unselected seeds in JSON metadata');
const importGPL=vm.runInNewContext(parserCode+'parseTextPalette(input)',{input:fs.readFileSync(path.join(root,'dist/palettes/retro-source-union-1024.gpl'),'utf8')});
assert.equal(importGPL.length,1024);assert.ok(importGPL.every(c=>subset.includes(c)));
assert.ok(Math.abs(actualMinimum-report.minimum_delta_e_2000)<1e-9);
assert.ok(actualMinimum>4.2);

let state=12345;
const random=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state/4294967296;};
function brute(query,p=points) {
  let id=0,d=Infinity;
  for(let i=0;i<p.length;i++) { const e=C.deltaE00Squared(query,p[i].cie); if(e<d){d=e;id=i;} }
  return [id,d];
}
for(let i=0;i<150;i++) {
  const q=C.rgbToLab(...[0,0,0].map(()=>Math.floor(random()*256)));
  const b=brute(q),fast=C.nearestCiede2000(points,q,Math.floor(random()*points.length));
  assert.equal(fast[0],b[0]);assert.equal(fast[1],b[1]);
  const indexed=C.nearestCiede2000(points,q,Math.floor(random()*points.length),index);
  assert.equal(indexed[0],b[0]);assert.equal(indexed[1],b[1]);
}
function runWorker(palette,pixels,w,h,engine,dither='none',preserveAlpha=true,strength=.8) {
  const messages=[];
  const context={performance,Uint8ClampedArray,Float32Array,self:{postMessage:m=>messages.push(m)}};
  vm.createContext(context);
  context.importScripts=p=>vm.runInContext(fs.readFileSync(path.join(root,'dist',p),'utf8'),context);
  vm.runInContext(fs.readFileSync(path.join(root,'dist/quantize-worker.js'),'utf8'),context);
  context.self.onmessage({data:{type:'quantize',buffer:new Uint8ClampedArray(pixels).buffer,width:w,height:h,palette,engine,dither,preserveAlpha,strength}});
  const done=messages.find(m=>m.type==='done');
  assert.ok(done,JSON.stringify(messages));
  return {...done,pixels:Array.from(new Uint8ClampedArray(done.buffer))};
}
const pixels=Array.from({length:64},(_,i)=>[...Array.from({length:3},()=>Math.floor(random()*256)),i%7===0?0:i%7===1?128:255]).flat();
for(const engine of ['oklab','ciede2000']) for(const dither of ['none','floyd']) for(const preserve of [true,false]) {
  const result=runWorker(subset,pixels,8,8,engine,dither,preserve);
  const legal=new Set(subset.map(h=>rgb(h).join(',')));
  assert.equal(result.stats.metric,engine==='oklab'?'OK':'00');
  assert.ok(Number.isFinite(result.stats.mean));
  for(let i=0;i<pixels.length;i+=4) {
    assert.equal(result.pixels[i+3],preserve?pixels[i+3]:255);
    if(preserve && pixels[i+3]===0) assert.deepEqual(result.pixels.slice(i,i+4),pixels.slice(i,i+4));
    else {
      assert.ok(legal.has(result.pixels.slice(i,i+3).join(',')));
      if(engine==='ciede2000' && dither==='none') {
        assert.deepEqual(result.pixels.slice(i,i+3),rgb(subset[brute(C.rgbToLab(...pixels.slice(i,i+3)))[0]]));
      }
    }
  }
}
for(const engine of ['oklab','ciede2000']) {
  const exactPixels=subset.flatMap(h=>[...rgb(h),255]);
  const result=runWorker(subset,exactPixels,32,32,engine);
  assert.deepEqual(result.pixels,Array.from(exactPixels));assert.ok(result.stats.mean<1e-10);
  const zeroDither=runWorker(subset,pixels,8,8,engine,'floyd',true,0);
  assert.deepEqual(zeroDither.pixels,runWorker(subset,pixels,8,8,engine).pixels);
  const transparent=runWorker(subset,[12,34,56,0],1,1,engine);
  assert.equal(transparent.stats.used,0);assert.equal(transparent.stats.mean,0);
  assert.deepEqual(runWorker(['#ffffff'],[1,2,3,255],1,1,engine).pixels,[255,255,255,255]);
}
console.log(`PASS: 34 Sharma reference pairs; RGB conversion; exact pruning vs full scan; both engines/dithering/alpha; 1024 unique parent colors; minimum ΔE00 ${actualMinimum.toFixed(9)}.`);
