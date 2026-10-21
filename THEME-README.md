# Runneth — a new Shopify theme for My Cup Runneth Over Anointing Oils

A complete, from-scratch Online Store 2.0 theme. Nothing from the old site is reused:
new layout, new type system, new colour system, new homepage narrative, new product
page, new cart, new navigation and new footer. All copy, images and colours are
editable in the Shopify theme editor.

## Design rationale — what each inspiration gallery taught, and where it landed

| Gallery | Pattern it curates | Applied in this theme |
| --- | --- | --- |
| **land-book.com** (landing pages) | One clear narrative per page, generous whitespace, editorial serif headlines, a single primary CTA repeated | Homepage runs as a story: Hero → Trust → Products → Purpose → Story → Sizes → Testimonies → Scripture → FAQ → Community → Newsletter. One olive "Shop" button is the primary CTA everywhere. |
| **supahero.io** (hero sections) | Eyebrow + headline + sub + 2 CTAs + proof line, product visual on the right | `sections/hero.liquid`: eyebrow "Biblical anointing oils", Psalm 23:5 headline with gold italic emphasis, two buttons, 5-star proof line with avatar stack, floating "prayed over" card on the image. Split and full-bleed layouts. |
| **pricingpages.design** (pricing pages) | Tiered cards, one highlighted "most popular", value anchoring, per-unit notes | `sections/size-tiers.liquid`: 1 oz / 2 oz / 4 oz / Gift sets cards with "Most popular" and "Best gift" flags. On the product page the size pills show the price under each size and flag the largest as "Best value". |
| **socialproofexamples.com** (social proof) | Star ratings near CTAs, verified badges, specific quotes with name + place, aggregate rating | Rating line under the product title, `sections/testimonials.liquid` with aggregate "4.9 average", verified badges, product links, and a trust list under Add to cart. Testimonials also run on every product page. |
| **reallygoodemails.com** (email design) | Dark modular blocks, single-purpose offer, clear fine print | `sections/newsletter.liquid`: dark card with a gold "Claim 10% off" button, one field, fine print. Rotating announcement bar carries the offer across the site. |
| **deck.gallery** (pitch decks) | One idea per slide, big numbers, problem → solution → proof → ask | Each section carries one idea. Story section uses three big-number stats. The homepage ends with the "ask" (scripture banner + newsletter). |
| **posts.design** (social posts) | Bold brand-colour blocks, short punchy text | `sections/social-grid.liquid` (6-up community grid) and `scripture-banner.liquid` (full-width dark block with a single large serif quote). |
| **adfolio.design** (ad creatives) | Benefit-first headline, offer framing, urgency | Announcement bar messages, "Shop by purpose" tiles named after the need ("Protection", "Healing"), free-shipping progress bar in the cart drawer. |
| **navbar.gallery** (navigation bars) | Minimal sticky nav, logo left, centred links, cart + one accent button right, dropdowns | `sections/header.liquid`: sticky blurred header, centred menu with hover dropdowns, search/account/cart icons, olive "Shop oils" button, mobile drawer with accordion sub-menus and the brand scripture in the footer of the drawer. |
| **ogimage.gallery** (link previews) | Branded 1200×630 share image with title | `snippets/meta-tags.liquid` outputs Open Graph + Twitter cards; a global "Social sharing image" setting feeds every page that has no image of its own. Product JSON-LD is included for rich results. |

## Brand system

* **Colours** — ivory ground `#FAF6EE`, parchment surfaces `#F1E9DA`, olive primary `#3F5233`,
  gold accent `#B8903F`, oil-amber highlight `#C7742E`, deep olive dark sections `#1E2619`.
* **Type** — Playfair Display for headings, Work Sans for body (both from the Shopify font
  library, changeable in Theme settings → Typography).
* **Voice** — Psalm 23:5 is the spine: tagline in the header drawer, footer, password page,
  scripture banner and announcement bar.

## Features

* Sticky header with dropdown menus, mobile drawer, search drawer
* Rotating announcement bar
* Cart drawer with AJAX add-to-cart, quantity steppers, free-shipping progress bar, order notes / prayer requests
* Product page: thumbnail gallery, size pills with prices, dynamic checkout, sticky mobile add-to-cart bar,
  trust list, scripture block (reads `product.metafields.custom.scripture` and `custom.scripture_reference` when set),
  collapsible tabs, share, product recommendations, testimonials, JSON-LD
* Collection page: banner, sort, storefront filters (configure under Online Store → Navigation → Filters), pagination
* Templates: home, product, collection, collections list, cart, page, page.about, page.contact, page.faq,
  blog, article, search, 404, password, gift card, all customer account pages
* Fully editable in the theme editor; every section has presets so it can be added to any page

## Install

### Option A — upload the zip (fastest)
1. Download `my-cup-runneth-over-theme.zip` from this repo.
2. Shopify admin → Online Store → Themes → **Add theme → Upload zip file**.
3. Customize: upload the logo (Theme settings → Brand), pick the hero image, assign the
   four "Shop by purpose" tiles to collections, add Instagram images to the Social grid.
4. Preview, then **Publish**.

### Option B — connect from GitHub (recommended, keeps the theme in sync)
Online Store → Themes → Add theme → **Connect from GitHub** → repository
`jeffreydegraft-hash/Jeffrey-`, branch `claude/blissful-goldberg-qe772g`. The theme files live at the
root of that branch, which is what Shopify's GitHub integration requires. Every push to the branch then
updates the theme in Shopify automatically.

### Option C — Admin API
`themeCreate` with the public zip URL:
`https://raw.githubusercontent.com/jeffreydegraft-hash/Jeffrey-/claude/blissful-goldberg-qe772g/my-cup-runneth-over-theme.zip`

### Menus the theme expects
* `main-menu` — top navigation (add a "Shop" item with collection sub-links to get the dropdown)
* `footer` — help links (Shipping, Returns, Contact, FAQ)

### Pages the theme links to
Create pages with handles `about`, `contact` (assign template **page.contact**) and `faq`
(assign template **page.faq**).
