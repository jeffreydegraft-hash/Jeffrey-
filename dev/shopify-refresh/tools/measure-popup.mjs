/* Measure the welcome pop-in at phone viewports: node measure-popup.mjs <distDir> */
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]);
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'index.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const out = process.argv[3] || '';
for (const v of [{ w: 320, h: 568 }, { w: 360, h: 640 }, { w: 375, h: 553 }, { w: 375, h: 667 }, { w: 390, h: 664 }, { w: 390, h: 844 }, { w: 430, h: 932 }]) {
  const ctx = await browser.newContext({ viewport: { width: v.w, height: v.h }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'load' }); await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => document.querySelector('newsletter-popup').show());
  await page.waitForTimeout(900);
  const info = await page.evaluate(() => {
    const q = (s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), w: Math.round(r.width), h: Math.round(r.height), fs: cs.fontSize }; };
    return { vh: innerHeight, popup: q('newsletter-popup'), media: q('.newsletter-popup__media'), title: q('.newsletter-popup__title'), prose: q('.newsletter-popup__body .prose'), input: q('.newsletter-popup input[type=email]'), button: q('.newsletter-popup .button'), decline: q('.newsletter-popup__decline'), close: q('.newsletter-popup .pop-in__close-button'), code: q('.newsletter-popup__code') };
  });
  console.log(`${v.w}x${v.h}`, JSON.stringify(info));
  if (out) await page.screenshot({ path: `${out}-${v.w}x${v.h}.png` });
  await ctx.close();
}
await browser.close(); server.close();
