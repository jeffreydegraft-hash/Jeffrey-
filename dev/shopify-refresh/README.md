# Mount of Olives: visual refresh of the live Shopify theme

The refresh lives in Shopify as an **unpublished copy** of the live theme. The live theme has not been changed. Nothing goes live until the owner presses Publish on the copy.

| | Theme | ID |
| --- | --- | --- |
| Previous live theme (now UNPUBLISHED, untouched) | Updated copy of Mount of Olives - Live | 145442373692 |
| Refresh, **published by the owner on Oct 20** (now MAIN) | Mount of Olives – Refresh (preview, not live) | 167488356412 |
| Phone fixes (UNPUBLISHED, made Oct 20 by `themeDuplicate` of the live theme) | Mount of Olives – Phone fixes (not live) | 167594754108 |

- The live theme's name still says "preview, not live"; it can be renamed under Online Store → Themes → … → Rename.
- Preview of the phone-fixes copy: `https://mountofolives.co/?preview_theme_id=167594754108`
- Every later change goes into the phone-fixes copy; the owner publishes it when ready, and the next round needs a fresh duplicate again.
- Publishing is blocked for the connection used here (`themePublish` is refused by its safety policy); the owner publishes from Online Store → Themes. After publishing, the connection can no longer write to this theme either, so later edits go into a fresh duplicate.
- Theme editor: Shopify admin → Online Store → Themes → the Refresh copy → Customize

## What changed in the copy

The look stays the same brand: deep olive `#2C3227`, cream `#FAF7F2`, linen `#F0EBE3`, soft gold `#C4A265`, Cormorant headings and Montserrat text.

**Top of the page**
- One olive announcement bar, with two rotating messages. It replaces the three stacked bars that repeated the same words.
- The header shows the shop name as a wordmark, like the bottle labels ("MOUNT of OLIVES"), centred between the menu and the cart. If a logo image is uploaded in the header settings, it replaces the wordmark.

**Hero**
- New section "Mount of Olives hero" (`sections/mo-hero.liquid`). The headline and gold Shop now button sit above the 8-bottle photo, so no text covers the labels.
- The dark gradient over the photo is removed, and the photo's white background blends into the cream page.
- On phones, the line-up shows as two rows of four bottles.
- The original slideshow hero is still in the homepage template, only hidden. It can be switched back on in the editor.

**Bottle links**
- Each bottle in the hero photo is a link with a visible Shop button under it. On a computer, hovering a bottle fills its button.
- Seven bottles open their product page directly.
- Frankincense & Myrrh opens its collection, where shoppers choose Frankincense, Myrrh or the blend.
- The links are "Bottle link" blocks in the hero section, one per bottle, left to right. A block can point at a collection instead of a product.
- The "Find your oil" tiles also open the product page. Frankincense & Myrrh is the exception: it opens its collection.
- Collection pages now show each collection's own description under the title.

**Below the hero**
- New "text with icons" band for the four pillars: Rooted in Scripture, Set Apart for You, Clean Ingredients, Anointed with Purpose. The pillar copy comes from the store's own product descriptions and labels.
- Featured collection: three products per row. The photos blend into the page instead of sitting in white boxes.
- "Find your oil": the eight oil collections, each with its theme word (Radiance, Revitalize, …). The grey overlay is gone and the text sits below each photo.
- Squalane serum now has its own section: the face photo with the 100% Olive Squalane bottle stepping over its corner, beside the text. Both photos and the button open the product page. This uses Prestige's "Multiple media with text" section. Its image blocks gained an optional Link setting; nothing else in that file changed. Before, the serum was a full-width photo with small text over it.
- Featured product (Frankincense & Myrrh) now shows its name, price and short description. Before, it showed neither name nor price.
- Psalm 23:5 scripture band on olive.
- Journal heading renamed to "The Anointing Journal".
- Footer moved to olive.

**Site-wide**
- Brand colour schemes replace Prestige's default greys and blacks.
- Add to cart is solid olive and Buy it now is gold, with olive text for contrast.
- Product pages carry native feature lines: free US shipping over $45, natural, paraben-free and vegan, and secure checkout.
- Collection pages show a plain title banner. Before, the title was white on white.
- The cart's own free-shipping bar is switched on at **$45**, which matches the store's actual free-shipping rate. The theme previously said $50.
- `assets/custom-design.css` is rewritten against Prestige's real class names. The old file was mostly Dawn selectors that never matched.

**Removed from `layout/theme.liquid`**
- The injected script that showed made-up "Sarah M. in Nashville just purchased…" pop-ups. The names and cities were random, not real orders.
- The injected trust bar, product badges and cart widgets. Native theme settings and blocks above now cover these.

## Notes

- 29 unused files named `assets/zz-tmp-*` were added to the copy while preparing the preview. The Shopify connection blocks file deletion, so they are still there. They can be deleted under Edit code; nothing references them.
- The store favicon (`mo-favicon.png` in Files) is a fully transparent image, so browser tabs show a blank icon.
- `snippets/aeo-organization-schema.liquid` and `aeo-article-schema.liquid` point to `assets/logo.png`, which does not exist.
- The Reputon Etsy Reviews app is not installed. Shopify stripped its leftover blocks when the templates were saved; they render nothing on the live site either.

## Header change (Prestige `sections/header.liquid`)

When no logo image is set, the shop name is split around " of " and set as the wordmark. The 600 weight of the heading font is loaded for it. Everything else in the file is unchanged.

## Tools

`tools/` renders a theme folder locally with liquidjs and the store's data, then screenshots it with Chromium (`render.mjs`, `data.mjs`, `shoot.mjs`, `measure.mjs`). It also runs Shopify Theme Check (`tc.mjs`). `clicktest.mjs` clicks every bottle at desktop, tablet and phone widths and checks which page opens.

The theme source and the store export are not in this repo. Prestige is a licensed theme, and the export holds store data. `extract_theme.py` writes theme files saved from Admin API responses into a folder.

## Patterns borrowed from design galleries (Oct 20)

The owner shared a list of ten design-inspiration galleries (land-book, supahero, pricingpages.design, socialproofexamples, reallygoodemails, deck.gallery, posts.design, adfolio, navbar.gallery, ogimage.gallery). The ones about decks, social posts, ads and emails are not about the website. From the rest, applied in the unpublished copy, in the same minimal style:

- **Shop mega menu** (navbar.gallery): the header's "Shop" opens a panel listing every oil by name in columns (Anointing oils, Frankincense & Myrrh, Serums) with two product photos on the right. It uses Prestige's own mega-menu block. It needs a new navigation menu in Shopify, `main-menu-refresh`, defined in `menu-refresh.json`; the live `main-menu` is untouched. On phones the drawer shows Shop with a sub-level.
- **Compare sizes** (pricingpages.design): under the size picker on product pages, a small table shows each size's price and price per ounce, and marks the best value with the saving. It is a Liquid block in `templates/product.json`; the ounces come from the size names ("4 ounce (118 ml)"), so products without ounce sizes show nothing.
- **Questions, answered** (land-book, pricing pages): five of the store's own FAQ answers on the homepage, before the footer, with a link to the full FAQ page. Prestige's FAQ section, no new code.
- **Share image** (ogimage.gallery): `assets/mo-share-image.jpg`, a 1200×630 card with the wordmark and the bottle line-up, used by `snippets/social-meta-tags.liquid` for any page without its own image, such as the homepage. Source: `theme-files/share-image-source.html`.
- **Social proof** (socialproofexamples): the store's products carry Shopify's standard `reviews.rating` / `reviews.rating_count` metafields with real counts (Hyssop 39, Rose of Sharon 9, Pomegranate 9, others 1–2, all 5.0), and a `ReputonEtsyReviews` metafield holding 130 real Etsy reviews with author names and text (118 five-star). Added: a `rating` block under the title on product pages (Prestige's own, reads the standard metafields, hidden when a product has none; product cards already show the same stars), and a "From our customers" testimonials section on the homepage with four real Etsy reviews quoted verbatim, attributed by first name, product and "Etsy review". Nothing invented. The heading is "Rated 4 stars and up by {count} customers": `sections/testimonials.liquid` replaces `{count}` at page load with the live number of reviews rated 4 or more (Etsy reviews individually; each product's Junip count when its Junip average is at least 4; and Amazon reviews, once pasted into a `custom.amazon_reviews` json metafield on a product or the shop, in the same shape as the Etsy data: `{"reviews": [{"authorName": "...", "rating": 5, "relativeTimeDescription": "...", "text": "..."}]}`), so it updates itself as reviews come in; 131 on Oct 20 without Amazon. The section also has an "Amazon reviews rated 4 stars and up" number setting that is added to the count, for the figure shown on the Amazon listings; it is left empty. The owner asked to add 1,024 reviews to the count without supplying them; no number was entered, because a count that is not backed by real reviews would be a false claim to customers. The owner was asked for the Amazon reviews or the listing's real counts; Amazon is not reachable from the session and the store holds none. If the data ever yields zero, the heading falls back to "Loved by our customers". The four quoted testimonials are fixed text. A weekly read-only check that reports new reviews and suggests quotes is in `weekly-review-check.md`; it must be created from the claude.ai scheduled-tasks screen with the Shopify connector attached.
- The menu `main-menu-refresh` was created in Shopify on Oct 20 (`gid://shopify/Menu/257054539836`) with HTTP links; the live `main-menu` is unchanged.

## Phone fixes (Oct 20, after the refresh went live)

The owner's iPhone screenshot showed the two rows of bottles in the hero out of line with each other, and asked that everything work and look good at phone width.

- **Hero rows (`sections/mo-hero.liquid`, `assets/custom-design.css`).** On phones the section used to show the exact left and right halves of the line-up photo. The bottles are not centred in each half, so the first row stood about 5% further right than the second. Now each row shows a band of the photo centred on its own bottles (`--mo-hero-row-span`, `--mo-hero-row-one-start`, `--mo-hero-row-two-start`, computed from the Bottle link blocks: the fuller row sets the band width, and the bottles of both rows stand in the same columns). Measured in Chromium at 320, 360, 390 and 430px: the Shop buttons of both rows sit at 12.5/37.5/62.5/87.5% of the row width; the bottles themselves are within 5px of each other, the remainder being uneven spacing in the photo itself. The bottles are also about 5% larger than before.
- **Photo blend in Safari.** In the same screenshot the photo's white background did not blend into the cream page (each row showed as a lighter rectangle), while Chromium blends it. WebKit drops `mix-blend-mode` when a `filter` sits on the same element (WebKit bug 293903, fixed in mid-2025 but not on older iPhones). The brightness filter is gone (the photo background is 255/253/254, so multiply alone gives the page cream within two levels), the 1px clip of the photo's grey edge column moved to the frame wrapper, the wrapper carries the cream background, and the media box is isolated. This could not be tested here (no WebKit); the owner checks it on the phone.
- `tools/rowalign.mjs` measures the phone rows and Shop buttons; `tools/heroshot.mjs` screenshots the desktop hero; `tools/phoneaudit.mjs` screenshots every page at phone widths and runs DOM checks (overflow, clipped text, small tap targets, tiny text, broken images, script errors). `tools/render.mjs` now also renders cart, contact, FAQ, about, blog, article, search, 404, collections list, login and register pages. `clicktest.mjs` scrolls each row into view before sampling.

### Phone audit, round one (Oct 20)

`tools/phoneaudit.mjs` screenshotted every page at 320 and 390px (full page, plus the menu drawer and cart drawer) and ran DOM checks. No page overflows sideways. Five reviewer agents went through the tiles; their verified findings and the fixes, all in `assets/custom-design.css` unless noted:

- **"Find your oil" tiles at 320px**: long names pushed tiles out of the two-column grid (flex items with `min-width: auto`). Tiles now get `min-width: 0` and a slightly smaller name on very narrow phones; the text sits at the bottom of each tile (`grid-template-rows: auto 1fr`) so names line up across a row even when the theme word above wraps.
- **Featured collection tabs**: "Frankincense & Myrrh" and "Serums" were cut off at the screen edge (Prestige's tab strip never wraps). On phones the strip is now a wrapping, centred flex row with a smaller tab size.
- **Hero Shop labels** were 9px on phones; now 10px like desktop. **Announcement bar** phone text 10px → 11px (`sections/header-group.json`), with tighter tracking under 360px so it stays on one line. **Best value badge** 10px → 11px.
- **Cart thumbnails** sat in white squares; they now multiply onto the page like every other product photo (`.line-item__media`).
- **Safari blend**: `filter: brightness()` removed from every blended photo (hero, product cards, collection tiles, product gallery, mega-menu photos), because WebKit drops `mix-blend-mode` when a filter is on the same element.
- **Product descriptions**: the pasted HTML holds non-breaking spaces between ingredient names, so at phone width words broke in the middle ("Oleuropein-aglycone" split across lines). `snippets/product-info.liquid` and the below-gallery branch of `sections/main-product.liquid` now replace `&nbsp;` and U+00A0 with spaces before output. The "How to use" bullets carried inline `padding-left: 60px` divs; a CSS override resets those to the theme's list indent. Two content fixes are left to the owner: the section labels in the descriptions (RESTORE, HOW TO USE, SCRIPTURAL REFERENCE) are plain paragraphs and would read better as Heading 6 in the admin editor.
- **Orphan words**: pillar headings and product card names use `text-wrap: balance`.
- **Size picker at 320px**: narrower swatch padding so two sizes share a row.
- **Footer** (`sections/footer-group.json`): the links column was headed with the menu's internal name "Footer menu", now "Help"; "Connect with Us!" was an `<h3>`, now a bold paragraph.
- **Customer reviews carousel**: Prestige stacks every quote in one grid cell, so the carousel is as tall as the longest quote and short quotes left a large blank. The fourth quote is now a real Etsy review of similar length (Tatiana, Frankincense & Myrrh, verbatim) and quotes are centred in the carousel.
- The "(NaN)" review count and the empty cart drawer seen in the local render were renderer artefacts (the mock rating metafield lacked Shopify's `rating` key; the drawer is rendered with an empty cart). `tools/data.mjs` now mirrors Shopify's rating object.

All checked again in Chromium at 320 and 390px; Theme Check reports the same 15 pre-existing offences as before.
