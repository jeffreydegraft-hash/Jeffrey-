/* Local preview renderer for the Mount of Olives Prestige theme.
   Renders a theme folder's JSON templates with liquidjs and the store's real data.
   Usage: node render.mjs <themeDir> <outDir> [page ...]
   An approximation of Shopify's renderer, for looking at layout and styling only. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Liquid, Tag, Value } from 'liquidjs';
import crypto from 'node:crypto';
import * as D from './data.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const [ROOT_ARG, OUT_ARG, ...ONLY] = process.argv.slice(2);
const ROOT = path.resolve(ROOT_ARG || path.join(HERE, '..', 'live'));
const OUT = path.resolve(OUT_ARG || path.join(HERE, 'dist'));
fs.mkdirSync(path.join(OUT, 'assets'), { recursive: true });

const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\s*\/\*[\s\S]*?\*\/\s*/, ''));
const warnings = new Set();
const warn = (m) => {
  if (!warnings.has(m)) console.error('  ! ' + m);
  warnings.add(m);
};

/* ---------- settings ---------- */
const schema = readJson(path.join(ROOT, 'config/settings_schema.json'));
const settingsData = readJson(path.join(ROOT, 'config/settings_data.json'));
const rawSettings = typeof settingsData.current === 'string' ? settingsData.presets[settingsData.current] : settingsData.current;
const settingDefs = {};
for (const group of schema) for (const s of group.settings || []) if (s.id) settingDefs[s.id] = s;

/* color schemes: defaults from the schema definition, overridden by settings_data */
const schemeDef = settingDefs.color_schemes;
const schemeFieldDefs = (schemeDef && schemeDef.definition) || [];
const colorSchemes = Object.entries(rawSettings.color_schemes || {}).map(([id, s]) => {
  const out = { id, settings: {} };
  for (const def of schemeFieldDefs) if (def.id) out.settings[def.id] = coerce(def, (s.settings || {})[def.id]);
  for (const [k, v] of Object.entries(s.settings || {})) if (!(k in out.settings)) out.settings[k] = /^#|^rgb/.test(String(v)) ? new D.Color(v) : v;
  out.toString = () => id;
  return out;
});
const schemeById = Object.fromEntries(colorSchemes.map((s) => [s.id, s]));
const schemeFor = (id) => schemeById[id] || null;

function fontFromHandle(handle) {
  const m = String(handle || '').match(/^(.*)_([ni])(\d)$/);
  const fam = m ? m[1] : String(handle);
  const style = m && m[2] === 'i' ? 'italic' : 'normal';
  const weight = m ? Number(m[3]) * 100 : 400;
  const family = fam.split('_').map((w) => w[0].toUpperCase() + w.slice(1)).join(' ');
  const serif = /cormorant|garamond|playfair|baskerville|lora|serif/i.test(family);
  return { family, fallback_families: serif ? 'serif' : 'sans-serif', weight, style, system_q: false, _handle: fam, toString() { return this.family; } };
}

function coerce(def, value) {
  if (!def) return value;
  const v = value === undefined ? def.default : value;
  switch (def.type) {
    case 'color_scheme':
      return schemeFor(v || def.default) || schemeFor('scheme-1');
    case 'font_picker':
      return fontFromHandle(v || def.default);
    case 'color':
      return v ? new D.Color(v) : '';
    case 'color_background':
      return v || '';
    case 'image_picker':
      return v ? D.shopImage(v) : null;
    case 'link_list':
      return (v && D.linklists[v]) || null;
    case 'collection':
      return (v && D.collections[v]) || null;
    case 'collection_list':
      return (v || []).map((h) => D.collections[h]).filter(Boolean);
    case 'product':
      return (v && D.productsByHandle[v]) || null;
    case 'product_list':
      return (v || []).map((h) => D.productsByHandle[h]).filter(Boolean);
    case 'blog':
      return (v && D.blogs[v]) || null;
    case 'article':
      return (v && D.articles.find((a) => a.handle === v)) || null;
    case 'page':
      return (v && D.pages[v]) || null;
    case 'url':
      return typeof v === 'string' ? v.replace(/^shopify:\/\/(collections|products|pages|blogs)\//, '/$1/') : v;
    case 'range':
    case 'number':
      return v === undefined || v === null || v === '' ? def.default : Number(v);
    case 'checkbox':
      return v === undefined ? !!def.default : !!v;
    case 'richtext':
    case 'inline_richtext':
    case 'text':
    case 'textarea':
    case 'html':
      return v === undefined || v === null ? '' : v;
    default:
      return v === undefined ? null : v;
  }
}

const settings = {};
for (const [id, def] of Object.entries(settingDefs)) settings[id] = coerce(def, rawSettings[id]);
for (const [k, v] of Object.entries(rawSettings)) if (!(k in settings) && !['sections', 'blocks', 'content_for_index'].includes(k)) settings[k] = v;
settings.color_schemes = Object.assign([...colorSchemes], schemeById);

/* ---------- locales ---------- */
const locale = readJson(path.join(ROOT, 'locales/en.default.json'));
function translate(key, params = {}) {
  let node = locale;
  for (const part of String(key).split('.')) {
    node = node && typeof node === 'object' ? node[part] : undefined;
    if (node === undefined) {
      warn(`missing translation ${key}`);
      return `translation missing: en.${key}`;
    }
  }
  if (node && typeof node === 'object') {
    const n = Number(params.count);
    node = n === 0 && node.zero !== undefined ? node.zero : n === 1 ? node.one : node.other;
  }
  return String(node).replace(/\{\{\s*(\w+)\s*\}\}/g, (_, k) => (params[k] !== undefined ? params[k] : ''));
}

/* ---------- money ---------- */
const fmt = (n) => n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const money = (c, f = D.shop.money_format) => f.replace(/\{\{\s*amount\s*\}\}/, fmt(Number(c || 0) / 100)).replace(/\{\{\s*amount_no_decimals\s*\}\}/, String(Math.round(Number(c || 0) / 100)));

/* ---------- engine ---------- */
const engine = new Liquid({
  root: [path.join(ROOT, 'snippets')],
  partials: path.join(ROOT, 'snippets'),
  extname: '.liquid',
  cache: true,
  strictFilters: false,
  strictVariables: false,
  lenientIf: true,
  jsTruthy: false,
  dynamicPartials: true,
  ownPropertyOnly: false,
  fs: {
    exists: async (p) => fs.existsSync(p),
    existsSync: (p) => fs.existsSync(p),
    readFile: async (p) => preprocess(await fs.promises.readFile(p, 'utf8')),
    readFileSync: (p) => preprocess(fs.readFileSync(p, 'utf8')),
    resolve: (root, file, ext) => path.resolve(root, file.endsWith(ext) ? file : file + ext),
    fallback: (file) => {
      warn(`missing snippet ${path.basename(file)}`);
      return path.join(HERE, '_missing.liquid');
    },
    dirname: (p) => path.dirname(p),
    sep: path.sep,
    contains: () => true,
  },
});
fs.writeFileSync(path.join(HERE, '_missing.liquid'), '<!-- missing snippet -->');

const kw = (rest) => {
  const o = {};
  for (const r of rest) if (Array.isArray(r)) o[r[0]] = r[1];
  return o;
};
const attrs = (obj) =>
  Object.entries(obj)
    .filter(([, v]) => v !== undefined && v !== null && v !== false && v !== '')
    .map(([k, v]) => (v === true ? k : `${k}="${String(v).replace(/"/g, '&quot;')}"`))
    .join(' ');

engine.registerFilter('t', (key, ...rest) => translate(key, kw(rest)));
engine.registerFilter('json', (v) => {
  const seen = new WeakSet();
  return JSON.stringify(v === undefined ? null : v, (k, val) => {
    if (k.startsWith('_') || k === 'preview_image' || k === 'image' || k === 'collections') return undefined;
    if (val && typeof val === 'object') {
      if (seen.has(val)) return undefined;
      seen.add(val);
    }
    return val;
  });
});
engine.registerFilter('money', (v) => money(v));
engine.registerFilter('money_with_currency', (v) => money(v, D.shop.money_with_currency_format));
engine.registerFilter('money_without_currency', (v) => fmt(Number(v || 0) / 100));
engine.registerFilter('money_without_trailing_zeros', (v) => money(v).replace(/\.00(?=\D*$)/, ''));
engine.registerFilter('md5', (s) => crypto.createHash('md5').update(String(s === undefined || s === null ? '' : s)).digest('hex'));
engine.registerFilter('handle', D.handleize);
engine.registerFilter('handleize', D.handleize);
engine.registerFilter('asset_url', (f) => `/assets/${f}`);
engine.registerFilter('shopify_asset_url', (f) => `/assets/${f}`);
engine.registerFilter('file_url', (f) => `files/${f}`);
engine.registerFilter('stylesheet_tag', (u) => `<link href="${u}" rel="stylesheet" type="text/css" media="all" />`);
engine.registerFilter('script_tag', (u) => `<script src="${u}" type="text/javascript"></script>`);
engine.registerFilter('image_url', (img) => {
  if (!img) return '';
  if (typeof img === 'string') return img.startsWith('shopify://') ? D.shopImage(img).src : img;
  return img.src || (img.preview_image && img.preview_image.src) || '';
});
engine.registerFilter('img_url', (img) => (img && img.src) || '');
engine.registerFilter('image_tag', function (src, ...rest) {
  const o = kw(rest);
  const file = String(src).split('/').pop();
  const img = [...Object.values(D.productsByHandle).flatMap((p) => p.media)].find((m) => m.src === src) || D.imageFrom(file);
  let width = o.width !== undefined && o.width !== null && o.width !== '' ? Number(o.width) : img ? img.width : undefined;
  let height = o.height !== undefined && o.height !== null && o.height !== '' ? Number(o.height) : undefined;
  if (height === undefined && width && img) height = Math.round(width / img.aspect_ratio);
  const alt = String(o.alt !== undefined && o.alt !== null ? o.alt : img ? img.alt : '').replace(/"/g, '&quot;');
  const extra = {};
  for (const [k, v] of Object.entries(o)) if (!['width', 'height', 'alt', 'widths', 'sizes', 'preload', 'srcset'].includes(k)) extra[k.replace(/_/g, '-')] = v;
  return `<img src="${src}" alt="${alt}" ${attrs({ width, height, sizes: o.sizes })} ${attrs(extra)}>`;
});
engine.registerFilter('placeholder_svg_tag', (name, cls) => `<svg class="${cls || 'placeholder-svg'}" viewBox="0 0 525 525" xmlns="http://www.w3.org/2000/svg"><rect width="525" height="525" fill="currentColor" opacity=".06"/></svg>`);
engine.registerFilter('payment_type_svg_tag', (type, ...rest) => `<svg class="${kw(rest).class || 'payment-icon'}" viewBox="0 0 38 24" width="38" height="24" role="img" aria-label="${type}" xmlns="http://www.w3.org/2000/svg"><rect width="38" height="24" rx="3" fill="#fff" stroke="#ccc"/><text x="19" y="15" text-anchor="middle" font-family="sans-serif" font-size="7" fill="#333">${String(type).replace(/_/g, ' ').slice(0, 9)}</text></svg>`);
engine.registerFilter('payment_button', () => `<div class="shopify-payment-button"><button type="button" class="shopify-payment-button__button shopify-payment-button__button--unbranded">Buy it now</button></div>`);
engine.registerFilter('payment_terms', () => '');
engine.registerFilter('login_button', () => '');
engine.registerFilter('inline_asset_content', (f) => {
  const p = path.join(ROOT, 'assets', f);
  return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '';
});
const FONT_FILES = {
  Cormorant: (w, s) => `cormorant-latin-${Math.min(700, Math.max(300, w))}-${s}.woff2`,
  Montserrat: (w, s) => `montserrat-latin-${Math.min(700, Math.max(400, w))}-${s}.woff2`,
};
const fontFile = (font) => (FONT_FILES[font.family] ? FONT_FILES[font.family](font.weight, font.style) : null);
engine.registerFilter('font_face', (font) => {
  if (!font || !font.family) return '';
  const file = fontFile(font);
  if (!file) {
    warn(`no local font for ${font.family}`);
    return '';
  }
  return `@font-face { font-family: ${font.family}; font-weight: ${font.weight}; font-style: ${font.style}; font-display: fallback; src: url("/fonts/${file}") format("woff2"); }`;
});
engine.registerFilter('font_modify', (font, prop, value) => {
  if (!font) return font;
  const f = { ...font, toString: font.toString };
  if (prop === 'weight') f.weight = value === 'bolder' || value === 'bold' ? (font.weight < 600 ? 700 : 900) : value === 'lighter' ? Math.max(100, font.weight - 300) : Number(value) || font.weight;
  if (prop === 'style') f.style = value;
  return f;
});
engine.registerFilter('font_url', (font) => (font && fontFile(font) ? `/fonts/${fontFile(font)}` : ''));
const toColor = (c) => (c instanceof D.Color ? c : c ? new D.Color(String(c)) : null);
engine.registerFilter('color_brightness', (c) => {
  c = toColor(c);
  return c ? (c.red * 299 + c.green * 587 + c.blue * 114) / 1000 : 0;
});
engine.registerFilter('color_mix', (a, b, w) => {
  a = toColor(a);
  b = toColor(b);
  if (!a || !b) return a || b || '';
  const p = Number(w) / 100;
  const mix = (x, y) => Math.round(x * p + y * (1 - p));
  return new D.Color(`rgb(${mix(a.red, b.red)}, ${mix(a.green, b.green)}, ${mix(a.blue, b.blue)})`);
});
engine.registerFilter('color_modify', (c, prop, val) => {
  c = toColor(c);
  if (!c) return '';
  if (prop === 'alpha') return new D.Color(`rgba(${c.red}, ${c.green}, ${c.blue}, ${val})`);
  return c;
});
engine.registerFilter('color_to_rgb', (c) => {
  c = toColor(c);
  return c ? (c.alpha < 1 ? `rgba(${c.red}, ${c.green}, ${c.blue}, ${c.alpha})` : `rgb(${c.red}, ${c.green}, ${c.blue})`) : '';
});
engine.registerFilter('color_to_hex', (c) => (toColor(c) || {}).hex || '');
engine.registerFilter('color_lighten', (c, a) => {
  c = toColor(c);
  const f = (v) => Math.round(v + (255 - v) * (Number(a) / 100));
  return c ? new D.Color(`rgb(${f(c.red)}, ${f(c.green)}, ${f(c.blue)})`) : '';
});
engine.registerFilter('color_darken', (c, a) => {
  c = toColor(c);
  const f = (v) => Math.round(v * (1 - Number(a) / 100));
  return c ? new D.Color(`rgb(${f(c.red)}, ${f(c.green)}, ${f(c.blue)})`) : '';
});
engine.registerFilter('format_address', (a) => (a ? `<p>${[a.name, a.address1, a.city, a.country].filter(Boolean).join('<br>')}</p>` : ''));
engine.registerFilter('within', (url) => url);
engine.registerFilter('url_for_vendor', (v) => `/collections/vendors?q=${encodeURIComponent(v)}`);
engine.registerFilter('url_param_escape', (s) => encodeURIComponent(String(s || '')));
engine.registerFilter('url_encode', (s) => encodeURIComponent(String(s || '')));
engine.registerFilter('link_to', (text, url) => `<a href="${url}">${text}</a>`);
engine.registerFilter('link_to_tag', (text, tag) => `<a href="/collections/all/${D.handleize(tag)}">${text}</a>`);
engine.registerFilter('link_to_remove_tag', (text, tag) => `<a href="/collections/all">${text}</a>`);
engine.registerFilter('weight_with_unit', (w) => `${w} lb`);
engine.registerFilter('time_tag', (d) => `<time datetime="${d}">${new Date(d).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</time>`);
engine.registerFilter('video_tag', () => '<video playsinline muted loop></video>');
engine.registerFilter('external_video_tag', () => '<iframe title="video" src="about:blank"></iframe>');
engine.registerFilter('external_video_url', () => 'about:blank');
engine.registerFilter('model_viewer_tag', () => '<div>3D</div>');
engine.registerFilter('structured_data', () => '{}');
engine.registerFilter('default_errors', () => '');
engine.registerFilter('format_code', (c) => String(c || ''));
engine.registerFilter('line_items_for', () => []);
engine.registerFilter('item_count_for_variant', () => 0);
engine.registerFilter('unit_price_with_measurement', (p) => money(p));
engine.registerFilter('escape_once', (s) => String(s || '').replace(/&(?!amp;|lt;|gt;|quot;|#39;)/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'));
engine.registerFilter('newline_to_br', (s) => String(s || '').replace(/\n/g, '<br>\n'));
engine.registerFilter('sum', (arr, prop) => (Array.isArray(arr) ? arr.reduce((s, x) => s + Number(prop ? x && x[prop] : x || 0), 0) : 0));
engine.registerFilter('app_block_placeholder', (b) => `<div class="app-block-placeholder" style="padding:2.5rem 1rem;text-align:center;border:1px dashed rgb(var(--text-color) / .25);font:500 12px/1.4 sans-serif;letter-spacing:.08em;text-transform:uppercase;opacity:.7">App: ${String(b && b.type || '').split('/')[3] || 'app block'} (rendered by the app on the real store)</div>`);

/* ---------- tags ---------- */
class SkipTag extends Tag {
  constructor(token, remain, liquid) {
    super(token, remain, liquid);
    const stream = liquid.parser.parseStream(remain);
    stream.on(`tag:end${token.name}`, () => stream.stop()).on('template', () => {}).on('end', () => { throw new Error(`${token.name} not closed`); });
    stream.start();
  }
  *render() {
    return '';
  }
}
class StyleTag extends Tag {
  constructor(token, remain, liquid) {
    super(token, remain, liquid);
    this.templates = [];
    const stream = liquid.parser.parseStream(remain);
    stream.on('tag:endstyle', () => stream.stop()).on('template', (t) => this.templates.push(t)).on('end', () => { throw new Error('style not closed'); });
    stream.start();
  }
  *render(ctx, emitter) {
    emitter.write('<style data-shopify>');
    yield this.liquid.renderer.renderTemplates(this.templates, ctx, emitter);
    emitter.write('</style>');
  }
}
class FormTag extends Tag {
  constructor(token, remain, liquid) {
    super(token, remain, liquid);
    this.raw = token.args;
    this.templates = [];
    const stream = liquid.parser.parseStream(remain);
    stream.on('tag:endform', () => stream.stop()).on('template', (t) => this.templates.push(t)).on('end', () => { throw new Error('form not closed'); });
    stream.start();
  }
  *render(ctx, emitter) {
    const m = this.raw.match(/^\s*'([^']+)'|^\s*"([^"]+)"/);
    const type = m ? m[1] || m[2] : 'form';
    const kv = {};
    for (const mm of this.raw.matchAll(/([\w-]+)\s*:\s*('([^']*)'|"([^"]*)"|([^,]+))/g)) {
      kv[mm[1]] = mm[3] !== undefined ? mm[3] : mm[4] !== undefined ? mm[4] : yield new Value(mm[5].trim(), this.liquid).value(ctx);
    }
    const actions = { product: '/cart/add', customer: '/contact#newsletter', contact: '/contact', localization: '/localization', cart: '/cart' };
    emitter.write(`<form method="post" action="${actions[type] || '/'}" accept-charset="UTF-8" ${attrs(kv)}><input type="hidden" name="form_type" value="${type}">`);
    ctx.push({ form: { errors: null, posted_successfully_q: process.env.FORM_POSTED === '1', email: '', body: '', id: 'new' } });
    yield this.liquid.renderer.renderTemplates(this.templates, ctx, emitter);
    ctx.pop();
    emitter.write('</form>');
  }
}
class PaginateTag extends Tag {
  constructor(token, remain, liquid) {
    super(token, remain, liquid);
    const m = token.args.match(/^\s*(.+?)\s+by\s+(.+?)\s*$/);
    this.items = new Value(m ? m[1] : token.args, liquid);
    this.size = new Value(m ? m[2] : '20', liquid);
    this.templates = [];
    const stream = liquid.parser.parseStream(remain);
    stream.on('tag:endpaginate', () => stream.stop()).on('template', (t) => this.templates.push(t)).on('end', () => { throw new Error('paginate not closed'); });
    stream.start();
  }
  *render(ctx, emitter) {
    const items = (yield this.items.value(ctx)) || [];
    const size = Number(yield this.size.value(ctx)) || 20;
    const total = Array.isArray(items) ? items.length : 0;
    const pages = Math.max(1, Math.ceil(total / size));
    ctx.push({ paginate: { current_page: 1, current_offset: 0, items: total, page_size: size, pages, parts: [], previous: null, next: null, page_param: 'page' } });
    yield this.liquid.renderer.renderTemplates(this.templates, ctx, emitter);
    ctx.pop();
  }
}
class SectionsTag extends Tag {
  constructor(token, remain, liquid) {
    super(token, remain, liquid);
    this.name = token.args.trim().replace(/^['"]|['"]$/g, '');
  }
  *render(ctx, emitter) {
    emitter.write(yield renderGroup(this.name, ctx.getAll()));
  }
}
class SectionTag extends Tag {
  constructor(token, remain, liquid) {
    super(token, remain, liquid);
    this.name = token.args.trim().replace(/^['"]|['"]$/g, '');
  }
  *render(ctx, emitter) {
    emitter.write(yield renderSection(this.name, this.name, {}, ctx.getAll(), { index: 1 }));
  }
}
/* Shopify renders "liquid" type settings as Liquid in the surrounding context */
class EvalLiquidTag extends Tag {
  constructor(token, remain, liquid) {
    super(token, remain, liquid);
    this.value = new Value(token.args, liquid);
  }
  *render(ctx, emitter) {
    const src = yield this.value.value(ctx);
    if (!src) return;
    const tpl = this.liquid.parse(preprocess(String(src)));
    yield this.liquid.renderer.renderTemplates(tpl, ctx, emitter);
  }
}
class NoopTag extends Tag {
  *render() {
    return '';
  }
}
engine.registerTag('schema', SkipTag);
engine.registerTag('doc', SkipTag);
engine.registerTag('javascript', SkipTag);
engine.registerTag('stylesheet', SkipTag);
engine.registerTag('style', StyleTag);
engine.registerTag('form', FormTag);
engine.registerTag('paginate', PaginateTag);
engine.registerTag('sections', SectionsTag);
engine.registerTag('section', SectionTag);
engine.registerTag('content_for', NoopTag);
engine.registerTag('eval_liquid', EvalLiquidTag);

function preprocess(src) {
  return src
    .replace(/\{%-?\s*render\s+block\s*-?%\}/g, '{{ block | app_block_placeholder }}')
    .replace(/\{\{-?\s*block\.settings\.liquid\s*-?\}\}/g, '{% eval_liquid block.settings.liquid %}')
    .replace(/\.(\w+)\?(?=[\s%}|)\],])/g, '.$1_q')
    .replace(/\b([\w.]+)\s*(==|!=)\s*empty\b/g, (m, v, op) => (op === '==' ? `${v}.size == 0` : `${v}.size > 0`))
    .replace(/\{%-?\s*#[^%]*-?%\}/g, '')
    .replace(/\{%(-?)\s*liquid\b([\s\S]*?)(-?)%\}/g, (m, l, body, r) => `{%${l} liquid${body.replace(/^\s*comment\s*$[\s\S]*?^\s*endcomment\s*$/gm, '').replace(/^(\s*)#.*$/gm, '$1')}${r}%}`);
}

const parsed = new Map();
function parseFile(file) {
  if (parsed.has(file)) return parsed.get(file);
  const src = fs.readFileSync(file, 'utf8');
  const sm = src.match(/\{%-?\s*schema\s*-?%\}([\s\S]*?)\{%-?\s*endschema\s*-?%\}/);
  let sch = null;
  if (sm) {
    try {
      /* Shopify accepts trailing commas in section schemas */
      sch = JSON.parse(sm[1].replace(/,(\s*[}\]])/g, '$1'));
    } catch (e) {
      warn(`schema JSON error in ${path.relative(ROOT, file)}: ${e.message}`);
    }
  }
  let tpl;
  try {
    tpl = engine.parse(preprocess(src.replace(/\{%-?\s*schema\s*-?%\}[\s\S]*?\{%-?\s*endschema\s*-?%\}/, '')), file);
  } catch (e) {
    throw new Error(`Liquid parse error in ${path.relative(ROOT, file)}: ${e.message}`);
  }
  const out = { tpl, schema: sch };
  parsed.set(file, out);
  return out;
}

/* ---------- sections ---------- */
function buildSection(id, type, data, sch, extra) {
  const s = {};
  for (const def of (sch && sch.settings) || []) if (def.id) s[def.id] = coerce(def, (data.settings || {})[def.id]);
  for (const [k, v] of Object.entries(data.settings || {})) if (!(k in s)) s[k] = v;
  const blockDefs = Object.fromEntries(((sch && sch.blocks) || []).map((b) => [b.type, b]));
  const blocks = [];
  for (const bid of data.block_order || Object.keys(data.blocks || {})) {
    const b = (data.blocks || {})[bid];
    if (!b || b.disabled) continue;
    const def = blockDefs[b.type] || blockDefs['@app'] || { settings: [] };
    const bs = {};
    for (const sd of def.settings || []) if (sd.id) bs[sd.id] = coerce(sd, (b.settings || {})[sd.id]);
    for (const [k, v] of Object.entries(b.settings || {})) if (!(k in bs)) bs[k] = v;
    blocks.push({ id: bid, type: b.type, settings: bs, shopify_attributes: `data-shopify-editor-block="${bid}"` });
  }
  return { id, type, settings: s, blocks, index: extra.index || 1, index0: (extra.index || 1) - 1, location: extra.location || 'template' };
}

async function renderSection(id, type, data, globals, extra = {}) {
  const file = path.join(ROOT, 'sections', `${type}.liquid`);
  if (!fs.existsSync(file)) return `<!-- missing section ${type} -->`;
  const { tpl, schema: sch } = parseFile(file);
  const section = buildSection(id, type, data, sch, extra);
  let html;
  try {
    html = await engine.render(tpl, { section }, { globals: { ...globals, section } });
  } catch (e) {
    warn(`section ${type} failed: ${e.message.split('\n')[0]}`);
    html = `<pre style="color:#b00;white-space:pre-wrap;padding:1rem">Preview error in section ${type}: ${e.message.split('\n')[0]}</pre>`;
  }
  const tag = (sch && sch.tag) || 'div';
  const cls = ['shopify-section', extra.group ? `shopify-section-group-${extra.group}` : '', sch && sch.class].filter(Boolean).join(' ');
  return `<${tag} id="shopify-section-${id}" class="${cls}">${html}</${tag}>`;
}

async function renderGroup(name, globals) {
  const file = path.join(ROOT, 'sections', `${name}.json`);
  if (!fs.existsSync(file)) return `<!-- missing group ${name} -->`;
  const group = readJson(file);
  let out = '';
  let i = 0;
  for (const sid of group.order) {
    const data = group.sections[sid];
    if (data.disabled) continue;
    i++;
    out += await renderSection(`sections--1__${sid}`, data.type, data, globals, { index: i, location: name.replace('-group', ''), group: name });
  }
  return out;
}

/* ---------- pages ---------- */
function globalsFor(pageType, extra = {}) {
  return {
    shop: D.shop,
    settings,
    routes: D.routes,
    cart: D.makeCart([]),
    localization: D.localization,
    linklists: D.linklists,
    collections: D.collectionsList,
    pages: D.pages,
    blogs: D.blogs,
    all_products: D.productsByHandle,
    request: { page_type: pageType, locale: { iso_code: 'en', name: 'English', root_url: '/' }, origin: 'https://mountofolives.co', host: 'mountofolives.co', path: extra.path || '/', design_mode: false, visual_preview_mode: false },
    template: { name: pageType, suffix: null, directory: null, toString() { return pageType; } },
    canonical_url: `https://mountofolives.co${extra.path || '/'}`,
    page_title: extra.page_title || D.shop.name,
    page_description: D.shop.description,
    page_image: null,
    content_for_header: `<script>window.Shopify={shop:'mount-of-olives-co.myshopify.com',locale:'en',country:'US',currency:{active:'USD',rate:'1.0'},routes:{root:'/'},designMode:false,theme:{id:1,name:'preview',role:'main'},loadFeatures:function(f,cb){cb&&cb()}};</script>`,
    current_tags: null,
    current_page: 1,
    customer: null,
    predictive_search: { performed: false, resources: { products: [], collections: [], pages: [], articles: [], queries: [] } },
    recommendations: { performed: false, products: [], products_count: 0 },
    country_option_tags: '<option value="United States">United States</option>',
    all_country_option_tags: '<option value="United States">United States</option>',
    powered_by_link: '',
    ...extra,
  };
}

const FM = D.productsByHandle['frankincense-myrrh-anointing-oil'];

/* a cart line for a product's first variant, with the fields Prestige's line-item snippet reads */
function lineItem(handle, quantity, index) {
  const product = D.productsByHandle[handle];
  const variant = product.selected_or_first_available_variant;
  const unit = variant.price;
  return {
    id: variant.id, key: `${variant.id}:${index}`, product_id: product.id, variant_id: variant.id, index,
    title: product.has_only_default_variant ? product.title : `${product.title} - ${variant.title}`, product_title: product.title, variant_title: product.has_only_default_variant ? null : variant.title,
    product, variant, vendor: product.vendor, sku: variant.sku, url: variant.url, image: product.featured_image, quantity,
    price: unit, final_price: unit, original_price: unit, line_price: unit * quantity, final_line_price: unit * quantity, original_line_price: unit * quantity,
    total_discount: 0, discounts: [], line_level_discount_allocations: [], line_level_total_discount: 0, properties: {}, selling_plan_allocation: null,
    options_with_values: product.has_only_default_variant ? [] : product.options.map((name, i) => ({ name, value: variant.options[i] })),
    unit_price: null, unit_price_measurement: null, gift_card: false, requires_shipping: true, taxable: true, grams: 0, message: null,
    url_to_remove: `/cart/change?line=${index}&quantity=0`,
  };
}
const CART_ITEMS = [lineItem('hyssop', 1, 1), lineItem('frankincense-myrrh-anointing-oil', 2, 2)];
const JOURNAL = D.blogs['the-anointing-journal'];
const FIRST_ARTICLE = JOURNAL.articles[0];
const SEARCH_RESULTS = D.collections['all-products'].products.filter((p) => /hyssop|rose|latter/i.test(p.title));

const PAGES = {
  index: () => globalsFor('index', { path: '/', page_title: 'Mount of Olives' }),
  product: () => globalsFor('product', { product: FM, collection: null, path: FM.url, page_title: FM.title, recommendations: { performed: true, products: D.collections.all.products.filter((p) => p !== FM).slice(0, 4), products_count: 4 } }),
  collection: () => globalsFor('collection', { collection: D.collections['all-products'], path: '/collections/all-products', page_title: 'All Anointing Oil Products' }),
  'collection-fm': () => globalsFor('collection', { collection: D.collections['frankincense-myrrh'], path: '/collections/frankincense-myrrh', page_title: 'Frankincense & Myrrh' }),
  cart: () => globalsFor('cart', { cart: D.makeCart(CART_ITEMS), path: '/cart', page_title: 'Your cart' }),
  'page-contact': () => globalsFor('page', { __template: 'page.contact', page: D.pages['contact'], path: '/pages/contact', page_title: D.pages['contact'].title }),
  'page-faq': () => globalsFor('page', { __template: 'page.faq', page: D.pages['faqs'], path: '/pages/faqs', page_title: D.pages['faqs'].title }),
  'page-about': () => globalsFor('page', { __template: 'page', page: D.pages['about-us'], path: '/pages/about-us', page_title: D.pages['about-us'].title }),
  'page-our-science': () => globalsFor('page', { __template: 'page.our-science', page: D.pages['our-science'], path: '/pages/our-science', page_title: D.pages['our-science'].title }),
  blog: () => globalsFor('blog', { blog: JOURNAL, path: JOURNAL.url, page_title: JOURNAL.title }),
  article: () => globalsFor('article', { blog: JOURNAL, article: FIRST_ARTICLE, path: FIRST_ARTICLE.url, page_title: FIRST_ARTICLE.title }),
  search: () => globalsFor('search', { path: '/search?q=hyssop', page_title: 'Search', search: { performed: true, terms: 'hyssop', results: SEARCH_RESULTS, results_count: SEARCH_RESULTS.length, types: ['product'], sort_by: 'relevance', default_sort_by: 'relevance', sort_options: [{ name: 'Relevance', value: 'relevance' }, { name: 'Price, low to high', value: 'price-ascending' }], filters: [] } }),
  '404': () => globalsFor('404', { path: '/missing', page_title: 'Page not found' }),
  'list-collections': () => globalsFor('list-collections', { path: '/collections', page_title: 'Collections' }),
  'customers-login': () => globalsFor('customers/login', { __template: 'customers/login', path: '/account/login', page_title: 'Login' }),
  'customers-register': () => globalsFor('customers/register', { __template: 'customers/register', path: '/account/register', page_title: 'Create account' })
};

async function renderPage(name) {
  const globals = PAGES[name]();
  const tplFile = path.join(ROOT, 'templates', `${globals.__template || name.replace(/-fm$/, '')}.json`);
  const tpl = readJson(tplFile);
  let content = '';
  let i = 0;
  for (const sid of tpl.order) {
    const data = tpl.sections[sid];
    if (data.disabled) continue;
    i++;
    content += await renderSection(`template--1__${sid}`, data.type, data, globals, { index: i });
  }
  const { tpl: layout } = parseFile(path.join(ROOT, 'layout', `${tpl.layout || 'theme'}.liquid`));
  return engine.render(layout, { content_for_layout: content }, { globals });
}

for (const name of ONLY.length ? ONLY : Object.keys(PAGES)) {
  const html = await renderPage(name);
  fs.writeFileSync(path.join(OUT, `${name}.html`), html);
  console.log(`rendered ${name} (${(html.length / 1024).toFixed(0)} KB)`);
}

/* assets, fonts, images */
for (const f of fs.readdirSync(path.join(ROOT, 'assets'))) fs.copyFileSync(path.join(ROOT, 'assets', f), path.join(OUT, 'assets', f));
fs.mkdirSync(path.join(OUT, 'fonts'), { recursive: true });
for (const pkg of ['cormorant', 'montserrat']) {
  const dir = path.join(HERE, 'node_modules/@fontsource', pkg, 'files');
  for (const f of fs.readdirSync(dir)) if (/-latin-\d+-(normal|italic)\.woff2$/.test(f)) fs.copyFileSync(path.join(dir, f), path.join(OUT, 'fonts', f));
}
const imgOut = path.join(OUT, 'img');
if (!fs.existsSync(imgOut)) fs.symlinkSync(path.join(HERE, '..', 'img'), imgOut);
console.log(warnings.size ? `${warnings.size} warning(s)` : 'no warnings');
