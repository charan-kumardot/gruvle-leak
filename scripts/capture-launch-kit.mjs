/**
 * Captures real screenshots + a demo video walkthrough of the live
 * production site (https://gruvle-leak-web.vercel.app) for launch-kit/.
 * Everything here is a genuine recording of the actual deployed product —
 * nothing is mocked or hand-drawn.
 *
 * Usage: node scripts/capture-launch-kit.mjs
 * Requires: npx playwright install chromium (already done once per machine)
 */
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import path from "node:path";

const SITE = "https://gruvle-leak-web.vercel.app";
const ROOT = path.resolve(import.meta.dirname, "..", "launch-kit");
const SHOTS_DESKTOP = path.join(ROOT, "screenshots", "desktop");
const SHOTS_MOBILE = path.join(ROOT, "screenshots", "mobile");
const VIDEO_DIR = path.join(ROOT, "video");

for (const dir of [SHOTS_DESKTOP, SHOTS_MOBILE, VIDEO_DIR]) mkdirSync(dir, { recursive: true });

async function shootDesktop(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  const page = await context.newPage();

  await page.goto(SITE, { waitUntil: "load" });
  await page.waitForTimeout(2800); // let the hero's staggered entrance + logo draw-in finish
  await page.screenshot({ path: path.join(SHOTS_DESKTOP, "01-landing-hero.png") });

  await page.evaluate(() => document.querySelector("#live-demo")?.scrollIntoView({ behavior: "instant", block: "start" }));
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(SHOTS_DESKTOP, "02-live-demo-picker.png") });

  // Run the live demo for a real, non-mocked screenshot of actual findings
  const shopifyPill = page.getByRole("button", { name: "SaaS" });
  if (await shopifyPill.isVisible().catch(() => false)) {
    await shopifyPill.click();
    await page.waitForTimeout(4500); // loading-step animation + real API round trip
    await page.screenshot({ path: path.join(SHOTS_DESKTOP, "03-live-demo-results.png"), fullPage: false });

    const firstFinding = page.locator("#live-demo button").filter({ hasText: /View evidence/ }).first();
    if (await firstFinding.isVisible().catch(() => false)) {
      await firstFinding.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(SHOTS_DESKTOP, "04-live-demo-evidence.png") });
    }
  }

  await page.evaluate(() => document.querySelector("#pricing")?.scrollIntoView({ behavior: "instant", block: "start" }));
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(SHOTS_DESKTOP, "05-pricing.png") });

  await page.evaluate(() => document.querySelector("#faq")?.scrollIntoView({ behavior: "instant", block: "start" }));
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(SHOTS_DESKTOP, "06-faq.png") });

  await page.goto(`${SITE}/login`, { waitUntil: "load" });
  await page.screenshot({ path: path.join(SHOTS_DESKTOP, "07-login.png") });

  await page.goto(`${SITE}/signup`, { waitUntil: "load" });
  await page.screenshot({ path: path.join(SHOTS_DESKTOP, "08-signup.png") });

  await context.close();
}

async function shootMobile(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });
  const page = await context.newPage();

  await page.goto(SITE, { waitUntil: "load" });
  await page.waitForTimeout(2800);
  await page.screenshot({ path: path.join(SHOTS_MOBILE, "01-landing-hero.png") });

  await page.evaluate(() => document.querySelector("#live-demo")?.scrollIntoView({ behavior: "instant", block: "start" }));
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(SHOTS_MOBILE, "02-live-demo-picker.png") });

  await page.evaluate(() => document.querySelector("#pricing")?.scrollIntoView({ behavior: "instant", block: "start" }));
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(SHOTS_MOBILE, "03-pricing.png") });

  await context.close();
}

async function recordWalkthrough(browser) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: VIDEO_DIR, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();

  await page.goto(SITE, { waitUntil: "load" });
  await page.waitForTimeout(2200); // let the hero entrance animation play

  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
  await page.mouse.wheel(0, 900);
  await page.waitForTimeout(1200);
  await page.mouse.wheel(0, 900);
  await page.waitForTimeout(1200);

  await page.evaluate(() => document.querySelector("#live-demo")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  await page.waitForTimeout(1200);

  const saasPill = page.getByRole("button", { name: "SaaS" });
  if (await saasPill.isVisible().catch(() => false)) {
    await saasPill.click();
    await page.waitForTimeout(4800);

    const firstFinding = page.locator("#live-demo button").filter({ hasText: /View evidence/ }).first();
    if (await firstFinding.isVisible().catch(() => false)) {
      await firstFinding.click();
      await page.waitForTimeout(2000);
      await firstFinding.click();
      await page.waitForTimeout(600);
    }

    const retailPill = page.getByRole("button", { name: "Retail" });
    if (await retailPill.isVisible().catch(() => false)) {
      await retailPill.click();
      await page.waitForTimeout(4800);
    }
  }

  await page.evaluate(() => document.querySelector("#pricing")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  await page.waitForTimeout(1500);

  await context.close(); // finalizes the video file
}

const browser = await chromium.launch();
try {
  console.log("Capturing desktop screenshots...");
  await shootDesktop(browser);
  console.log("Capturing mobile screenshots...");
  await shootMobile(browser);
  console.log("Recording demo walkthrough video...");
  await recordWalkthrough(browser);
  console.log("Done. See launch-kit/screenshots and launch-kit/video.");
} finally {
  await browser.close();
}
