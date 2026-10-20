# LinkedIn launch kit: The Encyclopedia of Polyphenols

Everything needed for one LinkedIn post about the book.

| File | What it is | How to use it |
|---|---|---|
| `post-copy.md` | Three versions of the caption, plus the first-comment text and posting notes | Copy and paste into LinkedIn |
| `carousel/encyclopedia-of-polyphenols-carousel.pdf` | Six-slide carousel (1080 x 1350) | Upload as a **document** post |
| `carousel/slide-01.png` to `slide-06.png` | The same slides as individual images at 2x resolution | Previews, or for other platforms |
| `hero-square.png` | Single square image (1080 x 1080 at 2x) | Attach to an image post |

## Slide outline

1. Hook: "What do you actually know about the plant compounds in your food?"
2. A name is only a starting point (compound names as chips)
3. Four questions that build a fuller picture: food sources, absorption, metabolism, the research
4. Not all evidence weighs the same (evidence ladder from cells in a dish to human trials)
5. Polyphenols are not one thing (flavonoids, phenolic acids, stilbenes, lignans)
6. Call to action with the Amazon link and a scannable QR code

## Editing and re-rendering

The graphics are plain HTML and CSS in `source/`, so any wording or colour change is a text edit.

```bash
cd source
npm install playwright            # once; Chromium is downloaded on first install
node render.mjs                   # rewrites carousel/*.png, the PDF and hero-square.png
```

Colours live in the `:root` block at the top of `source/slides.html` and `source/hero.html`.
Fonts are Fraunces (headlines) and DM Sans (body), both bundled in `source/fonts/` under the SIL Open Font License.
The QR code in `source/qr-amazon.png` points at `https://www.amazon.com/dp/B0HMVCQSFP`.
