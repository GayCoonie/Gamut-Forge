// Execute the actual page loader and version switch against real shipped assets.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),cp=require('node:child_process');
const root=path.join(__dirname,'..'),dist=path.join(root,'dist');
const tree=JSON.parse(cp.execFileSync('python',['-c',`import json,xml.etree.ElementTree as E
r=E.parse('dist/palettes/okhwb-walks-1024-atlas.svg').getroot()
def node(e):return dict(tag=e.tag.split('}')[-1],attrs=e.attrib,text=e.text or '',children=[node(c) for c in e])
print(json.dumps(node(r)))`],{cwd:root,maxBuffer:8*1024*1024}));
class Element{
 constructor(tag,attrs={},text=''){this.tag=tag;this.attrs={...attrs};this.textContent=text;this.children=[];this.listeners={};this.style={};this.classList={toggle:()=>{}};}
 get dataset(){return Object.fromEntries(Object.entries(this.attrs).filter(([k])=>k.startsWith('data-')).map(([k,v])=>[k.slice(5),v]));}
 setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}
 append(...nodes){for(const n of nodes){n.parent=this;this.children.push(n);}}
 replaceChildren(...nodes){this.children=[];this.append(...nodes);}
 remove(){this.parent.children=this.parent.children.filter(c=>c!==this);}
 addEventListener(k,fn){this.listeners[k]=fn;}
 matches(s){if(s[0]==='.')return (this.attrs.class||'').split(' ').includes(s.slice(1));const m=s.match(/^(\w+)(?:\[([^\]]+)\])?$/);return !!m&&this.tag===m[1]&&(!m[2]||Object.hasOwn(this.attrs,m[2]));}
 querySelectorAll(s){if(s.includes(' > ')){const [parent,child]=s.split(' > ');return this.querySelectorAll(parent).flatMap(p=>p.children.filter(c=>c.matches(child)));}return this.children.flatMap(c=>[...(c.matches(s)?[c]:[]),...c.querySelectorAll(s)]);}
 querySelector(s){return this.querySelectorAll(s)[0]||null;}
 clone(){const n=new Element(this.tag,this.attrs,this.textContent);n.append(...this.children.map(c=>c.clone()));return n;}
}
function fromTree(t){const n=new Element(t.tag,t.attrs,t.text);n.append(...t.children.map(fromTree));return n;}
(async()=>{
 const ids=Object.fromEntries(['atlas','version','inspect','patterns','paths','grays','audit'].map(id=>[id,new Element('div')]));ids.version.value='v3';
 const c={document:{querySelector:s=>ids[s.slice(1)],createElementNS:(_,tag)=>new Element(tag),createElement:tag=>new Element(tag),importNode:n=>n.clone()},DOMParser:class{parseFromString(){return fromTree(tree);}},fetch:async p=>({ok:true,text:async()=>fs.readFileSync(path.join(dist,p),'utf8'),json:async()=>JSON.parse(fs.readFileSync(path.join(dist,p),'utf8'))})};
 vm.createContext(c);await vm.runInContext(fs.readFileSync(path.join(dist,'okhwb-walks-page.js'),'utf8'),c);
 assert.equal(ids.patterns.children.length,6,ids.inspect.textContent);assert.equal(ids.grays.children.length,16);
 for(const [version,stem] of [['v3','okhwb-walks-1024'],['v2','okhwb-staggered-1024'],['v1','okhwb-triangle-1024'],['v3','okhwb-walks-1024']]){
  ids.version.value=version;ids.version.listeners.change();assert.equal(ids.atlas.children.length,48);
  const data=JSON.parse(fs.readFileSync(path.join(dist,'palettes',stem+'.json')));
  ids.atlas.children.forEach((panel,h)=>{
   const colors=panel.querySelectorAll('polygon').map(p=>p.attrs.fill);
   assert.deepEqual(colors,data.colors.slice(h*21,(h+1)*21).concat(data.colors.slice(-16)));
   assert.equal(panel.querySelectorAll('.walk-overlay').length,version==='v3'?1:0);
  });
  assert.equal(ids.paths.disabled,version!=='v3');
 }
 console.log('Passed: actual atlas loader, six pattern diagrams, 48 panels, 16 grays, and v3/v2/v1/v3 color switching.');
})().catch(e=>{console.error(e);process.exitCode=1;});
