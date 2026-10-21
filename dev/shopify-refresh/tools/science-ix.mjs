/* Interaction test for the Our Science page: node ix.mjs <distDir> <outDir> */
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
const root = path.resolve(process.argv[2]); const out = path.resolve(process.argv[3]); fs.mkdirSync(out, { recursive: true });
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => { const u = decodeURIComponent(req.url.split('?')[0]); const p = path.join(root, u === '/' ? 'index.html' : u); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res); });
await new Promise((r) => server.listen(0, r));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const log = (...a) => console.log(...a);
async function open(v) {
  const ctx = await browser.newContext({ viewport: { width: v.w, height: v.h }, deviceScaleFactor: v.m ? 2 : 1, isMobile: v.m, hasTouch: v.m });
  const page = await ctx.newPage(); const errors = []; page.on('pageerror', (e) => errors.push(e.message.slice(0, 160)));
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/page-our-science.html`, { waitUntil: 'load' }); await page.evaluate(() => document.fonts.ready);
  return { ctx, page, errors };
}
async function shotEl(page, sel, file) { const el = page.locator(sel).first(); await el.scrollIntoViewIfNeeded(); await page.waitForTimeout(500); await el.screenshot({ path: path.join(out, file) }); }

for (const v of [{ w: 390, h: 844, m: true, n: 'phone' }, { w: 1440, h: 900, m: false, n: 'desktop' }]) {
  const { ctx, page, errors } = await open(v);
  // timeline: click each step
  const steps = page.locator('.timeline__nav button');
  const n = await steps.count(); log(v.n, 'timeline steps', n);
  for (let i = 0; i < n; i++) { await steps.nth(i).click(); await page.waitForTimeout(900); await shotEl(page, '.shopify-section--timeline', `${v.n}-timeline-${i + 1}.png`); }
  // tabs: click each title
  const tabs = page.locator(v.m ? '.shopify-section--tabs .accordion-group summary' : '.shopify-section--tabs button[role=tab]');
  const tn = await tabs.count(); log(v.n, 'tabs', tn);
  for (let i = 0; i < tn; i++) { await tabs.nth(i).scrollIntoViewIfNeeded(); await tabs.nth(i).click(); await page.waitForTimeout(700); }
  await shotEl(page, '.shopify-section--tabs', `${v.n}-tabs-last.png`);
  // shop the look
  if (v.m) {
    const btn = page.locator('.shopify-section--shop-the-look button, .shopify-section--shop-the-look .button').filter({ hasText: /view products/i }).first();
    await btn.scrollIntoViewIfNeeded(); await btn.click(); await page.waitForTimeout(900);
    await page.screenshot({ path: path.join(out, 'phone-look-popover.png') });
    const popover = await page.evaluate(() => { const p = document.querySelector('shop-the-look-popover[open]'); if (!p) return null; return { items: p.querySelectorAll('product-card, .product-card, .horizontal-product-card, [class*=product-card]').length, titles: [...p.querySelectorAll('a')].map((a) => a.textContent.trim()).filter(Boolean).slice(0, 6) }; });
    log('phone popover', JSON.stringify(popover));
    await page.keyboard.press('Escape'); await page.waitForTimeout(400);
  } else {
    const hs = page.locator('.shopify-section--shop-the-look .shop-the-look__hot-spot:visible');
    log('desktop hotspots', await hs.count());
    await hs.nth(2).scrollIntoViewIfNeeded(); await hs.nth(2).click(); await page.waitForTimeout(900);
    await shotEl(page, '.shopify-section--shop-the-look', 'desktop-look-hotspot3.png');
    const shown = await page.evaluate(() => { const c = document.querySelector('.shop-the-look__item.is-selected [class*=item-carousel] .is-selected, .shop-the-look__item.is-selected .is-selected'); return c ? c.textContent.replace(/\s+/g, ' ').trim().slice(0, 80) : null; });
    log('desktop selected product card', shown);
  }
  // glossary: open an accordion
  const acc = page.locator('.shopify-section--faq summary').first();
  await acc.scrollIntoViewIfNeeded(); await acc.click(); await page.waitForTimeout(700);
  await shotEl(page, '.shopify-section--faq', `${v.n}-faq-open.png`);
  // anchor link
  await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForTimeout(300);
  const link = page.locator('a[href="#ingredients"]').first(); await link.click(); await page.waitForTimeout(900);
  const anchor = await page.evaluate(() => { const a = document.getElementById('ingredients'); const r = a.getBoundingClientRect(); const h = document.querySelector('#shopify-section-header, header, .header'); const hr = h ? h.getBoundingClientRect() : null; return { anchorTop: Math.round(r.top), headerBottom: hr ? Math.round(hr.bottom) : null, scrollY: Math.round(scrollY) }; });
  log(v.n, 'anchor', JSON.stringify(anchor));
  // overflow check
  const overflow = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  log(v.n, 'overflow', JSON.stringify(overflow), 'errors', errors.filter((e) => !/json|JSON/.test(e)).slice(0, 3));
  await ctx.close();
}
await browser.close(); server.close();
