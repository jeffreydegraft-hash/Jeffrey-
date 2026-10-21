/* Bold Amazon Store images: colour fields from each label, giant type, bottles bleeding off the edge.
   node amazon-tiles-bold.mjs <copy.json> <srcDir with *-white.jpg> <outDir> */
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import { chromium } from 'playwright-core';
import { fileURLToPath } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const [copyFile, srcDir, outDir] = process.argv.slice(2).map((p) => path.resolve(p));
fs.mkdirSync(outDir, { recursive: true });
const copy = JSON.parse(fs.readFileSync(copyFile, 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const COL = { // label colours: pastel field, deep text
  'frankincense-myrrh': ['#e6d8c6', '#4a3728'], hyssop: ['#ddcfe9', '#4f3570'], spikenard: ['#cfe0cc', '#2f5a3a'], 'latter-rain': ['#cbdeee', '#2f5a80'],
  'rose-of-sharon': ['#f3cbc4', '#8c3b3f'], 'lily-of-the-valley': ['#e2e5e7', '#45505a'], pomegranate: ['#f2c2ba', '#7d2a24'], gethsemane: ['#f4ebb6', '#5f5414'],
  frankincense: ['#e6e3c5', '#54552a'], myrrh: ['#f3d3bc', '#8a4a22'], squalane: ['#eadfcb', '#6b4a1e'] };
const fonts = { 'cormorant-500': 'node_modules/@fontsource/cormorant/files/cormorant-latin-500-normal.woff2', 'cormorant-500i': 'node_modules/@fontsource/cormorant/files/cormorant-latin-500-italic.woff2', 'cormorant-600': 'node_modules/@fontsource/cormorant/files/cormorant-latin-600-normal.woff2', 'montserrat-400': 'node_modules/@fontsource/montserrat/files/montserrat-latin-400-normal.woff2', 'montserrat-500': 'node_modules/@fontsource/montserrat/files/montserrat-latin-500-normal.woff2' };
const types = { '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]); let p = null;
  if (u.startsWith('/img/')) p = path.join(srcDir, u.slice(5));
  else if (u.startsWith('/fonts/')) p = path.join(HERE, fonts[u.slice(7).replace('.woff2', '')] || '');
  if (!p || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, r));
const base = `http://127.0.0.1:${server.address().port}`;
const css = `
@font-face{font-family:Cormorant;font-weight:500;src:url(/fonts/cormorant-500.woff2) format("woff2")}
@font-face{font-family:Cormorant;font-weight:500;font-style:italic;src:url(/fonts/cormorant-500i.woff2) format("woff2")}
@font-face{font-family:Cormorant;font-weight:600;src:url(/fonts/cormorant-600.woff2) format("woff2")}
@font-face{font-family:Montserrat;font-weight:400;src:url(/fonts/montserrat-400.woff2) format("woff2")}
@font-face{font-family:Montserrat;font-weight:500;src:url(/fonts/montserrat-500.woff2) format("woff2")}
*{margin:0;box-sizing:border-box} html,body{width:100%;height:100%} body{color:#2c3227;font-family:Montserrat,sans-serif;overflow:hidden;position:relative;background:#faf7f2}
.field{position:absolute;inset:0;isolation:isolate}
.big{font-family:Cormorant,serif;font-weight:600;text-transform:uppercase;letter-spacing:.02em;line-height:.92}
.serif{font-family:Cormorant,serif;font-weight:500;text-transform:uppercase;letter-spacing:.06em;line-height:1.02}
.caps{font-family:Montserrat,sans-serif;font-weight:500;text-transform:uppercase;letter-spacing:.24em}
.body{font-family:Montserrat,sans-serif;font-weight:400;line-height:1.45}
.mult{mix-blend-mode:multiply}
.wordmark{font-family:Cormorant,serif;font-weight:500;letter-spacing:.14em;text-transform:uppercase}
.wordmark small{font-size:.55em;text-transform:lowercase;letter-spacing:.05em;font-style:italic;margin:0 .15em}
`;
const doc = (w, h, body) => `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body style="width:${w}px;height:${h}px">${body}</body></html>`;
const tiles = [];
const heroSplit = (eyebrow, title, line, titleSize) => `
  <div style="position:absolute;left:0;top:0;width:1400px;height:600px;background:#2c3227;color:#faf7f2;padding:0 90px 0 470px;display:flex;flex-direction:column;justify-content:center;gap:22px">
    <div class="wordmark" style="font-size:40px;color:#c4a265">Mount <small>of</small> Olives</div>
    <div class="big" style="font-size:${titleSize}px">${esc(title)}</div>
    <div class="body" style="font-size:26px;color:#e9e2d6;max-width:800px">${esc(line)}</div>
  </div>
  <div class="field" style="left:1400px;width:1600px;background:#efe3cc"><img class="mult" src="/img/hero-white.jpg" style="position:absolute;left:60px;top:28px;height:544px;width:auto"></div>`;
tiles.push({ name: 'hero-home-3000x600.jpg', w: 3000, h: 600, html: heroSplit(copy.hero_home.eyebrow, copy.hero_home.eyebrow, copy.hero_home.line, 108) });
tiles.push({ name: 'hero-shop-3000x600.jpg', w: 3000, h: 600, html: heroSplit(copy.hero_shop.eyebrow, copy.hero_shop.title, copy.hero_shop.line, 108) });
for (const o of copy.oils) {
  const [field, deep] = COL[o.key];
  tiles.push({ name: `tile-${o.key}-1500x1500.jpg`, w: 1500, h: 1500, html: `
  <div class="field" style="background:${field}">
    <img class="mult" src="/img/${o.image.replace('.jpg', '-white.jpg')}" style="position:absolute;left:560px;top:300px;width:1280px;height:1280px">
    <div style="position:absolute;left:100px;top:100px;width:1300px;color:${deep}">
      <div class="big" style="font-size:${o.word.length > 9 ? 150 : 190}px">${esc(o.word)}</div>
      <div class="caps" style="font-size:34px;margin-top:34px">${esc(o.name)}</div>
      <div class="body" style="font-size:36px;margin-top:40px;max-width:640px">${esc(o.line)}</div>
    </div>
    <div class="caps" style="position:absolute;left:100px;top:1210px;font-size:26px;color:${deep}">${esc(o.verse)}</div>
  </div>` });
}
tiles.push({ name: 'tile-scripture-1500x750.jpg', w: 1500, h: 750, html: `
  <div class="field" style="background:#c4a265;color:#2c3227">
    <div class="big" style="position:absolute;left:90px;top:-40px;font-size:520px;opacity:.35">“</div>
    <div style="position:absolute;left:120px;top:0;height:640px;width:1280px;display:flex;flex-direction:column;justify-content:center;gap:34px">
      <div style="font-family:Cormorant,serif;font-weight:500;font-style:italic;font-size:76px;line-height:1.15">${esc(copy.scripture.quote)}</div>
      <div class="caps" style="font-size:26px">${esc(copy.scripture.ref)}</div>
    </div>
  </div>` });
tiles.push({ name: 'tile-story-1500x750.jpg', w: 1500, h: 750, html: `
  <div class="field" style="background:#2c3227">
    <img src="/img/praying-with-frankincense-myrrh.jpg" style="position:absolute;left:600px;top:0;width:900px;height:750px;object-fit:cover;object-position:60% 35%">
    <div style="position:absolute;left:0;top:0;width:600px;height:640px;padding:0 60px 0 90px;color:#faf7f2;display:flex;flex-direction:column;justify-content:center;gap:24px">
      <div class="caps" style="font-size:22px;color:#c4a265">${esc(copy.story.eyebrow)}</div>
      <div class="big" style="font-size:72px">${esc(copy.story.title)}</div>
      <div class="body" style="font-size:24px;color:#e9e2d6">${esc(copy.story.line)}</div>
    </div>
  </div>` });
const plants = ['Frankincense', 'Myrrh', 'Spikenard', 'Hyssop', 'Pomegranate', 'Rose of Sharon', 'Lily of the valley', 'Olive'];
tiles.push({ name: 'tile-inside-1500x750.jpg', w: 1500, h: 750, html: `
  <div class="field" style="background:#2c3227;color:#faf7f2">
    <div style="position:absolute;left:90px;top:90px;width:620px">
      <div class="caps" style="font-size:22px;color:#c4a265">${esc(copy.inside.eyebrow)}</div>
      <div class="big" style="font-size:84px;margin-top:26px">Seven biblical botanicals. One olive base.</div>
      <div class="body" style="font-size:22px;color:#e9e2d6;margin-top:30px;max-width:560px">Naturally derived. Cruelty-free. No parabens, phthalates, sulfates, or synthetic fragrance.</div>
    </div>
    <div style="position:absolute;left:820px;top:96px;width:600px;display:grid;grid-template-columns:1fr 1fr;gap:26px 40px">
      ${plants.map((p, i) => `<div style="border-top:1px solid rgba(196,162,101,.6);padding-top:16px"><div class="caps" style="font-size:16px;color:#c4a265">0${i + 1}</div><div class="serif" style="font-size:40px;margin-top:8px">${esc(p)}</div></div>`).join('')}
    </div>
  </div>` });
tiles.push({ name: 'tile-sizes-1500x750.jpg', w: 1500, h: 750, html: `
  <div class="field" style="background:#efe3cc;color:#2c3227">
    <div style="position:absolute;left:90px;top:90px;width:520px">
      <div class="caps" style="font-size:22px;color:#8a6a2a">Choose your size</div>
      <div class="big" style="font-size:104px;margin-top:22px">Three sizes</div>
      <div class="body" style="font-size:24px;margin-top:26px;max-width:460px">Every oil comes in 1 oz, 2 oz, and 4 oz. Shown: Frankincense &amp; Myrrh.</div>
    </div>
    <img class="mult" src="/img/p-frankincense-myrrh-3-white.jpg" style="position:absolute;left:640px;top:250px;width:380px;height:380px">
    <img class="mult" src="/img/p-frankincense-myrrh-2-white.jpg" style="position:absolute;left:880px;top:170px;width:460px;height:460px">
    <img class="mult" src="/img/p-frankincense-myrrh-white.jpg" style="position:absolute;left:1110px;top:60px;width:570px;height:570px">
    <div class="caps" style="position:absolute;left:760px;top:668px;font-size:20px">1 oz</div>
    <div class="caps" style="position:absolute;left:1060px;top:668px;font-size:20px">2 oz</div>
    <div class="caps" style="position:absolute;left:1340px;top:668px;font-size:20px">4 oz</div>
  </div>` });
tiles.push({ name: 'logo-400x400.png', w: 400, h: 400, png: true, html: `<div style="position:absolute;inset:0;background:#fff;display:flex;align-items:center;justify-content:center"><img src="/img/mo-favicon-sprig.png" style="width:360px;height:360px"></div>` });
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
for (const t of tiles) {
  const ctx = await browser.newContext({ viewport: { width: t.w, height: t.h }, deviceScaleFactor: 1 });
  const page = await ctx.newPage(); await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => r.abort());
  await page.setContent(doc(t.w, t.h, t.html).replace(/src="\//g, `src="${base}/`).replace(/url\(\//g, `url(${base}/`), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(300);
  const overflow = await page.evaluate(() => [...document.querySelectorAll('.big,.serif,.body,.caps')].some((e) => e.scrollWidth > e.clientWidth + 1));
  await page.screenshot({ path: path.join(outDir, t.name), type: t.png ? 'png' : 'jpeg', quality: t.png ? undefined : 92 });
  console.log(t.name, overflow ? 'TEXT OVERFLOW' : 'ok'); await ctx.close();
}
await browser.close(); server.close();
