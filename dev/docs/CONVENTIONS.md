# Olivet — Mount of Olives Shopify theme: conventions for every file

Theme root: /home/user/Jeffrey-  (Shopify Online Store 2.0 theme at repo root).
Directories: layout/ templates/ templates/customers/ sections/ snippets/ assets/ config/ locales/

## Design intent (from emilkowalski/skills: emil-design-eng, animate, mobile-native, apple-design, break-ui, animation-performance)
- Quiet, editorial, reverent. Warm ivory page, deep olive ink, a little gold. Serif display headings (Cormorant Garamond), DM Sans body.
- Motion is sparse and purposeful. Every animation names its purpose (feedback / spatial consistency / state / prevent jarring / marketing explanation). Nothing animates on keyboard shortcuts.

## CSS tokens (defined in assets/base.css on :root — USE THEM, never invent parallel values)
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);        /* enter/exit, default */
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);    /* on-screen movement */
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);     /* drawers/sheets */
--dur-press: 120ms;  --dur-fast: 160ms;  --dur-base: 200ms;  --dur-slow: 260ms;  --dur-drawer: 400ms;  --dur-reveal: 500ms;
Colors (rgb triplets, use rgb(var(--c-bg)) or rgba(var(--c-ink), .6)):
--c-bg, --c-bg-2 (sage surface), --c-ink, --c-ink-2 (muted), --c-line (border), --c-accent (olive), --c-accent-ink, --c-gold, --c-dark-bg, --c-dark-ink
Color schemes come from settings (color_scheme_group); sections wrap content in `<div class="color-{{ section.settings.color_scheme }}">` which sets the --c-* vars.
Typography: --font-heading, --font-body; type scale classes: .h0 .h1 .h2 .h3 .h4 .eyebrow .lead .body .small .caption
Spacing: --space-1 (4px) … --space-12 (96px); --gutter: clamp(16px, 4vw, 40px); --page-max: 1320px; --section-y: clamp(56px, 8vw, 112px)
Radii: --r-sm 6px, --r-md 10px, --r-lg 16px, --r-pill 999px
Shadows: --shadow-sm, --shadow-md, --shadow-lg (semi-transparent, never solid borders for elevation)
Layout helpers: .page-width, .section, .section--tight, .grid, .grid--2, .grid--3, .grid--4, .stack, .cluster, .visually-hidden, .skip-link

## Hard motion rules (review will block violations)
1. Only `transform`, `opacity` (and `clip-path`, `filter` in moderation) animate. Never width/height/margin/padding/top/left. Accordions use `grid-template-rows: 0fr → 1fr` (the one tolerated exception).
2. Never `transition: all`. List properties. Never `ease-in`. Never built-in `ease-out` on a deliberate animation: use var(--ease-out).
3. Never `scale(0)`; entrances start at scale(.96–.98) + opacity 0, or translateY(8–12px) + opacity 0.
4. UI durations ≤ 300ms except drawers (≤ 500ms) and marketing reveals (≤ 600ms). Exits faster than entrances.
5. Every pressable: `.btn:active{transform:scale(.97)}` with `transition: transform var(--dur-press) var(--ease-out)`; feedback on pointer-down (CSS :active).
6. ALL :hover rules live inside `@media (hover: hover) and (pointer: fine) { … }`.
7. `@media (prefers-reduced-motion: reduce)`: remove transform motion, keep opacity/color.
8. Popovers/menus: `transform-origin` at the trigger (top center for header dropdown/search). Modals centered.
9. Stagger entering lists with `--i` index: `transition-delay: calc(var(--i, 0) * 50ms)`, max ~8 items.
10. Transitions (not keyframes) for anything rapidly re-triggered (cart line updates, toggles).
11. Scroll reveal: elements get `data-reveal` (optionally `style="--i: n"`); JS adds `.is-visible`. CSS: `.js [data-reveal]{opacity:0;transform:translateY(12px);transition:opacity var(--dur-reveal) var(--ease-out),transform var(--dur-reveal) var(--ease-out)} .js [data-reveal].is-visible{opacity:1;transform:none}`. Without JS everything is visible. Never put data-reveal on the hero's first heading or on anything above the fold that the user must read immediately… EXCEPT the hero uses `@starting-style` entrance (no JS).

## Mobile-native baseline (already in layout/base.css; don't undo)
viewport-fit=cover + interactive-widget=resizes-content; theme-color per scheme; -webkit-tap-highlight-color: transparent; -webkit-text-size-adjust:100%; inputs ≥16px; controls get touch-action: manipulation + user-select:none; drawers use 100dvh + env(safe-area-inset-*); hero uses svh; drawers/sheets use overscroll-behavior: contain; carousels use scroll-snap + touch-action: pan-y.

## Liquid conventions
- Sections: `{% schema %}` with literal English labels (no t: keys in schema). Every section wraps in `<div class="section color-{{ section.settings.color_scheme }}" id="section-{{ section.id }}">` unless it is header/footer/drawer. Provide `padding_top`/`padding_bottom` range settings only where useful; most sections use `.section` default spacing and expose a `spacing` select (default|tight|none).
- Storefront strings go through locales: `{{ 'cart.empty' | t }}`; add every key you use to locales/en.default.json (it is a shared file: ADD keys, never remove; keep valid JSON).
- Icons: `{% render 'icon', name: 'cart', size: 20 %}` (snippets/icon.liquid has: cart, bag, search, close, menu, chevron-down, chevron-right, chevron-left, arrow-right, arrow-up-right, plus, minus, check, user, leaf, drop, flask, map-pin, mail, phone, instagram, facebook, tiktok, youtube, pinterest, x, star, info, error, success, filter, lock, external).
- Images: `{% render 'image', image: img, sizes: '(min-width: 990px) 50vw, 100vw', widths: '400, 600, 800, 1200, 1600', class: 'media__img', loading: 'lazy', ratio: '4/5' %}` (snippets/image.liquid uses image_url + image_tag; `ratio` sets aspect-ratio via the wrapper). Placeholders: `{{ 'product-1' | placeholder_svg_tag: 'placeholder' }}`.
- Buttons: `.btn .btn--primary|--secondary|--ghost|--dark .btn--full .btn--sm`. Links: `.link` (underline on hover gated), `.link--arrow`.
- Product cards: `{% render 'card-product', product: product, index: forloop.index0, show_secondary_image: true, sizes: '...' %}`.
- Prices: `{% render 'price', product: product, use_variant: true, show_badges: true %}`.
- Money: `{{ price | money }}` (shop format). Never hardcode currency symbols.
- Accessibility: focus-visible rings (`:focus-visible{outline:2px solid rgb(var(--c-accent));outline-offset:3px}`), aria-expanded on toggles, dialogs with role=dialog aria-modal, focus trapped (window.Olivet.trapFocus / releaseFocus), Escape closes.
- Forms: Shopify `{% form %}` tags; inputs `.field .field__input .field__label`; `.form-status` for errors (role=alert).
- JS: vanilla, custom elements where stateful. Shared helpers on `window.Olivet` (assets/theme.js): `Olivet.trapFocus(el)`, `Olivet.releaseFocus()`, `Olivet.getFocusable(el)`, `Olivet.pubsub.subscribe(name, cb)` / `publish(name, data)`, events: 'cart:updated', 'variant:changed', `Olivet.fetchConfig(type)`, `Olivet.debounce(fn, ms)`, `Olivet.prefersReducedMotion()`. Drawers extend `Olivet.Drawer` class contract: element has `[data-drawer]`, open via `el.open(trigger)`, close via `el.close()`, uses class `.is-open` on the element and `body.drawer-open` on body; panel transitions on `transform`, backdrop on `opacity`.
- Cart: routes in `window.Olivet.routes` {cart_add_url, cart_change_url, cart_update_url, cart_url, predictive_search_url, root_url}. Add to cart posts FormData to cart_add_url with `sections=cart-drawer,cart-icon-bubble` and then calls `document.querySelector('cart-drawer').renderContents(response)`; the drawer re-renders from `response.sections['cart-drawer']` by replacing `#CartDrawer-Inner` and the bubble by replacing `#cart-icon-bubble`.
- Never use `{{ 'x' | asset_url | stylesheet_tag }}` per-section CSS files; all CSS lives in assets/base.css, assets/components.css, assets/templates.css (loaded in layout). Section-specific CSS goes in templates.css under a comment header `/* === section: name === */`.
- Keep Liquid tidy: `{%- -%}` whitespace control, 2-space indentation, `{% liquid %}` blocks for logic.

## Break-ui expectations (design for the worst case from the start)
- Product titles up to ~70 chars wrap to 2 lines (line-clamp: 2) on cards; prices never truncate; "From $16.98" vs "$23.98" both align (tabular-nums).
- Empty states: empty cart, empty collection, no search results, no blog posts, no image on product — all designed, never blank.
- Menus with 1 or 12 items; footer with 0 social links; announcement text up to 90 chars (wraps, never clips).
- Long emails in account pages: overflow-wrap:anywhere. Count of 1: pluralization via locale `one`/`other`.

## Output routing for build agents (IMPORTANT — several agents work at once)
- Write Liquid/JSON/JS files straight into the theme at the paths you were assigned. Never touch files not assigned to you (except read).
- CSS: do NOT edit assets/*.css. Write your CSS to `/tmp/claude-0/-home-user-Jeffrey-/4d0ac68c-723a-59d5-903f-722bcbe696f5/scratchpad/css/<your-group>.css` (one file). The integrator concatenates all of them into assets/templates.css in the layout. Prefix every class with your section's block name (BEM: `.hero`, `.hero__title`, `.hero--tall`) so files never collide. You MAY use any class already defined in assets/base.css and assets/components.css (read them first; reuse `.btn`, `.media`, `.card`, `.price`, `.accordion`, `.drawer__*`, `.scripture`, `.empty-state`, `.eyebrow`, `.h1…h5`, `.lead`, `.section`, `.page-width`, `.grid`, `.stack`, `.cluster`).
- Locales: do NOT edit locales/en.default.json. Write any NEW keys you need as a nested JSON object to `/tmp/claude-0/-home-user-Jeffrey-/4d0ac68c-723a-59d5-903f-722bcbe696f5/scratchpad/locales/<your-group>.json`; the integrator deep-merges them. Read locales/en.default.json first and reuse existing keys wherever one fits.
- Brand copy lives in `/tmp/claude-0/-home-user-Jeffrey-/4d0ac68c-723a-59d5-903f-722bcbe696f5/scratchpad/brand/copy.json` (home / products / pages). Use it verbatim for section defaults and template JSON. Brand facts in `.../scratchpad/brand/content.md`.
- Reference: Shopify Dawn is cloned at `/tmp/claude-0/-home-user-Jeffrey-/4d0ac68c-723a-59d5-903f-722bcbe696f5/scratchpad/ref/dawn` — use it ONLY to confirm Liquid objects/filters/form tags and the Section Rendering API. Do not copy its markup or CSS; this theme has its own design.
- Validate: run `cd /home/user/Jeffrey- && shopify theme check --path . -o json 2>/dev/null | head -c 20000` (or `-o text`) and fix every offense in YOUR files only (ignore offenses in files you don't own, including missing-asset warnings for assets/templates.css which the integrator creates). Also run `node --check` on any JS you write.
- Section schema rules: `"name"` ≤ 25 chars; every section that can be added to templates gets `"presets": [{ "name": "…" }]` except main-* sections; `"disabled_on": { "groups": ["header", "footer"] }` on body sections; use `"tag": "section"` only if you want the wrapper tag; `"class"` on schema may be used (`"class": "section-wrapper"`).

## JS contracts between groups (implement exactly)
- `window.Olivet` (assets/theme.js) exposes: pubsub, EVENTS {cartUpdated:'cart:updated', cartError:'cart:error', variantChanged:'variant:changed', drawerOpened, drawerClosed}, Drawer base class, trapFocus/releaseFocus, formatMoney(cents), debounce, fetchConfig, prefersReducedMotion, routes, strings, config.
- Custom elements already defined in theme.js: `menu-drawer`, `search-drawer`, `sticky-header`, `olivet-accordion`, `quantity-input`, `localization-form`, `details-disclosure`, `share-button`. Any element with `[data-drawer]` attribute and a `.open()` method can be opened with `<button data-drawer-open="#elementId" aria-expanded="false">`.
- Drawer markup contract: `<menu-drawer id="MenuDrawer" data-drawer class="menu-drawer" aria-hidden="true" inert><div class="drawer__backdrop" data-drawer-backdrop></div><div class="drawer__panel drawer__panel--left" data-drawer-panel role="dialog" aria-modal="true" aria-label="…"><div class="drawer__header">…<button data-drawer-close class="drawer__close">…</button></div><div class="drawer__body">…</div></div></menu-drawer>`. Submenus: `<button data-submenu-open="#Submenu-1" aria-expanded="false">`, panel `<div id="Submenu-1" data-submenu class="menu-drawer__submenu" inert>` with a `<button data-submenu-back>`.
- Cart (assets/cart.js, owned by the cart group) defines: `cart-drawer` (extends Olivet.Drawer; `renderContents(response)` swaps `#CartDrawer-Inner` from `response.sections['cart-drawer']` and `#cart-icon-bubble` inner HTML from `response.sections['cart-icon-bubble']`, then opens; `getSectionsToRender()` returns ['cart-drawer','cart-icon-bubble']), `cart-items` (cart page & drawer line list: quantity change → POST cart_change_url with `{ line, quantity, sections: [...], sections_url }`, remove buttons `<button is="cart-remove-button">` or `<cart-remove-button data-index>`), `product-form` (wraps `{% form 'product' %}`; on submit: POST FormData to routes.cart_add_url with `sections` appended; on success → if drawer exists `renderContents` + open, else redirect to cart_url; button gets `.is-loading` then `.is-transitioning` with label swapped to strings.added for 1.6s; on error shows `.product-form__error` with role=alert), `free-shipping-bar` (reads data-total, data-threshold; animates `.free-shipping-bar__fill` with transform scaleX). The header's cart link must be `<a href="{{ routes.cart_url }}" id="cart-icon-bubble" class="header__icon header__icon--cart" data-drawer-open="#CartDrawer" aria-expanded="false">{% render 'cart-icon-bubble' %}</a>` (the cart group's JS turns clicks into drawer opens when cart_type is drawer; when the drawer is absent it stays a link).
- Product (assets/product.js, owned by the product group) defines: `variant-picker` (fieldsets of radio pills `name="options[Size]"` or selects; on change fetches `{{ product.url }}?variant=<id>&section_id=<section.id>` and swaps `#price-<section.id>`, `#Inventory-<section.id>`, `#ProductSubmitButton-<section.id>` state, `#Sku-<section.id>`, the hidden `input[name=id]`, updates URL via replaceState, switches gallery to the variant's media, publishes Olivet.EVENTS.variantChanged), `media-gallery` (thumbnails + main stage; mobile is a scroll-snap carousel), `product-recommendations` (fetches `routes.product_recommendations_url?section_id=…&product_id=…&limit=4`, injects HTML).
- Search (assets/predictive-search.js, owned by the header group) defines `predictive-search` custom element: input with debounce 250ms → fetch `routes.predictive_search_url?q=…&resources[type]=product,collection,page,article&resources[limit]=4&section_id=predictive-search`, injects `#predictive-search-results` from the `predictive-search` section's HTML, aria-live, arrow-key navigation, Escape closes.
- Section rendering: cart-drawer markup lives in `snippets/cart-drawer.liquid` rendered by the layout AND by `sections/cart-drawer.liquid` (`{% render 'cart-drawer' %}`) so `?sections=cart-drawer` works. Same pattern for `cart-icon-bubble`.

## REVIEW PHASE (supersedes "Output routing for build agents" above)
The build is fully integrated. From now on the theme files are the single source of truth:
- Edit CSS directly in assets/templates.css (section styles, grouped under "section group: …" comments), assets/components.css or assets/base.css.
- Edit locale strings directly in locales/en.default.json (keep valid JSON, add keys, never remove keys still in use).
- Do NOT write to the scratchpad css/ or locales/ folders; nothing merges them any more.
