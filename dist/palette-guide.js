(async function(){
const catalogResponse=await fetch('./palette-catalog.json',{cache:'no-cache'});
if(!catalogResponse.ok)throw Error('Could not load the palette catalog. Reload this page to retry.');
const catalog=await catalogResponse.json();
const meta=Object.fromEntries(catalog.map(p=>[p.key,[p.stem,p.description]]));
const select=document.querySelector('#palette'),view=document.querySelector('#view'),canvas=document.querySelector('#chart'),ctx=canvas.getContext('2d');let hits=[],requestId=0;
select.replaceChildren(...catalog.map(p=>new Option(p.name,p.key)));
const requested=new URLSearchParams(location.search).get('palette');if(meta[requested])select.value=requested;else if(requested)throw Error('This palette is not in the catalog. Reload the page to refresh the list.');
async function draw(){
 const request=++requestId,key=select.value,[stem,description]=meta[key];
 hits=[];ctx.clearRect(0,0,canvas.width,canvas.height);
 document.querySelector('#stats').textContent='Loading palette…';
 document.querySelector('#tooltip').textContent='Loading palette colors…';
 try{
 const response=await fetch('./palettes/'+stem+'.json',{cache:'no-cache'});
 if(!response.ok)throw Error('Could not load this palette. Reload the page to retry.');
 const data=await response.json();
 if(request!==requestId)return;
 const colors=data.colors?.map(c=>typeof c==='string'?c:c.hex);
 if(!colors?.length||!colors.every(c=>/^#[0-9a-f]{6}$/i.test(c)))throw Error('This palette file contains invalid color data.');
 const name=catalog.find(p=>p.key===key).name;
 history.replaceState(null,'','?palette='+key);document.title=name+' · Gamut Forge';
 document.querySelector('#description').textContent=description;
 document.querySelector('#title').textContent=name;
 document.querySelector('#usePalette').href='./?palette='+key;
 document.querySelector('#stats').textContent=colors.length.toLocaleString()+' unique colors';
 document.querySelector('#downloads').innerHTML=['txt','gpl','kpl','json','png'].map(ext=>`<a href="./palettes/${stem}.${ext}" download>${ext==='gpl'?'GIMP':ext==='kpl'?'Krita':ext.toUpperCase()}</a>`).join('')+`<a href="./palettes/${stem}-package.zip" download>All formats (ZIP)</a>`;
 if(key.startsWith('randomStrata')){const link=document.createElement('a');link.href='./random-strata.html';link.textContent='Trial reports & generator →';document.querySelector('#downloads').append(link);}
 const diagram=catalog.find(p=>p.key===key).diagram;
 if(diagram){const link=document.createElement('a');link.href='./'+diagram;link.textContent='Sampling diagram →';document.querySelector('#downloads').append(link);}
 const grid=view.value==='swatches';canvas.height=grid?1440:1050;hits=[];ctx.fillStyle='#19151f';ctx.fillRect(0,0,canvas.width,canvas.height);
 colors.forEach((hex,i)=>{
  const rgb=[1,3,5].map(p=>parseInt(hex.slice(p,p+2),16)),[L,a,b]=GamutColor.rgbToLab(...rgb),C=Math.hypot(a,b),h=(Math.atan2(b,a)*180/Math.PI+360)%360;
  let x,y,w;
  if(grid){const side=Math.ceil(Math.sqrt(colors.length));w=1440/side;x=i%side*w;y=Math.floor(i/side)*w;}
  else{const panel=C<.0002?0:Math.floor(h/30);x=panel%4*360+42+C/145*296;y=Math.floor(panel/4)*350+308-L/100*266;w=colors.length===4096?5:8;x-=w/2;y-=w/2;}
  ctx.fillStyle=hex;ctx.fillRect(x,y,w,w);hits.push({x,y,w,hex,L,C,h});
 });
 if(!grid){ctx.font='14px system-ui';for(let panel=0;panel<12;panel++){const x=panel%4*360,y=Math.floor(panel/4)*350;ctx.fillStyle='#cfc5dc';ctx.fillText(`${panel*30}–${(panel+1)*30}° Lab hue`,x+42,y+24);ctx.strokeStyle='#55465f';ctx.beginPath();ctx.moveTo(x+40,y+40);ctx.lineTo(x+40,y+310);ctx.lineTo(x+338,y+310);ctx.stroke();ctx.font='11px system-ui';ctx.fillText('100',x+9,y+47);ctx.fillText('L*',x+9,y+177);ctx.fillText('0',x+20,y+311);ctx.fillText('0',x+39,y+329);ctx.fillText('Chroma C* →',x+138,y+329);ctx.fillText('145',x+317,y+329);ctx.font='14px system-ui';}}
 document.querySelector('#caption').textContent=grid?'Every palette color appears once, in its stored order. No colors are interpolated.':'Each square is an actual palette color, positioned by CIELAB D65 lightness and chroma within a 30° hue slice. All panels use the same scale. Squares can overlap; their area does not represent gamut volume. True grays appear in the first panel. Use Every swatch to see each entry separately.';
 document.querySelector('#tooltip').textContent='Point to a color to inspect its hex value.';
 if(Number.isFinite(data.report?.minimum_delta_e_2000))document.querySelector('#stats').textContent=`${colors.length.toLocaleString()} colors · minimum ${data.report.minimum_delta_e_2000.toFixed(3)} ΔE00`;
 }catch(error){if(request===requestId){document.querySelector('#stats').textContent='Palette could not be loaded';document.querySelector('#tooltip').textContent=error.message;}}

}
canvas.addEventListener('pointermove',e=>{const box=canvas.getBoundingClientRect(),x=(e.clientX-box.left)*canvas.width/box.width,y=(e.clientY-box.top)*canvas.height/box.height;const hit=hits.findLast(p=>x>=p.x&&x<=p.x+p.w&&y>=p.y&&y<=p.y+p.w);if(hit)document.querySelector('#tooltip').textContent=`${hit.hex} · L* ${hit.L.toFixed(2)} · C* ${hit.C.toFixed(2)} · hue ${hit.h.toFixed(1)}°`;});
select.addEventListener('change',draw);view.addEventListener('change',draw);await draw();

})().catch(error=>{document.querySelector('#stats').textContent='Atlas could not be loaded';document.querySelector('#tooltip').textContent=error.message;});
