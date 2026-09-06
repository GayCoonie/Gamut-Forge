(async()=>{
 const stem='./palettes/martian-expansion-1024';
 const responses=await Promise.all([fetch(stem+'-atlas.svg',{cache:'no-cache'}),fetch(stem+'.json',{cache:'no-cache'})]);
 if(responses.some(r=>!r.ok))throw Error('Palette assets could not be loaded. Reload to retry.');
 const [source,data]=await Promise.all([responses[0].text(),responses[1].json()]);
 const xml=new DOMParser().parseFromString(source,'image/svg+xml');
 if(xml.querySelector('parsererror'))throw Error('The wheel atlas could not be read.');
 if(data.colors.length!==1024||xml.querySelectorAll('[data-index]').length!==1024)throw Error('The palette atlas is incomplete.');
 const atlas=document.querySelector('#atlas');atlas.append(document.importNode(xml.documentElement,true));
 function inspect(index){
  const p=data.samples[index],family=p.family===null?'Shared gray':data.families[p.family].label;
  document.querySelector('#inspect').textContent=`${p.hex} · ${family} · ${p.source_name?'Warren Mars anchor: '+p.source_name:p.kind.replaceAll('-',' ')}${p.hsv?' · HSV '+p.hsv.map((v,i)=>(i?v*100:v).toFixed(2)+(i?'%':'°')).join(' / '):''}`;
 }
 atlas.addEventListener('pointerover',e=>{const p=e.target.closest('[data-index]');if(p)inspect(Number(p.dataset.index));});
 atlas.addEventListener('click',e=>{const p=e.target.closest('[data-index]');if(p)inspect(Number(p.dataset.index));});
 document.querySelector('#outlines').addEventListener('change',e=>atlas.classList.toggle('hide-outlines',!e.target.checked));
 const ramps=document.querySelector('#ramps');
 for(const family of data.families){
  const card=document.createElement('section');card.className='ramp';const title=document.createElement('h3');title.textContent=family.label;card.append(title);
  for(const [start,end,extra] of [[0,13,''],[13,21,' muted-strip']]){
   const row=document.createElement('div');row.className='strip'+extra;
   for(let cell=start;cell<end;cell++){
    const index=family.index*21+cell,p=data.samples[index],b=document.createElement('button');b.type='button';b.style.background=p.hex;
    b.className=p.kind==='source-anchor'?'anchor':'';b.title=p.hex+' · '+(p.source_name||p.kind);b.setAttribute('aria-label',b.title);
    b.onpointerenter=()=>inspect(index);b.onclick=()=>inspect(index);b.onfocus=()=>inspect(index);row.append(b);
   }card.append(row);
  }ramps.append(card);
 }
 const r=data.report;document.querySelector('#audit').textContent=`${r.unique_colors.toLocaleString()} unique RGB colors; all ${r.source_anchor_count_retained} source anchors retained. Minimum ${r.minimum_delta_e_2000.toFixed(3)} ΔE00; ${r.pairs_below_2} pairs below 2. No minimum-distance threshold was imposed.`;
 document.querySelector('#inspect').textContent='Point to a color to inspect its origin and values.';
})().catch(error=>{document.querySelector('#inspect').textContent=error.message;});
