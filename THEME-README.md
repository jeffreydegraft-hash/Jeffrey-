# Overflow: a Shopify theme for My Cup Runneth Over Anointing Oils

Overflow replaces the earlier Runneth design (kept at commit `a993a4a`). It is product-first,
in the way the best-selling direct-to-consumer stores are: a white page, near-black type and
pill buttons. Each oil's own label color tints its card, its photo background and its accents.

## What changed, and why

| Pattern from top stores | Where it lives |
| --- | --- |
| Hero shows a real person with the product, with two clear buttons | `sections/hero-lineup.liquid`: copy beside the lifestyle photo, then a shelf of all eight bottles. |
| Shop the range straight from the homepage, without carousels | `sections/oil-grid.liquid` + `snippets/oil-card.liquid`: all eight oils, each with its label meaning, verse and a one-tap Add to cart. |
| Guided selling quiz | `sections/oil-quiz.liquid`: two questions, then one oil with its verse and an Add to cart. Gift and church answers point to the collection. |
| Build-a-bundle to raise order value | `snippets/bundle-ui.liquid`: pick any six oils for the six-bottle product. The picks travel with the order as the line item property "Your oils". It is used on the homepage and on that product's own page. |
| Shipping, returns and secure checkout next to the buy button | `sections/main-product.liquid`, buy buttons block. |
| Upsell in the cart and on the product page | Cart drawer and product page link to the six-bottle collection. |
| Static announcement bar | One message, no rotation. |

The label text for every oil (meaning, verses, botanical source, label color) is in
`snippets/oil-data.liquid`.

## Settings to know

* **Theme settings › Cart › The Anointing Collection**: the six-bottle product, the oils it can
  contain, and how many bottles make a set.
* **Homepage › Hero: photo and bottles › Photo**: the lifestyle photo. Set its focal point on
  the face and bottle so phone crops keep both.
* **Homepage › Collection builder › Collection photo**: optional; defaults to the six-bottle
  product's photo.
* **Typography**: Harmonia Sans for headings and body, Playfair Display italic for Scripture.
