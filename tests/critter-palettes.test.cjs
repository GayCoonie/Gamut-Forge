// Independent JS verification of Python-generated palette data.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.join(__dirname,'..');require('../dist/color-math.js');const C=global.GamutColor;
const context={window:{GAMUT_PALETTES:{}}};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'dist/critter-palettes.js'),'utf8'),context);
const palettes=context.window.GAMUT_PALETTES;
const specs=[['staticBloom1024','static-bloom-1024',1024],['staticBloom4096','static-bloom-4096',4096],['rgb343Control','rgb343-control',1024]];
for(const [key,stem,n] of specs){
 const colors=Array.from(palettes[key].colors),file=ext=>fs.readFileSync(path.join(root,`dist/palettes/${stem}.${ext}`),'utf8');
 assert.equal(colors.length,n);assert.equal(new Set(colors).size,n);assert.ok(colors.includes('#000000')&&colors.includes('#ffffff'));
 assert.deepEqual(file('txt').trim().split(/\r?\n/),colors);
 const data=JSON.parse(file('json'));assert.deepEqual(data.colors,colors);
 const gpl=file('gpl').split(/\r?\n/).filter(l=>/^\s*\d+\s+\d+\s+\d+/.test(l)).map(l=>'#'+l.trim().split(/\s+/).slice(0,3).map(v=>(+v).toString(16).padStart(2,'0')).join(''));
 assert.deepEqual(gpl,colors);
 const lab=colors.map(hex=>C.prepareLab(C.rgbToLab(...[1,3,5].map(p=>parseInt(hex.slice(p,p+2),16)))));
 let min=Infinity,below=0;
 for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){const d=C.deltaE00(lab[i],lab[j]);min=Math.min(min,d);if(d<2)below++;}
 assert.ok(Math.abs(min-data.report.minimum_delta_e_2000)<1e-9);assert.equal(below,data.report.pairs_below_2);
 if(key!=='rgb343Control'){assert.ok(min>=2);assert.equal(below,0);}
 console.log(`${key}: ${n} unique; audited all pairs; minimum ΔE00 ${min.toFixed(9)}.`);
}
const large=new Set(palettes.staticBloom4096.colors);assert.ok(palettes.staticBloom1024.colors.every(c=>large.has(c)));
const cube=new Set(palettes.rgb343Control.colors);
for(let r=0;r<8;r++)for(let g=0;g<16;g++)for(let b=0;b<8;b++){
 const hex='#'+[Math.round(r*255/7),g*17,Math.round(b*255/7)].map(v=>v.toString(16).padStart(2,'0')).join('');assert.ok(cube.has(hex));
}
const html=fs.readFileSync(path.join(root,'dist/index.html'),'utf8');for(const [key]of specs)assert.ok(html.includes(`value="${key}"`));
assert.ok(html.includes('./critter-palettes.js'));console.log('PASS: nested palettes; complete RGB343 cube; TXT/GPL/JSON equality; page integration.');
