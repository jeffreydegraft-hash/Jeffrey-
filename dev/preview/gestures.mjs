/* Gesture tests for the spring-driven sheets (apple-design §2–§9).
   Drives the cart bottom sheet on a phone viewport with pointer events:
   flick to dismiss, slow drag springs back, upward drag rubber-bands,
   and a re-open during the exit reverses instead of jumping.
   Usage: node gestures.mjs [--dist dir]   (render 'product' into dist first) */
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { chromium } from 'playwright-core';

const HERE = path.resolve(new URL('.', import.meta.url).pathname);
const distIdx = process.argv.indexOf('--dist');
const DIST = path.resolve(distIdx >= 0 ? process.argv[distIdx + 1] : path.join(HERE, 'dist'));
const TYPES = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const file = path.join(DIST, decodeURIComponent(req.url.split('?')[0]));
  if (!file.startsWith(DIST) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox'] });

const results = [];
const check = (name, ok, detail = '') => { results.push(ok); console.log(`${ok ? '✓' : '✗'} ${name}${detail ? ' — ' + detail : ''}`); };

const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
await page.goto(`${BASE}/product.html`, { waitUntil: 'load' });
await page.waitForTimeout(300);

const drawer = '#CartDrawer';
const state = () => page.evaluate((sel) => {
  const d = document.querySelector(sel);
  const p = d && d.querySelector('[data-drawer-panel]');
  const m = p ? new DOMMatrixReadOnly(getComputedStyle(p).transform) : null;
  return { open: d && d.classList.contains('is-open'), closing: d && d.classList.contains('is-closing'), y: m ? Math.round(m.m42) : null, h: p ? Math.round(p.getBoundingClientRect().height) : 0 };
}, drawer);
const openDrawer = async () => {
  await page.evaluate((sel) => document.querySelector(sel).open(document.getElementById('cart-icon-bubble')), drawer);
  await page.waitForFunction((sel) => { const p = document.querySelector(sel + ' [data-drawer-panel]'); return new DOMMatrixReadOnly(getComputedStyle(p).transform).m42 === 0; }, drawer, { timeout: 2000 }).catch(() => {});
};
const handleBox = async () => {
  const el = await page.$(`${drawer} [data-sheet-handle]`);
  return el ? el.boundingBox() : null;
};
const drag = async (dy, ms, steps) => {
  const box = await handleBox();
  const x = box.x + box.width / 2;
  const y = box.y + Math.min(box.height / 2, 10);
  await page.mouse.move(x, y);
  await page.mouse.down();
  for (let i = 1; i <= steps; i++) {
    await page.mouse.move(x, y + (dy * i) / steps);
    await page.waitForTimeout(ms / steps);
  }
  const mid = await state();
  await page.mouse.up();
  return mid;
};

// 0. the sheet is a bottom sheet with a handle on phones
await openDrawer();
let s = await state();
check('cart opens as a sheet at rest (translateY 0)', s.open && s.y === 0, JSON.stringify(s));
const box = await handleBox();
check('sheet has a drag handle', !!box, box ? `${Math.round(box.width)}x${Math.round(box.height)}` : 'none');
const isBottom = await page.evaluate((sel) => getComputedStyle(document.querySelector(sel + ' [data-drawer-panel]')).getPropertyValue('--sheet-axis').trim() === 'y', drawer);
check('phone geometry is a bottom sheet (axis y)', isBottom);

if (box) {
  // 1. slow short drag → springs back open
  const mid = await drag(70, 700, 14);
  check('drag tracks the finger 1:1', Math.abs(mid.y - 70) <= 6, `y=${mid.y} for 70px`);
  await page.waitForTimeout(700);
  s = await state();
  check('slow short drag springs back open', s.open && Math.abs(s.y) <= 1, JSON.stringify(s));

  // 2. upward drag rubber-bands
  const up = await drag(-120, 500, 12);
  check('dragging past open rubber-bands (resists)', up.y < 0 && up.y > -80, `y=${up.y} for −120px`);
  await page.waitForTimeout(700);
  s = await state();
  check('returns to rest after the rubber-band', s.open && Math.abs(s.y) <= 1, JSON.stringify(s));

  // 3. quick flick down → dismisses with momentum
  await drag(140, 90, 6);
  await page.waitForTimeout(80);
  const t1 = await state();
  check('flick starts closing immediately', !t1.open && (t1.closing || t1.y > 140), JSON.stringify(t1));
  await page.waitForFunction((sel) => !document.querySelector(sel).classList.contains('is-closing'), drawer, { timeout: 2000 }).catch(() => {});
  s = await state();
  const inert = await page.evaluate((sel) => document.querySelector(sel).hasAttribute('inert'), drawer);
  check('flick dismisses the sheet', !s.open && !s.closing && inert, JSON.stringify(s));

  // 4. re-open during the exit reverses from the current position (no jump to closed)
  await openDrawer();
  await page.evaluate((sel) => document.querySelector(sel).close(), drawer);
  await page.waitForTimeout(90);
  const before = await state();
  await page.evaluate((sel) => document.querySelector(sel).open(), drawer);
  await page.waitForTimeout(16);
  const after = await state();
  check('re-open mid-close continues from the on-screen position', after.y <= before.y + 2 && after.y < before.h * 0.9, `closing y=${before.y} → reopening y=${after.y} (sheet ${before.h}px)`);
  await page.waitForTimeout(800);
  s = await state();
  check('…and settles open', s.open && Math.abs(s.y) <= 1, JSON.stringify(s));
}

// 5. reduced motion: no transform motion, still opens and closes
const rctx = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
const rp = await rctx.newPage();
await rp.goto(`${BASE}/product.html`, { waitUntil: 'load' });
await rp.waitForTimeout(200);
await rp.evaluate((sel) => document.querySelector(sel).open(), drawer);
await rp.waitForTimeout(260);
const r = await rp.evaluate((sel) => { const p = document.querySelector(sel + ' [data-drawer-panel]'); return { t: getComputedStyle(p).transform, o: getComputedStyle(p).opacity, open: document.querySelector(sel).classList.contains('is-open') }; }, drawer);
check('reduced motion: opens without movement (opacity only)', r.open && (r.t === 'none' || r.t === 'matrix(1, 0, 0, 1, 0, 0)') && Number(r.o) > 0.9, JSON.stringify(r));
await rctx.close();

check('no JS errors', errors.length === 0, errors.join(' | '));
await browser.close();
server.close();
const failed = results.filter((x) => !x).length;
console.log(`\n${results.length - failed}/${results.length} gesture checks passed`);
process.exit(failed ? 1 : 0);
