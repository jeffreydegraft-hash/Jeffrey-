import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]); const out = process.argv[3];
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'product.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
for (const v of [{ n: 'desktop', w: 1440, h: 1000, m: false, s: 1 }, { n: 'phone', w: 390, h: 844, m: true, s: 2 }]) {
  const ctx = await browser.newContext({ viewport: { width: v.w, height: v.h }, deviceScaleFactor: v.s, isMobile: v.m, hasTouch: v.m });
  const page = await ctx.newPage(); await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'load' }); await page.waitForTimeout(1200);
  const el = page.locator('.mo-sizes').first(); await el.scrollIntoViewIfNeeded(); await page.waitForTimeout(300);
  const b = await el.boundingBox();
  await page.screenshot({ path: `${out}-${v.n}.png`, clip: { x: v.m ? 0 : b.x - 40, y: Math.max(0, b.y - 260), width: v.m ? v.w : b.width + 80, height: b.height + 420 } });
  console.log(v.n, 'rows:', await page.locator('.mo-sizes__row').count(), 'badge:', await page.locator('.mo-sizes__badge').first().textContent());
  await ctx.close();
}
await browser.close(); server.close();
