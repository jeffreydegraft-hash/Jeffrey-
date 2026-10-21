/* Screenshot the welcome pop-in: <distDir> <outPrefix> [open]  (open = call show() on load) */
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]); const prefix = process.argv[3]; const forceOpen = process.argv[4] === 'open';
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'index.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
for (const v of [{ w: 390, h: 844, m: true }, { w: 1440, h: 900, m: false }]) {
  const ctx = await browser.newContext({ viewport: { width: v.w, height: v.h }, deviceScaleFactor: v.m ? 2 : 1, isMobile: v.m, hasTouch: v.m });
  const page = await ctx.newPage(); const errors = []; page.on('pageerror', (e) => errors.push(e.message.slice(0, 120)));
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'load' }); await page.evaluate(() => document.fonts.ready);
  if (forceOpen) await page.evaluate(() => document.querySelector('newsletter-popup').show());
  await page.waitForTimeout(1500);
  const info = await page.evaluate(() => { const p = document.querySelector('newsletter-popup'); const r = p.getBoundingClientRect(); const btn = p.querySelector('button[type=submit], a.button, .button'); const b = btn && btn.getBoundingClientRect(); return { open: p.hasAttribute('open'), box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], button: b && [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)], appeared: localStorage.getItem('theme:popup-appeared'), href: (p.querySelector('a.button') || {}).getAttribute ? p.querySelector('a.button').getAttribute('href') : null }; });
  await page.screenshot({ path: `${prefix}-${v.w}.png` });
  console.log(v.w, JSON.stringify(info), errors.slice(0, 2));
  await ctx.close();
}
await browser.close(); server.close();
