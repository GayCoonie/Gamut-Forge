(async()=>{
  const base='./palettes/',stem='okhwb-walks-1024';
  const responses=await Promise.all([stem+'-atlas.svg',stem+'.json','okhwb-staggered-1024.json','okhwb-triangle-1024.json'].map(p=>fetch(base+p,{cache:'no-cache'})));
  if(responses.some(r=>!r.ok))throw Error('Palette assets could not be loaded. Reload to retry.');
  const [source,v3,v2,v1]=await Promise.all([responses[0].text(),...responses.slice(1).map(r=>r.json())]);
  const svg=new DOMParser().parseFromString(source,'image/svg+xml');
  if(svg.querySelector('parsererror'))throw Error('The triangle atlas could not be read.');
  const groups=[...svg.querySelectorAll('g[data-hue]')],ns='http://www.w3.org/2000/svg';
  if(groups.length!==48)throw Error('The triangle atlas is incomplete.');
  const atlas=document.querySelector('#atlas'),version=document.querySelector('#version');
  const inspect=text=>document.querySelector('#inspect').textContent=text;
  function panel(group){
    const node=document.createElementNS(ns,'svg');node.setAttribute('viewBox','0 0 220 230');node.setAttribute('role','img');
    node.setAttribute('aria-label',group.dataset.hue+' degree source-hue triangle');
    const copy=document.importNode(group,true);copy.removeAttribute('transform');node.append(copy);return node;
  }
  const patterns=document.querySelector('#patterns');patterns.replaceChildren(...[0,2,4,1,3,5].map(i=>panel(groups[i])));
  function draw(){
    const current={v1,v2,v3}[version.value];
    atlas.replaceChildren(...groups.map((group,hue)=>{
      const node=panel(group);
      if(current!==v3){
        node.querySelectorAll('.walk-overlay').forEach(mark=>mark.remove());
        const texts=node.querySelectorAll('g[data-hue] > text');
        texts[1].textContent=current===v1?'V1 · fixed hue':'V2 · staggered hues';
        node.querySelectorAll('polygon').forEach(poly=>{
          const index=Number(poly.dataset.cell),p=current.samples[index<21?hue*21+index:1008+index-21];
          poly.setAttribute('fill',p.hex);
          poly.querySelector('title').textContent=`${p.hex} · ${version.value.toUpperCase()} · H ${p.h.toFixed(6)}° · W ${p.w.toFixed(4)} · B ${p.b.toFixed(4)}`;
        });
      }
      return node;
    }));
    inspect(`${version.value.toUpperCase()}: point to a cell to inspect its color and coordinates.`);
    document.querySelector('#paths').disabled=current!==v3;
  }
  for(const target of [atlas,patterns])target.addEventListener('pointerover',event=>{
    const p=event.target.closest('polygon');if(p)inspect(p.querySelector('title').textContent);
  });
  version.addEventListener('change',draw);
  document.querySelector('#paths').addEventListener('change',event=>atlas.classList.toggle('show-paths',event.target.checked));
  for(const p of v3.samples.filter(p=>p.kind==='gray')){
    const button=document.createElement('button');button.style.background=p.hex;
    button.title=`${p.hex} · W ${p.w.toFixed(4)} · B ${p.b.toFixed(4)}`;button.setAttribute('aria-label',button.title);
    button.onclick=()=>inspect(button.title);button.onfocus=button.onclick;document.querySelector('#grays').append(button);
  }
  const r=v3.report;
  document.querySelector('#audit').textContent=`${r.unique_colors.toLocaleString()} distinct RGB colors; ${r.sampled_hue_count.toLocaleString()} sampled hue angles; ${r.exact_colors_shared_with_v1} RGB colors shared with v1. V3 minimum ${r.minimum_delta_e_2000.toFixed(3)} ΔE00, with ${r.pairs_below_2} pairs below 2. V2 minimum ${v2.report.minimum_delta_e_2000.toFixed(3)}; v1 minimum ${v1.report.minimum_delta_e_2000.toFixed(3)}. Measurements describe the result; they do not select its colors.`;
  draw();
})().catch(error=>{document.querySelector('#inspect').textContent=error.message;});
