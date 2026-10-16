# Olivet — Apple-first design specification

The owner chose an Apple-first direction. This document supersedes the visual
language in CONVENTIONS.md (the editorial ivory / gold / serif look is retired).
CONVENTIONS.md still governs Liquid conventions, JS contracts, accessibility and
the Never Ship motion rules, and its "REVIEW PHASE" note: edit theme files
directly; nothing merges scratchpad CSS any more.

Source of the rules: `skills/apple-design/SKILL.md` (read it in full), plus
`skills/emil-design-eng`, `skills/animate`, `skills/mobile-native`.
Reference look: apple.com product and store pages.

---

## 0. Brand integrity (binding — added after owner feedback; overrides anything below)

The owner said the rebuild "didn't keep my logos or my art work" and must "keep to the brand".
The Apple-first layout stays, but the merchant's OWN identity is used intact and prominently:

1. **Logos come only from the merchant's files.** Every logo slot (header, footer, password page,
   gift card) renders `{% render 'brand-logo', ... %}` (snippets/brand-logo.liquid — params: tone
   'light'|'dark', override, width, class, wordmark_class, priority, alt_empty). It falls back
   settings.logo → shop.brand.logo → (dark grounds: settings.logo_inverse) → the store-name wordmark.
   Never draw, trace, recreate or recolour a logo. No invented emblems: no olive branches, leaf marks,
   mountains, doves, monograms or "mark" glyphs anywhere (snippets/olive-branch.liquid is retired).
2. **No fabricated product art.** Do not draw bottles, labels or products in SVG/CSS. When a section
   has no image, use the merchant's real product media (e.g. a `product` setting's featured_media)
   or render text-only. Placeholders are Shopify's neutral placeholder_svg_tag only in the editor.
3. **Never alter the merchant's photos or artwork.** No mix-blend-mode, filter, opacity tricks,
   grayscale or duotone on product/brand images; `object-fit: contain` for product shots so labels are
   never cropped; no rounded crops that cut through a label. Product photos are shot on white, so
   product media stages and product tiles use a WHITE ground (#FFFFFF) — put them on #F5F5F7 sections
   when a tile edge is needed, Apple Store style — instead of blending photos into gray.
4. **Brand words and scripture follow the labels** (MOUNT OF OLIVES™ / [oil] / THE ANOINTING OIL /
   theme word / botanical / verse). Do not invent new taglines or theme words.
5. **Colour:** the olive accent (#4A5A2A / #5F7034) is PROVISIONAL until sampled from the real logo and
   labels. Keep colour usage restrained so it can be swapped by changing the scheme settings only
   (no hard-coded accent colours in section CSS).

---

## 1. Principles to make visible

1. **System font, hierarchy from weight + size + tracking.** No serif, no italic display type, no uppercase letter-spaced eyebrows. ("Default to the platform's system font before a custom face.")
2. **Restraint.** White and #F5F5F7 surfaces, near-black type, one accent: olive. Colour comes from product imagery, not decoration. No ornaments, no gold, no dividers where a surface change will do.
3. **Centred, generous, product-first.** Big centred headlines, a one-line subhead, two calls to action (filled pill + "Learn more ›" link), then large product imagery. Vertical rhythm is generous.
4. **Materials.** Navigation, sheets, drawers and popovers are translucent layers (`backdrop-filter`) floating over content. Dim to focus for modal sheets.
5. **Fluid, physical motion.** Springs for anything a user can touch. Sheets follow the finger 1:1 and can be flicked away; motion starts from the on-screen value and inherits release velocity. Rubber-band at edges.
6. **Response on press.** `:active` feedback on pointer-down for every control.

---

## 2. Tokens (assets/base.css `:root`; color schemes via settings)

### Font
```css
--font-system: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, Arial, system-ui, sans-serif;
--font-heading: var(--font-system);   /* layout overrides only if the merchant turns the system font off */
--font-body: var(--font-system);
```

### Type scale (Apple.com values; letter-spacing is size-specific — never one value for all)
| Class | Size | Line height | Weight | Tracking | Use |
|---|---|---|---|---|---|
| `.h0` | `clamp(48px, 6.6vw, 96px)` | 1.05 | 600 | -0.015em | hero headline |
| `.h1` | `clamp(40px, 5.2vw, 80px)` | 1.05 | 600 | -0.015em | page title |
| `.h2` | `clamp(32px, 4.2vw, 56px)` | 1.07 | 600 | -0.005em | section headline |
| `.h3` | `clamp(24px, 2.6vw, 40px)` | 1.1 | 600 | 0 | sub-section headline |
| `.h4` | `clamp(21px, 1.8vw, 28px)` | 1.14 | 600 | 0.007em | card headline |
| `.h5` | `19px` (21px ≥ 990) | 1.19 | 600 | 0.011em | tile title |
| `.lead` | `clamp(19px, 2vw, 28px)` | 1.14 | 400 | 0.007em | subheadline under a headline |
| `.eyebrow` | `17px` (21px ≥ 990 in heroes via `.eyebrow--lg`) | 1.19 | 600 | 0.011em | short label above a headline; colour `--c-gold` (the "detail" token, olive). **Not uppercase.** |
| `.tag` | `12px` | 1.33 | 600 | 0 | tiny label like "New" on tiles, colour `--c-gold` |
| body | `17px` | 1.47 | 400 | -0.022em | |
| `.small` | `14px` | 1.43 | 400 | -0.016em | |
| `.caption` | `12px` | 1.33 | 400 | -0.01em | legal, footnotes |

`text-wrap: balance` on headlines, `pretty` on paragraphs. `font-optical-sizing: auto`. Emphasis inside headlines (`<em>`) renders upright in the accent colour, never italic.

### Colour schemes (settings_data defaults; tokens keep their names)
| scheme | `--c-bg` | `--c-surface` | `--c-ink` | `--c-ink-2` | `--c-line` | `--c-accent` (buttons, links) | `--c-accent-ink` | `--c-gold` (detail: eyebrows, tags) |
|---|---|---|---|---|---|---|---|---|
| scheme-1 White | #FFFFFF | #F5F5F7 | #1D1D1F | #6E6E73 | #D2D2D7 | #4A5A2A | #FFFFFF | #5F7034 |
| scheme-2 Light gray | #F5F5F7 | #FFFFFF | #1D1D1F | #6E6E73 | #D2D2D7 | #4A5A2A | #FFFFFF | #5F7034 |
| scheme-3 Black | #000000 | #1D1D1F | #F5F5F7 | #A1A1A6 | #424245 | #F5F5F7 | #1D1D1F | #B7C88A |
| scheme-4 Graphite | #1D1D1F | #2C2C2E | #F5F5F7 | #A1A1A6 | #424245 | #F5F5F7 | #1D1D1F | #B7C88A |
| scheme-5 Olive tint | #EFF2E8 | #FFFFFF | #1D1D1F | #5B6252 | #D6DCCB | #4A5A2A | #FFFFFF | #4A5A2A |

Rules: never hex in section CSS (use tokens). Text on accent = `--c-accent-ink`. Muted text only on solid surfaces (on glass use `--c-ink` at 0.8 opacity minimum).

### Layout
```css
--page-max: 1200px (setting, default 1200);  --content-max: 980px;  --text-max: 692px;
--gutter: clamp(20px, 4vw, 48px);
--section-y: clamp(72px, 10vw, 140px) (default spacing; compact clamp(48px,7vw,96px), airy clamp(96px,12vw,180px));
--r-tile: 28px;  --r-card: 18px;  --r-media: 18px;  --r-btn: 980px;  --r-input: 12px;  --r-sheet: 20px;
```
Section headers are **centred** by default (`.section__header--center`). Text-heavy pages use `--text-max`.
Separation between sections comes from alternating `scheme-1` (white) and `scheme-2` (#F5F5F7) — no hairlines.

### Elevation & materials
```css
--shadow-tile: none;                                   /* tiles are flat */
--shadow-sheet: 0 12px 48px rgba(0,0,0,.16), 0 2px 8px rgba(0,0,0,.06);
--shadow-pop: 0 8px 32px rgba(0,0,0,.12);
--material-chrome: rgba(var(--c-bg), .72);            /* nav, toolbars */
--material-thick: rgba(var(--c-bg), .86);             /* sheets, drawers, popovers */
--material-blur: saturate(180%) blur(20px);
--material-blur-thick: saturate(180%) blur(30px);
--scrim: rgba(0, 0, 0, .32);
```
- Nav and toolbars: `background: var(--material-chrome); backdrop-filter: var(--material-blur)`.
- Sheets/drawers/popovers/search panel: `--material-thick` + `--material-blur-thick`, `--shadow-sheet`, `--r-sheet` on exposed corners. Never put a translucent surface on another translucent surface.
- `@media (prefers-reduced-transparency: reduce)` → solid `rgb(var(--c-bg))`, no blur. `@media (prefers-contrast: more)` → solid + 1px `--c-line` border.
- Scroll-edge effect instead of hard dividers under sticky chrome (fade/hairline only when content is underneath).

---

## 3. Components

### Buttons
- `.btn` = pill (`--r-btn`), 17px / 400 / -0.022em, min-height 44px, padding 0 22px. `.btn--lg` min-height 52px, padding 0 28px, 17px. `.btn--sm` min-height 36px, padding 0 16px, 14px.
- `.btn--primary`: `--c-accent` bg, `--c-accent-ink` text. Hover (gated): bg mixes 8% white (light) — use `filter: brightness(1.08)` or a token mix; press: `scale(.97)` 120ms `--ease-out`.
- `.btn--secondary`: transparent, 1px solid `--c-accent`, text `--c-accent`.
- `.link--chevron` ("Learn more ›"): text in `--c-accent`, 17px (21px in heroes via `.link--lg`), followed by a 10px chevron-right icon; hover underline (gated); press opacity .7.
- The standard CTA pair is: `<a class="btn btn--primary">Buy</a> <a class="link link--chevron">Learn more</a>`.

### Tiles (product cards, feature tiles)
- `.tile`: `--c-surface` background on a `--c-bg` section (so #F5F5F7 on white, white on #F5F5F7), radius `--r-tile`, padding `clamp(24px, 3vw, 40px)`, overflow hidden, **text centred**, flat (no border, no shadow).
- Product tile (`snippets/card-product.liquid`): `.tag` (theme word, accent detail), title `.h5`, price `.small` muted ("From $16.98"), then the image **below** the text (`object-fit: contain` on the tile, aspect 1/1, mix-blend-mode: multiply when the scheme is light so white product shots sit on the gray tile), then a CTA row: small pill "Buy" (links to product) + "Learn more ›". Hover (gated): image `scale(1.03)` 400ms `--ease-out`; press: tile `scale(.985)`.
- Feature tile (multicolumn, values, science): icon 40px in accent detail, `.h4` title, body `.small`/body muted, left- or centre-aligned per section setting.

### Navigation (header)
- Global nav: height 48px (52px ≥ 990), full-width translucent chrome; content max `--content-max`. Left: wordmark `shop.name` (17px, 600, -0.022em) or logo. Centre (≥ 990): links 14px / 400 / -0.016em at 0.8 opacity → 1 on hover/current. Right: search, account, bag icons (18–20px, 44px hit area). Hairline at bottom only once scrolled (scroll-edge).
- Desktop dropdown: Apple "flyout": full-width translucent panel dropping from under the nav (transform-origin top), child links in 24px/600 (primary column) and 12px muted group headings; dims the page below with `--scrim` at .2. Opens on click (and hover-intent ≥ 990 is optional — click is required for keyboard/touch).
- Mobile menu: full-viewport overlay that grows down from the nav (`clip-path: inset(0 0 100% 0)` → `inset(0)` or translateY spring), links 28px / 600, staggered 40ms; sub-menus slide in from the right; close morphs the menu icon to ×. Body scroll locked.
- Announcement "ribbon": `scheme-2`, centred 14px text with a `link--chevron` style link, min-height 44px, wraps never clips.

### Sheets & drawers (shared Drawer base, motion engine below)
| Drawer | ≥ 750px | < 750px |
|---|---|---|
| Cart | Right floating sheet: inset 12px top/right/bottom, width min(420px, 100% − 24px), radius `--r-sheet` | **Bottom sheet**: full width, max-height 92dvh, top radius `--r-sheet`, grab handle, drag down to dismiss |
| Facets (filter) | Left floating sheet | Bottom sheet, drag to dismiss |
| Menu | — | Full-screen overlay (above) |
| Search | Top translucent panel under the nav, height auto, `--r-sheet` bottom corners | Full-screen overlay sliding from the top |
| Lightbox | Centred modal (scale .96 → 1 + opacity; centred origin) | Full screen; drag down to dismiss |
- Grab handle: 36×5px pill, `--c-ink` at .2, centred, 8px from the top, inside a 44px tall touch zone (`[data-sheet-handle]`).
- Backdrop: `--scrim` opacity fade (opacity transition only).
- Sheet content scrolls (`overscroll-behavior: contain`); dragging the handle or dragging down while the content is scrolled to the top moves the sheet.

### Accordions (FAQ, product tabs)
Apple FAQ style: question 21px/600 (17px in compact product tabs), plus icon that rotates 45° to ×, hairline `--c-line` separators between items only, answer 17px muted. Animation stays `grid-template-rows` (tolerated).

### Forms
Inputs: 52px tall, radius `--r-input`, 1px border `#86868B`-equivalent → use `rgba(var(--c-ink), .32)`, 17px text, background `--c-bg`; focus: 4px ring `rgba(var(--c-accent), .25)` + border accent. Labels 14px/600 above; errors 14px in a red token `#E30000` is allowed ONLY via a new `--c-error` token defined in base.css.

### Badges
`.badge` 12px/600, pill, `--c-surface` bg; sale = accent detail text on `rgba(accent,.12)`; sold out = muted.

---

## 4. Motion system — `assets/motion.js` → `window.Olivet.motion`

All values from apple-design §4–§9 and animate / emil-design-eng.

```js
Olivet.motion.spring({ duration = 0.5, bounce = 0, velocity = 0 })
  // → { easing: 'linear(...)', duration: ms }  Apple's duration/bounce model:
  //   damping ratio ζ = 1 - bounce (bounce ≥ 0), response = duration (seconds).
  //   Simulates x(t) from 0 → 1 with initial velocity `velocity` (normalised: px/s ÷ distance),
  //   samples ~60 points into a CSS linear() easing; settle time becomes the duration.
Olivet.motion.animate(el, { from, to }, { duration, bounce, velocity, property = 'transform' })
  // WAAPI. If `from` is omitted, reads the CURRENT presentation value (getComputedStyle) so an
  // interrupted animation continues from where it is. Cancels any running animation on el first.
  // Commits the end value to el.style on finish. Returns a Promise. Reduced motion → instant + opacity fade.
Olivet.motion.project(velocityPxPerSec, decelerationRate = 0.998)   // Apple's projection
Olivet.motion.rubberband(overshoot, dimension, constant = 0.55)
Olivet.motion.SheetGesture  // class: new SheetGesture(panel, { axis: 'y' | 'x', dismissDirection: 1 | -1,
  //   handle, scrollContainer, onDismiss, onSettle })
  //   pointerdown → 10px hysteresis on the axis → setPointerCapture → track 1:1 (respect grab offset)
  //   → velocity history (last 80ms) → release: projected = offset + project(v);
  //   dismiss if projected > size * 0.5 (in dismissDirection) or v > 700 px/s; else spring back to 0
  //   with velocity handoff. Dragging opposite to dismiss rubber-bands. Ignores extra pointers.
  //   Only starts from the scroll container when it is scrolled to the top (y axis).
```
Spring presets (use these, don't invent):
| Use | duration | bounce |
|---|---|---|
| Sheet / drawer open | 0.5 | 0 |
| Sheet close (system) | 0.35 | 0 |
| Sheet settle after a drag release | 0.4 | 0.15 (only when the gesture carried momentum) |
| Menu overlay open | 0.45 | 0 |
| Popover / flyout | 0.3 | 0 |
| Lightbox | 0.4 | 0 |

CSS easings stay for CSS transitions (hover, press, colour, reveal): `--ease-out` etc. from base.css.
Durations: press 120ms, hover colour 160ms, reveals 600ms marketing (`translateY(24px)` + opacity, Apple-like), stagger 40–60ms, max 8 items.
Never Ship rules from CONVENTIONS still apply.

### Drawer base integration (assets/theme.js)
`Olivet.Drawer.open()` / `close()` animate the panel with `Olivet.motion.animate` springs (from the presentation value, so open-during-close reverses smoothly) instead of CSS transform transitions; the backdrop keeps an opacity transition. Panels declare their closed transform via `data-closed="translateX(100%)"` or `data-closed="translateY(100%)"` (default derived from `.drawer__panel--right|left|top|bottom`), and `data-sheet` on mobile bottom sheets turns on `SheetGesture`. `inert`/focus/aria contracts are unchanged.

---

## 5. Page compositions

### Homepage (templates/index.json)
1. **Hero** (`scheme-1`, layout `centered`): eyebrow "Mount of Olives" (or product line), h0 "Anointing oils for <em>prayer</em> and skin.", lead subhead (one sentence), CTA pair "Shop the oils" pill + "Learn about the science ›", then a large centred product image (merchant image; fallback = a stylised bottle illustration in tokens, not an ornament).
2. **Product grid** (`scheme-2`): centred h2 "Nine biblical blends.", lead "One olive base.", 3-up tiles (2-up ≥ 750 phone 1-up) — tiles on white surface over gray section.
3. **Values** (`scheme-1`): 4 feature items with icons, centred text, no band colour.
4. **Story** (`scheme-1`): image-with-text, large rounded media, h2 + body + "Read our story ›".
5. **Science** (`scheme-3` black): centred eyebrow + h2 + lead, three dark tiles (`--c-surface` #1D1D1F) with large numerals in accent detail, CTA link.
6. **Scripture** (`scheme-1`): centred, system font 600 at h2 size — quote set as a headline with curly quotes, reference as eyebrow below. (Apple "statement" style; not italic.)
7. **How to use** (`scheme-2`): three tiles with big numerals.
8. **Featured product** (`scheme-1`): 100% Squalane Oil — centred product hero mini: eyebrow, h2, price, CTA pair, large image.
9. **Journal** (`scheme-2`): three article tiles (image top, text below, rounded 18px).
10. **FAQ** (`scheme-1`): centred h2, accordion list in `--text-max`.

### Product page
Apple Store buy-flow feel: gallery left (sticky, rounded 18px, `--c-surface` bg, contain), info right: `.tag` theme word, h1 at `.h2` size, price, size options as large selectable **cards** (radius 12px, 1px border, 2px accent border when selected, 56px tall, title + price per option), quantity, full-width primary pill "Add to Bag", secondary text link "Buy it now"/dynamic checkout, then trust row (icons + 14px text), scripture as a quiet centred card, accordions. Mobile: gallery as full-bleed snap carousel with dots; sticky bottom "Add to Bag" bar (translucent material + safe-area) when the main button scrolls out of view.

### Collection
Centred title + description, toolbar (count left, sort right) as quiet 14px controls, filter chips; product tiles 3-up desktop, 2-up tablet, 1-up phone? (2-up on phone is acceptable with compact tile padding — decide by readability: 2-up with 16px padding, title 15px).

### Cart
Sheet (above) and page: line items as rows with 80px rounded images, 17px titles, quantity stepper pill, right-aligned prices; summary as a `--c-surface` tile; primary pill "Check Out" full width.

### Content pages (about, science, contact, blog, article, 404, password, accounts)
Centred page-hero (eyebrow, h1, lead) on white; body at `--text-max`; tiles for grouped facts; article body 19px/1.58 like Apple Newsroom; blog = tiles grid.

---

## 6. Never in the Apple redesign
Serif type; italic display type; uppercase letter-spaced eyebrows; gold; ornament dividers; hairlines between every section; heavy borders on cards; drop-shadows on flat tiles; centred body paragraphs longer than 3 lines (centre headlines and short leads only); colourful backgrounds behind text other than the 5 schemes.
