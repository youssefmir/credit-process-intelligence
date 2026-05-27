/**
 * Géométrie du plan de réseau : stations (étapes métier) et tracés entre stations.
 * Coordonnées dans un repère 1000 × 560 ; tracés à 45° façon plan de transport.
 */

export type StationId =
  | "depot"
  | "precheck"
  | "completion"
  | "offer"
  | "reoffer"
  | "returned"
  | "validation"
  | "missing"
  | "activated"
  | "declined"
  | "cancelled";

export type LineKind = "nominal" | "loop" | "approved" | "cancelled" | "declined";

export interface Station {
  id: StationId;
  label: string;
  x: number;
  y: number;
  terminus?: boolean;
  /** Position de l'étiquette relative à la station. */
  lx: number;
  ly: number;
  anchor: "start" | "middle" | "end";
}

export const VIEW = { x: 0, y: 66, w: 1000, h: 490 };

export const STATIONS: Station[] = [
  { id: "depot", label: "Dépôt", x: 40, y: 260, lx: 0, ly: -26, anchor: "start" },
  { id: "precheck", label: "Pré-contrôle", x: 170, y: 260, lx: 0, ly: -26, anchor: "middle" },
  { id: "completion", label: "Complétion", x: 330, y: 260, lx: 0, ly: -26, anchor: "middle" },
  { id: "offer", label: "Offre envoyée", x: 500, y: 260, lx: -48, ly: -58, anchor: "end" },
  { id: "reoffer", label: "Nouvelle offre", x: 500, y: 110, lx: 0, ly: -24, anchor: "middle" },
  { id: "returned", label: "Offre retournée", x: 650, y: 260, lx: 0, ly: -26, anchor: "middle" },
  { id: "validation", label: "Validation", x: 790, y: 260, lx: -48, ly: -58, anchor: "end" },
  { id: "missing", label: "Pièces manquantes", x: 790, y: 110, lx: 0, ly: -24, anchor: "middle" },
  { id: "activated", label: "Prêt activé", x: 960, y: 260, terminus: true, lx: 16, ly: -26, anchor: "end" },
  { id: "cancelled", label: "Annulée", x: 960, y: 400, terminus: true, lx: 16, ly: 38, anchor: "end" },
  { id: "declined", label: "Refusée", x: 40, y: 500, terminus: true, lx: -16, ly: 38, anchor: "start" },
];

export const BY_ID = Object.fromEntries(STATIONS.map((s) => [s.id, s])) as Record<StationId, Station>;

type Pt = [number, number];

const TRUNK: Partial<Record<string, Pt[]>> = {
  "depot>precheck": [[40, 260], [170, 260]],
  "precheck>completion": [[170, 260], [330, 260]],
  "completion>offer": [[330, 260], [500, 260]],
  "offer>returned": [[500, 260], [650, 260]],
  "returned>validation": [[650, 260], [790, 260]],
  "validation>activated": [[790, 260], [960, 260]],
  "offer>reoffer": [[500, 260], [460, 220], [460, 150], [500, 110]],
  "reoffer>offer": [[500, 110], [540, 150], [540, 220], [500, 260]],
  "validation>missing": [[790, 260], [750, 220], [750, 150], [790, 110]],
  "missing>validation": [[790, 110], [830, 150], [830, 220], [790, 260]],
};

function toCancelled(x: number): Pt[] {
  return [[x, 260], [x + 12, 272], [x + 12, 370], [x + 42, 400], [960, 400]];
}

function toDeclined(x: number): Pt[] {
  return [[x, 260], [x - 12, 272], [x - 12, 470], [x - 42, 500], [40, 500]];
}

/** Tracé d'un tronçon ; les sorties depuis « pièces manquantes » repassent par la validation. */
export function pathFor(from: StationId, to: StationId): Pt[] {
  const key = `${from}>${to}`;
  const direct = TRUNK[key];
  if (direct) return direct;
  if (from === "missing") {
    const back = TRUNK["missing>validation"] as Pt[];
    const rest = pathFor("validation", to);
    return [...back, ...rest.slice(1)];
  }
  const a = BY_ID[from];
  if (to === "cancelled" && a.y === 260) return toCancelled(a.x);
  if (to === "declined" && a.y === 260) return toDeclined(a.x);
  const b = BY_ID[to];
  return [[a.x, a.y], [b.x, b.y]];
}

export function kindFor(from: StationId, to: StationId): LineKind {
  if (to === "cancelled") return "cancelled";
  if (to === "declined") return "declined";
  if (to === "activated") return "approved";
  if (to === "reoffer" || to === "missing" || from === "reoffer" || from === "missing") return "loop";
  return "nominal";
}

export interface Track {
  from: StationId;
  to: StationId;
  kind: LineKind;
  points: Pt[];
  cum: number[];
  length: number;
}

export function makeTrack(from: StationId, to: StationId): Track {
  const points = pathFor(from, to);
  const cum = [0];
  for (let i = 1; i < points.length; i++) {
    const [x0, y0] = points[i - 1];
    const [x1, y1] = points[i];
    cum.push(cum[i - 1] + Math.hypot(x1 - x0, y1 - y0));
  }
  return { from, to, kind: kindFor(from, to), points, cum, length: cum[cum.length - 1] };
}

/** Point situé à la fraction p (0 → 1) du tracé. */
export function pointAt(track: Track, p: number): Pt {
  const d = Math.min(Math.max(p, 0), 1) * track.length;
  const { cum, points } = track;
  let i = 1;
  while (i < cum.length - 1 && cum[i] < d) i++;
  const seg = cum[i] - cum[i - 1] || 1;
  const t = (d - cum[i - 1]) / seg;
  const [x0, y0] = points[i - 1];
  const [x1, y1] = points[i];
  return [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t];
}

export function svgPath(points: Pt[]): string {
  return points.map(([x, y], i) => `${i ? "L" : "M"}${x} ${y}`).join(" ");
}

/** Épaisseur d'un tronçon proportionnelle à la racine du nombre de dossiers. */
export function strokeFor(cases: number, total: number): number {
  return 2 + 12 * Math.sqrt(cases / total);
}
