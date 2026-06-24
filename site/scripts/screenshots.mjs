/**
 * Captures du rapport pour la documentation (docs/img/), prises une fois les animations
 * terminées. Lance `vite preview` en arrière-plan sur un port dédié, puis l'arrête.
 *
 *   npm run build && node scripts/screenshots.mjs
 *
 * Formats : 1440 × 900 (ordinateur) et 390 × 844 (mobile), thème clair pour la série
 * principale, PNG optimisés (moins de 300 Ko chacun). L'ouverture est capturée telle quelle ;
 * les captures de détail sont recadrées sur un bloc (voir `frame` et `trim`).
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

const VIEW_H = 900;

/**
 * Cadre une capture sur l'essentiel, comme un recadrage : la barre de navigation fixe est
 * masquée, le bloc `from` est posé en haut du cadre et le bloc `through` doit tenir en entier
 * (la marge haute s'adapte, de 32 à 8 px). Les blocs coupés par un bord du cadre sont masqués.
 */
async function frame(page, from, through = from) {
  const span = await page.evaluate(
    ([a, b]) => {
      for (const el of document.querySelectorAll("[data-shot-hidden]")) {
        el.style.visibility = "";
        el.removeAttribute("data-shot-hidden");
      }
      document.querySelector(".topbar").style.visibility = "hidden";
      const top = document.querySelector(a);
      const end = document.querySelector(b);
      if (!top || !end) throw new Error(`introuvable : ${top ? b : a}`);
      return end.getBoundingClientRect().bottom - top.getBoundingClientRect().top;
    },
    [from, through],
  );
  const margin = Math.max(8, Math.min(32, Math.floor((VIEW_H - span) / 2)));
  if (span + margin > VIEW_H) console.warn(`Attention : « ${through} » dépasse le cadre de ${Math.round(span + margin - VIEW_H)} px`);
  await page.evaluate(
    ([sel, m]) => {
      const el = document.querySelector(sel);
      window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - m);
    },
    [from, margin],
  );
  await page.waitForTimeout(1800);
}

/** Masque les blocs coupés par le haut ou le bas du cadre (après les interactions). */
async function trim(page) {
  await page.evaluate(() => {
    const vh = window.innerHeight;
    const blocks = document.querySelectorAll(
      ".section-head > *, .wrap > :not(.grid), .grid > *, .wrap p, .wrap li, .wrap tr",
    );
    for (const el of blocks) {
      const r = el.getBoundingClientRect();
      if ((r.top < 0 && r.bottom > 0) || (r.top < vh && r.bottom > vh)) {
        el.style.visibility = "hidden";
        el.setAttribute("data-shot-hidden", "");
      }
    }
  });
  await page.waitForTimeout(150);
}

/**
 * Carte en mode performance, station « Offre envoyée » isolée et centrée : horizontalement
 * sur la station, verticalement entre ses deux issues (offre retournée, offre annulée).
 */
async function focusOfferSent(page) {
  await page.getByRole("button", { name: "Performance" }).click();
  await page.waitForTimeout(500);
  const canvas = await page.locator(".pm-canvas").boundingBox();
  const node = (text) => page.locator(".react-flow__node", { hasText: text }).first();
  const center = async (text) => {
    const b = await node(text).boundingBox();
    return b ? { x: b.x + b.width / 2, y: b.y + b.height / 2 } : null;
  };
  // Glissements successifs (chacun reste dans le canevas) jusqu'au cadrage voulu.
  for (let i = 0; i < 5 && canvas; i++) {
    const [sent, back, cancelled] = await Promise.all(["Offre envoyée", "Offre retournée", "Offre annulée"].map(center));
    if (!sent || !back || !cancelled) break;
    const dx = sent.x - (canvas.x + canvas.width / 2);
    const dy = (back.y + cancelled.y) / 2 - (canvas.y + canvas.height / 2);
    if (Math.abs(dx) < 4 && Math.abs(dy) < 4) break;
    const sx = Math.max(-(canvas.width - 120), Math.min(canvas.width - 120, dx));
    const sy = Math.max(-(canvas.height - 120), Math.min(canvas.height - 120, dy));
    const cx = canvas.x + canvas.width / 2;
    // Départ sur le fond de carte, loin des stations (bord haut ou bas selon le sens).
    const y0 = sy >= 0 ? canvas.y + 16 + sy : canvas.y + canvas.height - 16 + sy;
    await page.mouse.move(cx + sx / 2, Math.max(canvas.y + 8, Math.min(canvas.y + canvas.height - 8, y0)));
    await page.mouse.down();
    await page.mouse.move(cx - sx / 2, Math.max(canvas.y + 8, Math.min(canvas.y + canvas.height - 8, y0 - sy)), { steps: 16 });
    await page.mouse.up();
    await page.waitForTimeout(200);
  }
  await page.waitForTimeout(400);
  await node("Offre envoyée").click();
  await page.waitForTimeout(800);
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
      ["synthese", "#synthese .section-head", "#synthese .findings"],
      ["carte-processus", "#parcours .grid > :nth-child(2)", "#parcours .grid > :nth-child(2)", focusOfferSent],
      ["temps-perdu", "#temps .section-head", "#temps .grid > :nth-child(2)"],
      ["prediction", "#prediction .grid > :nth-child(3)", "#prediction .grid > :nth-child(7)"],
      ["business-case", "#business-case .section-head", "#business-case .opp-table"],
      ["simulateur", "#business-case .grid > :nth-child(4)", "#business-case .grid > :nth-child(4)"],
      ["conformite", "#conformite .wrap > :nth-child(2)", "#conformite .wrap > :nth-child(3)"],
    ];
    for (const [name, from, through, prepare] of shots) {
      await frame(page, from, through);
      if (prepare) await prepare(page);
      await trim(page);
      await save(page, name);
    }
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
