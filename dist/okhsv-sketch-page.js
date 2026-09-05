/* OKHSV construction atlas; backgrounds use Ottosson's reference conversion. */
(async function(){
  const q=s=>document.querySelector(s), hue=q('#hue'), canvas=q('#hueCanvas');
  const response=await fetch('./palettes/okhsv-sketch-1024.json');
  if(!response.ok)throw new Error('Palette data could not be loaded.');
  const data=await response.json(),samples=data.samples,cache=new Map(),pages=[];
  let hits=[];
  const fmt=p=>`${p.hex} · H ${p.h}° · S ${(p.s*100).toFixed(0)}% · V ${(p.v*100).toFixed(2)}% · ${p.kind} ${p.point}`;
  function inspect(p){q('#inspector').textContent=fmt(p);}
  function chip(p){const b=document.createElement('button');b.className='swatch';b.style.background=p.hex;b.title=fmt(p);b.setAttribute('aria-label',fmt(p));b.onclick=()=>inspect(p);b.onfocus=()=>inspect(p);return b;}
  function background(h){
    if(cache.has(h))return cache.get(h);
    const c=document.createElement('canvas');c.width=c.height=100;
    const cx=c.getContext('2d'),im=cx.createImageData(100,100);
    for(let y=0;y<100;y++)for(let x=0;x<100;x++){
      const v=1-y/99,rgb=v===0?[0,0,0]:okhsv_to_srgb(h/360,x/99,v),i=(y*100+x)*4;
      for(let k=0;k<3;k++)im.data[i+k]=Math.round(Math.min(255,Math.max(0,rgb[k])));
      im.data[i+3]=255;
    }
    cx.putImageData(im,0,0);cache.set(h,c);return c;
  }
  function draw(c,h,large=false){
    const ctx=c.getContext('2d'),pad=large?38:12,n=c.width-2*pad;
    ctx.fillStyle='#19151f';ctx.fillRect(0,0,c.width,c.height);
    if(q('#background').checked)ctx.drawImage(background(h),pad,pad,n,n);
    else{ctx.fillStyle='#27212e';ctx.fillRect(pad,pad,n,n);}
    ctx.lineWidth=1;ctx.strokeStyle='#9b8ea8';ctx.strokeRect(pad,pad,n,n);
    if(large){ctx.font='14px system-ui';ctx.fillStyle='#ddd4e5';ctx.fillText('V',9,27);ctx.fillText('1',18,pad+5);ctx.fillText('0',18,pad+n);ctx.fillText('S →',pad+n/2-10,pad+n+28);ctx.fillText('0',pad-3,pad+n+22);ctx.fillText('1',pad+n-4,pad+n+22);hits=[];}
    for(const p of samples.filter(p=>p.kind!=='gray'&&p.h===h)){
      const x=pad+p.s*n,y=pad+(1-p.v)*n,r=large?7:3.3;
      ctx.beginPath();if(p.kind==='tinted')ctx.rect(x-r,y-r,r*2,r*2);else ctx.arc(x,y,r,0,Math.PI*2);
      ctx.fillStyle=p.hex;ctx.fill();ctx.lineWidth=large?3:2;ctx.strokeStyle='#101015';ctx.stroke();ctx.lineWidth=large?1.5:1;ctx.strokeStyle=p.kind==='tinted'?'#40f1a6':'#fff';ctx.stroke();
      if(large)hits.push({x,y,r,p});
    }
  }
  function select(h){
    hue.value=h;draw(canvas,h,true);
    q('#mainSwatches').replaceChildren(...samples.filter(p=>p.kind==='main'&&p.h===h).map(chip));
    for(const page of pages)page.button.setAttribute('aria-pressed',String(page.h===h));
  }
  for(let i=0;i<48;i++){
    const h=i*7.5;hue.add(new Option(`${h}°`,h));
    const button=document.createElement('button');button.className='page';button.setAttribute('aria-label',`Inspect ${h} degree OKHSV hue page`);
    const label=document.createElement('span');label.textContent=`${h}°`;
    const small=document.createElement('small');small.textContent=i%4===0?'20 + 4 tinted samples':'20 main samples';
    const c=document.createElement('canvas');c.width=c.height=200;c.setAttribute('aria-hidden','true');
    button.append(label,c,small);button.onclick=()=>{select(h);q('#hueCanvas').scrollIntoView({block:'center',behavior:'smooth'});};
    q('#atlas').append(button);pages.push({h,c,button});draw(c,h);
  }
  q('#grays').replaceChildren(...samples.filter(p=>p.kind==='gray').map(chip));
  for(let h=0;h<360;h+=30){const col=document.createElement('div');col.className='tintcol';const label=document.createElement('span');label.textContent=`${h}°`;col.append(label,...samples.filter(p=>p.kind==='tinted'&&p.h===h).map(chip));q('#tints').append(col);}
  for(const [title,points] of [['20 main points',data.report.main_points_percent],['4 tinted points',data.report.tinted_points_percent]]){
    const table=document.createElement('table');table.innerHTML=`<caption>${title}</caption><thead><tr><th>Point</th><th>S %</th><th>V %</th></tr></thead>`;
    const tbody=document.createElement('tbody');points.forEach(([s,v],i)=>{const row=tbody.insertRow();[i+1,s,v].forEach(t=>row.insertCell().textContent=t);});table.append(tbody);q('#coordinates').append(table);
  }
  const r=data.report;q('#audit').textContent=`${r.unique_colors.toLocaleString()} unique colors · minimum ${r.minimum_delta_e_2000.toFixed(3)} ΔE00 · median nearest-neighbor distance ${r.nearest_neighbor_percentiles.median.toFixed(3)} ΔE00`;
  hue.onchange=()=>select(Number(hue.value));q('#background').onchange=()=>{select(Number(hue.value));for(const p of pages)draw(p.c,p.h);};
  canvas.onpointermove=e=>{const box=canvas.getBoundingClientRect(),x=(e.clientX-box.left)*canvas.width/box.width,y=(e.clientY-box.top)*canvas.height/box.height;const hit=hits.find(t=>Math.hypot(t.x-x,t.y-y)<=t.r+5);if(hit)inspect(hit.p);};
  select(0);
})().catch(error=>{document.querySelector('#audit').textContent=error.message;});
