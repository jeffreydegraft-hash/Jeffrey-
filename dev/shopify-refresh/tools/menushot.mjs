/* Open the Shop mega menu on desktop and screenshot it */
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]); const out = process.argv[3];
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'index.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = []; page.on('pageerror', (e) => errors.push(e.message));
await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'load' }); await page.waitForTimeout(1200);
const shop = page.locator('.header__primary-nav-item summary', { hasText: 'Shop' }).first();
await shop.hover(); await page.waitForTimeout(900);
await page.screenshot({ path: out, clip: { x: 0, y: 0, width: 1440, height: 640 } });
console.log('menu open:', await page.evaluate(() => !!document.querySelector('.header__menu-disclosure[open]')), errors.slice(0, 3));
await browser.close(); server.close();
