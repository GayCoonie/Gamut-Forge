const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const dist = path.join(__dirname, '../dist');
const catalog = JSON.parse(fs.readFileSync(path.join(dist, 'palette-catalog.json')));
const script = fs.readFileSync(path.join(dist, 'palette-guide.js'), 'utf8');
function harness(key, fail = '') {
  const rects = [], nodes = {};
  const ctx = {clearRect(){rects.length = 0;}, fillRect(...args){assert(args.every(Number.isFinite));rects.push({color:this.fillStyle,args});}, beginPath(){},moveTo(){},lineTo(){},stroke(){},fillText(){}};
  for (const id of ['palette','view','chart','stats','description','title','usePalette','downloads','tooltip','caption']) {
    nodes[id] = {value:'',textContent:'',listeners:{},replaceChildren(...children){this.children=children;this.value=children[0]?.value;},append(){},addEventListener(type,fn){this.listeners[type]=fn;}};
  }
  Object.assign(nodes.chart, {width:1440,height:1050,getContext:()=>ctx,getBoundingClientRect:()=>({left:0,top:0,width:1440,height:1050})});
  nodes.view.value = 'lab';
  const sandbox = {URLSearchParams,location:{search:'?palette='+key},history:{replaceState(){}},Option:function(name,value){this.name=name;this.value=value;},document:{querySelector:s=>nodes[s.slice(1)],createElement:()=>({})},fetch:async(url,options)=>{
    assert.equal(options.cache,'no-cache');
    return {ok:url!==fail,json:async()=>JSON.parse(fs.readFileSync(path.join(dist,url)))};
  }};
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(dist,'color-math.js'),'utf8'), sandbox);
  return {sandbox,nodes,rects,run:()=>vm.runInContext(script,sandbox)};
}
(async()=>{
  // No palette JavaScript bundles are present: both views must use JSON alone.
  for (const palette of catalog) {
    const h = harness(palette.key);
    await h.run();
    assert(!h.nodes.stats.textContent.includes('could not'), h.nodes.tooltip.textContent);
    assert.equal(h.rects.length, palette.count+1, palette.key+' Lab');
    h.nodes.view.value='swatches';
    await h.nodes.view.listeners.change();
    assert.equal(h.rects.length, palette.count+1, palette.key+' swatches');
    assert.equal(new Set(h.rects.slice(1).map(r=>r.color)).size,palette.count);
    for (const {args:[x,y,w,height]} of h.rects.slice(1)) {
      assert(x>=0 && y>=0 && x+w<=1440.001 && y+height<=1440.001);
    }
  }
  for (const fail of ['./palette-catalog.json','./palettes/okhwb-triangle-1024.json']) {
    const h=harness('okhwbTriangle1024',fail);await h.run();
    assert(h.nodes.stats.textContent.includes('could not be loaded'));
    assert(h.nodes.tooltip.textContent.includes('Reload'));
    assert.equal(h.rects.length,0);
  }
  // A slow previous request must not overwrite the latest selection.
  const h=harness('okhwbTriangle1024');await h.run();
  const originalFetch=h.sandbox.fetch;let release;
  h.sandbox.fetch=(url,options)=>url.includes('okhwb-triangle-1024.json')?new Promise(resolve=>{release=()=>resolve(originalFetch(url,options));}):originalFetch(url,options);
  const pending=h.nodes.palette.listeners.change();
  h.nodes.palette.value='oklabRings1024';await h.nodes.palette.listeners.change();
  const title=h.nodes.title.textContent;release();await pending;
  assert.equal(h.nodes.title.textContent,title);
  assert(title.includes('Oklab'));
  console.log(`Passed: ${catalog.length} palettes in both modes, failed loads, and stale-response protection.`);
})().catch(error=>{console.error(error);process.exitCode=1;});
