/**
 * Typographie française dans les textes de l'interface : espace insécable avant « : ; ? ! »,
 * à l'intérieur des guillemets « », et avant « % ». Ne touche que les textes JSX et les
 * chaînes (analyse syntaxique TypeScript), jamais le code.
 *
 *   node scripts/typo-fr.mjs          corrige les fichiers de src/
 *   node scripts/typo-fr.mjs --check  échoue si une correction est nécessaire
 */
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import ts from "typescript";

const NBSP = " ";
const check = process.argv.includes("--check");

function fixText(text) {
  return text
    .replace(/ ([:;?!»%])/g, `${NBSP}$1`)
    .replace(/« /g, `«${NBSP}`);
}

function files(dir) {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? files(p) : /\.(tsx?|ts)$/.test(f) ? [p] : [];
  });
}

let changed = 0;
for (const file of files("src")) {
  const src = readFileSync(file, "utf-8");
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, file.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const edits = [];
  const visit = (node) => {
    const kinds = [ts.SyntaxKind.JsxText, ts.SyntaxKind.StringLiteral, ts.SyntaxKind.NoSubstitutionTemplateLiteral, ts.SyntaxKind.TemplateHead, ts.SyntaxKind.TemplateMiddle, ts.SyntaxKind.TemplateTail];
    if (kinds.includes(node.kind)) {
      // Les chaînes d'import, de classes CSS et de propriétés techniques sont ignorées.
      const parent = node.parent;
      const technical = parent && (ts.isImportDeclaration(parent) || ts.isExportDeclaration(parent) || (ts.isJsxAttribute(parent) && ["className", "id", "href", "role", "type", "position", "aria-controls", "htmlFor", "key"].includes(parent.name.getText())));
      if (!technical) {
        const start = node.getStart();
        const end = node.getEnd();
        const raw = src.slice(start, end);
        const fixed = fixText(raw);
        if (fixed !== raw) edits.push({ start, end, fixed });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  if (!edits.length) continue;
  changed += edits.length;
  if (check) {
    console.error(`${file} : ${edits.length} espace(s) insécable(s) manquante(s)`);
    continue;
  }
  let out = src;
  for (const e of edits.sort((a, b) => b.start - a.start)) out = out.slice(0, e.start) + e.fixed + out.slice(e.end);
  writeFileSync(file, out);
  console.log(`${file} : ${edits.length} correction(s)`);
}
if (check && changed) process.exit(1);
console.log(check ? "Typographie conforme." : `${changed} correction(s) au total.`);
