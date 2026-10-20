// Renders the LinkedIn graphics from the HTML sources.
// Usage: node render.mjs   (run from the `source` folder)
// Outputs go to ../carousel/*.png, ../carousel/*.pdf and ../hero-square.png
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const here = path.dirname(fileURLToPath(import.meta.url));
const outCarousel = path.resolve(here, '..', 'carousel');
fs.mkdirSync(outCarousel, { recursive: true });

const browser = await chromium.launch();

// ---- Carousel: 6 slides at 1080x1350, exported as PNG (2x) and a single PDF ----
{
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(here, 'slides.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  const slides = page.locator('section.slide');
  const n = await slides.count();
  for (let i = 0; i < n; i++) {
    const file = path.join(outCarousel, `slide-${String(i + 1).padStart(2, '0')}.png`);
    await slides.nth(i).screenshot({ path: file, type: 'png' });
    console.log('wrote', file);
  }
  const pdf = path.join(outCarousel, 'encyclopedia-of-polyphenols-carousel.pdf');
  await page.pdf({ path: pdf, width: '1080px', height: '1350px', printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 }, preferCSSPageSize: true });
  console.log('wrote', pdf);
  await page.close();
}

// ---- Single square image: 1080x1080 at 2x ----
{
  const page = await browser.newPage({ viewport: { width: 1080, height: 1080 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(here, 'hero.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  const file = path.resolve(here, '..', 'hero-square.png');
  await page.locator('section.slide').first().screenshot({ path: file, type: 'png' });
  console.log('wrote', file);
  await page.close();
}

await browser.close();
