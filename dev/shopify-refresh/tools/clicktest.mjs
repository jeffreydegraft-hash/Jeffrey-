/* Click each bottle in the hero (by its measured centre in the photo) and report which page it opens. */
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]);
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'index.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const names = ['Rose of Sharon', 'Latter Rain', 'Hyssop', 'Spikenard', 'Lily of the Valley', 'Frankincense & Myrrh', 'Pomegranate', 'Gethsemane'];
const centres = [8.6, 20.5, 32.2, 43.7, 55.7, 68.1, 80.1, 91.9]; /* measured from the photo, % of width */
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
let bad = 0;
for (const v of [{ w: 1440, h: 900, m: false }, { w: 1024, h: 768, m: false }, { w: 390, h: 844, m: true }, { w: 360, h: 740, m: true }]) {
  const ctx = await browser.newContext({ viewport: { width: v.w, height: v.h }, deviceScaleFactor: 1, isMobile: v.m, hasTouch: v.m });
  const page = await ctx.newPage(); await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: 'load' }); await page.waitForTimeout(1300);
  const res = await page.evaluate(({ centres }) => {
    const out = [];
    const rows = [...document.querySelectorAll('.mo-hero__row')].filter((r) => r.offsetParent !== null);
    for (const row of rows) {
      /* a row can sit below the first screen on short phones: bring it into view before sampling */
      row.scrollIntoView({ block: 'center' });
      const rr = row.getBoundingClientRect();
      const f = row.querySelector('.mo-hero__frame').getBoundingClientRect();
      centres.forEach((c, i) => {
        for (const yPct of [0.30, 0.49, 0.70]) {
          const x = f.left + (c / 100) * f.width, y = f.top + yPct * f.height;
          if (x < rr.left || x > rr.right || y < rr.top || y > rr.bottom) continue;
          const el = document.elementFromPoint(x, y);
          const a = el && el.closest('a');
          out.push({ i, yPct, href: a ? a.getAttribute('href') : null });
        }
      });
    }
    const visibleLinks = [...document.querySelectorAll('.mo-hero__spot')].filter((a) => a.offsetParent !== null && getComputedStyle(a).display !== 'none').map((a) => a.getAttribute('href'));
    return { out, visibleLinks };
  }, { centres });
  const byBottle = {};
  for (const r of res.out) (byBottle[r.i] ||= new Set()).add(r.href);
  console.log(`\n${v.w}px: ${res.visibleLinks.length} bottle links reachable by keyboard`);
  names.forEach((n, i) => {
    const hrefs = [...(byBottle[i] || [])];
    const ok = hrefs.length === 1 && hrefs[0] && (i === 5 ? hrefs[0] === '/collections/frankincense-myrrh' : hrefs[0].startsWith('/products/'));
    if (!ok) bad++;
    console.log(`  ${ok ? 'ok ' : 'BAD'} ${n.padEnd(22)} -> ${hrefs.join(' | ') || '(nothing)'}`);
  });
  if (new Set(res.visibleLinks).size !== 8 || res.visibleLinks.length !== 8) { bad++; console.log('  BAD duplicate or missing keyboard links', res.visibleLinks); }
  await ctx.close();
}
await browser.close(); server.close();
console.log(bad ? `\n${bad} problem(s)` : '\nall bottles open the right page');
