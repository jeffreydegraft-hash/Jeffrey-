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

### Phone audit, round two (Oct 20, later)

Three more reviewer agents covered the cart, account, journal, search, 404, contact, FAQ, about and collections pages, each followed by a skeptic that re-checked every finding. Fixes, all in the phone-fixes copy:

- **Cart**: the size line under each item ("1 ounce (30 ml)") was 10px, now 11px; names break evenly at 320px; the Remove link has a thumb-sized tap area (pseudo-element, underline unchanged). The cart drawer shares the snippet.
- **Buttons**: Prestige paints the button fill as a gradient image sized 101%; on 2x and 3x screens a 1px light seam showed inside the right edge of olive and gold buttons. `background-origin: border-box` on `.button` closes it (verified by pixel sampling at DPR 2 and 3).
- **Journal**: card titles and the article title use `text-wrap: balance` (the card title is an inline link, so it is also made `display: block`); "Read more" links have a larger tap area; the article's share tiles are olive with cream icons instead of Facebook blue, X blue and Pinterest red; the article hero band uses the "small" image size so the 3:2 post photos are barely cropped on phones (`templates/article.json`).
- **Account pages**: `templates/customers/login.json` and `register.json` had no "fields" block, and Prestige renders the forms only inside that block, so both pages showed a heading and nothing else. The block is added. The store uses Shopify's new customer accounts (`customerAccountsV2.customerAccountsVersion = NEW_CUSTOMER_ACCOUNTS`), so these theme pages are not normally shown; the fix is insurance.
- **Collections page** (`templates/list-collections.json`): every tile was dimmed by the section's 30% black overlay, and the "All Anointing Oil Products" collection appeared as a tenth tile showing one bottle with its name printed across the label. The overlay is 0, a soft gradient at the bottom of each tile carries the white names (`--content-over-media-gradient-overlay`), and the section lists the nine real collections in the homepage order.
- **Contact page** (`templates/page.contact.json`): the form section printed the schema default title "Contact" under the page's own "Get in Touch" heading; the title is blank now. Left for the owner: the mailing address on this page says "Suite 103" while the footer says "Ste. 103-225"; one of them needs correcting in the editor.
- Rejected by the skeptic as taste: one full-width collection tile per row on phones (Prestige's default, nothing hidden).

Theme Check: the same 15 pre-existing offences. The themes table at the top names the copy to publish.

### Oct 21: address removed; praying photo in the product galleries

- The owner asked for the mailing address to go altogether. It is removed from the footer text block (`sections/footer-group.json`), the contact page (`templates/page.contact.json`) and the legacy footer block in `config/settings_data.json`; email and phone stay. Uploaded to the phone-fixes copy.
- The owner's praying photo (Files: `praying-with-frankincense-myrrh.jpg`) now replaces the sunflower-field photo in the product galleries of the seven oils that carried it (Hyssop, Rose of Sharon, Latter Rain, Gethsemane, Pomegranate, Lily of the Valley, Spikenard), at the same position (sixth image, under the oil-drop photo). Done with `productUpdate` (media), `productReorderMedia` and `fileUpdate` (reference removed from the product; the sunflower file itself stays in Files). Product media is store data, not theme data, so this is live immediately. Frankincense & Myrrh had no sunflower photo; the Frankincense and Myrrh singles carry a different prayer image and were left alone.

### Oct 21: favicon

The owner supplied the round "Mount of Olives Anointing Oils" logo for the favicon, then chose the version with the large olive sprig. It is cropped to the circle with a transparent outside, saved at 512px (`theme-files/mo-favicon-sprig.png`), uploaded to Files as `mo-favicon-sprig.png`, and set as `favicon` in `config/settings_data.json` in the phone-fixes copy (the previous `mo-favicon.png` in Files is fully transparent, which is why tabs showed no icon; the first candidate, `mo-favicon-logo.png`, stays in Files unused). At tab size the gold sprig inside the ring reads clearly; the lettering does not, as with any wordmark favicon.

`tools/bottle-composite.py` places a real product bottle (cut out of its white-background product photo) into the generated praying photo, keeping the hands in front; it is offered to the owner, not applied.

### Oct 21: welcome-offer pop-up and discount code

The owner asked for an engaging first-visit pop-up with a discount that exists in the backend, built to drive purchases.

- **Discount** `WELCOME10`: 10% off all products, once per customer, combinable with shipping discounts, no end date, created with `discountCodeBasicCreate` (title "Welcome offer: 10% off your first order"). The store already had older codes (10% to 50%); none was a welcome offer.
- **Pop-up** (`theme-files/newsletter-popup.liquid`, replaces Prestige's `sections/newsletter-popup.liquid`; styles under "Welcome offer pop-in" in `custom-design.css`; settings in `sections/overlay-group.json`): a photo strip (the bottle line-up), "10% off your first order", one email field, a gold "Get my 10% off" button and a small "No thanks" link. The form is Shopify's customer form with the `newsletter` tag, so the address lands in Customers with marketing consent. After the form posts, the same card shows "Your 10% off is ready", the code in a dashed box and a "Shop with 10% off" button whose link is `/discount/WELCOME10?redirect=/collections/all`: Shopify applies the code to that visitor's checkout and sends them to the shop, so nothing has to be typed. The code, texts, photo and link are section settings.
- **Behaviour**: appears after 6 seconds, on any page except the cart (a visitor landing on a product page from an ad sees it too), once per browser (Prestige stores `theme:popup-appeared` in localStorage when it opens and `theme:popup-filled` after signup), hidden for signed-in customers. The original Prestige file tested a setting name that does not exist (`show_only_for_visitors`), so "hide for account holders" never worked; fixed. On desktop the card sits bottom-left, away from the chat bubble; on phones it is a bottom card lifted 5.5rem so the chat pill stays reachable.
- Rendered and screenshotted locally in both states (`tools/popupshot.mjs`; `tools/render.mjs` takes `FORM_POSTED=1` to render the success state).

### Oct 21, later: pop-up review fixes

Three reviewer agents (conversion, code, copy) and a skeptic went over the pop-up in the local render. Fixes applied, verified again at 320x568, 360x640, 375x553, 375x667, 390x664, 390x844 and 430x932:

- The card is capped at the window height (`max-height` with `100dvh`, scrolls inside) and the photo strip is dropped on screens under 700px tall, so the close button is always on screen (it was off the top on an iPhone SE with Safari's bars showing).
- The live theme's old newsletter pop-up had already written Prestige's "already shown" flags into every returning visitor's browser, so the offer would never have appeared for them. A one-time inline reset (`theme:welcome-offer-v1`) clears those flags once.
- The success button sends a visitor who signed up on a product or collection page back to that page with the code applied (`request.path`), not to the all-products grid; the code is `url_escape`d and the link falls back to `routes.all_products_collection_url`.
- The code is applied the moment the success card renders (a same-origin fetch of `/discount/WELCOME10`), so it still counts at checkout if the card is closed without tapping the button.
- Product pages wait 12 seconds instead of 6 (the sticky add-to-cart bar already takes the bottom of a phone screen); the card does not appear on gift-card, policy, 404 and account pages; a rejected email reopens the card with the error; the email field is 16px on phones (no iOS zoom), the "No thanks" link has a 44px tap area, the card sits above the cookie banner (`z-index: 11`), the dialog is named by its visible title (`aria-label`) and the strip image loads early at low priority.
- Success text: "Tap the button and 10% comes off at checkout. Your code is WELCOME10 if you ever need it."

Uploaded to the new copy "Mount of Olives – Welcome offer + Science (not live)" (the phone-fixes copy had been published in the meantime and is now the live theme, renamed "Mount of Olives – Live (phone fixes, Oct 21)"). `tools/measure-popup.mjs` measures the card at the phone viewports above.

### Oct 21: interactive Our Science page

The owner asked for the Our Science page (`/pages/our-science`) to be more interactive and clickable, and rewritten without em dashes.

- **Template** `theme-files/page.our-science.json` (goes to `templates/`), built from Prestige's own sections so the owner can edit every word in the theme editor: a rich-text hero ("The science of sacred botanicals", Shop the oils, See every ingredient); a five-item icon band of the formulation standards; a four-step timeline (Rooted in Scripture, Extracted not synthesized, Carried by olive squalane, Made for anointing) with numbered steps to click through; tabs for the olive squalane base, the polyphenol complex, the botanicals and the standards (accordions on phones); eight botanical cards with the site's existing plant photos, each linking to its oil; a "Tap a bottle" shop-the-look section with gold hot spots on the two halves of the bottle line-up (each opens the product with a buy button); the A to Z ingredient glossary as accordions grouped in five categories with a category list on desktop; and a closing band with Shop the collection and a link to the FAQ. `tools/our-science-build.py` generates the template and the page body from one set of strings and refuses to write if an em or en dash slips in.
- **Copy**: every sentence of the existing page rewritten without em dashes; no claim added or removed. The brand name "Polyphenol Alpha (α)™" stays in the text; the tab title is "The polyphenol complex" because Prestige upper-cases tab titles and would turn the α into a capital.
- **Page body** (`theme-files/our-science-body.html`): the same copy as plain HTML, set as the page's content so search engines and any other theme show the dash-free text; the template takes over on the storefront (`templateSuffix: our-science`).
- **CSS** (end of `custom-design.css`): the botanical cards share one 3:2 frame whatever the photo's own shape (one plant photo is portrait); the glossary anchor lands below the sticky header.
- **Images**: `theme-files/mo-science-look-1.jpg` and `-2.jpg` are the left and right halves of the bottle line-up photo for the hot spots (Files); the plant photos are the ones already in the store's Files from the journal. The container cannot reach Shopify's image CDN, so the local render used same-size stand-ins for those; the Shopify preview shows the real photos.
- **Checks**: `tools/science-ix.mjs` clicks through the timeline steps, every tab, a glossary accordion, the phone "view products" popover and a desktop hot spot, and follows the anchor link, at 390 and 1440px; no page error, no sideways overflow. Theme Check: the same 15 pre-existing offences.

### Oct 21, afternoon: Science page uploaded, free shipping, dash sweep

- **Our Science** is on the copy "Mount of Olives – Welcome offer + Science (not live)": `templates/page.our-science.json` and `assets/custom-design.css` (checksums verified), the two line-up halves in Files as `mo-science-look-1.jpg` and `mo-science-look-2.jpg`, and the page record set to `templateSuffix: our-science` with the dash-free body. Until that copy is published the live theme shows the page through its default template, that is the dash-free body as plain text.
- **Free shipping**: the US "Standard" $0 rate in the General shipping profile applied at a cart total of $45 or more; it now applies at $40.50 (`deliveryProfileUpdate`, condition updated in place). The announcement bar and FAQ keep saying $45, which stays true; a $45 cart with WELCOME10 applied (10% off) is $40.50 and still ships free.
- **Dash sweep** (the owner said yes to the FAQ and About pages, and the rest was one shared sentence): About Us page body (five dashes), FAQ page body (seven, including "1 to 3 business days"), the FAQ answers in `templates/page.faq.json` and the same two answers in the homepage FAQ in `templates/index.json` (uploaded to the new copy), the shared "consecrating objects. They are designed to anoint…" sentence in nine product descriptions, and the six collection blurbs that opened with a dash. Two typos fixed on the way: "Sogn of Solomon 2:2" in the Lily of the Valley references, and "1 Samuel 16:13iJames 5:14-16" in the Gethsemane references. Left alone: the unpublished Discovery Set draft (ten dashes) and the journal posts (about 89 em dashes across twelve English posts plus en dashes in the Spanish ones). The new copy lives in `copy/`.
- A review workflow (claims, language, structure reviewers, then a skeptic per finding) checks the rewritten Science, About and FAQ copy against the originals; its confirmed findings are applied below if any.

### Oct 21, evening: no efficacy claims, Scripture first

The copy review confirmed that the dash-free rewrite had quietly softened several of the page's strongest claims ("synergistic", "therapeutic potential", "dramatically enhances the percutaneous absorption"). Asked whether to restore them, the owner said the opposite: soften, in fact drop claims like that altogether, and keep the page mostly spiritual.

- `tools/our-science-build.py` now carries the claim-free copy. Every glossary entry says what the compound is and where it is found (plus "an antioxidant" where that is its class); the botanical cards lead with each plant's meaning in the site's own words (prayer rising like incense, purification, extravagant worship, fruitfulness, purity and peace) and name the compound second; the hero opens with anointing in Scripture (Exodus 30, the horn of oil, the oil of gladness, the alabaster jar); the squalane tab names the olive's place in Scripture (Exodus 27:20, Exodus 30:22-25, 1 Samuel 16:13, Gethsemane); the closing band quotes Psalm 23:5. Gone: clinically meaningful, evidence-based, anti-inflammatory, antimicrobial, neuroprotective, wound-healing, collagen, UV, photoprotective, barrier, cellular vitality, bioavailability, penetrates deeper, superior absorption, measurably enhanced efficacy, dermatologist-conscious, microbiome. Kept: nourishes, hydrated, not greasy, non-comedogenic, light, stable.
- The same rule applied to the FAQ (page body and the theme's answers), About Us and the six collection blurbs (`copy/`): "clinically meaningful levels of antioxidants and anti-inflammatory benefits", "penetrate your skin", "deliver our botanical actives deep into the skin", "healing essence" and "antioxidant protection" are gone.
- A second review (claims hunter, Scripture checker, phone reader, then a skeptic per finding) runs on the new text; confirmed findings are applied before upload.
- Uploaded once the connector was back (checksums verified on the copy): `templates/page.our-science.json`, `templates/page.faq.json`, `templates/index.json`; the Science, FAQ and About page bodies and the six collection descriptions are live store data and changed at once.
- Second review, confirmed and applied (15 of 24 verified findings; the rest were refuted): "purifying and protective power" and "restorative power" in the Hyssop and Frankincense & Myrrh blurbs, "one of the most studied", "remarkably dense", "no synthetic penetration enhancers", "This is not a coincidence. It is by design.", "helps keep the other antioxidants stable", "with antioxidant activity", "cosmeceutical" in the Science tagline and the About opening, and the FAQ's "carries our botanical extracts with it" (now: because it comes from the olive, the tree that lit the tabernacle and anointed kings). The skeptics kept "cosmeceutical" everywhere else as the brand's standing category word. Every Scripture reference on the page checked out. Re-uploaded and verified.

### Oct 22: fix-all pass

The owner asked to fix every issue on the site, to make sure it works on phones, to take Exodus 30 out, and to replace the sunset praying-woman photo with the new praying photo everywhere. A page-by-page review (phone at 320 and 390 px, desktop at 1440 px, page text) found the issues below; each was checked by a second reviewer before it was fixed.

Theme copy (`theme-files/`, goes live when the unpublished copy is published):

- Exodus 30 removed from the Science page hero, the olive squalane tab, the page record text, the Amazon kit and the product description drafts.
- Footer verse now the King James wording, "Thou anointest my head with oil; my cup runneth over." Psalm 23:5, with curly quotes and no dash.
- Hero eyebrow "Anointing oils rooted in Scripture" instead of "With cosmeceuticals derived from biblical botanicals".
- Squalane section text without "derived from the purity" and "steeped in biblical tradition".
- Gethsemane kicker "Unscented", matching its label; Polyphenol Alpha (α)™ spelled with the space.
- Review heading "131 four- and five-star reviews" (the live count of 4 and 5 star reviews; it counts reviews, not customers).
- Page titles end with the store name; the pagination separator is a bar, not an en dash; copyright line without the hyphen.
- Hero hotspot label for the Frankincense & Myrrh bottle uses the product name instead of the all-caps collection title.
- Squalane bottle photo blended onto the cream page (it was a white box).
- Compare sizes: the "Best value" badge sits under the best price on every screen, per-ounce prices never wrap.
- Product cards keep a two-line title slot so prices line up across a row; the ampersand stays with the word before it.
- Free shipping copy stays at $45. The rate itself is free from $40.50 so that a $45 cart still ships free after the 10% WELCOME10 discount; that is why the copy says $45, not $40.
- "Cosmeceutical" removed from the homepage and FAQ answers and the Contact page.
- Pages that have no description of their own (and would fall back to the store-wide description in Online Store > Preferences, which still says "faith and science ... cosmeceuticals ... healing, protection") use the brand line instead, in search results and share previews.

Uploaded to the new unpublished copy **Mount of Olives – Fix-all (Oct 22, not live)** (`167626965052`, a duplicate of the live Science theme), 11 files, every checksum verified: templates index, page.our-science, page.faq, page.contact; sections footer-group, footer, mo-hero; snippets product-card, social-meta-tags; assets custom-design.css; layout theme.liquid. `config/settings_data.json` was left as it is on the live theme (it carries the Inbox chat and Junip app blocks).

Store data (live at once):

- The sunset praying-woman photo (`PRAYERIMAGE`) detached from Frankincense and Myrrh; the new praying photo now sits sixth on all ten oils, Frankincense & Myrrh included.
- New product descriptions and search snippets for all eleven products (`copy/products/`, built by `tools/product-descriptions-build.py`): Scripture first, no efficacy claims, no dashes, ingredient lists and How to use kept, Scripture lists in Bible order with the typos fixed (Proverbs 16:15, Numbers 20:5, Leviticus 14:4, Zechariah 10:1) and Exodus 30 taken out.
- Ten collection descriptions rewritten the same way (`copy/collections.json`); "All Anointing Oil Products" renamed "All Products"; squalane and pomegranate search titles without "Cosmeceutical" and "Antioxidant-Rich".
- Our Science page record: Exodus 30 out, King James verse. FAQ page record unchanged except the earlier dash fixes.
- Gallery photo descriptions: the "With Cosmeceuticals - product image N" text replaced with plain descriptions on 32 photos. Note: `fileUpdate` with only `alt` detached those photos from their products; they were re-attached with `referencesToAdd` and put back in order within about 15 minutes. When alt text is changed with `fileUpdate` again, re-read the product galleries afterwards.
- Footer menu "Refund policy" to "Refund Policy"; the prayer-guide summary without its em dash.
- Redirects: `/collections/anointing-oils` and `/shop` now go to All Products (23 journal links pointed at the first); 26 old journal redirects that ended on a missing page now land on the matching live post; two inert redirects removed (their paths are live posts).

Checked locally and found to be preview-only, not live issues: the "(2)" rating without reviews (the Junip reviews block renders only on Shopify), the journal card placeholder excerpt, and the JavaScript errors from the cart, recently viewed and country requests that the local preview cannot answer.

### Oct 22 (later): homepage fixes after the owner's phone check

Draft theme "Mount of Olives – Homepage fixes (Oct 22, not live)" (167628374076), a copy of the live theme with 14 files changed:

- Hero: the SHOP buttons sat on the bottle bases on phones. The layout had been tuned on a resized copy of the photo; the live photo (1942×809) puts the bottles at 17.9% to 86.7% of its height and 1.1% to 98.9% of its width. The bottle area and crops now match that photo, and each button hangs a fixed gap below its bottle (`assets/custom-design.css`, `templates/index.json`).
- Reviews heading counts five-star reviews only and reads "{count} five-star reviews"; Junip counts are added only when their average is 5 (`sections/testimonials.liquid`).
- Product cards show the review count instead of the star score (`config/settings_schema.json` default `product_rating_mode: count`; a value in `settings_data.json` is dropped by Shopify on upload).
- Homepage FAQ: shipping under $45 is "calculated at checkout" (there is no flat rate); "ethically sourced" removed; base described as olive squalane everywhere.
- Free-shipping bar: measures the order before order discounts while the discounted total stays at or above the $40.50 rate, so a $45 cart with WELCOME10 shows free shipping (`snippets/free-shipping-bar.liquid`); messages say US.
- Homepage title "Mount of Olives | Biblical Anointing Oils Rooted in Scripture"; meta description under 160 characters.
- "Find your oil" tiles blend onto cream; Shop now goes to All Products; email share link encoded; footer newsletter text and "Email" label; schema logo points at `mo-favicon.png`.
- Science page: 1 Corinthians 12:20 in King James wording ("many members, yet but one body").

Store changes in the same pass: Frankincense and Hyssop variant weights set to 0.8 lb like the other oils (Frankincense was 0, Hyssop 0.8 oz); Pomegranate collection image set to the 4 oz render.

Later the same night, in the same draft: the product page rating reads like Maelove's, "★★★★½ 4.7 (39 reviews)", and tapping the count jumps to a new Reviews section under the product.

- The average and the count combine every real review a product has: its Etsy listing's total from the ReputonEtsyReviews metafield (the app imports only part of a big listing, e.g. 48 of Frankincense & Myrrh's 122, so the listing's own average is used then), Amazon reviews in `custom.amazon_reviews`, and Junip reviews on the store (`snippets/product-rating.liquid`, `snippets/product-info.liquid`). Stars round to the nearest half.
- `sections/mo-reviews.liquid` (added after `main` in `templates/product.json`): heading, the badge, where the reviews come from ("122 on Etsy · 2 on mountofolives.co"), the six newest imported Etsy reviews with first names only and one date format, and a link to read the rest on Etsy. Hidden on products with no imported review to show (Gethsemane and Squalane have one mountofolives.co review each, with no text the theme can read, so their badge shows the count without a link). Etsy logins such as "fg2g0gpt" are left out of the name line. Review follow-ups after an independent check: the section joins the product section's spacing like other sections, the badge inside the section is not a link, and the small grey text is darker for contrast.
- Counts on Oct 22: Frankincense & Myrrh 124, Hyssop 39, Spikenard 24, Rose of Sharon 9, Pomegranate 9, Latter Rain 2, Gethsemane 1, Squalane 1; Lily of the Valley, Frankincense and Myrrh have none. 209 in all. Counts grow only with real reviews (finish the Reputon import, paste Amazon reviews into the metafield, Junip review requests).

Owner follow-up (same day): products with fewer than 10 reviews show the store-wide rating, labelled "4.9 (209 reviews of our oils)", instead of "(1 review)"; product cards leave the count out below 10. Amazon and eBay reviews count once pasted into `custom.amazon_reviews` / `custom.ebay_reviews` (product or shop metafields, `{"reviews": [{"rating": 5}]}`); none are in the store yet, so today's 209 is 205 Etsy and 4 mountofolives.co.

Non-English journal posts hidden (Oct 22): the 87 machine-translated posts are unpublished (not deleted). Each old address redirects to its English original where one exists (47) or to /blogs/the-anointing-journal (40), and the 27 older redirects that pointed at them now go straight to the final page. To bring one back, publish it in Online Store > Blog posts and delete its redirect in Navigation > URL redirects.

### Oct 22 (afternoon): QC fixes and a free review form, in the same draft

The full-site QC (220 findings) was triaged: 81 theme fixes went into the draft (structured data, share text, FAQ answers and links, footer phone link, collections, Our Science copy, contrast, cart, and more; see the commit). The draft now holds 30 changed files; checksums were compared after upload.

Customers can leave their own stars without a paid app. The Reviews section under each product has a "Write a review" button: stars, first name, email and the review. It is sent through Shopify's contact form, so it arrives as an email to the store. Nothing shows until the owner approves it:

1. Read the email ("Review for: <oil>", "Rating: 5 of 5 stars").
2. In Shopify admin, open Content > Metaobjects > Customer review > Add entry.
3. Pick the product, enter the stars (1 to 5), the first name, the review text and the date, set Status to Active, and save.

The review then shows first in that product's Reviews section and counts toward its stars and the store-wide total. Setting an entry back to Draft hides it again.

Journal, Oct 22 afternoon: the last 19 cleaned posts went up, with formatting fixes on 68 posts (title headings no longer repeated at the top of the body, pasted ChatGPT markup and empty paragraphs removed, bold subheads turned into real headings, the old "Gethsemane squalane" name updated, "[website name]" replaced). All 73 uploads were read back from the store and match their files (two differ only by a line break Shopify adds inside a heading). myrrh-bible, which was published with an empty body, is hidden and redirects to myrrh-anointing. vegan-squalane is left as it was: it tells the story of naming the squalane "Gethsemane", which needs the owner's wording now that the product is "100% Squalane Oil".

Amazon rating (Oct 22): the Amazon listing family shows 4.7 stars from 128 ratings, shared by every scent and size. It is stored in the shop metafield `custom.amazon_rating` ({"count", "average", "url"}) and counts only toward the store-wide figure, which now reads "4.8 (337 ratings of our oils)" on products with fewer than 10 reviews of their own and under the homepage reviews heading. Update the count and average in Settings > Custom data > Shop when Amazon's numbers change. Store fixes in the same pass: product copy (P1 to P11), product and collection SEO, size names "1 fl oz (30 ml)", 56 alt texts without em dashes, About page (Our Story, "Texas"), Our Science page (base of olive squalane and olive oil), 19 journal titles.
