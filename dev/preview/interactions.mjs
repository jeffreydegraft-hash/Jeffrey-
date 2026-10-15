/* Drives the drawers and the product page in Chromium against dist/.
   Usage: node interactions.mjs   (run `node render.mjs` first) */
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { chromium } from 'playwright-core';

const HERE = path.resolve(new URL('.', import.meta.url).pathname);
const DIST = path.join(HERE, 'dist');
const OUT = path.join(HERE, 'shots');
fs.mkdirSync(OUT, { recursive: true });
const TYPES = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const file = path.join(DIST, decodeURIComponent(req.url.split('?')[0]));
  if (!file.startsWith(DIST) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const exe = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const browser = await chromium.launch({ executablePath: exe, args: ['--no-sandbox'] });

const results = [];
const check = (name, ok, detail = '') => { results.push({ name, ok, detail }); console.log(`${ok ? '✓' : '✗'} ${name}${detail ? ' — ' + detail : ''}`); };

async function drawerTest(page, { name, trigger, drawer, shot }) {
  const t = page.locator(trigger).first();
  if (!(await t.count())) return check(`${name}: trigger exists`, false, trigger);
  await t.click();
  await page.waitForTimeout(650);
  const open = await page.evaluate((sel) => document.querySelector(sel)?.classList.contains('is-open'), drawer);
  check(`${name}: opens`, !!open);
  const focusInside = await page.evaluate((sel) => document.querySelector(sel)?.contains(document.activeElement), drawer);
  check(`${name}: focus moves inside`, !!focusInside, await page.evaluate(() => document.activeElement?.className || document.activeElement?.tagName));
  const locked = await page.evaluate(() => document.body.classList.contains('drawer-open'));
  check(`${name}: body scroll locked`, locked);
  const expanded = await t.getAttribute('aria-expanded');
  check(`${name}: trigger aria-expanded=true`, expanded === 'true', String(expanded));
  if (shot) await page.screenshot({ path: path.join(OUT, shot) });
  await page.keyboard.press('Escape');
  // Wait for the exit spring to settle (the drawer drops .is-closing when done)
  await page.waitForFunction((sel) => { const d = document.querySelector(sel); return d && !d.classList.contains('is-open') && !d.classList.contains('is-closing'); }, drawer, { timeout: 2000 }).catch(() => {});
  const closed = await page.evaluate((sel) => !document.querySelector(sel)?.classList.contains('is-open'), drawer);
  check(`${name}: Escape closes`, closed);
  const inert = await page.evaluate((sel) => document.querySelector(sel)?.hasAttribute('inert'), drawer);
  check(`${name}: inert after close`, !!inert);
  const back = await page.evaluate((sel) => document.activeElement === document.querySelector(sel), trigger);
  check(`${name}: focus returns to trigger`, back);
}

for (const vp of [{ n: 'phone', w: 390, h: 844, m: true }, { n: 'desktop', w: 1440, h: 900, m: false }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.m, hasTouch: vp.m, deviceScaleFactor: vp.m ? 2 : 1 });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`${BASE}/product.html`, { waitUntil: 'load' });
  await page.waitForTimeout(300);
  console.log(`\n— ${vp.n} (${vp.w}px)`);
  if (vp.m) await drawerTest(page, { name: 'menu drawer', trigger: '.header__menu-toggle', drawer: '#MenuDrawer', shot: 'drawer-menu--phone.png' });
  await drawerTest(page, { name: 'search drawer', trigger: '.header__icon--search', drawer: '#SearchDrawer', shot: `drawer-search--${vp.n}.png` });
  await drawerTest(page, { name: 'cart drawer', trigger: '#cart-icon-bubble', drawer: '#CartDrawer', shot: `drawer-cart--${vp.n}.png` });

  if (vp.m) {
    // submenu
    await page.locator('.header__menu-toggle').click();
    await page.waitForTimeout(450);
    const sub = page.locator('[data-submenu-open]').first();
    if (await sub.count()) {
      await sub.click();
      await page.waitForTimeout(300);
      check('menu drawer: submenu opens', await page.evaluate(() => !!document.querySelector('[data-submenu].is-open')));
      await page.screenshot({ path: path.join(OUT, 'drawer-submenu--phone.png') });
      await page.locator('[data-submenu].is-open [data-submenu-back]').click();
      await page.waitForTimeout(250);
      check('menu drawer: back closes submenu', await page.evaluate(() => !document.querySelector('[data-submenu].is-open')));
    }
    await page.keyboard.press('Escape');
    await page.waitForTimeout(700);
  }

  // product: variant pill updates hidden id + label
  const pills = page.locator('.variant-picker__pill, label.chip');
  if ((await pills.count()) > 1) {
    const before = await page.evaluate(() => document.querySelector('form[data-type="add-to-cart-form"] input[name="id"]')?.value);
    await pills.nth(1).click();
    await page.waitForTimeout(300);
    const after = await page.evaluate(() => document.querySelector('form[data-type="add-to-cart-form"] input[name="id"]')?.value);
    check('product: size pill changes variant id', before !== after, `${before} → ${after}`);
  }
  // accordion
  const summary = page.locator('olivet-accordion summary').first();
  if (await summary.count()) {
    await summary.click();
    await page.waitForTimeout(350);
    check('product: accordion opens', (await summary.getAttribute('aria-expanded')) === 'true');
  }
  // tap targets under 44px among visible interactive elements
  // Touch needs 40px+ (44px design target); fine pointers accept Apple's 36px desktop pills
  const minH = vp.m ? 40 : 32;
  const small = await page.evaluate((minH) => {
    const out = [];
    for (const el of document.querySelectorAll('a, button, summary, input, select, [role="button"], label.chip')) {
      if (el.closest('[inert], [hidden], .visually-hidden') || el.classList.contains('visually-hidden') || el.classList.contains('skip-link')) continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      // inline text links inside prose are exempt (WCAG 2.5.8 inline exception)
      if (el.tagName === 'A' && cs.display === 'inline' && el.closest('p, .rte, li')) continue;
      if (r.height < minH || r.width < 24) out.push(`${el.tagName.toLowerCase()}.${String(el.className).split(' ')[0]} ${Math.round(r.width)}x${Math.round(r.height)}`);
    }
    return [...new Set(out)].slice(0, 12);
  }, minH);
  check(`tap targets ≥ ${minH}px tall, 24px wide (${vp.n})`, small.length === 0, small.join(', '));
  check(`no JS errors (${vp.n})`, errors.length === 0, errors.join(' | '));
  await ctx.close();
}
await browser.close();
server.close();
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
