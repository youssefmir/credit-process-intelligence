/** Formats français : espace fine insécable pour les milliers, virgule décimale. */

const NNBSP = "\u202f";
const NBSP = "\u00a0";

export function num(x: number | null | undefined, digits = 0): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n.d.";
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
    .format(x)
    .replace(/\u00a0|\s/g, NNBSP)
    .replace(/^-/, "\u2212");
}

export function pct(x: number | null | undefined, digits = 0): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n.d.";
  return `${num(x * 100, digits)}${NBSP}%`;
}

/**
 * Part de tirages : un événement rare mais observé ne s'affiche pas « 0 % » (ni « 100 % »).
 * `compact` pour les tableaux et étiquettes : « < 1 % » au lieu de « moins de 1 % ».
 */
export function share(x: number | null | undefined, compact = false): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n.d.";
  if (x > 0 && x < 0.005) return compact ? `<${NBSP}1${NBSP}%` : `moins de 1${NBSP}%`;
  if (x < 1 && x >= 0.995) return compact ? `>${NBSP}99${NBSP}%` : `plus de 99${NBSP}%`;
  return pct(x);
}

export function eur(x: number | null | undefined, digits = 0): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n.d.";
  return `${num(x, digits)}${NBSP}€`;
}

/** Montant en milliers d'euros signé : « +48 k€ », « −89 k€ ». */
export function keur(x: number | null | undefined, digits = 0, signed = false): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n.d.";
  const v = x / 1000;
  const sign = signed && v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sign}${num(Math.abs(v), digits)}${NBSP}k€`;
}

export function days(x: number | null | undefined, digits = 1): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n.d.";
  return `${num(x, digits)}${NBSP}j`;
}

/** Durée en heures exprimée en « 1 h 26 ». */
export function hoursMinutes(hours: number): string {
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (m === 60) return `${h + 1}${NBSP}h`;
  return h > 0 ? `${h}${NBSP}h${NBSP}${String(m).padStart(2, "0")}` : `${m}${NBSP}min`;
}

export function dateFr(d: Date): string {
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });
}

export { NBSP, NNBSP };
