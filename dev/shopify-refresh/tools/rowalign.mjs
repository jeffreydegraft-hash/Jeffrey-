/* Measure the phone hero: row/frame/spot geometry, rendered bottle columns per row, and frame vs page colour.
   Usage: node rowalign.mjs <distDir> <outPrefix> [widths] */
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]); const prefix = process.argv[3] || 'rowalign'; const widths = (process.argv[4] || '320,360,390,430').split(',').map(Number);
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'index.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
for (const w of widths) {
  const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const page = await ctx.newPage(); await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'load' }); await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(1300);
  const m = await page.evaluate(() => {
    const rect = (e) => { const b = e.getBoundingClientRect(); return { l: +b.left.toFixed(1), t: +b.top.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) }; };
    const media = document.querySelector('.mo-hero__media');
    const rows = [...document.querySelectorAll('.mo-hero__row')].filter((r) => getComputedStyle(r).display !== 'none');
    return { media: rect(media), docW: document.documentElement.scrollWidth, rows: rows.map((row) => { const rr = rect(row); const f = rect(row.querySelector('.mo-hero__frame'));
      const spots = [...row.querySelectorAll('.mo-hero__spot')].filter((a) => getComputedStyle(a).display !== 'none').map((a) => { const s = rect(a); const lab = rect(a.querySelector('.mo-hero__spot-label')); return { href: a.getAttribute('href'), centrePctOfRow: +(((s.l + s.w / 2 - rr.l) / rr.w) * 100).toFixed(2), labelCentrePct: +(((lab.l + lab.w / 2 - rr.l) / rr.w) * 100).toFixed(2), labelW: lab.w, labelH: lab.h, labelBottomGap: +(rr.t + rr.h - (lab.t + lab.h)).toFixed(1) }; });
      return { row: rr, frame: f, spots }; }) };
  });
  const file = `${prefix}-${w}.png`;
  await page.locator('.mo-hero__media').screenshot({ path: file });
  console.log(JSON.stringify({ width: w, docW: m.docW, media: m.media, rows: m.rows, file }));
  await ctx.close();
}
await browser.close(); server.close();
