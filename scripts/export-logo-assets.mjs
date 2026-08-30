/**
 * Rasterizes the two logo SVGs (boxed favicon mark + transparent mark-only)
 * to PNG at standard sizes for launch-kit/brand/. Renders via a real
 * browser page so transparency and anti-aliasing are correct, rather than
 * hand-rolling an SVG rasterizer.
 */
import { chromium } from "playwright";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const OUT = path.join(ROOT, "launch-kit", "brand");
mkdirSync(OUT, { recursive: true });

const boxedSvg = readFileSync(path.join(ROOT, "web", "src", "app", "icon.svg"), "utf-8");
const markSvg = readFileSync(path.join(ROOT, "web", "public", "logo-mark.svg"), "utf-8");

const BOXED_SIZES = [16, 32, 48, 64, 128, 180, 192, 512, 1024];
const MARK_SIZES = [128, 512, 1024];

async function render(browser, svg, size, outPath, transparent) {
  const page = await browser.newPage({ viewport: { width: size, height: size } });
  await page.setContent(
    `<html><body style="margin:0;padding:0;width:${size}px;height:${size}px;">${svg.replace(
      /width="32" height="32"/,
      `width="${size}" height="${size}"`
    )}</body></html>`
  );
  await page.screenshot({ path: outPath, omitBackground: transparent });
  await page.close();
}

const browser = await chromium.launch();
try {
  for (const size of BOXED_SIZES) {
    await render(browser, boxedSvg, size, path.join(OUT, `icon-${size}.png`), false);
  }
  for (const size of MARK_SIZES) {
    await render(browser, markSvg, size, path.join(OUT, `mark-transparent-${size}.png`), true);
  }
  // A couple of conventionally-named copies for common launch-list requirements
  writeFileSync(path.join(OUT, "favicon-32.png"), readFileSync(path.join(OUT, "icon-32.png")));
  writeFileSync(path.join(OUT, "apple-touch-icon-180.png"), readFileSync(path.join(OUT, "icon-180.png")));
  writeFileSync(path.join(OUT, "social-profile-512.png"), readFileSync(path.join(OUT, "icon-512.png")));
  console.log("Done. See launch-kit/brand.");
} finally {
  await browser.close();
}
