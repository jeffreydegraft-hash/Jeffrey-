import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]); const out = process.argv[3];
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'og.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'load' }); await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(500);
await page.screenshot({ path: out, type: 'jpeg', quality: 90 });
/* phone sidebar menu */
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
const p2 = await ctx.newPage(); await p2.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
await p2.goto(`http://127.0.0.1:${server.address().port}/index.html`, { waitUntil: 'load' }); await p2.waitForTimeout(1000);
await p2.locator('button[aria-controls="sidebar-menu"]').first().tap(); await p2.waitForTimeout(900);
await p2.screenshot({ path: out.replace('.jpg', '-phone-menu.png') });
await browser.close(); server.close(); console.log('ok');
