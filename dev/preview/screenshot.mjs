/* Screenshots every rendered page in dist/ at desktop and phone widths.
   Usage: node screenshot.mjs [--out shots] [--dist dist] [page ...]
     page names match render.mjs: "customers/login" and "customers-login" both work.
     env VPS=phone (or desktop) limits the viewports; RM=1 emulates reduced motion.
   Phone pages are captured as viewport-sized pieces and stitched (Python + PIL):
   a fullPage capture in Chromium turns touch emulation off while it draws (so
   pointer: coarse CSS is lost) and comes out blank past ~16,384 device px.
   Output stays <page>--<viewport>.png; without PIL the pieces are kept as
   <page>--phone.png (first screen) plus <page>--phone--2.png, --3 … */
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { spawnSync } from 'node:child_process';
import { chromium } from 'playwright-core';

const HERE = path.resolve(new URL('.', import.meta.url).pathname);
const argv = process.argv.slice(2);
const outIdx = argv.indexOf('--out');
const OUT = path.resolve(outIdx >= 0 ? argv[outIdx + 1] : path.join(HERE, 'shots'));
const pageName = (n) => n.replace(/\.html$/, '').replace(/\//g, '-'); // render.mjs writes customers/login → customers-login.html
const only = argv.filter((a, i) => !a.startsWith('--') && argv[i - 1] !== '--out' && argv[i - 1] !== '--dist').map(pageName);
const distIdx = process.argv.indexOf('--dist');
const DIST = path.resolve(distIdx >= 0 ? process.argv[distIdx + 1] : path.join(HERE, 'dist'));
fs.mkdirSync(OUT, { recursive: true });

/* Serve dist over HTTP so fonts load (file:// blocks them via CORS) */
const TYPES = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const url = decodeURIComponent(req.url.split('?')[0]);
  let file = path.join(DIST, url === '/' ? 'index.html' : url);
  if (!file.startsWith(DIST) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    // Liquid-relative asset paths ("assets/x.css", "img/y.svg") resolve against the page directory, which is DIST already
    res.writeHead(404); res.end('not found'); return;
  }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const BASE = `http://127.0.0.1:${server.address().port}`;

const exe = process.env.CHROME_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
// SwiftShader instead of --disable-gpu: with the GPU path off, backdrop-filter leaves the
// text behind the glass sheets sharp, so every sheet looked see-through in the shots.
const browser = await chromium.launch({ executablePath: fs.existsSync(exe) ? exe : undefined, args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const pages = (only.length ? only : fs.readdirSync(DIST).filter((f) => f.endsWith('.html')).map((f) => f.replace(/\.html$/, ''))).sort();
const ALL_VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'phone', width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
];
const viewports = process.env.VPS ? ALL_VIEWPORTS.filter((v) => process.env.VPS.split(',').includes(v.name)) : ALL_VIEWPORTS;

/* ---------- stitching ---------- */
const STITCH_PY = `
import json, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
parts, out = json.load(open(sys.argv[1])), sys.argv[2]
tiles = []
for p in parts:
    im = Image.open(p['file']).convert('RGB')
    top = max(0, min(p['top'], im.height))
    bottom = max(top, min(top + p['height'], im.height))
    tiles.append(im.crop((0, top, im.width, bottom)))
canvas = Image.new('RGB', (max(t.width for t in tiles), sum(t.height for t in tiles)), (255, 255, 255))
y = 0
for t in tiles:
    canvas.paste(t, (0, y))
    y += t.height
canvas.save(out, optimize=False)
`;
let pilWarned = false;
/** parts: [{ buf, top, height }] in device px (top/height crop each piece). Returns the number of files written. */
function writeStitched(file, parts) {
  const tmp = fs.mkdtempSync(path.join(OUT, '.parts-'));
  try {
    const manifest = parts.map((p, i) => {
      const f = path.join(tmp, `${String(i).padStart(3, '0')}.png`);
      fs.writeFileSync(f, p.buf);
      return { file: f, top: p.top, height: p.height };
    });
    const mf = path.join(tmp, 'parts.json');
    fs.writeFileSync(mf, JSON.stringify(manifest));
    const r = spawnSync(process.env.PYTHON || 'python3', ['-I', '-c', STITCH_PY, mf, file], { encoding: 'utf8' });
    if (r.status === 0) return 1;
    if (!pilWarned) console.warn(`  ! stitching needs python3 with Pillow (${(r.stderr || r.error || '').toString().trim().split('\n').pop()}); keeping numbered pieces`);
    pilWarned = true;
    // Fallback: first piece keeps the usual name so other tools still find it
    parts.forEach((p, i) => fs.writeFileSync(i ? file.replace(/\.png$/, `--${i + 1}.png`) : file, p.buf));
    return parts.length;
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

/* Phone: scroll and take viewport shots, which keep touch emulation on. Sticky
   elements are pinned at their place in the flow and fixed ones are hidden after
   the first screen, so each piece shows the page as a full-page capture would. */
async function capturePieces(page, file, vp) {
  const dpr = vp.deviceScaleFactor || 1;
  const { total, vh } = await page.evaluate(() => ({ total: document.documentElement.scrollHeight, vh: window.innerHeight }));
  if (total <= vh + 1) {
    await page.screenshot({ path: file });
    return { total, pieces: 1 };
  }
  await page.evaluate(() => {
    window.__previewFixed = [];
    for (const el of document.querySelectorAll('body *')) {
      const pos = getComputedStyle(el).position;
      if (pos === 'sticky' || pos === '-webkit-sticky') {
        el.style.setProperty('position', 'relative', 'important');
        for (const side of ['top', 'right', 'bottom', 'left']) el.style.setProperty(side, 'auto', 'important');
      } else if (pos === 'fixed') {
        window.__previewFixed.push(el);
      }
    }
  });
  const parts = [];
  for (let y = 0, i = 0; y < total; y += vh, i++) {
    const actual = await page.evaluate(async ([y, first]) => {
      if (!first) window.__previewFixed.forEach((el) => el.style.setProperty('visibility', 'hidden', 'important'));
      window.scrollTo({ top: y, left: 0, behavior: 'instant' });
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      return window.scrollY;
    }, [y, i === 0]);
    await page.waitForTimeout(i === 0 ? 0 : 80); // scroll-driven class changes settle
    const buf = await page.screenshot();
    // the last scroll is clamped: crop the overlap with the previous piece
    parts.push({ buf, top: Math.round((y - actual) * dpr), height: Math.round(Math.min(vh, total - y) * dpr) });
  }
  return { total, pieces: writeStitched(file, parts) };
}

/* Desktop (no touch emulation to lose): one fullPage capture, or clipped
   fullPage pieces when the page passes the capture height. With SwiftShader the
   largest texture is 8192 device px: past it a single capture repeats the top of
   the page, so pieces stay under 8000. */
async function captureFullPage(page, file, vp) {
  const dpr = vp.deviceScaleFactor || 1;
  const total = await page.evaluate(() => document.documentElement.scrollHeight);
  const max = Math.floor(8000 / dpr);
  if (total <= max) {
    await page.screenshot({ path: file, fullPage: true });
    return { total, pieces: 1 };
  }
  const parts = [];
  for (let y = 0; y < total; y += max) {
    const h = Math.min(max, total - y);
    const buf = await page.screenshot({ fullPage: true, clip: { x: 0, y, width: vp.width, height: h } });
    parts.push({ buf, top: 0, height: Math.round(h * dpr) });
  }
  return { total, pieces: writeStitched(file, parts) };
}

const consoleErrors = {};
for (const vp of viewports) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile, hasTouch: !!vp.hasTouch, deviceScaleFactor: vp.deviceScaleFactor || 1, reducedMotion: process.env.RM ? 'reduce' : 'no-preference' });
  for (const name of pages) {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error' && !/net::ERR|Failed to load resource|fetch/i.test(m.text())) errors.push(`console: ${m.text()}`); });
    // "You may also like": answer <product-recommendations>' Section Rendering fetch with the
    // rendered page (render.mjs gives product pages a recommendations fixture)
    let recommendationsServed = false;
    await page.route('**/recommendations/products**', (route) => {
      const f = path.join(DIST, `${name}.html`);
      if (!fs.existsSync(f)) return route.fulfill({ status: 404, body: '' });
      recommendationsServed = true;
      return route.fulfill({ status: 200, contentType: 'text/html', body: fs.readFileSync(f) });
    });
    await page.goto(`${BASE}/${name}.html`, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts && document.fonts.ready);
    // Let @starting-style entrances and reveal observers settle; reveal everything for the full-page capture
    await page.waitForTimeout(400);
    // Scroll through so lazy images load, then back to the top for the capture
    const waitImages = () => page.evaluate(() => Promise.all([...document.images].filter((i) => !i.complete).map((i) => new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 1500); }))));
    await page.evaluate(async () => {
      const step = window.innerHeight * 0.8;
      for (let y = 0; y < document.documentElement.scrollHeight; y += step) { window.scrollTo({ top: y, behavior: 'instant' }); await new Promise((r) => setTimeout(r, 60)); }
    });
    await waitImages();
    if (recommendationsServed) { await page.waitForTimeout(200); await waitImages(); } // swapped-in tiles
    await page.evaluate(() => { document.querySelectorAll('[data-reveal]').forEach((n) => n.classList.add('is-visible')); window.scrollTo({ top: 0, behavior: 'instant' }); });
    await page.waitForTimeout(900); // reveal is 500ms + up to 350ms stagger
    const file = path.join(OUT, `${name}--${vp.name}.png`);
    for (const f of fs.readdirSync(OUT)) if (f.startsWith(`${name}--${vp.name}--`) && /--\d+\.png$/.test(f)) fs.rmSync(path.join(OUT, f)); // stale fallback pieces
    const { total: h, pieces } = vp.hasTouch ? await capturePieces(page, file, vp) : await captureFullPage(page, file, vp);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
    const overflow = await page.evaluate(() => {
      const vw = document.documentElement.clientWidth;
      if (document.documentElement.scrollWidth <= vw + 1) return false;
      // name the widest offenders (in-flow elements whose right edge passes the viewport)
      const out = [];
      for (const el of document.querySelectorAll('body *')) {
        const r = el.getBoundingClientRect();
        if (r.width && r.right > vw + 1 && getComputedStyle(el).position !== 'fixed' && !el.closest('[data-drawer]')) out.push(`${el.tagName.toLowerCase()}.${String(el.className).split(' ').slice(0, 2).join('.')} right=${Math.round(r.right)}`);
        if (out.length > 4) break;
      }
      return out.join(' | ') || `scrollWidth ${document.documentElement.scrollWidth} (fixed/drawer only)`;
    });
    console.log(`${overflow ? '⚠ ' : '✓ '}${name} @${vp.name} ${vp.width}px → ${path.basename(file)}${pieces > 1 ? ` (+${pieces - 1} pieces)` : ''} (${h}px tall${overflow ? ', OVERFLOW: ' + overflow : ''})`);
    if (errors.length) consoleErrors[`${name}@${vp.name}`] = errors;
    await page.close();
  }
  await context.close();
}
await browser.close();
server.close();
if (Object.keys(consoleErrors).length) {
  console.log('\nJS errors:');
  for (const [k, v] of Object.entries(consoleErrors)) console.log(` ${k}: ${[...new Set(v)].join(' | ')}`);
}
