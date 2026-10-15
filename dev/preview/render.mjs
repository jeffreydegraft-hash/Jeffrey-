/* Olivet preview renderer.
   Renders the theme's JSON templates with liquidjs and mock data into dev/preview/dist/*.html.
   This is a development aid only: Shopify's Liquid has objects and filters this shim approximates.
   Usage: node render.mjs [--out dist] [template ...]   e.g. node render.mjs index product cart */
import fs from 'node:fs';
import path from 'node:path';
import { Liquid, Tag, Value } from 'liquidjs';
import * as M from './mock.mjs';

const ROOT = M.ROOT;
const argv = process.argv.slice(2);
const outIdx = argv.indexOf('--out');
const OUT = path.resolve(outIdx >= 0 ? argv[outIdx + 1] : path.join(ROOT, 'dev/preview/dist'));
const only = argv.filter((a, i) => !a.startsWith('--') && argv[i - 1] !== '--out');

fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(path.join(OUT, 'assets'), { recursive: true });

/* ---------- settings ---------- */
const schema = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/settings_schema.json'), 'utf8'));
const settingsData = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/settings_data.json'), 'utf8'));
const rawSettings = typeof settingsData.current === 'string' ? settingsData.presets[settingsData.current] : settingsData.current;
const settingTypes = {};
for (const group of schema) for (const s of group.settings || []) settingTypes[s.id] = s;

function coerceSetting(def, value) {
  if (!def) return value;
  switch (def.type) {
    case 'font_picker':
      return M.fontFromHandle(value || def.default);
    case 'color':
      return value ? new M.Color(value) : null;
    case 'color_background':
      return value || '';
    case 'image_picker':
      return value && M.images[value] ? M.images[value] : null;
    case 'link_list':
      return M.linklists[value] || null;
    case 'collection':
      return M.collections[value] || null;
    case 'collection_list':
      return (value || []).map((h) => M.collections[h]).filter(Boolean);
    case 'product':
      return M.products.find((p) => p.handle === value) || null;
    case 'product_list':
      return (value || []).map((h) => M.products.find((p) => p.handle === h)).filter(Boolean);
    case 'blog':
      return M.blogs[value] || null;
    case 'article':
      return M.articles.find((a) => a.handle === value) || null;
    case 'page':
      return M.pages[value] || null;
    case 'url':
      return typeof value === 'string' ? value.replace('shopify://collections/', '/collections/').replace('shopify://products/', '/products/').replace('shopify://pages/', '/pages/').replace('shopify://blogs/', '/blogs/') : value;
    case 'range':
    case 'number':
      return value === undefined || value === null || value === '' ? def.default : Number(value);
    case 'checkbox':
      return value === undefined ? !!def.default : !!value;
    default:
      return value === undefined ? def.default : value;
  }
}

const settings = {};
for (const [id, def] of Object.entries(settingTypes)) settings[id] = coerceSetting(def, rawSettings[id]);
settings.color_schemes = Object.entries(rawSettings.color_schemes || {}).map(([id, s]) => {
  const out = { id, settings: {} };
  for (const [k, v] of Object.entries(s.settings)) out.settings[k] = k === 'background_gradient' ? v || '' : new M.Color(v);
  return out;
});

/* ---------- locales ---------- */
const locale = JSON.parse(fs.readFileSync(path.join(ROOT, 'locales/en.default.json'), 'utf8'));
function translate(key, params = {}) {
  let node = locale;
  for (const part of String(key).split('.')) {
    node = node && typeof node === 'object' ? node[part] : undefined;
    if (node === undefined) return `translation missing: en.${key}`;
  }
  if (typeof node === 'object' && node !== null) {
    const count = Number(params.count);
    node = count === 1 ? node.one : node.other;
    if (node === undefined) return `translation missing: en.${key}`;
  }
  return String(node).replace(/\{\{\s*(\w+)\s*\}\}/g, (_, k) => (params[k] !== undefined ? params[k] : `{{ ${k} }}`));
}

/* ---------- money ---------- */
function formatMoney(cents, format = M.shop.money_format) {
  const n = Number(cents || 0) / 100;
  const amount = n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return format.replace(/\{\{\s*amount(?:_no_decimals)?\s*\}\}/, format.includes('no_decimals') ? Math.round(n).toLocaleString('en-US') : amount);
}

/* ---------- liquid engine ---------- */
const engine = new Liquid({
  root: [path.join(ROOT, 'snippets'), ROOT],
  partials: path.join(ROOT, 'snippets'),
  extname: '.liquid',
  cache: true,
  strictFilters: false,
  strictVariables: false,
  lenientIf: true,
  jsTruthy: false,
  trimTagLeft: false,
  trimTagRight: false,
  ownPropertyOnly: false,
  relativeReference: false,
  fs: {
    exists: async (p) => fs.existsSync(p),
    existsSync: (p) => fs.existsSync(p),
    readFile: async (p) => preprocess(await fs.promises.readFile(p, 'utf8')),
    readFileSync: (p) => preprocess(fs.readFileSync(p, 'utf8')),
    resolve: (root, file, ext) => path.resolve(root, file.endsWith(ext) ? file : file + ext),
    fallback: (file) => {
      console.error(`  ! missing snippet ${path.basename(file)} (rendered as a comment)`);
      return path.join(ROOT, 'dev/preview/_missing.liquid');
    },
    dirname: (p) => path.dirname(p),
    sep: path.sep,
    contains: () => true,
  },
});
// Shopify Liquid treats "and"/"or" as left-to-right; liquidjs default is fine.

/* ---- filters ---- */
const attrs = (obj) =>
  Object.entries(obj)
    .filter(([, v]) => v !== undefined && v !== null && v !== false && v !== '')
    .map(([k, v]) => (v === true ? k : `${k}="${String(v).replace(/"/g, '&quot;')}"`))
    .join(' ');

engine.registerFilter('t', function (key, ...rest) {
  const params = {};
  for (const r of rest) if (Array.isArray(r)) params[r[0]] = r[1];
  return translate(key, params);
});
// Cycle-safe json (mock images reference themselves via preview_image)
engine.registerFilter('json', (v) => {
  const seen = new WeakSet();
  return JSON.stringify(v, (k, val) => {
    if (k === '_svg' || k === '_copy') return undefined;
    if (val && typeof val === 'object') {
      if (seen.has(val)) return undefined;
      seen.add(val);
    }
    return val;
  });
});
engine.registerFilter('money', (v) => formatMoney(v));
engine.registerFilter('money_with_currency', (v) => formatMoney(v, M.shop.money_with_currency_format));
engine.registerFilter('money_without_currency', (v) => (Number(v || 0) / 100).toFixed(2));
engine.registerFilter('money_without_trailing_zeros', (v) => formatMoney(v).replace(/\.00$/, ''));
engine.registerFilter('money_amount', (v) => (Number(v || 0) / 100).toFixed(2));
engine.registerFilter('handle', M.handleize);
engine.registerFilter('handleize', M.handleize);
engine.registerFilter('asset_url', (f) => `assets/${f}`);
engine.registerFilter('asset_img_url', (f) => `assets/${f}`);
engine.registerFilter('file_url', (f) => `files/${f}`);
engine.registerFilter('shopify_asset_url', (f) => `https://cdn.shopify.com/shopifycloud/shopify/assets/${f}`);
engine.registerFilter('stylesheet_tag', (u, ...rest) => `<link rel="stylesheet" href="${u}" media="all">`);
engine.registerFilter('script_tag', (u) => `<script src="${u}"></script>`);
engine.registerFilter('preload_tag', (u, ...rest) => { const o = {}; for (const r of rest) if (Array.isArray(r)) o[r[0]] = r[1]; return `<link rel="preload" href="${u}" ${attrs(o)}>`; });
engine.registerFilter('image_url', function (img, ...rest) {
  if (!img) return '';
  const src = typeof img === 'string' ? img : img.src || (img.preview_image && img.preview_image.src) || '';
  return src;
});
engine.registerFilter('img_url', (img) => (img && img.src) || '');
engine.registerFilter('image_tag', function (src, ...rest) {
  const o = {};
  for (const r of rest) if (Array.isArray(r)) o[r[0]] = r[1];
  const widths = o.widths ? String(o.widths).split(',').map((w) => w.trim()) : [];
  const srcset = widths.length ? widths.map((w) => `${src} ${w}w`).join(', ') : undefined;
  const key = path.basename(String(src), '.svg');
  const img = M.images[key];
  return `<img ${attrs({ src, srcset, sizes: o.sizes, class: o.class, loading: o.loading, alt: o.alt !== undefined ? o.alt : img ? img.alt : '', width: img ? img.width : undefined, height: img ? img.height : undefined, fetchpriority: o.fetchpriority, decoding: 'async' })}>`;
});
engine.registerFilter('placeholder_svg_tag', (name, cls) => `<svg class="${cls || 'placeholder-svg'}" viewBox="0 0 525 525" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><rect width="525" height="525" fill="currentColor" opacity=".08"/><path d="M262 90c-60 0-110 70-110 150 0 95 50 185 110 185s110-90 110-185c0-80-50-150-110-150zm0 40c38 0 70 55 70 110 0 75-32 145-70 145s-70-70-70-145c0-55 32-110 70-110z" fill="currentColor" opacity=".35"/><text x="262" y="470" text-anchor="middle" font-family="sans-serif" font-size="22" fill="currentColor" opacity=".5">${name}</text></svg>`);
engine.registerFilter('payment_type_svg_tag', (type, ...rest) => {
  const o = {};
  for (const r of rest) if (Array.isArray(r)) o[r[0]] = r[1];
  return `<svg class="${o.class || 'payment-icon'}" viewBox="0 0 38 24" width="38" height="24" role="img" aria-label="${type}" xmlns="http://www.w3.org/2000/svg"><rect width="38" height="24" rx="3" fill="currentColor" opacity=".12"/><text x="19" y="15" text-anchor="middle" font-family="sans-serif" font-size="8" fill="currentColor">${String(type).replace('_', ' ').slice(0, 10)}</text></svg>`;
});
engine.registerFilter('payment_button', () => `<div class="shopify-payment-button"><button type="button" class="shopify-payment-button__button shopify-payment-button__button--unbranded">Buy it now</button></div>`);
engine.registerFilter('inline_asset_content', (f) => `<!-- inline asset ${f} -->`);
engine.registerFilter('font_face', (font, ...rest) => {
  if (!font || !font.family) return '';
  const fam = font._handle;
  const style = font.style === 'italic' ? 'italic' : 'normal';
  const file = `fonts/${fam.replace(/_/g, '-')}-latin-${font.weight}-${style}.woff2`;
  return `@font-face { font-family: "${font.family}"; font-weight: ${font.weight}; font-style: ${style}; font-display: swap; src: url("${file}") format("woff2"); }`;
});
engine.registerFilter('font_modify', (font, prop, value) => {
  if (!font) return font;
  const f = { ...font, toString: font.toString };
  if (prop === 'weight') f.weight = value === 'bold' ? Math.min(font.weight + 300, 800) : value === 'lighter' ? Math.max(font.weight - 200, 100) : Number(value) || font.weight;
  if (prop === 'style') f.style = value;
  return f;
});
engine.registerFilter('font_url', (font) => (font ? `fonts/${font._handle.replace(/_/g, '-')}-latin-${font.weight}-${font.style}.woff2` : ''));
engine.registerFilter('color_brightness', (c) => (c && c.red !== undefined ? (c.red * 299 + c.green * 587 + c.blue * 114) / 1000 : 128));
const mod = (c, f) => {
  if (!c || c.red === undefined) return c;
  const hex = '#' + [c.red, c.green, c.blue].map((v) => Math.max(0, Math.min(255, Math.round(f(v)))).toString(16).padStart(2, '0')).join('');
  return new M.Color(hex);
};
engine.registerFilter('color_lighten', (c, amt) => mod(c, (v) => v + (255 - v) * (Number(amt) / 100)));
engine.registerFilter('color_darken', (c, amt) => mod(c, (v) => v * (1 - Number(amt) / 100)));
engine.registerFilter('color_modify', (c, prop, val) => (c && prop === 'alpha' ? `rgba(${c.rgb}, ${val})` : c));
engine.registerFilter('color_to_rgb', (c) => (c ? `rgb(${c.rgb})` : ''));
engine.registerFilter('color_mix', (c) => c);
engine.registerFilter('format_address', (a) => (a ? `<p>${[a.name || `${a.first_name || ''} ${a.last_name || ''}`.trim(), a.company, a.address1, a.address2, [a.city, a.province_code || a.province, a.zip].filter(Boolean).join(' '), a.country].filter(Boolean).join('<br>')}</p>` : ''));
engine.registerFilter('within', (url) => url);
engine.registerFilter('highlight', (text, q) => (q ? String(text).replace(new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'ig'), (m) => `<strong class="highlight">${m}</strong>`) : text));
engine.registerFilter('link_to', (text, url, title) => `<a href="${url}"${title ? ` title="${title}"` : ''}>${text}</a>`);
engine.registerFilter('weight_with_unit', (w, unit) => `${w} ${unit || 'g'}`);
engine.registerFilter('time_tag', (d, fmt) => `<time datetime="${d}">${d}</time>`);
engine.registerFilter('media_tag', (m) => `<img src="${m && m.src}" alt="">`);
engine.registerFilter('video_tag', (m) => `<video controls playsinline muted loop preload="metadata" class="media__img"></video>`);
engine.registerFilter('external_video_tag', () => `<iframe title="video" src="about:blank" class="media__img"></iframe>`);
engine.registerFilter('external_video_url', () => 'about:blank');
engine.registerFilter('model_viewer_tag', () => `<div class="media__img">3D model</div>`);
engine.registerFilter('structured_data', (o) => JSON.stringify({ '@type': 'Thing' }));
engine.registerFilter('standard_event_data', () => '');
engine.registerFilter('customer_login_link', (t) => `<a href="/account/login">${t}</a>`);
engine.registerFilter('customer_logout_link', (t) => `<a href="/account/logout">${t}</a>`);
engine.registerFilter('customer_register_link', (t) => `<a href="/account/register">${t}</a>`);
engine.registerFilter('default_errors', (e) => '');
engine.registerFilter('base64_encode', (s) => Buffer.from(String(s)).toString('base64'));
engine.registerFilter('md5', (s) => 'd41d8cd98f00b204e9800998ecf8427e');
engine.registerFilter('pluralize', (n, s, p) => (Number(n) === 1 ? s : p));
engine.registerFilter('sort_natural', (a, key) => (Array.isArray(a) ? [...a].sort((x, y) => String(key ? x[key] : x).localeCompare(String(key ? y[key] : y), undefined, { sensitivity: 'base' })) : a));
engine.registerFilter('item_count_for_variant', () => 0);
engine.registerFilter('line_items_for', () => []);
engine.registerFilter('unit_price_with_measurement', (p) => formatMoney(p));

/* ---- tags ---- */
class SkipTag extends Tag {
  constructor(token, remainTokens, liquid) {
    super(token, remainTokens, liquid);
    const stream = liquid.parser.parseStream(remainTokens);
    stream.on(`tag:end${token.name}`, () => stream.stop()).on('template', () => {}).on('end', () => { throw new Error(`tag ${token.name} not closed`); });
    stream.start();
  }
  *render() { return ''; }
}
class StyleTag extends Tag {
  constructor(token, remainTokens, liquid) {
    super(token, remainTokens, liquid);
    this.templates = [];
    const stream = liquid.parser.parseStream(remainTokens);
    stream.on('tag:endstyle', () => stream.stop()).on('template', (tpl) => this.templates.push(tpl)).on('end', () => { throw new Error('style not closed'); });
    stream.start();
  }
  *render(ctx, emitter) {
    emitter.write('<style>');
    yield this.liquid.renderer.renderTemplates(this.templates, ctx, emitter);
    emitter.write('</style>');
  }
}
class FormTag extends Tag {
  constructor(token, remainTokens, liquid) {
    super(token, remainTokens, liquid);
    this.argsRaw = token.args;
    this.templates = [];
    const stream = liquid.parser.parseStream(remainTokens);
    stream.on('tag:endform', () => stream.stop()).on('template', (tpl) => this.templates.push(tpl)).on('end', () => { throw new Error('form not closed'); });
    stream.start();
  }
  *render(ctx, emitter) {
    const raw = this.argsRaw;
    const typeMatch = raw.match(/^\s*'([^']+)'|^\s*"([^"]+)"/);
    const type = typeMatch ? typeMatch[1] || typeMatch[2] : 'form';
    const kv = {};
    for (const m of raw.matchAll(/([\w-]+)\s*:\s*('([^']*)'|"([^"]*)"|([^,]+))/g)) {
      const key = m[1];
      const val = m[3] !== undefined ? m[3] : m[4] !== undefined ? m[4] : yield new Value(m[5].trim(), this.liquid).value(ctx);
      kv[key] = val;
    }
    const actions = { product: '/cart/add', customer: '/contact#contact_form', contact: '/contact#ContactForm', storefront_password: '/password', customer_login: '/account/login', create_customer: '/account', recover_customer_password: '/account/recover', guest_login: '/account/login', customer_address: '/account/addresses', activate_customer_password: '/account/activate', reset_customer_password: '/account/reset', localization: '/localization', article: '/blogs/comment', cart: '/cart', new_comment: '/blogs/comment' };
    const method = type === 'localization' ? 'post' : 'post';
    emitter.write(`<form method="${method}" action="${actions[type] || '/'}" accept-charset="UTF-8" ${attrs(kv)}>`);
    emitter.write(`<input type="hidden" name="form_type" value="${type}"><input type="hidden" name="utf8" value="✓">`);
    const form = { errors: null, posted_successfully_q: false, email: '', body: '', author: '', password_needed: type === 'customer_login', name: '', phone: '', address1: '', first_name: '', last_name: '', id: 'new' };
    ctx.push({ form });
    yield this.liquid.renderer.renderTemplates(this.templates, ctx, emitter);
    ctx.pop();
    emitter.write('</form>');
  }
}
class PaginateTag extends Tag {
  constructor(token, remainTokens, liquid) {
    super(token, remainTokens, liquid);
    const m = token.args.match(/^\s*(.+?)\s+by\s+(.+?)\s*$/);
    this.collection = new Value(m ? m[1] : token.args, liquid);
    this.size = new Value(m ? m[2] : '20', liquid);
    this.templates = [];
    const stream = liquid.parser.parseStream(remainTokens);
    stream.on('tag:endpaginate', () => stream.stop()).on('template', (tpl) => this.templates.push(tpl)).on('end', () => { throw new Error('paginate not closed'); });
    stream.start();
  }
  *render(ctx, emitter) {
    const items = (yield this.collection.value(ctx)) || [];
    const size = Number(yield this.size.value(ctx)) || 20;
    const total = Array.isArray(items) ? items.length : 0;
    const pages = Math.max(1, Math.ceil(total / size));
    const parts = [];
    for (let p = 1; p <= pages; p++) parts.push({ title: String(p), url: `?page=${p}`, is_link: p !== 1 });
    const paginate = { current_page: 1, current_offset: 0, items: total, page_size: size, pages, parts, previous: null, next: pages > 1 ? { title: 'Next', url: '?page=2', is_link: true } : null, page_param: 'page' };
    ctx.push({ paginate });
    yield this.liquid.renderer.renderTemplates(this.templates, ctx, emitter);
    ctx.pop();
  }
}
class SectionTag extends Tag {
  constructor(token, remainTokens, liquid) {
    super(token, remainTokens, liquid);
    this.name = token.args.trim().replace(/^['"]|['"]$/g, '');
  }
  *render(ctx, emitter) {
    const html = yield renderSection(this.name, this.name, {}, ctx.getAll());
    emitter.write(html);
  }
}
class SectionsTag extends Tag {
  constructor(token, remainTokens, liquid) {
    super(token, remainTokens, liquid);
    this.name = token.args.trim().replace(/^['"]|['"]$/g, '');
  }
  *render(ctx, emitter) {
    const html = yield renderGroup(this.name, ctx.getAll());
    emitter.write(html);
  }
}
class LayoutTag extends Tag {
  constructor(token, remainTokens, liquid) {
    super(token, remainTokens, liquid);
    this.value = token.args.trim();
  }
  *render(ctx) {
    ctx.environments.__layout = this.value.replace(/['"]/g, '');
    return '';
  }
}
engine.registerTag('schema', SkipTag);
engine.registerTag('javascript', SkipTag);
engine.registerTag('stylesheet', SkipTag);
engine.registerTag('style', StyleTag);
engine.registerTag('form', FormTag);
engine.registerTag('paginate', PaginateTag);
engine.registerTag('section', SectionTag);
engine.registerTag('sections', SectionsTag);
engine.registerTag('layout', LayoutTag);

/* ---------- source preprocessing (Shopify-isms liquidjs can't parse) ---------- */
function preprocess(src) {
  return src
    .replace(/\.(\w+)\?(?=[\s%}|)])/g, '.$1_q') // product.gift_card? → gift_card_q
    .replace(/\b(cart|customer\.orders|collection\.products|search\.results|blog\.articles|article\.comments)\s*==\s*empty/g, (m, v) => (v === 'cart' ? 'cart.item_count == 0' : `${v}.size == 0`))
    .replace(/\b(cart|customer\.orders|collection\.products|search\.results|blog\.articles|article\.comments)\s*!=\s*empty/g, (m, v) => (v === 'cart' ? 'cart.item_count > 0' : `${v}.size > 0`))
    .replace(/\{%-?\s*#[^%]*-?%\}/g, '') // inline comments
    .replace(/\{%(-?)\s*liquid\s*\n([\s\S]*?)\n\s*(-?)%\}/g, (m, l, body, r) => `{%${l} liquid\n${body.replace(/^(\s*)#.*$/gm, '$1')}\n${r}%}`); // strip # comment lines inside liquid blocks
}

const parsedCache = new Map();
function parseFile(file) {
  if (parsedCache.has(file)) return parsedCache.get(file);
  const src = fs.readFileSync(file, 'utf8');
  const schemaMatch = src.match(/\{%-?\s*schema\s*-?%\}([\s\S]*?)\{%-?\s*endschema\s*-?%\}/);
  let sectionSchema = null;
  if (schemaMatch) {
    try {
      sectionSchema = JSON.parse(schemaMatch[1]);
    } catch (e) {
      console.error(`  ! schema JSON error in ${path.relative(ROOT, file)}: ${e.message}`);
    }
  }
  const body = preprocess(src.replace(/\{%-?\s*schema\s*-?%\}[\s\S]*?\{%-?\s*endschema\s*-?%\}/, ''));
  let tpl;
  try {
    tpl = engine.parse(body, file);
  } catch (e) {
    throw new Error(`Liquid parse error in ${path.relative(ROOT, file)}: ${e.message}`);
  }
  const out = { tpl, schema: sectionSchema };
  parsedCache.set(file, out);
  return out;
}


/* ---------- sections ---------- */
let blockCounter = 0;
function buildSectionObject(id, type, tplSection, sectionSchema) {
  const settings = {};
  for (const def of (sectionSchema && sectionSchema.settings) || []) settings[def.id] = coerceSetting(def, (tplSection.settings || {})[def.id]);
  for (const [k, v] of Object.entries(tplSection.settings || {})) if (!(k in settings)) settings[k] = v;
  const blockDefs = {};
  for (const b of (sectionSchema && sectionSchema.blocks) || []) blockDefs[b.type] = b;
  let blocks = [];
  const order = tplSection.block_order || Object.keys(tplSection.blocks || {});
  for (const bid of order) {
    const b = (tplSection.blocks || {})[bid];
    if (!b) continue;
    const def = blockDefs[b.type] || { settings: [] };
    const bs = {};
    for (const sdef of def.settings || []) bs[sdef.id] = coerceSetting(sdef, (b.settings || {})[sdef.id]);
    for (const [k, v] of Object.entries(b.settings || {})) if (!(k in bs)) bs[k] = v;
    blocks.push({ id: `${id}-${bid}`, type: b.type, settings: bs, shopify_attributes: `data-shopify-editor-block="${id}-${bid}"` });
  }
  // If no blocks in template, use the schema preset's blocks (editor default)
  if (!blocks.length && sectionSchema && sectionSchema.presets && sectionSchema.presets[0] && sectionSchema.presets[0].blocks) {
    for (const pb of sectionSchema.presets[0].blocks) {
      const def = blockDefs[pb.type] || { settings: [] };
      const bs = {};
      for (const sdef of def.settings || []) bs[sdef.id] = coerceSetting(sdef, (pb.settings || {})[sdef.id]);
      blocks.push({ id: `${id}-${++blockCounter}`, type: pb.type, settings: bs, shopify_attributes: '' });
    }
  }
  if (!tplSection.settings && sectionSchema && sectionSchema.presets && sectionSchema.presets[0] && sectionSchema.presets[0].settings) {
    for (const [k, v] of Object.entries(sectionSchema.presets[0].settings)) if (settings[k] === undefined || settings[k] === null) settings[k] = coerceSetting((sectionSchema.settings || []).find((s) => s.id === k), v);
  }
  return { id, settings, blocks, index: 1, index0: 0, location: 'template', type };
}

async function renderSection(id, type, tplSection, globals) {
  const file = path.join(ROOT, 'sections', `${type}.liquid`);
  if (!fs.existsSync(file)) return `<!-- missing section ${type} -->`;
  const { tpl, schema: sectionSchema } = parseFile(file);
  const section = buildSectionObject(id, type, tplSection, sectionSchema);
  // Shopify exposes `section` to snippets rendered from a section; liquidjs isolates render scope, so pass it as a global.
  const html = await engine.render(tpl, { section }, { globals: { ...globals, section } });
  return `<div id="shopify-section-${id}" class="shopify-section${sectionSchema && sectionSchema.class ? ' ' + sectionSchema.class : ''}">${html}</div>`;
}

async function renderGroup(name, globals) {
  const file = path.join(ROOT, 'sections', `${name}.json`);
  if (!fs.existsSync(file)) return `<!-- missing group ${name} -->`;
  const group = JSON.parse(fs.readFileSync(file, 'utf8'));
  let out = '';
  for (const sid of group.order) out += await renderSection(sid, group.sections[sid].type, group.sections[sid], globals);
  return out;
}

/* ---------- page contexts ---------- */
function globalsFor(pageType, extra = {}) {
  const cart = extra.cart || M.makeCart(false);
  const template = { name: pageType.split('.')[0].replace('customers/', ''), suffix: pageType.includes('.') ? pageType.split('.')[1] : null, directory: pageType.startsWith('customers/') ? 'customers' : null, toString() { return this.name; } };
  return {
    shop: M.shop,
    settings,
    routes: M.routes,
    cart,
    localization: M.localization,
    linklists: M.linklists,
    collections: M.collections,
    pages: M.pages,
    blogs: M.blogs,
    all_products: Object.fromEntries(M.products.map((p) => [p.handle, p])),
    request: { page_type: extra.page_type || pageType.replace('customers/', '').split('.')[0], locale: { iso_code: 'en', name: 'English' }, origin: 'https://mountofolives.co', host: 'mountofolives.co', path: extra.path || '/', design_mode: false, visual_preview_mode: false },
    template,
    canonical_url: `https://mountofolives.co${extra.path || '/'}`,
    page_title: extra.page_title || M.shop.name,
    page_description: extra.page_description || M.shop.description,
    page_image: null,
    content_for_header: '<!-- content_for_header -->',
    content_for_additional_checkout_buttons: '',
    current_tags: null,
    current_page: 1,
    customer: extra.customer === undefined ? null : extra.customer,
    predictive_search: { performed: false, terms: '', resources: { products: [], collections: [], pages: [], articles: [], queries: [] } },
    recommendations: { performed: false, products: [], products_count: 0, intent: 'related' },
    powered_by_link: '<a href="https://www.shopify.com">Powered by Shopify</a>',
    ...extra,
  };
}

const PAGES = {
  index: () => globalsFor('index', { path: '/', page_title: 'Mount of Olives' }),
  product: () => {
    const product = M.products[0];
    return globalsFor('product', { product, collection: M.collections.all, path: product.url, page_title: product.title, page_description: product._copy.oneLiner });
  },
  'product-squalane': () => {
    const product = M.products[10];
    return globalsFor('product', { product, path: product.url, page_title: product.title });
  },
  collection: () => globalsFor('collection', { collection: M.collections.all, path: '/collections/all', page_title: 'All anointing oils' }),
  'collection-empty': () => globalsFor('collection', { collection: { ...M.collections.all, products: [], products_count: 0 }, path: '/collections/all', page_title: 'All anointing oils' }),
  'list-collections': () => globalsFor('list-collections', { collections: M.collections, path: '/collections', page_title: 'Collections' }),
  cart: () => globalsFor('cart', { path: '/cart', page_title: 'Your cart' }),
  'cart-empty': () => globalsFor('cart', { cart: M.makeCart(true), path: '/cart', page_title: 'Your cart' }),
  search: () => globalsFor('search', { search: { performed: true, terms: 'frankincense', results: M.products.slice(0, 2), results_count: 2, types: ['product'], sort_by: 'relevance', filters: [] }, path: '/search?q=frankincense', page_title: 'Search' }),
  'search-empty': () => globalsFor('search', { search: { performed: true, terms: 'xyzzy', results: [], results_count: 0, types: ['product'], filters: [] }, path: '/search?q=xyzzy', page_title: 'Search' }),
  page: () => globalsFor('page', { page: M.pages['about-us'], path: '/pages/about-us', page_title: 'About' }),
  'page.about': () => globalsFor('page.about', { page: M.pages['about-us'], path: '/pages/about-us', page_title: 'About' }),
  'page.science': () => globalsFor('page.science', { page: M.pages['our-science'], path: '/pages/our-science', page_title: 'Our Science' }),
  'page.contact': () => globalsFor('page.contact', { page: M.pages.contact, path: '/pages/contact', page_title: 'Contact' }),
  blog: () => globalsFor('blog', { blog: M.blogs['the-anointing-journal'], path: '/blogs/the-anointing-journal', page_title: 'The Anointing Journal' }),
  article: () => globalsFor('article', { blog: M.blogs['the-anointing-journal'], article: M.articles[0], path: M.articles[0].url, page_title: M.articles[0].title }),
  404: () => globalsFor('404', { path: '/nope', page_title: 'Page not found' }),
  password: () => globalsFor('password', { path: '/password', page_title: 'Mount of Olives' }),
  'customers/login': () => globalsFor('customers/login', { path: '/account/login', page_title: 'Log in' }),
  'customers/register': () => globalsFor('customers/register', { path: '/account/register', page_title: 'Create account' }),
  'customers/account': () => globalsFor('customers/account', { customer: M.customer, path: '/account', page_title: 'Account' }),
  'customers/order': () => globalsFor('customers/order', { customer: M.customer, order: M.orders[0], path: '/account/orders/1', page_title: 'Order #1042' }),
  'customers/addresses': () => globalsFor('customers/addresses', { customer: M.customer, path: '/account/addresses', page_title: 'Addresses' }),
  'customers/activate_account': () => globalsFor('customers/activate_account', { path: '/account/activate', page_title: 'Activate account' }),
  'customers/reset_password': () => globalsFor('customers/reset_password', { path: '/account/reset', page_title: 'Reset password' }),
};

/* ---------- render ---------- */
async function renderTemplate(name) {
  const makeGlobals = PAGES[name];
  if (!makeGlobals) throw new Error(`unknown preview page ${name}`);
  const globals = makeGlobals();
  const tplName = name.replace(/-(squalane|empty)$/, '');
  const jsonFile = path.join(ROOT, 'templates', `${tplName}.json`);
  const liquidFile = path.join(ROOT, 'templates', `${tplName}.liquid`);
  let layoutName = 'theme';
  let content = '';
  if (fs.existsSync(jsonFile)) {
    const tpl = JSON.parse(fs.readFileSync(jsonFile, 'utf8'));
    if (tpl.layout) layoutName = tpl.layout;
    for (const sid of tpl.order) {
      try {
        content += await renderSection(`template--${tplName.replace(/[^a-z0-9]/gi, '-')}__${sid}`, tpl.sections[sid].type, tpl.sections[sid], globals);
      } catch (e) {
        content += `<pre style="color:#b00;white-space:pre-wrap">Section ${tpl.sections[sid].type} failed: ${e.message}</pre>`;
        console.error(`  ! ${name} / ${tpl.sections[sid].type}: ${e.message}`);
      }
    }
  } else if (fs.existsSync(liquidFile)) {
    const { tpl } = parseFile(liquidFile);
    content = await engine.render(tpl, {}, { globals });
    if (globals.__layout === 'none') return content;
  } else {
    throw new Error(`template ${tplName} not found`);
  }
  if (layoutName === false || layoutName === 'none') return content;
  const { tpl: layoutTpl } = parseFile(path.join(ROOT, 'layout', `${layoutName}.liquid`));
  return engine.render(layoutTpl, { content_for_layout: content }, { globals });
}

const targets = only.length ? only : Object.keys(PAGES);
let failures = 0;
for (const name of targets) {
  try {
    const html = await renderTemplate(name);
    const file = path.join(OUT, `${name.replace('/', '-')}.html`);
    fs.writeFileSync(file, html);
    console.log(`✓ ${name} → ${path.relative(ROOT, file)} (${(html.length / 1024).toFixed(0)} KB)`);
  } catch (e) {
    failures++;
    console.error(`✗ ${name}: ${e.message}`);
  }
}

/* ---------- static assets ---------- */
for (const f of fs.readdirSync(path.join(ROOT, 'assets'))) fs.copyFileSync(path.join(ROOT, 'assets', f), path.join(OUT, 'assets', f));
M.writeImages(OUT);
const fontsOut = path.join(OUT, 'fonts');
fs.mkdirSync(fontsOut, { recursive: true });
for (const pkg of ['cormorant-garamond', 'dm-sans']) {
  const dir = path.join(ROOT, 'dev/preview/node_modules/@fontsource', pkg, 'files');
  if (!fs.existsSync(dir)) continue;
  for (const f of fs.readdirSync(dir)) if (f.includes('latin-') && !f.includes('ext') && f.endsWith('.woff2')) fs.copyFileSync(path.join(dir, f), path.join(fontsOut, f));
}
console.log(failures ? `${failures} page(s) failed` : 'all pages rendered');
process.exit(failures ? 1 : 0);
