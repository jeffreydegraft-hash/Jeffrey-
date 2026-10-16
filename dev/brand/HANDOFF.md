# Brand handoff: put the merchant's real logo and artwork into the theme

Status (Oct 2026): the Apple-first theme on this branch is built and verified
(theme check 0 offenses, `dev/preview` interactions 45/45, gestures 13/13).
Every logo slot already renders the merchant's own file through
`snippets/brand-logo.liquid`; product photos come from Shopify product media.
What is still missing is the merchant's **logo, favicon and homepage/about
banner files**, which live in the live store's current theme and Files. Nothing
has been published; the owner must approve before anything goes to the store.

Design rules: `dev/docs/APPLE-SPEC.md` (§0 Brand integrity is binding) and
`dev/docs/CONVENTIONS.md`.

## What the brand looks like (public sources: product labels on the marketplaces)
- Wordmark "MOUNT OF OLIVES™"; descriptor line "THE ANOINTING OIL" under each oil's name.
- Label order: MOUNT OF OLIVES™ / oil / THE ANOINTING OIL / theme word / botanical / verse / volume.
- Per-scent label colours with floral or gold ornament on amber glass, mostly black caps.
- No pictorial emblem is known: never draw olive branches, leaves, doves or bottles.
- The olive accent in `config/settings_data.json` (#4A5A2A / #5F7034) is provisional:
  replace it with colours sampled from the real logo and labels (step 4).

## The owner prefers the current live site (Oct 2026)
After seeing the Apple-first rebuild, the owner said the current site looks better.
The live theme ("Updated copy of Mount of Olives") is the reference for the brand:
- Palette measured from the live homepage: deep green #2C3327 (announcement bar),
  cream #F8F7F3 / #FBF7F3 (top bars), gold #C5A263 (primary button), light grey #EFEFEF.
- Type: classic serif display set in uppercase with wide tracking ("THE ANOINTING OIL
  COLLECTION"), small uppercase tracked labels and navigation.
- Artwork: the hero is a photo of all eight amber bottles with hand-illustrated
  watercolour floral labels, each scent in its own colours (Rose of Sharon pink,
  Latter Rain blue, Hyssop purple, Spikenard green, Lily of the Valley lavender,
  Frankincense & Myrrh green and gold, Pomegranate red, Gethsemane yellow-green).
- Labels: "MOUNT of OLIVES™" wordmark, oil name in serif, "THE ANOINTING OIL" gold band,
  theme word in script (Radiance, Revitalize, Purification & Protection, Renewal,
  Illuminate, Restore, Eternal, Unscented), botanical and verse.
Any further work keeps this look; improvements go under the hood unless the owner asks.

## Steps once the Shopify connector is connected (read-only)
1. Run `queries/00-shop-identity.admin.graphql` and `queries/01-main-theme.admin.graphql`.
2. Run `queries/02-theme-brand-files.admin.graphql` with the MAIN theme id. It returns
   the live `config/settings_data.json`, `templates/*.json` and `sections/*.json`.
   Save the result and run `python3 -I tools/extract_theme_image_refs.py <file>` to list
   every `shopify://shop_images/...` reference (logo, favicon, banners).
3. Copy those references **verbatim** into this theme (never paste cdn.shopify.com URLs):
   | Live key | This theme |
   | --- | --- |
   | `current.logo` (or a vintage header `logo`) | `config/settings_data.json` → `current.logo` |
   | `current.logo_width` | `current.logo_width` (60–260, step 10) |
   | `current.favicon` | `current.favicon` |
   | any light/inverse logo picker | `current.logo_inverse` |
   | hero / image-banner / slideshow first image | `templates/index.json` → `sections.hero.settings.image` |
   | image-with-text / about images | `templates/index.json` story, `templates/page.about.json` |
   | footer logo (if separate) | `sections/footer-group.json` → `footer.settings.logo` |
   `queries/03-uploaded-files.admin.graphql` lists Content › Files; `queries/05-shop-brand.storefront.graphql`
   reads Settings › Brand (logo, square logo, cover image, brand colours).
4. Download the original logo and a label photo (URLs from query 03) into a new empty
   folder and run `python3 -I tools/brand_palette.py <file> 6`. Map the measured colours
   into `current.color_schemes` (accent and detail only, after contrast checks), keep the
   white / #F5F5F7 grounds, and show the owner the swatches before applying.
5. Re-render (`cd dev/preview && node render.mjs && node screenshot.mjs`), run
   `node interactions.mjs` and `node gestures.mjs`, `shopify theme check --path .`,
   then send the owner screenshots. Do not publish; push as an unpublished theme only
   when the owner says so.

## Open questions for the owner
- Approve the redesign (screenshots were sent in the build session).
- The hero and story fall back to products with handles `frankincense-myrrh-anointing-oil`
  and `gethsemane-anointing-oil-unscented`; confirm they exist.
- "Cosmeceutical" wording (tagline, science heading) was flagged by a marketplace; keep or change?
- Shorten the announcement bar to "Free US shipping on orders $45+."?
