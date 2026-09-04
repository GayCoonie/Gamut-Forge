const $ = (selector) => document.querySelector(selector);
const builtins = window.GAMUT_PALETTES;
const els = {
  imageDrop: $('#imageDrop'), imageInput: $('#imageInput'), imagePrompt: $('#imagePrompt'), imageMeta: $('#imageMeta'),
  paletteSelect: $('#paletteSelect'), paletteInput: $('#paletteInput'), paletteCanvas: $('#paletteCanvas'), paletteName: $('#paletteName'), paletteCount: $('#paletteCount'),
  dither: $('#ditherSelect'), strength: $('#strength'), strengthOut: $('#strengthOut'), strengthRow: $('#strengthRow'), alpha: $('#preserveAlpha'),
  process: $('#processButton'), progressWrap: $('#progressWrap'), progressBar: $('#progressBar'), progressText: $('#progressText'),
  sourceCanvas: $('#sourceCanvas'), resultCanvas: $('#resultCanvas'), sourceWrap: $('#sourceWrap'), resultWrap: $('#resultWrap'),
  sourceCaption: $('#sourceCaption'), resultCaption: $('#resultCaption'), previewGrid: $('#previewGrid'), download: $('#downloadButton'), metrics: $('#metrics')
};

let imageData = null;
let imageName = 'image';
let currentPalette = { name: builtins.maxCoverage.name, colors: builtins.maxCoverage.colors };
let worker = null;

function uniqueColors(colors) {
  const seen = new Set();
  return colors.filter(hex => {
    const key = hex.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key); return true;
  });
}

function drawPalette() {
  const c = els.paletteCanvas, ctx = c.getContext('2d');
  const colors = currentPalette.colors;
  const cols = Math.ceil(Math.sqrt(colors.length * 8));
  const rows = Math.ceil(colors.length / cols);
  const w = c.width / cols, h = c.height / rows;
  ctx.clearRect(0, 0, c.width, c.height);
  colors.forEach((color, i) => {
    ctx.fillStyle = color;
    ctx.fillRect((i % cols) * w, Math.floor(i / cols) * h, Math.ceil(w), Math.ceil(h));
  });
  els.paletteName.textContent = currentPalette.name;
  els.paletteCount.textContent = `${colors.length.toLocaleString()} colors`;
}

async function loadImage(file) {
  if (!file?.type.startsWith('image/')) throw new Error('Choose an image file.');
  const bitmap = await createImageBitmap(file);
  const canvas = els.sourceCanvas;
  canvas.width = bitmap.width; canvas.height = bitmap.height;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.clearRect(0, 0, canvas.width, canvas.height); ctx.drawImage(bitmap, 0, 0);
  bitmap.close();
  imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  imageName = file.name.replace(/\.[^.]+$/, '') || 'image';
  els.sourceWrap.classList.remove('empty');
  els.imagePrompt.textContent = file.name;
  els.imageMeta.textContent = `${canvas.width.toLocaleString()} × ${canvas.height.toLocaleString()} · ${formatBytes(file.size)}`;
  els.sourceCaption.textContent = `${canvas.width} × ${canvas.height}`;
  els.process.disabled = false;
  els.resultWrap.classList.add('empty'); els.download.disabled = true;
  resetMetrics();
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1048576).toFixed(1)} MB`;
}

function parseTextPalette(text) {
  const colors = [];
  const gplLines = text.split(/\r?\n/);
  for (const line of gplLines) {
    const rgb = line.match(/^\s*(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})(?:\s|$)/);
    if (rgb && rgb.slice(1).every(v => +v <= 255)) colors.push(`#${rgb.slice(1).map(v => (+v).toString(16).padStart(2,'0')).join('')}`);
  }
  const hexes = text.match(/#[0-9a-fA-F]{6}(?![0-9a-fA-F])/g) || [];
  return uniqueColors([...colors, ...hexes]);
}

async function paletteFromImage(file) {
  const bitmap = await createImageBitmap(file);
  const c = document.createElement('canvas'); c.width = bitmap.width; c.height = bitmap.height;
  const ctx = c.getContext('2d', { willReadFrequently: true }); ctx.drawImage(bitmap, 0, 0); bitmap.close();
  const data = ctx.getImageData(0, 0, c.width, c.height).data;
  const out = [], seen = new Set();
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] === 0) continue;
    const key = (data[i] << 16) | (data[i + 1] << 8) | data[i + 2];
    if (!seen.has(key)) { seen.add(key); out.push(`#${key.toString(16).padStart(6,'0')}`); }
    if (out.length > 65535) throw new Error('Palette images are limited to 65,535 unique colors.');
  }
  return out;
}

async function importPalette(file) {
  let colors;
  if (file.type.startsWith('image/')) colors = await paletteFromImage(file);
  else colors = parseTextPalette(await file.text());
  if (!colors.length) throw new Error('No RGB colors were found in that file.');
  currentPalette = { name: file.name, colors };
  els.paletteSelect.value = '';
  drawPalette(); resetMetrics();
}

function run() {
  if (!imageData || !currentPalette.colors.length) return;
  if (worker) worker.terminate();
  worker = new Worker('./quantize-worker.js');
  const copy = new Uint8ClampedArray(imageData.data);
  els.process.disabled = true; els.download.disabled = true;
  els.progressWrap.hidden = false; setProgress(1, 'Preparing palette…');
  worker.onmessage = ({ data }) => {
    if (data.type === 'progress') return setProgress(data.value, data.label);
    if (data.type === 'error') { finishError(data.message); return; }
    if (data.type === 'done') {
      const pixels = new Uint8ClampedArray(data.buffer);
      const out = new ImageData(pixels, data.width, data.height);
      els.resultCanvas.width = data.width; els.resultCanvas.height = data.height;
      els.resultCanvas.getContext('2d').putImageData(out, 0, 0);
      els.resultWrap.classList.remove('empty');
      els.resultCaption.textContent = `${data.width} × ${data.height} · ${currentPalette.name}`;
      renderMetrics(data.stats);
      setProgress(100, 'Complete');
      setTimeout(() => { els.progressWrap.hidden = true; }, 900);
      els.process.disabled = false; els.download.disabled = false;
      worker.terminate(); worker = null;
    }
  };
  worker.onerror = e => finishError(e.message || 'The quantizer stopped unexpectedly.');
  worker.postMessage({
    type: 'quantize', buffer: copy.buffer, width: imageData.width, height: imageData.height,
    palette: currentPalette.colors, dither: els.dither.value, strength: +els.strength.value / 100,
    preserveAlpha: els.alpha.checked
  }, [copy.buffer]);
}

function setProgress(value, label) { els.progressBar.style.width = `${value}%`; els.progressText.textContent = label; }
function finishError(message) { els.progressWrap.hidden = false; setProgress(0, message); els.process.disabled = false; worker?.terminate(); worker = null; }
function resetMetrics() { [...els.metrics.querySelectorAll('strong')].forEach(x => x.textContent = '—'); }
function renderMetrics(s) {
  const vals = [`${s.used.toLocaleString()} / ${currentPalette.colors.length.toLocaleString()}`, s.mean.toFixed(4), s.max.toFixed(4), '0', `${s.elapsed.toFixed(0)} ms`];
  [...els.metrics.querySelectorAll('strong')].forEach((x, i) => x.textContent = vals[i]);
}

els.imageInput.addEventListener('change', () => loadImage(els.imageInput.files[0]).catch(e => finishError(e.message)));
['dragenter','dragover'].forEach(t => els.imageDrop.addEventListener(t, e => { e.preventDefault(); els.imageDrop.classList.add('dragging'); }));
['dragleave','drop'].forEach(t => els.imageDrop.addEventListener(t, e => { e.preventDefault(); els.imageDrop.classList.remove('dragging'); }));
els.imageDrop.addEventListener('drop', e => loadImage(e.dataTransfer.files[0]).catch(err => finishError(err.message)));
els.paletteSelect.addEventListener('change', () => { const p = builtins[els.paletteSelect.value]; if (!p) return; currentPalette = { name:p.name, colors:p.colors }; drawPalette(); resetMetrics(); });
els.paletteInput.addEventListener('change', () => importPalette(els.paletteInput.files[0]).catch(e => finishError(e.message)));
els.dither.addEventListener('change', () => { els.strengthRow.hidden = els.dither.value === 'none'; });
els.strength.addEventListener('input', () => { els.strengthOut.value = `${els.strength.value}%`; });
els.process.addEventListener('click', run);
document.querySelectorAll('[data-view]').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('[data-view]').forEach(x => x.classList.toggle('active', x === btn));
  els.previewGrid.className = `preview-grid ${btn.dataset.view}`;
}));
els.download.addEventListener('click', () => els.resultCanvas.toBlob(blob => {
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${imageName}-gamut-forge.png`; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}, 'image/png'));

drawPalette();
