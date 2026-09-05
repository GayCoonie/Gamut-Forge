(async function(){
  const q=s=>document.querySelector(s),response=await fetch('./palettes/oklab-rings-1024.json');
  if(!response.ok)throw Error('Palette data could not be loaded.');
  const data=await response.json(),report=data.report,samples=data.samples,pages=[];
  const actual=p=>{const [L,a,b]=p.actual_oklab;return `actual Oklab (${L.toFixed(4)}, ${a.toFixed(4)}, ${b.toFixed(4)})`;};
  const description=p=>`${p.hex} · requested L ${p.L.toFixed(2)}, C ${p.C.toFixed(4)}, h ${p.h}° · ${actual(p)} · ${p.selected?'retained':'omitted'}${p.outside_srgb?' · target clipped to sRGB':''}`;
  function inspect(p){q('#inspect').textContent=description(p);}
  function draw(page){
    const ctx=page.canvas.getContext('2d'),cx=160,cy=160,inner=42,step=13;
    ctx.clearRect(0,0,320,320);ctx.font='14px system-ui';ctx.fillStyle='#c4bbce';ctx.textAlign='center';ctx.fillText('0°',cx,13);ctx.fillText('180°',cx,315);ctx.fillText('90°',301,164);ctx.fillText('270°',20,164);
    for(const p of page.samples){
      const start=(p.h-7.5)*Math.PI/180-Math.PI/2,end=(p.h+7.5)*Math.PI/180-Math.PI/2,r0=inner+p.ring*step,r1=r0+step-1;
      ctx.beginPath();ctx.arc(cx,cy,r1,start+.006,end-.006);ctx.arc(cx,cy,r0,end-.006,start+.006,true);ctx.closePath();
      ctx.fillStyle=p.selected||q('#omitted').checked?p.hex:'#211b29';ctx.fill();ctx.lineWidth=.8;ctx.strokeStyle=p.selected?'#7b6c87':'#382e43';ctx.stroke();
      if(!p.selected&&q('#omitted').checked){const a=p.h*Math.PI/180-Math.PI/2,r=(r0+r1)/2;ctx.fillStyle='#fff';ctx.fillRect(cx+Math.cos(a)*r-2,cy+Math.sin(a)*r,4,1);}
      if(p.outside_srgb&&q('#clipped').checked){const a=p.h*Math.PI/180-Math.PI/2,r=(r0+r1)/2;ctx.beginPath();ctx.arc(cx+Math.cos(a)*r,cy+Math.sin(a)*r,1.5,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();}
    }
    ctx.fillStyle='#c4bbce';ctx.fillText('C = 0',cx,156);ctx.fillText('→ .25',cx,175);
  }
  for(const L of report.lightness_levels){
    const section=document.createElement('section');section.className='wheel';
    const title=document.createElement('h2');title.textContent=`L = ${L.toFixed(2)}`;
    const cells=samples.filter(p=>p.L===L),kept=new Set(cells.filter(p=>p.selected).map(p=>p.hex)).size,total=new Set(cells.map(p=>p.hex)).size;
    const count=document.createElement('p');count.textContent=`${kept} / ${total} distinct slice colors retained`;
    const canvas=document.createElement('canvas');canvas.width=canvas.height=320;canvas.setAttribute('aria-label',`Requested Oklab L ${L} ring samples; ${kept} distinct colors retained`);
    section.append(title,count,canvas);q('#wheels').append(section);const page={canvas,samples:cells};pages.push(page);draw(page);
    canvas.onpointermove=e=>{const b=canvas.getBoundingClientRect(),x=(e.clientX-b.left)*320/b.width-160,y=(e.clientY-b.top)*320/b.height-160,r=Math.hypot(x,y);if(r<42||r>=146)return;const ring=Math.floor((r-42)/13),h=(Math.atan2(y,x)*180/Math.PI+450)%360,hi=Math.floor((h+7.5)/15)%24;const p=cells.find(p=>p.ring===ring&&p.h===hi*15);if(p)inspect(p);};
    const button=document.createElement('button');button.textContent=`L = ${L.toFixed(2)}`;button.onclick=()=>{
      q('#accessibleSamples').replaceChildren(...cells.map(p=>{const b=document.createElement('button');b.textContent=`C ${p.C.toFixed(3)}, h ${p.h}°`;b.title=description(p);b.onclick=()=>inspect(p);return b;}));
    };q('#coordinateList').append(button);
  }
  for(const p of data.palette_entries.filter(p=>p.source==='okhsv')){const b=document.createElement('button');b.className='chip';b.style.background=p.hex;b.title=`${p.hex} · ${actual(p)} · borrowed from OKHSV Sketch`;b.setAttribute('aria-label',b.title);b.onclick=()=>q('#inspect').textContent=b.title;b.onfocus=b.onclick;q('#fillers').append(b);}
  q('#audit').textContent=`Minimum ${report.minimum_delta_e_2000.toFixed(6)} ΔE00 · ${report.pairs_below_2} pairs below 2 · ${report.gray_count} true grays · no threshold relaxation`;
  for(const input of ['#omitted','#clipped'])q(input).onchange=()=>pages.forEach(draw);
})().catch(error=>document.querySelector('#audit').textContent=error.message);
