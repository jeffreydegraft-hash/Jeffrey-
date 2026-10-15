/* Screenshots every rendered page in dist/ at desktop and phone widths.
   Usage: node screenshot.mjs [--out shots] [page ...] */
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { chromium } from 'playwright-core';

const HERE = path.resolve(new URL('.', import.meta.url).pathname);
const argv = process.argv.slice(2);
const outIdx = argv.indexOf('--out');
const OUT = path.resolve(outIdx >= 0 ? argv[outIdx + 1] : path.join(HERE, 'shots'));
const only = argv.filter((a, i) => !a.startsWith('--') && argv[i - 1] !== '--out');
const DIST = path.join(HERE, 'dist');
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
const browser = await chromium.launch({ executablePath: fs.existsSync(exe) ? exe : undefined, args: ['--no-sandbox', '--disable-gpu'] });
const pages = (only.length ? only : fs.readdirSync(DIST).filter((f) => f.endsWith('.html')).map((f) => f.replace(/\.html$/, ''))).sort();
const viewports = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'phone', width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
];
const consoleErrors = {};
for (const vp of viewports) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile, hasTouch: !!vp.hasTouch, deviceScaleFactor: vp.deviceScaleFactor || 1, reducedMotion: 'no-preference' });
  for (const name of pages) {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error' && !/net::ERR|Failed to load resource|fetch/i.test(m.text())) errors.push(`console: ${m.text()}`); });
    await page.goto(`${BASE}/${name}.html`, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts && document.fonts.ready);
    // Let @starting-style entrances and reveal observers settle; reveal everything for the full-page capture
    await page.waitForTimeout(400);
    await page.evaluate(() => { document.querySelectorAll('[data-reveal]').forEach((n) => n.classList.add('is-visible')); window.scrollTo(0, 0); });
    await page.waitForTimeout(250);
    const file = path.join(OUT, `${name}--${vp.name}.png`);
    await page.screenshot({ path: file, fullPage: true });
    const h = await page.evaluate(() => document.documentElement.scrollHeight);
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
    console.log(`${overflow ? '⚠ ' : '✓ '}${name} @${vp.name} ${vp.width}px → ${path.basename(file)} (${h}px tall${overflow ? ', OVERFLOW: ' + overflow : ''})`);
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
