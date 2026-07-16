/**
 * Exporte les modèles BPMN (docs/bpmn/*.bpmn) en SVG avec le moteur de rendu bpmn-js,
 * dans un navigateur sans interface (Playwright, Chromium). Aucun accès réseau.
 *
 *   node scripts/export-bpmn-svg.mjs
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..", "..");
const viewerJs = readFileSync(resolve(here, "..", "node_modules/bpmn-js/dist/bpmn-viewer.production.min.js"), "utf-8");
const css = ["diagram-js.css", "bpmn-js.css"].map((f) => readFileSync(resolve(here, "..", "node_modules/bpmn-js/dist/assets", f), "utf-8")).join("\n");

/** Identifiants de marqueurs déterministes (bpmn-js les tire au hasard) : même SVG à chaque export. */
function stableIds(svg) {
  const ids = new Map();
  // Les identifiants aléatoires comptent 25 caractères ; « marker-end » et consorts ne sont pas touchés.
  return svg.replace(/\bmarker-[a-z0-9]{10,}\b/g, (id) => {
    if (!ids.has(id)) ids.set(id, `marker-${ids.size + 1}`);
    return ids.get(id);
  });
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 2400, height: 1200 } });
  await page.setContent(`<!doctype html><html><head><style>${css} html,body,#c{margin:0;width:100%;height:100%;background:#fff}</style></head><body><div id="c"></div></body></html>`);
  await page.addScriptTag({ content: viewerJs });
  for (const name of ["as-is", "to-be"]) {
    const xml = readFileSync(resolve(root, "docs/bpmn", `${name}.bpmn`), "utf-8");
    const svg = await page.evaluate(async (x) => {
      const container = document.getElementById("c");
      container.innerHTML = "";
      // eslint-disable-next-line no-undef
      const viewer = new BpmnJS({ container, bpmnRenderer: { defaultFillColor: "#ffffff", defaultStrokeColor: "#111111", defaultLabelColor: "#111111" } });
      await viewer.importXML(x);
      const { svg } = await viewer.saveSVG();
      viewer.destroy();
      return svg;
    }, xml);
    const out = resolve(root, "docs/bpmn", `${name}.svg`);
    writeFileSync(out, `${stableIds(svg)}\n`);
    console.log(`SVG écrit : docs/bpmn/${name}.svg (${Math.round(svg.length / 1024)} Ko)`);
  }
} finally {
  await browser.close();
}
