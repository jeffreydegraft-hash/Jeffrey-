/* Screenshot rendered preview pages with Chromium.
   Usage: node shoot.mjs <distDir> <outPrefix> [page] [--full] */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';

const [DIST, PREFIX, PAGE = 'index', ...flags] = process.argv.slice(2);
const full = flags.includes('--full');
const root = path.resolve(DIST);
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  let p = path.join(root, u === '/' ? `${PAGE}.html` : u);
  if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) {
    res.writeHead(404);
    return res.end();
  }
  res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, r));
const port = server.address().port;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' }).catch(() => chromium.launch());
const views = [
  { name: 'desktop', width: 1440, height: 900, mobile: false },
  { name: 'phone', width: 390, height: 844, mobile: true },
];
for (const v of views) {
  const ctx = await browser.newContext({ viewport: { width: v.width, height: v.height }, deviceScaleFactor: v.mobile ? 2 : 1, isMobile: v.mobile, hasTouch: v.mobile });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (route) => route.abort());
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  /* reveal everything that waits for scroll-triggered animations */
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 400) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 60));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${PREFIX}-${v.name}.png`, fullPage: full });
  if (errors.length) console.log(`${v.name} errors:`, [...new Set(errors)].slice(0, 8));
  await ctx.close();
}
await browser.close();
server.close();
console.log('shot', PREFIX);
