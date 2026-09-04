function srgbByteToLinear(v) { const c = v / 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; }
function hexToRgb(hex) { const n = parseInt(hex.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
function linearToOklab(r, g, b) {
  const l = .4122214708*r + .5363325363*g + .0514459929*b;
  const m = .2119034982*r + .6806995451*g + .1073969566*b;
  const s = .0883024619*r + .2817188376*g + .6299787005*b;
  const l_ = Math.cbrt(l), m_ = Math.cbrt(m), s_ = Math.cbrt(s);
  return [
    .2104542553*l_ + .793617785*m_ - .0040720468*s_,
    1.9779984951*l_ - 2.428592205*m_ + .4505937099*s_,
    .0259040371*l_ + .7827717662*m_ - .808675766*s_
  ];
}
function clamp(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

function makeTree(points, ids, depth = 0) {
  if (!ids.length) return null;
  const axis = depth % 3;
  ids.sort((a,b) => points[a].lab[axis] - points[b].lab[axis]);
  const mid = ids.length >> 1;
  return { id:ids[mid], axis, left:makeTree(points,ids.slice(0,mid),depth+1), right:makeTree(points,ids.slice(mid+1),depth+1) };
}
function nearest(tree, points, q) {
  let best = -1, bestD = Infinity;
  (function visit(node) {
    if (!node) return;
    const p = points[node.id].lab;
    const d0=q[0]-p[0], d1=q[1]-p[1], d2=q[2]-p[2], d=d0*d0+d1*d1+d2*d2;
    if (d < bestD) { bestD=d; best=node.id; }
    const delta=q[node.axis]-p[node.axis];
    visit(delta < 0 ? node.left : node.right);
    if (delta*delta < bestD) visit(delta < 0 ? node.right : node.left);
  })(tree);
  return [best,bestD];
}
function addError(arr, pos, er, eg, eb, weight) { arr[pos]+=er*weight; arr[pos+1]+=eg*weight; arr[pos+2]+=eb*weight; }

self.onmessage = ({data}) => {
  if (data.type !== 'quantize') return;
  try {
    const started = performance.now();
    const input = new Uint8ClampedArray(data.buffer);
    const output = new Uint8ClampedArray(input.length);
    const palette = data.palette.map((hex, id) => {
      const rgb=hexToRgb(hex), lin=rgb.map(srgbByteToLinear); return { id, rgb, lin, lab:linearToOklab(...lin) };
    });
    if (!palette.length) throw new Error('The palette is empty.');
    const tree = makeTree(palette, palette.map((_,i)=>i));
    self.postMessage({type:'progress',value:7,label:'Mapping pixels…'});
    let errorSum=0,errorMax=0,visible=0; const used=new Set();
    const w=data.width,h=data.height;

    const writePixel = (i, p, sourceLab) => {
      output[i]=p.rgb[0]; output[i+1]=p.rgb[1]; output[i+2]=p.rgb[2];
      output[i+3]=data.preserveAlpha ? input[i+3] : 255;
      used.add(p.id); visible++;
      const dl=sourceLab[0]-p.lab[0], da=sourceLab[1]-p.lab[1], db=sourceLab[2]-p.lab[2];
      const e=Math.sqrt(dl*dl+da*da+db*db); errorSum+=e; if(e>errorMax) errorMax=e;
    };

    if (data.dither === 'floyd') {
      let curr=new Float32Array((w+2)*3), next=new Float32Array((w+2)*3);
      for(let y=0;y<h;y++) {
        const reverse=y%2===1;
        for(let step=0;step<w;step++) {
          const x=reverse?w-1-step:step, i=(y*w+x)*4, ep=(x+1)*3;
          if(input[i+3]===0 && data.preserveAlpha) { output.set(input.subarray(i,i+4),i); continue; }
          const base=[srgbByteToLinear(input[i]),srgbByteToLinear(input[i+1]),srgbByteToLinear(input[i+2])];
          const sourceLab=linearToOklab(...base);
          const corrected=[clamp(base[0]+curr[ep]),clamp(base[1]+curr[ep+1]),clamp(base[2]+curr[ep+2])];
          const [id]=nearest(tree,palette,linearToOklab(...corrected)); const p=palette[id]; writePixel(i,p,sourceLab);
          const strength=data.strength, er=(corrected[0]-p.lin[0])*strength, eg=(corrected[1]-p.lin[1])*strength, eb=(corrected[2]-p.lin[2])*strength;
          if(!reverse) { addError(curr,ep+3,er,eg,eb,7/16); addError(next,ep-3,er,eg,eb,3/16); addError(next,ep,er,eg,eb,5/16); addError(next,ep+3,er,eg,eb,1/16); }
          else { addError(curr,ep-3,er,eg,eb,7/16); addError(next,ep+3,er,eg,eb,3/16); addError(next,ep,er,eg,eb,5/16); addError(next,ep-3,er,eg,eb,1/16); }
        }
        const tmp=curr; curr=next; next=tmp; next.fill(0);
        if(y%24===0) self.postMessage({type:'progress',value:7+Math.round(90*y/h),label:`Dithering row ${y.toLocaleString()} of ${h.toLocaleString()}`});
      }
    } else {
      const cache=new Map();
      for(let y=0;y<h;y++) {
        for(let x=0;x<w;x++) {
          const i=(y*w+x)*4;
          if(input[i+3]===0 && data.preserveAlpha) { output.set(input.subarray(i,i+4),i); continue; }
          const key=(input[i]<<16)|(input[i+1]<<8)|input[i+2]; let hit=cache.get(key);
          const sourceLab=linearToOklab(srgbByteToLinear(input[i]),srgbByteToLinear(input[i+1]),srgbByteToLinear(input[i+2]));
          if(!hit) { const [id]=nearest(tree,palette,sourceLab); hit=palette[id]; cache.set(key,hit); }
          writePixel(i,hit,sourceLab);
        }
        if(y%32===0) self.postMessage({type:'progress',value:7+Math.round(90*y/h),label:`Matching row ${y.toLocaleString()} of ${h.toLocaleString()}`});
      }
    }
    self.postMessage({type:'done',buffer:output.buffer,width:w,height:h,stats:{used:used.size,mean:visible?errorSum/visible:0,max:errorMax,elapsed:performance.now()-started}},[output.buffer]);
  } catch (error) { self.postMessage({type:'error',message:error.message || String(error)}); }
};
