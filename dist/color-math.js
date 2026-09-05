/* Perceptual color math. sRGB / D65 / CIE 1931 2° observer.
 * CIEDE2000: Sharma, Wu & Dalal (2005), kL = kC = kH = 1.
 * Independently implemented from the published equations; tested against
 * https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/
 * No CIELAB Euclidean shortlist is used as an approximation to ΔE00.
 */
(() => {
  const rad = Math.PI / 180, pow25 = 6103515625;
  const srgbByteToLinear = v => {
    const c = v / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  function linearToLab(r, g, b) {
    const f = t => t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116;
    const x = f((0.4124564*r + 0.3575761*g + 0.1804375*b) / 0.95047);
    const y = f(0.2126729*r + 0.7151522*g + 0.0721750*b);
    const z = f((0.0193339*r + 0.1191920*g + 0.9503041*b) / 1.08883);
    return [116*y - 16, 500*(x-y), 200*(y-z)];
  }
  const rgbToLab = (r,g,b) => linearToLab(srgbByteToLinear(r),srgbByteToLinear(g),srgbByteToLinear(b));
  const prepareLab = lab => [lab[0],lab[1],lab[2],Math.hypot(lab[1],lab[2])];
  function lightnessTermSquared(a,b) {
    const t = (a[0]+b[0])/2 - 50, t2 = t*t;
    const d = (b[0]-a[0]) / (1 + 0.015*t2/Math.sqrt(20+t2));
    return d*d;
  }
  function deltaE00Squared(p, q, upperBound = Infinity) {
    const c1 = p[3] ?? Math.hypot(p[1],p[2]);
    const c2 = q[3] ?? Math.hypot(q[1],q[2]);
    const c7 = ((c1+c2)/2)**7;
    const G = 0.5 * (1-Math.sqrt(c7/(c7+pow25)));
    const a1 = (1+G)*p[1], a2 = (1+G)*q[1];
    const cp1 = Math.hypot(a1,p[2]), cp2 = Math.hypot(a2,q[2]);
    const C = (cp1+cp2)/2, dc = (cp2-cp1)/(1+0.045*C);
    const light = lightnessTermSquared(p,q);
    if (upperBound < Infinity) {
      // |RT| <= sqrt(3): minimizing the quadratic over the other
      // coordinate leaves >= 1/4 of either squared chroma/hue term.
      if (light+0.25*dc*dc > upperBound+1e-10) return Infinity;
      // |T| <= 1.93, and dH² can be computed without either hue angle.
      const hueSq = Math.max(0,2*(cp1*cp2-a1*a2-p[2]*q[2])) / (1+0.02895*C)**2;
      const lower = Math.max(0.25*hueSq,(1-Math.sqrt(3)/2)*(dc*dc+hueSq));
      if (light+lower > upperBound+1e-10) return Infinity;
    }
    const hue = (a,b) => { const h=Math.atan2(b,a)/rad; return h < 0 ? h+360 : h; };
    const h1 = cp1 === 0 ? 0 : hue(a1,p[2]);
    const h2 = cp2 === 0 ? 0 : hue(a2,q[2]);
    let dh = h2-h1;
    if (cp1*cp2 === 0) dh = 0;
    else if (dh > 180) dh -= 360;
    else if (dh < -180) dh += 360;
    const dH = 2*Math.sqrt(cp1*cp2)*Math.sin(dh*rad/2);
    let H = h1+h2;
    if (cp1*cp2 !== 0) {
      if (Math.abs(h1-h2) <= 180) H /= 2;
      else H = (H < 360 ? H+360 : H-360)/2;
    }
    const T = 1 - 0.17*Math.cos((H-30)*rad) + 0.24*Math.cos(2*H*rad)
      + 0.32*Math.cos((3*H+6)*rad) - 0.20*Math.cos((4*H-63)*rad);
    const dht = dH/(1+0.015*C*T);
    const C7 = C**7;
    const rt = -2*Math.sqrt(C7/(C7+pow25)) * Math.sin(60*rad*Math.exp(-(((H-275)/25)**2)));
    return Math.max(0,light+dc*dc+dht*dht+rt*dc*dht);
  }
  function makeCiedeIndex(points) {
    return points.map((_,id)=>id).sort((a,b)=>points[a].cie[0]-points[b].cie[0] || a-b);
  }
  function nearestCiede2000(points, query, seed = 0, index = null) {
    const q = prepareLab(query);
    let best = seed, bestD = deltaE00Squared(q,points[seed].cie);
    let start=0,end=points.length;
    if (index) {
      // SL is monotonic in |Lbar-50|; endpoints give its maximum over
      // this palette. This bounds an inclusive lightness interval exactly.
      const t=Math.max(Math.abs((q[0]+points[index[0]].cie[0])/2-50),
        Math.abs((q[0]+points[index[index.length-1]].cie[0])/2-50));
      const radius=Math.sqrt(bestD+1e-10)*(1+0.015*t*t/Math.sqrt(20+t*t))+1e-9;
      const lowerBound = value => {
        let lo=0,hi=index.length;
        while(lo<hi) { const mid=(lo+hi)>>>1; if(points[index[mid]].cie[0]<value) lo=mid+1; else hi=mid; }
        return lo;
      };
      start=lowerBound(q[0]-radius);end=lowerBound(q[0]+radius);
    }
    for (let pos=start;pos<end;pos++) {
      const id=index ? index[pos] : pos;
      if (id === seed) continue;
      // Rigorous lower bound: the chroma/hue quadratic is nonnegative
      // (|RT| <= 2). A tiny guard avoids pruning a numeric boundary tie.
      if (lightnessTermSquared(q,points[id].cie) > bestD + 1e-12) continue;
      const d = deltaE00Squared(q,points[id].cie,bestD);
      if (d < bestD || (d === bestD && id < best)) { best=id; bestD=d; }
    }
    return [best,bestD];
  }
  globalThis.GamutColor = {srgbByteToLinear,linearToLab,rgbToLab,prepareLab,
    lightnessTermSquared,deltaE00Squared,deltaE00:(a,b)=>Math.sqrt(deltaE00Squared(a,b)),makeCiedeIndex,nearestCiede2000};
})();
