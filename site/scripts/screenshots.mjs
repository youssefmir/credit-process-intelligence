/**
 * Captures du rapport pour la documentation (docs/img/), prises une fois les animations
 * terminées. Lance `vite preview` en arrière-plan sur un port dédié, puis l'arrête.
 *
 *   npm run build && node scripts/screenshots.mjs
 *
 * Formats : 1440 × 900 (ordinateur) et 390 × 844 (mobile), thème clair pour la série
 * principale, PNG optimisés (moins de 300 Ko chacun).
 */
import { spawn } from "node:child_process";
import { mkdirSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import sharp from "sharp";

const here = dirname(fileURLToPath(import.meta.url));
const siteDir = resolve(here, "..");
const outDir = resolve(siteDir, "..", "docs", "img");
const port = 4174;
const basePath = process.env.BASE_PATH ?? "/credit-process-intelligence/";
const url = `http://127.0.0.1:${port}${basePath}`;
const MAX_BYTES = 300 * 1024;

const server = spawn(resolve(siteDir, "node_modules/.bin/vite"), ["preview", "--port", String(port), "--strictPort", "--host", "127.0.0.1"], {
  cwd: siteDir,
  stdio: "ignore",
});

async function waitForServer() {
  for (let i = 0; i < 80; i++) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`Le serveur de prévisualisation ne répond pas sur ${url}`);
}

async function save(page, name) {
  const raw = await page.screenshot({ type: "png" });
  let quality = 90;
  let buf = await sharp(raw).png({ palette: true, quality, effort: 10, compressionLevel: 9 }).toBuffer();
  while (buf.length > MAX_BYTES && quality > 40) {
    quality -= 10;
    buf = await sharp(raw).png({ palette: true, quality, effort: 10, compressionLevel: 9 }).toBuffer();
  }
  const path = resolve(outDir, `${name}.png`);
  await sharp(buf).toFile(path);
  console.log(`${name}.png  ${Math.round(statSync(path).size / 1024)} Ko`);
}

async function scrollTo(page, selector, offset = 72) {
  await page.evaluate(
    ([sel, off]) => {
      const el = document.querySelector(sel);
      if (!el) throw new Error(`introuvable : ${sel}`);
      window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - off);
    },
    [selector, offset],
  );
  await page.waitForTimeout(1800);
}

/** Fait défiler toute la page pour déclencher les apparitions, puis revient en haut. */
async function warmUp(page) {
  const height = await page.evaluate(() => document.body.scrollHeight);
  for (let y = 0; y < height; y += 700) {
    await page.evaluate((v) => window.scrollTo(0, v), y);
    await page.waitForTimeout(90);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
}

mkdirSync(outDir, { recursive: true });
try {
  await waitForServer();
  const browser = await chromium.launch();
  try {
    // Ouverture, clair et sombre, ordinateur.
    for (const scheme of ["light", "dark"]) {
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: scheme });
      const page = await ctx.newPage();
      await page.goto(url, { waitUntil: "networkidle" });
      await page.waitForTimeout(7000);
      await save(page, scheme === "light" ? "ouverture-clair" : "ouverture-sombre");
      await ctx.close();
    }

    // Série principale (clair, ordinateur).
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "light" });
    const page = await ctx.newPage();
    await page.goto(url, { waitUntil: "networkidle" });
    await page.getByRole("button", { name: /Mettre en pause le rejeu/ }).click();
    await warmUp(page);
    const shots = [
      ["#synthese", "synthese"],
      [".pm", "carte-processus", 140],
      ["#temps .waffle", "temps-perdu", 200],
      ["#prediction .acceptance", "prediction", 110],
      ["#business-case .opp-table", "business-case", 120],
      [".sim", "simulateur", 120],
      ["#conformite .timeline", "conformite", 220],
    ];
    for (const [selector, name, offset] of shots) {
      await scrollTo(page, selector, offset ?? 72);
      if (name === "carte-processus") {
        // Mode performance, puis déplacement jusqu'au cœur du processus (offre → validation).
        await page.getByRole("button", { name: "Performance" }).click();
        const box = await page.locator(".pm-canvas").boundingBox();
        if (box) {
          const y = box.y + box.height / 2;
          for (let i = 0; i < 1; i++) {
            await page.mouse.move(box.x + box.width - 60, y);
            await page.mouse.down();
            await page.mouse.move(box.x + 120, y, { steps: 12 });
            await page.mouse.up();
          }
        }
        await page.waitForTimeout(600);
      }
      await save(page, name);
    }
    await scrollTo(page, ".bpmn", 150);
    await page.getByRole("tab", { name: /TO-BE/ }).click();
    await page.waitForTimeout(1500);
    await save(page, "bpmn-to-be");
    await ctx.close();

    // Mobile.
    const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: "light", deviceScaleFactor: 1 });
    const mpage = await mctx.newPage();
    await mpage.goto(url, { waitUntil: "networkidle" });
    await mpage.waitForTimeout(5000);
    await save(mpage, "mobile-clair");
    await mctx.close();
  } finally {
    await browser.close();
  }
} finally {
  server.kill();
}
