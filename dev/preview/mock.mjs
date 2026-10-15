/* Mock store data for the Olivet preview renderer.
   Shapes follow Shopify's Liquid objects closely enough for the theme to render. */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '../..');
const copy = JSON.parse(fs.readFileSync(path.join(ROOT, 'dev/preview/copy.json'), 'utf8'));

/* ---------- helpers ---------- */
export const handleize = (s) =>
  String(s)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ---------- images (generated SVGs) ---------- */
const PALETTE = {
  'frankincense-myrrh-anointing-oil': ['#8C6B3F', '#F1E4CC'],
  frankincense: ['#B08D57', '#F7EEDC'],
  'myrrh-anointing-oil-1': ['#6E4B2E', '#EFE2D2'],
  'gethsemane-anointing-oil-unscented': ['#5E6B4E', '#EAEEE2'],
  'spikenard-anointing-oil': ['#7A5C8A', '#EFE7F2'],
  'pomegranate-anointing-oil': ['#9C3B3B', '#F6E3E0'],
  'lily-of-the-valley': ['#8FA07F', '#F0F3EA'],
  hyssop: ['#4E6E8A', '#E4ECF2'],
  'rose-of-sharon': ['#B86A7A', '#F7E6EA'],
  'latter-rain-anointing-oil': ['#3F6E6A', '#E1EEEC'],
  '100-squalane': ['#2F3F2A', '#F3EFE6'],
};

export function bottleSvg(title, [ink, bg], variant = 0) {
  const label = esc(title.replace(' Anointing Oil', '').replace(' (Unscented)', ''));
  const shift = variant * 18;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 1000" width="800" height="1000">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${bg}"/><stop offset="1" stop-color="${bg}" stop-opacity=".6"/></linearGradient>
    <linearGradient id="glass" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${ink}" stop-opacity=".92"/><stop offset=".5" stop-color="${ink}" stop-opacity=".7"/><stop offset="1" stop-color="${ink}" stop-opacity=".95"/></linearGradient>
  </defs>
  <rect width="800" height="1000" fill="url(#g)"/>
  <ellipse cx="400" cy="860" rx="190" ry="26" fill="${ink}" opacity=".15"/>
  <g transform="translate(${shift} 0)">
    <rect x="330" y="150" width="140" height="70" rx="10" fill="#1F2A1C"/>
    <rect x="345" y="120" width="110" height="40" rx="8" fill="#B08D57"/>
    <path d="M300 230 h200 c20 0 30 12 30 30 v560 c0 30 -20 50 -50 50 h-160 c-30 0 -50 -20 -50 -50 v-560 c0 -18 10 -30 30 -30z" fill="url(#glass)"/>
    <rect x="285" y="420" width="230" height="260" rx="6" fill="#F7F3EC"/>
    <text x="400" y="505" font-family="Georgia, serif" font-size="26" text-anchor="middle" fill="#1F2A1C" letter-spacing="2">MOUNT OF OLIVES</text>
    <line x1="330" y1="528" x2="470" y2="528" stroke="#B08D57" stroke-width="2"/>
    <text x="400" y="582" font-family="Georgia, serif" font-size="30" font-style="italic" text-anchor="middle" fill="#1F2A1C">${label}</text>
    <text x="400" y="620" font-family="Helvetica, Arial, sans-serif" font-size="14" text-anchor="middle" fill="#5F6A58" letter-spacing="3">THE ANOINTING OIL</text>
    <text x="400" y="660" font-family="Helvetica, Arial, sans-serif" font-size="13" text-anchor="middle" fill="#5F6A58">2 FL OZ · 60 mL</text>
  </g>
</svg>`;
}

export function sceneSvg(name, [ink, bg], w = 1600, h = 1200) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">
  <defs><radialGradient id="r" cx=".3" cy=".3" r=".9"><stop offset="0" stop-color="${bg}"/><stop offset="1" stop-color="${ink}" stop-opacity=".55"/></radialGradient></defs>
  <rect width="${w}" height="${h}" fill="url(#r)"/>
  <g fill="none" stroke="#B08D57" stroke-width="3" opacity=".7" transform="translate(${w * 0.55} ${h * 0.25})">
    <path d="M0 0 C 60 120, 120 220, 90 420"/>
    <path d="M30 80 c -70 -10 -120 20 -140 70 c 60 10 110 -10 140 -70z"/>
    <path d="M60 170 c 70 -10 120 20 140 70 c -60 10 -110 -10 -140 -70z"/>
    <path d="M70 250 c -70 -10 -120 20 -140 70 c 60 10 110 -10 140 -70z"/>
    <path d="M85 330 c 70 -10 120 20 140 70 c -60 10 -110 -10 -140 -70z"/>
    <ellipse cx="-20" cy="130" rx="16" ry="24" fill="#2F3F2A"/>
    <ellipse cx="120" cy="300" rx="16" ry="24" fill="#2F3F2A"/>
  </g>
  <text x="60" y="${h - 60}" font-family="Helvetica, Arial, sans-serif" font-size="28" fill="#F7F3EC" opacity=".8">${esc(name)}</text>
</svg>`;
}

/* ---------- images registry ---------- */
export const images = {};
export function makeImage(key, { width, height, alt, svg }) {
  const img = {
    id: Object.keys(images).length + 1,
    src: `img/${key}.svg`,
    width,
    height,
    aspect_ratio: width / height,
    alt: alt || '',
    media_type: 'image',
    position: 1,
    preview_image: null,
    _svg: svg,
    toString() {
      return this.src;
    },
  };
  img.preview_image = img;
  images[key] = img;
  return img;
}

export function writeImages(outDir) {
  const dir = path.join(outDir, 'img');
  fs.mkdirSync(dir, { recursive: true });
  for (const [key, img] of Object.entries(images)) fs.writeFileSync(path.join(dir, `${key}.svg`), img._svg);
}

/* ---------- products ---------- */
const SIZES = [
  { title: '1 ounce (30 ml)', price: 1698 },
  { title: '2 ounce (60 ml)', price: 2498 },
  { title: '4 ounce (118 ml)', price: 3498 },
];

class OptionValue {
  constructor(name, available, variant) {
    this.name = name;
    this.available = available;
    this.variant = variant;
    this.swatch = null;
    this.selected = false;
  }
  toString() {
    return this.name;
  }
}

export const products = copy.products.products.map((p, i) => {
  const handle = p.handle;
  const pal = PALETTE[handle] || ['#2F3F2A', '#F3EFE6'];
  const media = [0, 1, 2].map((v) => {
    const img = makeImage(`${handle}-${v + 1}`, { width: 800, height: 1000, alt: `${p.title} bottle`, svg: bottleSvg(p.title, pal, v) });
    img.position = v + 1;
    img.id = 1000 + i * 10 + v;
    return img;
  });
  const isSqualane = handle === '100-squalane';
  const sizes = isSqualane ? [{ title: '4 ounce (118 ml)', price: 2398 }] : SIZES;
  const variants = sizes.map((s, vi) => ({
    id: 40000 + i * 10 + vi,
    title: isSqualane ? 'Default Title' : s.title,
    price: s.price,
    compare_at_price: i === 0 && vi === 0 ? 1998 : null,
    available: !(i === 3 && vi === 2),
    option1: isSqualane ? 'Default Title' : s.title,
    option2: null,
    option3: null,
    options: [isSqualane ? 'Default Title' : s.title],
    featured_media: media[Math.min(vi, 2)],
    featured_image: media[Math.min(vi, 2)],
    sku: `MOO-${handle.slice(0, 4).toUpperCase()}-${vi + 1}`,
    inventory_management: 'shopify',
    inventory_quantity: i === 3 && vi === 2 ? 0 : 12,
    inventory_policy: 'deny',
    requires_shipping: true,
    unit_price: null,
    unit_price_measurement: null,
    url: `/products/${handle}?variant=${40000 + i * 10 + vi}`,
    selling_plan_allocations: [],
    quantity_rule: { min: 1, max: null, increment: 1 },
    weight: 120,
    weight_unit: 'g',
  }));
  const firstAvailable = variants.find((v) => v.available) || variants[0];
  const optionValues = variants.map((v) => new OptionValue(v.option1, v.available, v));
  if (optionValues[0]) optionValues[0].selected = true;
  const prices = variants.map((v) => v.price);
  const prod = {
    id: 7000 + i,
    handle,
    title: p.title,
    url: `/products/${handle}`,
    type: 'Anointing oil',
    vendor: 'Mount of Olives',
    // A stand-in for the merchant's own description (kept distinct from the meaning/botanical blocks)
    description: `<p>${esc(p.oneLiner)}</p><p>Each bottle is blended, tested, and bottled by hand in Richmond, Texas. Apply a few drops after the shower or at the pulse points during prayer.</p>`,
    content: '',
    featured_media: media[0],
    featured_image: media[0],
    media,
    images: media,
    variants,
    selected_or_first_available_variant: firstAvailable,
    selected_variant: null,
    first_available_variant: firstAvailable,
    has_only_default_variant: isSqualane,
    options: ['Size'],
    options_with_values: isSqualane ? [] : [{ name: 'Size', position: 1, values: optionValues, selected_value: firstAvailable.option1 }],
    price: Math.min(...prices),
    price_min: Math.min(...prices),
    price_max: Math.max(...prices),
    price_varies: Math.min(...prices) !== Math.max(...prices),
    compare_at_price: variants[0].compare_at_price,
    compare_at_price_min: variants[0].compare_at_price || 0,
    compare_at_price_max: variants[0].compare_at_price || 0,
    compare_at_price_varies: false,
    available: true,
    tags: ['anointing-oil', p.themeWord.toLowerCase()],
    collections: [],
    metafields: { custom: {} },
    gift_card_q: false,
    quantity_price_breaks_configured_q: false,
    requires_selling_plan: false,
    selling_plan_groups: [],
    template_suffix: null,
    created_at: '2024-02-01',
    published_at: '2024-02-01',
    _copy: p,
    object_type: 'product',
  };
  prod.description = prod.description;
  return prod;
});

/* ---------- collections ---------- */
const colImage = makeImage('collection-all', { width: 1600, height: 1200, alt: 'All anointing oils', svg: sceneSvg('All anointing oils', ['#2F3F2A', '#E7EBE1']) });
const colImage2 = makeImage('collection-nine', { width: 1600, height: 1200, alt: 'Nine biblical blends', svg: sceneSvg('Nine biblical blends', ['#8C6B3F', '#F1E4CC']) });

const priceFilter = {
  label: 'Price',
  param_name: 'filter.v.price',
  type: 'price_range',
  presentation: 'text',
  range_max: 3498,
  min_value: { param_name: 'filter.v.price.gte', value: null },
  max_value: { param_name: 'filter.v.price.lte', value: null },
  active_values: [],
  url_to_remove: '/collections/all',
  values: [],
};
const sizeFilter = {
  label: 'Size',
  param_name: 'filter.v.option.size',
  type: 'list',
  presentation: 'text',
  active_values: [],
  inactive_values: [],
  url_to_remove: '/collections/all',
  values: SIZES.map((s) => ({ label: s.title, value: s.title, param_name: 'filter.v.option.size', count: 10, active: false, url_to_add: '/collections/all?filter=1', url_to_remove: '/collections/all', swatch: null })),
};

export const collections = {
  all: {
    id: 1,
    handle: 'all',
    title: copy.products.collections.all.title,
    description: `<p>${esc(copy.products.collections.all.description)}</p>`,
    url: '/collections/all',
    image: colImage,
    featured_image: colImage,
    products,
    products_count: products.length,
    all_products_count: products.length,
    filters: [sizeFilter, priceFilter],
    sort_by: 'manual',
    default_sort_by: 'manual',
    sort_options: [['manual', 'Featured'], ['best-selling', 'Best selling'], ['title-ascending', 'Alphabetically, A-Z'], ['title-descending', 'Alphabetically, Z-A'], ['price-ascending', 'Price, low to high'], ['price-descending', 'Price, high to low'], ['created-ascending', 'Date, old to new'], ['created-descending', 'Date, new to old']].map(([value, name]) => ({ value, name })),
    all_tags: ['anointing-oil'],
    current_type: null,
    current_vendor: null,
  },
  'nine-biblical-oil-blends': {
    id: 2,
    handle: 'nine-biblical-oil-blends',
    title: copy.products.collections.nineBlends.title,
    description: `<p>${esc(copy.products.collections.nineBlends.description)}</p>`,
    url: '/collections/nine-biblical-oil-blends',
    image: colImage2,
    featured_image: colImage2,
    products: products.slice(0, 9),
    products_count: 9,
    all_products_count: 9,
    filters: [sizeFilter, priceFilter],
    sort_by: 'manual',
    default_sort_by: 'manual',
    sort_options: [],
    all_tags: [],
  },
};
collections['frontpage'] = { ...collections.all, handle: 'frontpage', title: 'Home page', url: '/collections/frontpage' };
/* Shopify's `collections` global is iterable AND indexable by handle */
export const collectionsList = Object.assign([collections.all, collections['nine-biblical-oil-blends']], collections);
products.forEach((p) => (p.collections = [collections.all]));

/* ---------- menus ---------- */
const link = (title, url, links = []) => ({ title, url, links, child_active: false, active: false, current: false, type: 'http_link', levels: links.length ? 1 : 0, handle: handleize(title) });
export const linklists = {
  'main-menu': {
    handle: 'main-menu',
    title: 'Main menu',
    levels: 2,
    links: [
      link('Shop', '/collections/all', [
        link('All anointing oils', '/collections/all'),
        link('Nine biblical blends', '/collections/nine-biblical-oil-blends'),
        link('100% Squalane Oil', '/products/100-squalane'),
        link('Frankincense & Myrrh', '/products/frankincense-myrrh-anointing-oil'),
        link('Spikenard', '/products/spikenard-anointing-oil'),
      ]),
      link('Our science', '/pages/our-science'),
      link('About', '/pages/about-us'),
      link('The Anointing Journal', '/blogs/the-anointing-journal'),
      link('Contact', '/pages/contact'),
    ],
  },
  footer: {
    handle: 'footer',
    title: 'Footer menu',
    levels: 1,
    links: [link('Search', '/search'), link('About us', '/pages/about-us'), link('Our science', '/pages/our-science'), link('Contact', '/pages/contact'), link('Shipping policy', '/policies/shipping-policy'), link('Refund policy', '/policies/refund-policy')],
  },
};
linklists['main-menu'].links[0].links.forEach((l) => (l.levels = 0));

/* ---------- pages, blog ---------- */
export const pages = {
  'about-us': { id: 1, object_type: 'page', handle: 'about-us', title: 'About Mount of Olives', url: '/pages/about-us', content: copy.pages.about.sections.map((s) => `<h2>${esc(s.heading)}</h2>${s.body.map((b) => `<p>${esc(b)}</p>`).join('')}`).join(''), template_suffix: 'about' },
  'our-science': { id: 2, handle: 'our-science', title: 'Our Science', url: '/pages/our-science', content: copy.pages.science.sections.map((s) => `<h2>${esc(s.heading)}</h2>${s.body.map((b) => `<p>${esc(b)}</p>`).join('')}`).join(''), template_suffix: 'science' },
  contact: { id: 3, handle: 'contact', title: 'Contact', url: '/pages/contact', content: `<p>${esc(copy.pages.contact.intro)}</p>`, template_suffix: 'contact' },
};

const articleImg = (i) => makeImage(`article-${i}`, { width: 1600, height: 1067, alt: 'Journal', svg: sceneSvg('The Anointing Journal', [['#2F3F2A', '#E7EBE1'], ['#8C6B3F', '#F1E4CC'], ['#5E6B4E', '#EAEEE2']][i % 3]) });
const articleTitles = ['What Is Anointing Oil? A Biblical Guide to Its Meaning and Purpose', 'Hyssop: The Biblical Herb of Purification and Cleansing', 'Frankincense & Myrrh: Sacred Biblical Gifts and Their Meaning', 'Not all olives are created equal', 'A Brief History of Anointing Oil in Christianity'];
export const articles = articleTitles.map((t, i) => ({
  id: 100 + i,
  title: t,
  handle: handleize(t),
  url: `/blogs/the-anointing-journal/${handleize(t)}`,
  author: 'Mount of Olives',
  user: { name: 'Mount of Olives' },
  published_at: `2026-0${(i % 9) + 1}-1${i}T10:00:00Z`,
  created_at: `2026-0${(i % 9) + 1}-1${i}T10:00:00Z`,
  image: i === 3 ? null : articleImg(i),
  excerpt: 'Anointing oil runs through Scripture, from the tabernacle in Exodus to the house at Bethany. Here is what it meant then, and how it is used in prayer today.',
  excerpt_or_content: 'Anointing oil runs through Scripture, from the tabernacle in Exodus to the house at Bethany. Here is what it meant then, and how it is used in prayer today.',
  content: `<p>${esc(copy.home.faq[0].a)}</p><h2>In the tabernacle</h2><p>${esc(copy.pages.about.sections[1].body[0])}</p><blockquote>${esc(copy.home.scripture.quote)}<br>— ${esc(copy.home.scripture.reference)}</blockquote><p>${esc(copy.pages.science.sections[0].body[0])} ${esc(copy.pages.science.sections[0].body[1])}</p><h2>How it is used today</h2><p>${esc(copy.home.faq[1].a)}</p>`,
  tags: ['Scripture', 'Botanicals'],
  object_type: 'article',
  comments: [],
  comments_count: 0,
  comments_enabled_q: true,
  moderated_q: true,
}));
export const blogs = {
  'the-anointing-journal': { id: 1, handle: 'the-anointing-journal', title: 'The Anointing Journal', url: '/blogs/the-anointing-journal', articles, articles_count: articles.length, all_tags: ['Scripture', 'Botanicals'], comments_enabled_q: true, moderated_q: true, previous_article: null, next_article: null },
};
articles.forEach((a, i) => {
  a.blog = blogs['the-anointing-journal'];
});

/* ---------- cart ---------- */
export function makeCart(empty = false) {
  const items = empty
    ? []
    : [
        { product: products[0], variant: products[0].variants[1], quantity: 2 },
        { product: products[4], variant: products[4].variants[0], quantity: 1 },
        { product: products[10], variant: products[10].variants[0], quantity: 1 },
      ].map((l, i) => ({
        id: l.variant.id,
        key: `${l.variant.id}:abc${i}`,
        index: i,
        quantity: l.quantity,
        title: `${l.product.title}${l.variant.title !== 'Default Title' ? ' - ' + l.variant.title : ''}`,
        product: l.product,
        product_id: l.product.id,
        product_title: l.product.title,
        variant: l.variant,
        variant_id: l.variant.id,
        variant_title: l.variant.title === 'Default Title' ? null : l.variant.title,
        options_with_values: l.variant.title === 'Default Title' ? [] : [{ name: 'Size', value: l.variant.title }],
        url: l.variant.url,
        image: l.variant.featured_media,
        price: l.variant.price,
        original_price: l.variant.price,
        final_price: l.variant.price,
        line_price: l.variant.price * l.quantity,
        original_line_price: l.variant.price * l.quantity,
        final_line_price: l.variant.price * l.quantity,
        properties: {},
        selling_plan_allocation: null,
        line_level_discount_allocations: [],
        discounts: [],
        unit_price: null,
        unit_price_measurement: null,
        sku: l.variant.sku,
        vendor: 'Mount of Olives',
        requires_shipping: true,
        gift_card: false,
        taxable: true,
        parent_relationship: null,
      }));
  const total = items.reduce((s, i) => s + i.final_line_price, 0);
  return {
    items,
    item_count: items.reduce((s, i) => s + i.quantity, 0),
    total_price: total,
    items_subtotal_price: total,
    original_total_price: total,
    total_discount: 0,
    currency: { iso_code: 'USD', symbol: '$', name: 'United States Dollar' },
    note: '',
    attributes: {},
    cart_level_discount_applications: [],
    discount_applications: [],
    requires_shipping: true,
    taxes_included: false,
    duties_included: false,
    empty_q: items.length === 0,
    checkout_charge_amount: total,
  };
}

/* ---------- shop, routes, request ---------- */
export const shop = {
  name: 'Mount of Olives',
  email: 'info@mountofolives.co',
  description: copy.home.hero.subheading,
  domain: 'mountofolives.co',
  permanent_domain: 'mount-of-olives.myshopify.com',
  url: 'https://mountofolives.co',
  secure_url: 'https://mountofolives.co',
  money_format: '${{amount}}',
  money_with_currency_format: '${{amount}} USD',
  currency: 'USD',
  enabled_currencies: [{ iso_code: 'USD', symbol: '$' }],
  enabled_payment_types: ['visa', 'master', 'american_express', 'discover', 'paypal', 'shop_pay', 'apple_pay', 'google_pay'],
  customer_accounts_enabled: true,
  customer_accounts_optional: true,
  taxes_included: false,
  shipping_policy: { title: 'Shipping policy', url: '/policies/shipping-policy', body: '' },
  refund_policy: { title: 'Refund policy', url: '/policies/refund-policy', body: '' },
  privacy_policy: { title: 'Privacy policy', url: '/policies/privacy-policy', body: '' },
  terms_of_service: { title: 'Terms of service', url: '/policies/terms-of-service', body: '' },
  policies: [
    { title: 'Shipping policy', url: '/policies/shipping-policy' },
    { title: 'Refund policy', url: '/policies/refund-policy' },
    { title: 'Privacy policy', url: '/policies/privacy-policy' },
    { title: 'Terms of service', url: '/policies/terms-of-service' },
  ],
  address: { address1: '10193 W Grand Pkwy S, Ste. 103-225', city: 'Richmond', province: 'Texas', province_code: 'TX', zip: '77407', country: 'United States', summary: 'Richmond, Texas' },
  phone: '(713) 364-2010',
  brand: { short_description: copy.home.hero.subheading, slogan: copy.home.footer.tagline, logo: null, square_logo: null, colors: {} },
  checkout: { guest_login: true },
  published_locales: [{ iso_code: 'en', name: 'English', primary: true }],
  types: ['Anointing oil'],
  vendors: ['Mount of Olives'],
  products_count: products.length,
  collections_count: 2,
};

export const routes = {
  root_url: '/',
  account_url: '/account',
  account_login_url: '/account/login',
  account_logout_url: '/account/logout',
  account_recover_url: '/account/recover',
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

export const localization = {
  available_countries: [
    { iso_code: 'US', name: 'United States', currency: { iso_code: 'USD', symbol: '$' } },
    { iso_code: 'CA', name: 'Canada', currency: { iso_code: 'CAD', symbol: '$' } },
  ],
  available_languages: [{ iso_code: 'en', endonym_name: 'English', name: 'English', primary: true }],
  country: { iso_code: 'US', name: 'United States', currency: { iso_code: 'USD', symbol: '$' } },
  language: { iso_code: 'en', endonym_name: 'English', name: 'English', primary: true },
  market: { handle: 'us', id: 1 },
};

export const customer = {
  id: 1,
  first_name: 'Aleksandra',
  last_name: 'Wiśniewska-Kowalczyk',
  name: 'Aleksandra Wiśniewska-Kowalczyk',
  email: 'aleksandra.wisniewska-kowalczyk@northwind-industries-holdings.example.com',
  phone: '(713) 555-0199',
  accepts_marketing: true,
  orders_count: 2,
  total_spent: 8794,
  default_address: { id: 1, first_name: 'Aleksandra', last_name: 'Wiśniewska-Kowalczyk', address1: '10193 W Grand Pkwy S', address2: 'Ste. 103-225', city: 'Richmond', province: 'Texas', province_code: 'TX', zip: '77407', country: 'United States', country_code: 'US', phone: '(713) 555-0199', company: '', name: 'Aleksandra Wiśniewska-Kowalczyk', summary: '10193 W Grand Pkwy S, Richmond, Texas', url: '/account/addresses/1', street: '10193 W Grand Pkwy S, Ste. 103-225' },
  addresses: [],
  addresses_count: 2,
  orders: [],
  tags: [],
  has_account: true,
};
customer.addresses = [customer.default_address, { ...customer.default_address, id: 2, address1: '1 Short St', address2: '', city: 'Houston', zip: '77002', url: '/account/addresses/2', summary: '1 Short St, Houston, Texas', street: '1 Short St' }];
export const orders = [
  {
    id: 1,
    name: '#1042',
    order_number: 1042,
    customer_url: '/account/orders/1',
    created_at: '2026-09-28T14:12:00Z',
    cancelled: false,
    cancelled_at: null,
    cancel_reason: null,
    cancel_reason_label: null,
    financial_status: 'paid',
    financial_status_label: 'Paid',
    fulfillment_status: 'fulfilled',
    fulfillment_status_label: 'Fulfilled',
    total_price: 5996,
    subtotal_price: 5996,
    total_discounts: 0,
    shipping_price: 0,
    tax_price: 0,
    total_duties: null,
    total_refunded_amount: 0,
    discount_applications: [],
    shipping_methods: [{ title: 'Standard', price: 0 }],
    tax_lines: [],
    billing_address: customer.default_address,
    shipping_address: customer.default_address,
    line_items: makeCart().items.slice(0, 2).map((i) => ({ ...i, fulfillment: { tracking_url: 'https://example.com/track', tracking_number: '1Z999', tracking_company: 'UPS', created_at: '2026-09-29T10:00:00Z' }, successfully_fulfilled_quantity: i.quantity })),
    line_items_subtotal_price: 5996,
    transactions: [],
    note: null,
  },
  {
    id: 2,
    name: '#1031',
    order_number: 1031,
    customer_url: '/account/orders/2',
    created_at: '2026-06-02T09:30:00Z',
    cancelled: false,
    financial_status: 'paid',
    financial_status_label: 'Paid',
    fulfillment_status: 'unfulfilled',
    fulfillment_status_label: 'Unfulfilled',
    total_price: 2398,
    subtotal_price: 2398,
    total_discounts: 0,
    shipping_price: 599,
    tax_price: 0,
    discount_applications: [],
    shipping_methods: [{ title: 'Standard', price: 599 }],
    tax_lines: [],
    billing_address: customer.default_address,
    shipping_address: customer.default_address,
    line_items: makeCart().items.slice(2).map((i) => ({ ...i, fulfillment: null })),
    line_items_subtotal_price: 2398,
    transactions: [],
  },
];
customer.orders = orders;

/* ---------- fonts & colors ---------- */
export function fontFromHandle(handle) {
  const m = String(handle).match(/^(.*)_([ni])(\d)$/);
  const familyHandle = m ? m[1] : String(handle);
  const style = m && m[2] === 'i' ? 'italic' : 'normal';
  const weight = m ? Number(m[3]) * 100 : 400;
  const family = familyHandle.split('_').map((w) => w[0].toUpperCase() + w.slice(1)).join(' ');
  const serif = /garamond|playfair|cormorant|baskerville|lora|crimson|fraunces|serif/i.test(family);
  return {
    family,
    fallback_families: serif ? 'Georgia, serif' : 'system-ui, sans-serif',
    weight,
    style,
    system_q: false,
    baseline_ratio: 0.5,
    _handle: familyHandle,
    toString() {
      return this.family;
    },
  };
}

export class Color {
  constructor(hex) {
    this.hex = hex;
    const h = hex.replace('#', '');
    const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
    this.red = (n >> 16) & 255;
    this.green = (n >> 8) & 255;
    this.blue = n & 255;
    this.alpha = 1;
    this.rgb = `${this.red}, ${this.green}, ${this.blue}`;
    this.rgba = `${this.rgb}, 1`;
  }
  toString() {
    return this.hex;
  }
}

export { copy, ROOT };
