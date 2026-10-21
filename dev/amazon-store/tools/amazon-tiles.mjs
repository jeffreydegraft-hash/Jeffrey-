/* Render Amazon Store images in the brand's type: node amazon-tiles.mjs <copy.json> <imgDir> <outDir> */
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const [copyFile, imgDir, outDir] = process.argv.slice(2).map((p) => path.resolve(p));
fs.mkdirSync(outDir, { recursive: true });
const copy = JSON.parse(fs.readFileSync(copyFile, 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const fonts = { 'cormorant-500': 'node_modules/@fontsource/cormorant/files/cormorant-latin-500-normal.woff2', 'cormorant-500i': 'node_modules/@fontsource/cormorant/files/cormorant-latin-500-italic.woff2', 'montserrat-400': 'node_modules/@fontsource/montserrat/files/montserrat-latin-400-normal.woff2', 'montserrat-500': 'node_modules/@fontsource/montserrat/files/montserrat-latin-500-normal.woff2' };
const types = { '.html': 'text/html', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  let p = null;
  if (u.startsWith('/img/')) { p = path.join(imgDir, u.slice(5)); if (!fs.existsSync(p)) p = path.join(imgDir, '..', 'amazon', 'src', u.slice(5)); }
  else if (u.startsWith('/fonts/')) p = path.join(HERE, fonts[u.slice(7).replace('.woff2', '')] || '');
  if (!p || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, r));
const base = `http://127.0.0.1:${server.address().port}`;
const css = `
@font-face{font-family:Cormorant;font-weight:500;src:url(/fonts/cormorant-500.woff2) format("woff2")}
@font-face{font-family:Cormorant;font-weight:500;font-style:italic;src:url(/fonts/cormorant-500i.woff2) format("woff2")}
@font-face{font-family:Montserrat;font-weight:400;src:url(/fonts/montserrat-400.woff2) format("woff2")}
@font-face{font-family:Montserrat;font-weight:500;src:url(/fonts/montserrat-500.woff2) format("woff2")}
*{margin:0;box-sizing:border-box} html,body{width:100%;height:100%} body{background:#faf7f2;color:#2c3227;font-family:Montserrat,sans-serif;overflow:hidden;position:relative}
.serif{font-family:Cormorant,serif;font-weight:500;text-transform:uppercase;letter-spacing:.06em;line-height:1.05}
.caps{font-family:Montserrat,sans-serif;font-weight:500;text-transform:uppercase;letter-spacing:.22em;color:#c4a265}
.body{font-family:Montserrat,sans-serif;font-weight:400;line-height:1.5}
.blend{mix-blend-mode:multiply}
.wordmark{font-family:Cormorant,serif;font-weight:500;letter-spacing:.14em;text-transform:uppercase}
.wordmark small{font-size:.55em;text-transform:lowercase;letter-spacing:.05em;font-style:italic;margin:0 .15em}
`;
const page_ = (w, h, body) => `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body style="width:${w}px;height:${h}px">${body}</body></html>`;
const tiles = [];
// 1. Home hero 3000x600: safe zone x 450..2550
tiles.push({ name: 'hero-home-3000x600.jpg', w: 3000, h: 600, html: `
  <div style="position:absolute;left:480px;top:0;height:600px;width:860px;display:flex;flex-direction:column;justify-content:center;gap:26px">
    <div class="wordmark" style="font-size:62px">Mount <small>of</small> Olives</div>
    <div class="caps" style="font-size:24px">${esc(copy.hero_home.eyebrow)}</div>
    <div class="serif" style="font-size:86px">${esc(copy.hero_home.title)}</div>
    <div class="body" style="font-size:29px;max-width:760px">${esc(copy.hero_home.line)}</div>
  </div>
  <img src="/img/hero-cream.jpg" style="position:absolute;left:1330px;top:30px;height:540px;width:auto">` });
// 2. Shop hero
tiles.push({ name: 'hero-shop-3000x600.jpg', w: 3000, h: 600, html: `
  <div style="position:absolute;left:480px;top:0;height:600px;width:860px;display:flex;flex-direction:column;justify-content:center;gap:26px">
    <div class="caps" style="font-size:24px">${esc(copy.hero_shop.eyebrow)}</div>
    <div class="serif" style="font-size:86px">${esc(copy.hero_shop.title)}</div>
    <div class="body" style="font-size:27px;max-width:780px">${esc(copy.hero_shop.line)}</div>
  </div>
  <img src="/img/hero-cream.jpg" style="position:absolute;left:1330px;top:30px;height:540px;width:auto">` });
// 3. Oil tiles 1500x1500 (bottom 12% left clear for Amazon's link title)
for (const o of copy.oils) tiles.push({ name: `tile-${o.key}-1500x1500.jpg`, w: 1500, h: 1500, html: `
  <div style="position:absolute;left:0;right:0;top:110px;text-align:center;padding:0 120px">
    <div class="caps" style="font-size:26px;margin-bottom:22px">${esc(o.word)}</div>
    <div class="serif" style="font-size:${o.name.length > 14 ? 96 : 118}px">${esc(o.name)}</div>
    <div class="body" style="font-size:34px;margin-top:22px;color:#2c3227">${esc(o.line)}</div>
    <div class="caps" style="font-size:22px;margin-top:18px;color:#2c3227;opacity:.75">${esc(o.verse)}</div>
  </div>
  <img src="/img/${o.image.replace('.jpg','-cream.jpg')}" style="position:absolute;left:300px;top:420px;width:900px;height:900px;object-fit:contain">` });
// 4. Scripture tile 1500x750 (olive)
tiles.push({ name: 'tile-scripture-1500x750.jpg', w: 1500, h: 750, html: `
  <div style="position:absolute;inset:0;background:#2c3227;color:#faf7f2;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 160px 90px">
    <div style="font-family:Cormorant,serif;font-style:italic;font-weight:500;font-size:64px;line-height:1.2">“${esc(copy.scripture.quote)}”</div>
    <div class="caps" style="font-size:24px;margin-top:34px">${esc(copy.scripture.ref)}</div>
  </div>` });
// 5. Story tile 1500x750 with the praying photo
tiles.push({ name: 'tile-story-1500x750.jpg', w: 1500, h: 750, html: `
  <img src="/img/praying-with-frankincense-myrrh.jpg" style="position:absolute;left:0;top:0;width:1500px;height:750px;object-fit:cover;object-position:50% 38%">
  <div style="position:absolute;inset:0;background:linear-gradient(to right, rgba(44,50,39,.78) 0%, rgba(44,50,39,.55) 48%, rgba(44,50,39,0) 75%)"></div>
  <div style="position:absolute;left:110px;top:0;height:660px;width:720px;display:flex;flex-direction:column;justify-content:center;gap:22px;color:#faf7f2">
    <div class="caps" style="font-size:22px">${esc(copy.story.eyebrow)}</div>
    <div class="serif" style="font-size:66px">${esc(copy.story.title)}</div>
    <div class="body" style="font-size:26px;max-width:640px">${esc(copy.story.line)}</div>
  </div>` });
// 6. What is inside tile 1500x750
tiles.push({ name: 'tile-inside-1500x750.jpg', w: 1500, h: 750, html: `
  <div style="position:absolute;left:110px;top:0;height:660px;width:820px;display:flex;flex-direction:column;justify-content:center;gap:22px">
    <div class="caps" style="font-size:22px">${esc(copy.inside.eyebrow)}</div>
    <div class="serif" style="font-size:60px">${esc(copy.inside.title)}</div>
    <div class="body" style="font-size:24px;max-width:780px">${esc(copy.inside.line)}</div>
  </div>
  <img src="/img/p-squalane-cream.jpg" style="position:absolute;left:960px;top:-20px;width:600px;height:600px;object-fit:contain">` });
// 7. Logo 400x400
tiles.push({ name: 'logo-400x400.png', w: 400, h: 400, png: true, html: `
  <div style="position:absolute;inset:0;background:#fff;display:flex;align-items:center;justify-content:center"><img src="/img/mo-favicon-sprig.png" style="width:360px;height:360px"></div>` });
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
for (const t of tiles) {
  const ctx = await browser.newContext({ viewport: { width: t.w, height: t.h }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.setContent(page_(t.w, t.h, t.html).replace(/src="\//g, `src="${base}/`).replace(/url\(\//g, `url(${base}/`), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(300);
  const overflow = await page.evaluate(() => [...document.querySelectorAll('.serif,.body,.caps')].some((e) => e.scrollWidth > e.clientWidth + 1));
  await page.screenshot({ path: path.join(outDir, t.name), type: t.png ? 'png' : 'jpeg', quality: t.png ? undefined : 92, fullPage: false });
  console.log(t.name, overflow ? 'TEXT OVERFLOW' : 'ok');
  await ctx.close();
}
await browser.close(); server.close();
