# Olivet — the Mount of Olives storefront theme

A from-scratch Shopify Online Store 2.0 theme for [mountofolives.co](https://mountofolives.co), rebuilt around the design-engineering rules in [emilkowalski/skills](https://github.com/emilkowalski/skills): purposeful motion (transform and opacity only, strong custom easings, press feedback on every control, hover gated to real pointers, reduced-motion variants), native-feeling mobile behaviour, and worst-case-first layouts.

The theme lives at the root of this repository so Shopify's GitHub integration can connect it directly.

## Install on the store

**Option A — connect from GitHub (recommended)**

1. In Shopify admin go to **Online Store → Themes → Add theme → Connect from GitHub**.
2. Pick this repository and the branch you want to track. Shopify imports the theme as an unpublished theme and keeps it in sync with the branch.
3. Open **Customize** to preview, then **Publish** when ready.

**Option B — Shopify CLI**

```bash
npm install -g @shopify/cli@latest
shopify theme push --unpublished --theme "Olivet" --store mount-of-olives.myshopify.com
```

`shopify theme dev` gives a live preview against your real products.

## After installing: five-minute setup

1. **Logo and favicon** — Theme settings → Logo.
2. **Menus** — the header reads `main-menu`; the footer uses `main-menu` for "Shop" and `footer` for "Company". Create them under Navigation if they don't exist.
3. **Pages and templates** — assign templates in the page editor: *About us* → `page.about`, *Our science* → `page.science`, *Contact* → `page.contact`.
4. **Homepage sections** — the home template ships with the brand copy pre-filled (hero, nine blends, values, story, science, scripture, how to use, squalane, journal, FAQ, newsletter). Pick the featured collection and product, and add images in the editor.
5. **Product content (optional but recommended)** — add these product metafields under Settings → Custom data → Products, namespace `custom`:

   | Key | Type | Used for |
   | --- | --- | --- |
   | `theme_word` | Single line text | The one-word theme on cards and product pages (e.g. *Reverence*) |
   | `scripture_quote` | Multi-line text | The verse on the product page |
   | `scripture_reference` | Single line text | e.g. *Matthew 2:11* |
   | `meaning` | Multi-line text | Biblical significance paragraph |
   | `ingredients` | Multi-line text | Ingredient list shown in the Ingredients accordion |

   Until metafields are filled, the theme uses built-in defaults for the eleven current products (see `snippets/product-defaults.liquid`), so the pages are complete on day one.

## What's inside

```
layout/        theme.liquid, password.liquid
templates/     JSON templates (index, product, collection, cart, pages, blog, search, 404, password, customers/*)
sections/      header, footer, cart drawer, product, collection, home sections, pages, blog, customer accounts
snippets/      shared partials: product card, price, image, icons, quantity input, pagination, cart line items…
assets/        base.css (tokens, type, buttons, forms, motion), components.css, templates.css, theme.js, cart.js, product.js, predictive-search.js, facets.js, customer.js
config/        settings_schema.json, settings_data.json (brand colours, fonts, cart, search)
locales/       en.default.json
dev/preview/   local mock renderer + screenshot tool (not part of the theme)
```

### Motion system

Tokens in `assets/base.css`:

```css
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);     /* enter / exit */
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1); /* on-screen movement */
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);  /* drawers and sheets */
--dur-press: 120ms; --dur-fast: 160ms; --dur-base: 200ms; --dur-drawer: 400ms;
```

Rules applied throughout: only `transform` and `opacity` animate; entrances start at `scale(.96–.98)` or `translateY(8–12px)` with `opacity: 0`, never `scale(0)`; exits are faster than entrances; every pressable scales to `.97` on press; every `:hover` rule sits inside `@media (hover: hover) and (pointer: fine)`; `prefers-reduced-motion` removes movement but keeps fades; nothing animates on keyboard shortcuts.

### Mobile

`viewport-fit=cover` with safe-area insets on fixed UI, `100dvh` drawers, `100svh` hero, 16px inputs (no iOS zoom), `touch-action: manipulation` on controls, scroll-snap carousels, and a translucent sticky header that hides on scroll down and returns on scroll up.

## Local preview (no store needed)

`dev/preview` renders the templates with sample data so you can look at the design without a store connection. It approximates Shopify's Liquid and is a visual aid only.

```bash
cd dev/preview && npm install
npm run preview        # renders dist/*.html and screenshots to shots/
```

## Checks

```bash
shopify theme check --path .
```

CI runs the same check plus JSON validation on every push (`.github/workflows/theme-check.yml`).
