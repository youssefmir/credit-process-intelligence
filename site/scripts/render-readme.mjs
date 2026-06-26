/**
 * Contrôle du rendu du README : conversion Markdown → HTML avec un style proche de GitHub
 * (markdown-it, github-markdown-css, mermaid), puis capture pleine page par Playwright.
 *
 *   node scripts/render-readme.mjs
 *
 * Sortie : site/test-results/readme/README.html et readme-render.png (non versionnés).
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "@playwright/test";
import MarkdownIt from "markdown-it";

const here = dirname(fileURLToPath(import.meta.url));
const site = resolve(here, "..");
const root = resolve(site, "..");
const out = resolve(site, "test-results", "readme");
mkdirSync(out, { recursive: true });

const md = new MarkdownIt({ html: true, linkify: true, typographer: false });
const fence = md.renderer.rules.fence;
md.renderer.rules.fence = (tokens, idx, options, env, self) => {
  const token = tokens[idx];
  if (token.info.trim() === "mermaid") return `<pre class="mermaid">${md.utils.escapeHtml(token.content)}</pre>`;
  return fence(tokens, idx, options, env, self);
};

const body = md.render(readFileSync(resolve(root, "README.md"), "utf-8"));
const css = readFileSync(resolve(site, "node_modules/github-markdown-css/github-markdown-light.css"), "utf-8");
const mermaidJs = readFileSync(resolve(site, "node_modules/mermaid/dist/mermaid.min.js"), "utf-8");
const html = `<!doctype html><html lang="fr"><head><meta charset="utf-8"><base href="${pathToFileURL(root).href}/">
<style>${css} body{background:#fff;margin:0} .markdown-body{box-sizing:border-box;max-width:1012px;margin:0 auto;padding:32px 45px}</style>
</head><body><article class="markdown-body">${body}</article>
<script>${mermaidJs}</script>
<script>mermaid.initialize({ startOnLoad: false, theme: "neutral" }); mermaid.run().then(() => { document.body.dataset.ready = "1"; });</script>
</body></html>`;
const htmlPath = resolve(out, "README.html");
writeFileSync(htmlPath, html);

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(pathToFileURL(htmlPath).href);
  await page.waitForFunction(() => document.body.dataset.ready === "1", null, { timeout: 30_000 });
  const broken = await page.evaluate(() => [...document.images].filter((i) => !i.complete || i.naturalWidth === 0).map((i) => i.getAttribute("src")));
  const mermaidOk = await page.evaluate(() => document.querySelectorAll("pre.mermaid svg").length);
  await page.screenshot({ path: resolve(out, "readme-render.png"), fullPage: true });
  console.log(`Rendu : ${resolve(out, "readme-render.png")}`);
  console.log(`Diagrammes Mermaid rendus : ${mermaidOk} ; images cassées : ${broken.length ? broken.join(", ") : "aucune"}`);
  if (errors.length) console.log(`Erreurs : ${errors.join(" | ")}`);
  if (broken.length || errors.length) process.exitCode = 1;
} finally {
  await browser.close();
}
