# Mount of Olives: visual refresh of the live Shopify theme

The refresh lives in Shopify as an **unpublished copy** of the live theme. The live theme has not been changed. Nothing goes live until the owner presses Publish on the copy.

| | Theme | ID |
| --- | --- | --- |
| Live (MAIN, untouched) | Updated copy of Mount of Olives - Live | 145442373692 |
| Refresh (UNPUBLISHED) | Mount of Olives – Refresh (preview, not live) | 167488356412 |

- Preview: `https://mountofolives.co/?preview_theme_id=167488356412`
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
- Squalane serum now has its own image-and-text section. Before, it was a full-width photo with small text over it.
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
