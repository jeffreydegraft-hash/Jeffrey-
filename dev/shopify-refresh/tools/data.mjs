/* Store data for the local Prestige preview, built from the Admin API export in store.json
   and the photos downloaded into ../img. Approximates Shopify's Liquid objects. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const IMG = path.join(HERE, '..', 'img');
const store = JSON.parse(fs.readFileSync(path.join(HERE, 'store.json'), 'utf8'));

export const handleize = (s) =>
  String(s || '')
    .toLowerCase()
    .replace(/['"’]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

/* ---------- colours ---------- */
export class Color {
  constructor(value) {
    this.raw = value;
    let r = 0, g = 0, b = 0, a = 1;
    const v = String(value || '').trim();
    const m = v.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/i);
    if (m) {
      [r, g, b] = [m[1], m[2], m[3]].map(Number);
      a = m[4] === undefined ? 1 : Number(m[4]);
    } else {
      const h = v.replace('#', '');
      const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h.slice(0, 6), 16) || 0;
      r = (n >> 16) & 255;
      g = (n >> 8) & 255;
      b = n & 255;
      if (h.length === 8) a = parseInt(h.slice(6, 8), 16) / 255;
    }
    this.red = r;
    this.green = g;
    this.blue = b;
    this.alpha = a;
    this.rgb = `${r} ${g} ${b}`;
    this.rgba = `${r} ${g} ${b} / ${a}`;
    this.hex = '#' + [r, g, b].map((x) => Math.round(x).toString(16).padStart(2, '0')).join('');
  }
  toString() {
    return this.alpha === 0 ? 'rgba(0,0,0,0)' : this.hex;
  }
  valueOf() {
    return this.toString();
  }
}

/* ---------- images ---------- */
const localFiles = fs.existsSync(IMG) ? fs.readdirSync(IMG) : [];
const imageCache = new Map();

/* Map a CDN URL or shopify://shop_images/... reference to a downloaded file */
const KNOWN = {
  '4_oz_in_the_line_copy.jpg': 'hero.jpg',
  'SerumAnointingoil.jpg': 'shop-serum.jpg',
  '4_oz_bottle.jpg': 'col-hyssop.jpg',
  '4_oz_box_3.jpg': 'col-rose-of-sharon.jpg',
  '4_oz_box_4.jpg': 'col-spikenard.jpg',
  '4_oz_box_5.jpg': 'col-frankincense-myrrh.jpg',
  '4_oz_box_1.jpg': 'col-gethsemane.jpg',
  '4_oz_box_6.jpg': 'col-latter-rain.jpg',
  '4oz_box.jpg': 'col-lily-of-the-valley.jpg',
  'Screen_Shot_2022-01-07_at_9.28.36_AM.png': 'col-pomegranate.png',
  'Serum_Anointing_oil.jpg': 'col-serums.jpg',
  '4ozF_M.jpg': 'p-frankincense-myrrh.jpg',
  '2ozF_Mbottle.jpg': 'p-frankincense-myrrh-2.jpg',
  '1ozFrankincense_Myrrh.jpg': 'p-frankincense-myrrh-3.jpg',
  'IMG_9234.jpg': 'p-lifestyle.jpg',
  '4ozbottle_1.jpg': 'p-frankincense.jpg',
  '4ozGethsemane.jpg': 'p-gethsemane.jpg',
  '4ozHyssop.jpg': 'p-hyssop.jpg',
  '4ozLatter.jpg': 'p-latter-rain.jpg',
  '4ozlilyofthevalley.jpg': 'p-lily-of-the-valley.jpg',
  '4ozbottle.jpg': 'p-myrrh.jpg',
  '4ozPomegranate.jpg': 'p-pomegranate.jpg',
  '4ozRoseofSharon.jpg': 'p-rose-of-sharon.jpg',
  '4ozSpikenard.jpg': 'p-spikenard.jpg',
  'squalane1oz.jpg': 'p-squalane.jpg',
  'oil-of-gladness-biblical-anointing-joy.jpg': 'a-gladness.jpg',
};
const ARTICLE_PREFIX = { 'ornate-ancient-vessels': 'a-magi.png', 'hands-gently-anointing': 'a-howto.png' };

export function imageFrom(urlOrRef, { width, height, alt } = {}) {
  if (!urlOrRef) return null;
  const base = decodeURIComponent(String(urlOrRef).split('?')[0].split('/').pop());
  let file = KNOWN[base];
  if (!file) for (const [pre, f] of Object.entries(ARTICLE_PREFIX)) if (base.startsWith(pre)) file = f;
  if (!file && localFiles.includes(base)) file = base;
  const key = `${file || base}|${alt || ''}`;
  if (imageCache.has(key)) return imageCache.get(key);
  let w = width, h = height;
  if (file && (!w || !h)) {
    const dims = readDims(path.join(IMG, file));
    if (dims) [w, h] = dims;
  }
  w = w || 1000;
  h = h || 1000;
  const img = {
    _file: file || null,
    src: file ? `/img/${file}` : `/img/missing.svg`,
    width: w,
    height: h,
    aspect_ratio: w / h,
    alt: alt || '',
    id: Math.abs(hash(key)),
    media_type: 'image',
    presentation: { focal_point: '50.0% 50.0%' },
    toString() {
      return this.src;
    },
  };
  img.preview_image = img;
  img.image = img;
  imageCache.set(key, img);
  return img;
}

function hash(s) {
  let h = 0;
  for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) | 0;
  return h;
}

function readDims(file) {
  try {
    const buf = fs.readFileSync(file);
    if (buf[0] === 0x89 && buf[1] === 0x50) return [buf.readUInt32BE(16), buf.readUInt32BE(20)];
    let i = 2;
    while (i < buf.length) {
      if (buf[i] !== 0xff) return null;
      const marker = buf[i + 1];
      const len = buf.readUInt16BE(i + 2);
      if (marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc) return [buf.readUInt16BE(i + 7), buf.readUInt16BE(i + 5)];
      i += 2 + len;
    }
  } catch {}
  return null;
}

/* shopify://shop_images/name.jpg */
export function shopImage(ref) {
  if (!ref) return null;
  return imageFrom(String(ref).replace('shopify://shop_images/', ''));
}

/* ---------- money ---------- */
const cents = (amount) => Math.round(Number(amount || 0) * 100);

/* ---------- product metafields (review data exported from the store) ---------- */
const MF_FILE = path.join(HERE, 'metafields.json');
const allMetafields = fs.existsSync(MF_FILE) ? JSON.parse(fs.readFileSync(MF_FILE, 'utf8')) : {};
function productMetafields(handle) {
  const out = {};
  for (const [ns, fields] of Object.entries(allMetafields[handle] || {})) {
    out[ns] = {};
    for (const [key, f] of Object.entries(fields)) {
      let value = f.value;
      if (f.type === 'json' || f.type === 'rating') value = JSON.parse(value);
      /* Shopify exposes a rating metafield as { rating, scale_min, scale_max } */
      if (f.type === 'rating' && value && value.value !== undefined) value = { rating: Number(value.value), scale_min: Number(value.scale_min), scale_max: Number(value.scale_max) };
      else if (f.type === 'number_integer') value = Number(value);
      out[ns][key] = { type: f.type, value };
    }
  }
  return out;
}

/* ---------- products ---------- */
const productNodes = store.products.nodes;
export const products = productNodes.map((p) => {
  const media = p.media.nodes
    .filter((m) => m.preview && m.preview.image)
    .map((m, i) => {
      const im = imageFrom(m.preview.image.url, { width: m.preview.image.width, height: m.preview.image.height, alt: m.alt || m.preview.image.altText || p.title });
      return { ...im, position: i + 1, media_type: 'image', preview_image: im, id: im.id + i, toString() { return im.src; } };
    });
  /* media we could not download falls back to the product's first photo */
  const first = media.find((m) => m._file) || media[0];
  for (const m of media) if (!m._file && first) Object.assign(m, { src: first.src, _file: first._file, width: first.width, height: first.height, aspect_ratio: first.aspect_ratio });
  const options = p.options.map((o) => o.name);
  const variants = p.variants.nodes.map((v, i) => {
    const opts = v.selectedOptions.map((o) => o.value);
    const variant = {
      id: Number(v.legacyResourceId),
      title: v.title,
      name: `${p.title} - ${v.title}`,
      sku: v.sku || '',
      barcode: '',
      price: cents(v.price),
      compare_at_price: v.compareAtPrice ? cents(v.compareAtPrice) : null,
      available: v.availableForSale,
      inventory_quantity: v.inventoryQuantity,
      inventory_management: 'shopify',
      inventory_policy: 'deny',
      options: opts,
      option1: opts[0] || null,
      option2: opts[1] || null,
      option3: opts[2] || null,
      url: `/products/${p.handle}?variant=${v.legacyResourceId}`,
      featured_image: first || null,
      featured_media: first || null,
      image: first || null,
      requires_shipping: true,
      requires_selling_plan: false,
      selling_plan_allocations: [],
      quantity_rule: { min: 1, max: null, increment: 1 },
      quantity_price_breaks: [],
      unit_price_measurement: null,
      weight: 0,
      taxable: true,
      position: i + 1,
      store_availabilities: [],
      metafields: {},
    };
    variant.toString = () => String(variant.id);
    return variant;
  });
  const prices = variants.map((v) => v.price);
  const firstAvailable = variants.find((v) => v.available) || variants[0];
  const product = {
    id: Number(p.legacyResourceId),
    handle: p.handle,
    title: p.title,
    url: `/products/${p.handle}`,
    vendor: p.vendor,
    type: p.productType,
    tags: p.tags,
    description: p.descriptionHtml,
    content: p.descriptionHtml,
    available: variants.some((v) => v.available),
    price: Math.min(...prices),
    price_min: Math.min(...prices),
    price_max: Math.max(...prices),
    price_varies: Math.min(...prices) !== Math.max(...prices),
    compare_at_price: null,
    compare_at_price_min: 0,
    compare_at_price_max: 0,
    compare_at_price_varies: false,
    variants,
    selected_variant: null,
    selected_or_first_available_variant: firstAvailable,
    first_available_variant: firstAvailable,
    has_only_default_variant: variants.length === 1 && variants[0].title === 'Default Title',
    options,
    options_by_name: {},
    featured_image: first || null,
    featured_media: first || null,
    media,
    images: media,
    gift_card_q: false,
    requires_selling_plan: false,
    selling_plan_groups: [],
    template_suffix: null,
    published_at: p.publishedAt,
    created_at: p.createdAt,
    metafields: productMetafields(p.handle),
    collections: [],
    quantity_price_breaks_configured_q: false,
    status: p.status,
  };
  product.options_with_values = p.options.map((o) => {
    const values = o.values.map((val, vi) => {
      const variant = variants.find((v) => v.options[o.position - 1] === val) || null;
      const ov = {
        name: val,
        id: Math.abs(hash(p.handle + o.name + val)),
        available: variant ? variant.available : false,
        selected: firstAvailable && firstAvailable.options[o.position - 1] === val,
        variant,
        product_url: null,
        swatch: null,
        position: vi + 1,
        toString() {
          return val;
        },
      };
      return ov;
    });
    const opt = {
      name: o.name,
      position: o.position,
      values,
      selected_value: firstAvailable ? firstAvailable.options[o.position - 1] : values[0]?.name,
      toString() {
        return o.name;
      },
    };
    product.options_by_name[o.name.toLowerCase()] = opt;
    return opt;
  });
  return product;
});

/* only published products show on the storefront */
const visible = products.filter((p) => p.status === 'ACTIVE');
export const productsByHandle = Object.fromEntries(products.map((p) => [p.handle, p]));

/* ---------- collections ---------- */
export const collections = {};
for (const c of store.collections.nodes) {
  const items = c.products.nodes.map((n) => productsByHandle[n.handle]).filter((p) => p && p.status === 'ACTIVE');
  const image = c.image ? imageFrom(c.image.url, { width: c.image.width, height: c.image.height, alt: c.image.altText || c.title }) : null;
  const col = {
    id: Number(c.legacyResourceId),
    handle: c.handle,
    title: c.title,
    url: `/collections/${c.handle}`,
    description: c.descriptionHtml,
    image,
    featured_image: image || (items[0] && items[0].featured_image) || null,
    products: items,
    products_count: items.length,
    all_products_count: items.length,
    all_tags: [],
    all_types: [],
    all_vendors: [],
    filters: [],
    sort_by: 'best-selling',
    default_sort_by: 'best-selling',
    sort_options: [],
    template_suffix: null,
    metafields: {},
    current_type: null,
    current_vendor: null,
  };
  collections[c.handle] = col;
  for (const p of items) p.collections.push(col);
}
collections.all = { ...collections['all-products'], handle: 'all', url: '/collections/all', title: 'Products', products: visible, products_count: visible.length, all_products_count: visible.length };
export const collectionsList = Object.assign(Object.values(collections), collections);

/* ---------- menus ---------- */
function link(item, depth = 0) {
  const links = (item.items || []).map((i) => link(i, depth + 1));
  return {
    title: item.title,
    url: item.url.replace('https://mountofolives.co', ''),
    type: String(item.type || '').toLowerCase() + '_link',
    links,
    levels: links.length ? 1 + Math.max(0, ...links.map((l) => l.levels)) : 0,
    current: false,
    active: false,
    child_active: false,
    child_current: false,
    handle: handleize(item.title),
    object: null,
  };
}
export const linklists = {};
for (const m of store.menus.nodes) linklists[m.handle] = { handle: m.handle, title: m.title, levels: 1, links: m.items.map((i) => link(i)) };

/* ---------- blog ---------- */
const blogNode = store.blogs.nodes[0];
export const articles = blogNode.articles.nodes.map((a, i) => {
  const image = a.image ? imageFrom(a.image.url, { width: a.image.width, height: a.image.height, alt: a.image.altText || a.title }) : null;
  return {
    id: 1000 + i,
    handle: a.handle,
    title: a.title,
    url: `/blogs/${blogNode.handle}/${a.handle}`,
    excerpt: a.summary ? `<p>${a.summary}</p>` : '',
    excerpt_or_content: a.summary ? `<p>${a.summary}</p>` : '<p>Read the full article in The Anointing Journal.</p>',
    content: a.summary ? `<p>${a.summary}</p>` : '',
    image,
    published_at: a.publishedAt,
    created_at: a.publishedAt,
    author: (a.author && a.author.name) || 'Mount of Olives',
    tags: a.tags,
    comments: [],
    comments_count: 0,
    comments_enabled_q: false,
    user: { name: (a.author && a.author.name) || 'Mount of Olives', first_name: 'Mount', last_name: 'of Olives', bio: '', image: null },
    metafields: {},
  };
});
/* Shopify orders blog.articles newest first */
articles.sort((a, b) => String(b.published_at).localeCompare(String(a.published_at)));
export const blogs = {
  [blogNode.handle]: {
    id: 1,
    handle: blogNode.handle,
    title: blogNode.title,
    url: `/blogs/${blogNode.handle}`,
    articles,
    articles_count: articles.length,
    all_tags: [...new Set(articles.flatMap((a) => a.tags))],
    tags: [],
    comments_enabled_q: false,
    metafields: {},
  },
};

/* ---------- pages ---------- */
export const pages = Object.fromEntries(store.pages.nodes.map((p) => [p.handle, { handle: p.handle, title: p.title, url: `/pages/${p.handle}`, content: `<p>${p.bodySummary || ''}</p>`, metafields: {} }]));

/* ---------- shop, routes, localization, cart ---------- */
export const shop = {
  name: store.shop.name,
  email: store.shop.email,
  description: store.shop.description,
  url: 'https://mountofolives.co',
  secure_url: 'https://mountofolives.co',
  domain: 'mountofolives.co',
  permanent_domain: 'mount-of-olives-co.myshopify.com',
  money_format: store.shop.currencyFormats.moneyFormat,
  money_with_currency_format: store.shop.currencyFormats.moneyWithCurrencyFormat,
  currency: 'USD',
  locale: 'en',
  customer_accounts_enabled: true,
  customer_accounts_optional: true,
  enabled_payment_types: ['american_express', 'apple_pay', 'diners_club', 'discover', 'google_pay', 'master', 'paypal', 'shopify_pay', 'venmo', 'visa'],
  brand: { metafields: { social_links: {} }, logo: null, square_logo: null },
  policies: [],
  products_count: visible.length,
  collections_count: Object.keys(collections).length,
  metafields: {},
  accepts_gift_cards: true,
};

export const routes = {
  root_url: '/',
  account_url: '/account',
  account_login_url: '/account/login',
  account_logout_url: '/account/logout',
  account_register_url: '/account/register',
  account_addresses_url: '/account/addresses',
  collections_url: '/collections',
  all_products_collection_url: '/collections/all',
  search_url: '/search',
  predictive_search_url: '/search/suggest',
  cart_url: '/cart',
  cart_add_url: '/cart/add',
  cart_change_url: '/cart/change',
  cart_clear_url: '/cart/clear',
  cart_update_url: '/cart/update',
  product_recommendations_url: '/recommendations/products',
};

const US = { iso_code: 'US', name: 'United States', currency: { iso_code: 'USD', symbol: '$', name: 'US Dollar' }, unit_system: 'imperial', popular_q: true };
const EN = { iso_code: 'en', name: 'English', endonym_name: 'English', primary: true, root_url: '/' };
export const localization = { available_countries: [US], available_languages: [EN], country: US, language: EN, market: { id: 1, handle: 'us' } };

export function makeCart(items = []) {
  const total = items.reduce((s, i) => s + i.final_line_price, 0);
  return {
    items,
    item_count: items.reduce((s, i) => s + i.quantity, 0),
    total_price: total,
    items_subtotal_price: total,
    original_total_price: total,
    total_discount: 0,
    empty_q: items.length === 0,
    note: '',
    attributes: {},
    cart_level_discount_applications: [],
    discount_applications: [],
    currency: { iso_code: 'USD', symbol: '$' },
    requires_shipping: true,
    checkout_charge_amount: total,
    duties_included: false,
    taxes_included: false,
  };
}
