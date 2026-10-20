import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]); const pg = process.argv[3] || 'index'; const w = +(process.argv[4] || 320);
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'index.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
const page = await ctx.newPage(); await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
await page.goto(`http://127.0.0.1:${server.address().port}/${pg}.html`, { waitUntil: 'load' }); await page.evaluate(() => document.fonts.ready);
await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 50)); } window.scrollTo(0, 0); }); await page.waitForTimeout(500);
const out = await page.evaluate(() => {
  const r = (e) => { const b = e.getBoundingClientRect(); return { top: Math.round(b.top + scrollY), h: Math.round(b.height), w: Math.round(b.width) }; };
  const desc = (e) => `${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}${typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\s+/).slice(0, 3).join('.') : ''}`;
  const res = { scrollHeight: document.documentElement.scrollHeight, bodyHeight: document.body.scrollHeight };
  const footer = document.querySelector('.footer, #shopify-section-sections--footer, [id^="shopify-section-sections"] footer, footer');
  res.footerBottom = footer ? r(footer).top + r(footer).h : null;
  res.below = [...document.querySelectorAll('body *')].filter((e) => { const b = e.getBoundingClientRect(); return b.height > 0 && b.bottom + scrollY > res.footerBottom + 2 && getComputedStyle(e).position !== 'fixed'; }).slice(0, 12).map((e) => ({ el: desc(e), ...r(e), pos: getComputedStyle(e).position }));
  const sec = document.querySelector('[id$="__mo-testimonials"]') || document.querySelector('.shopify-section--testimonials');
  if (sec) {
    res.section = r(sec);
    res.items = [...sec.querySelectorAll('.testimonial-item, testimonial-item, [class*="testimonial"]')].slice(0, 14).map((e) => ({ el: desc(e), ...r(e), display: getComputedStyle(e).display, minH: getComputedStyle(e).minHeight }));
    res.sectionHTML = sec.innerHTML.replace(/\s+/g, ' ').slice(0, 1800);
  }
  return res;
});
console.log(JSON.stringify(out, null, 1));
await browser.close(); server.close();
