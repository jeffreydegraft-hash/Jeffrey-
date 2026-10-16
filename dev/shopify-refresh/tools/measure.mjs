import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]); const widths = (process.argv[3] || '320,360,390,430').split(',').map(Number);
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'index.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
for (const w of widths) {
  const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const page = await ctx.newPage(); await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'load' }); await page.evaluate(() => document.fonts.ready);
  const m = await page.evaluate(() => { const r = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; };
    return { header: r('.header'), logo: r('.header__logo'), wordmark: r('.mo-wordmark'), nav: r('.header__primary-nav'), secondary: r('.header__secondary-nav'), search: r('.header__search-link'), cart: r('.header__cart-link'), heroTitle: r('.mo-hero__title') }; });
  console.log(w, JSON.stringify(m));
  await ctx.close();
}
await browser.close(); server.close();
