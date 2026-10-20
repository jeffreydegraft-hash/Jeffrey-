/* Phone-width audit of every rendered page: full-page screenshots plus DOM checks.
   Usage: node phoneaudit.mjs <distDir> <outDir> [widths] [pages]
   Checks: horizontal overflow (and which elements cause it), clipped text, small tap targets, tiny text,
   broken images, console/page errors. Also opens the menu drawer and the cart drawer on the home page. */
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]); const outDir = path.resolve(process.argv[3] || 'audit');
const widths = (process.argv[4] || '320,360,390,430').split(',').map(Number);
const pages = process.argv[5] ? process.argv[5].split(',') : fs.readdirSync(root).filter((f) => f.endsWith('.html') && f !== 'og.html').map((f) => f.replace(/\.html$/, ''));
fs.mkdirSync(outDir, { recursive: true });
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.json': 'application/json' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'index.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const port = server.address().port;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const report = [];

const CHECKS = () => {
  const vw = document.documentElement.clientWidth;
  const vis = (e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && e.closest('[hidden],[aria-hidden="true"],template,dialog:not([open]),details:not([open]) > :not(summary)') === null; };
  const desc = (e) => `${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}${e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/).slice(0, 3).join('.') : ''}`;
  const txt = (e) => (e.innerText || e.getAttribute('aria-label') || e.getAttribute('alt') || '').trim().replace(/\s+/g, ' ').slice(0, 50);
  const out = { overflow: document.documentElement.scrollWidth > vw ? document.documentElement.scrollWidth - vw : 0, overflowers: [], clipped: [], smallTaps: [], tinyText: [], brokenImages: [], fontsFailed: [] };
  for (const e of document.querySelectorAll('body *')) {
    if (!vis(e)) continue;
    const r = e.getBoundingClientRect();
    if (r.right > vw + 1 && r.width < vw * 3 && !e.closest('.mo-hero__row') && !e.closest('[class*="scroll"], [class*="carousel"], [class*="slider"], [class*="marquee"]')) out.overflowers.push({ el: desc(e), right: Math.round(r.right), text: txt(e) });
    const cs = getComputedStyle(e);
    if (['A', 'BUTTON', 'INPUT', 'SELECT', 'SUMMARY', 'LABEL'].includes(e.tagName) && !(e.tagName === 'INPUT' && ['hidden', 'radio', 'checkbox'].includes(e.type))) {
      const hit = e.closest('label') && e.tagName !== 'LABEL' ? null : e;
      if (hit && (r.height < 32 || r.width < 32)) out.smallTaps.push({ el: desc(e), w: Math.round(r.width), h: Math.round(r.height), text: txt(e) });
    }
    if (e.children.length === 0 && e.textContent.trim() && parseFloat(cs.fontSize) < 11 && !e.closest('.sr-only, .visually-hidden')) out.tinyText.push({ el: desc(e), size: cs.fontSize, text: txt(e) });
    if (e.children.length === 0 && e.textContent.trim() && cs.overflow !== 'visible' && e.scrollWidth > e.clientWidth + 2 && cs.whiteSpace === 'nowrap' && cs.textOverflow !== 'ellipsis') out.clipped.push({ el: desc(e), text: txt(e), scrollWidth: e.scrollWidth, clientWidth: e.clientWidth });
  }
  for (const img of document.querySelectorAll('img')) if (vis(img) && img.complete && img.naturalWidth === 0 && !img.src.startsWith('data:')) out.brokenImages.push({ el: desc(img), src: img.getAttribute('src') });
  out.overflowers = out.overflowers.slice(0, 12); out.smallTaps = out.smallTaps.slice(0, 20); out.tinyText = out.tinyText.slice(0, 15); out.clipped = out.clipped.slice(0, 15);
  out.height = document.documentElement.scrollHeight;
  return out;
};

for (const pg of pages) {
  for (const w of widths) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 160)));
    page.on('console', (m) => m.type() === 'error' && errors.push('console: ' + m.text().slice(0, 160)));
    await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
    await page.goto(`http://127.0.0.1:${port}/${pg}.html`, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 500) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 60)); } window.scrollTo(0, 0); });
    await page.waitForTimeout(600);
    const checks = await page.evaluate(CHECKS);
    const file = path.join(outDir, `${pg}-${w}.png`);
    await page.screenshot({ path: file, fullPage: true });
    report.push({ page: pg, width: w, file, errors: [...new Set(errors)].slice(0, 6), ...checks });
    if (pg === 'index' && (w === 390 || w === 320)) {
      /* menu drawer */
      const burger = page.locator('.header__icon-wrapper button[aria-controls], .header button[aria-controls="sidebar-menu"], button.header__icon-wrapper').first();
      try { await burger.click({ timeout: 2000 }); await page.waitForTimeout(900); const f = path.join(outDir, `menu-${w}.png`); await page.screenshot({ path: f }); const c = await page.evaluate(CHECKS); report.push({ page: 'menu-drawer', width: w, file: f, errors: [], ...c, overflowers: c.overflowers }); await page.keyboard.press('Escape'); await page.waitForTimeout(400); } catch (e) { report.push({ page: 'menu-drawer', width: w, failed: String(e).slice(0, 120) }); }
      /* cart drawer */
      try { const cart = page.locator('a[aria-controls="cart-drawer"]').first(); await cart.click({ timeout: 2000 }); await page.waitForTimeout(900); const f = path.join(outDir, `cart-drawer-${w}.png`); await page.screenshot({ path: f }); const c = await page.evaluate(CHECKS); report.push({ page: 'cart-drawer', width: w, file: f, errors: [], ...c }); } catch (e) { report.push({ page: 'cart-drawer', width: w, failed: String(e).slice(0, 120) }); }
    }
    await ctx.close();
  }
}
await browser.close(); server.close();
fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 1));
for (const r of report) {
  const flags = [];
  if (r.failed) flags.push('FAILED ' + r.failed);
  if (r.overflow) flags.push(`overflow +${r.overflow}px (${r.overflowers.map((o) => o.el).slice(0, 3).join(', ')})`);
  if (r.clipped && r.clipped.length) flags.push(`clipped ${r.clipped.length}`);
  if (r.smallTaps && r.smallTaps.length) flags.push(`small taps ${r.smallTaps.length}`);
  if (r.tinyText && r.tinyText.length) flags.push(`tiny text ${r.tinyText.length}`);
  if (r.brokenImages && r.brokenImages.length) flags.push(`broken images ${r.brokenImages.length}`);
  if (r.errors && r.errors.length) flags.push(`errors ${r.errors.length}`);
  console.log(`${r.page.padEnd(20)} ${String(r.width).padStart(3)}  ${flags.join(' | ') || 'clean'}`);
}
