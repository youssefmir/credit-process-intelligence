import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { loadReplay, type Replay } from "../lib/data";
import { num } from "../lib/format";
import { useReducedMotion } from "../lib/motion";
import {
  BY_ID,
  makeTrack,
  STATIONS,
  strokeFor,
  svgPath,
  VIEW,
  type LineKind,
  type StationId,
  type Track,
} from "../lib/network";
import { usePalette, type Palette } from "../lib/theme";

/** Durée de lecture du journal complet à vitesse 1× (millisecondes). */
const BASE_DURATION_MS = 48_000;
/** Durée minimale d'affichage d'un tronçon (minutes simulées) pour voir les transitions instantanées. */
const MIN_LEG_MIN = 6 * 60;
const SPEEDS = [0.5, 1, 2, 4];
/** Les tronçons très rares (moins de 10 dossiers) ne sont pas dessinés. */
const MIN_DRAWN_CASES = 10;
const TERMINI: StationId[] = ["activated", "declined", "cancelled"];

interface Prepared {
  ids: StationId[];
  t0: Date;
  total: number;
  starts: Float64Array;
  offsets: Int32Array;
  stations: Int8Array;
  times: Float64Array;
  finishTimes: Record<string, Float64Array>;
  tracks: Map<string, Track>;
  transitions: { from: StationId; to: StationId; cases: number }[];
  n: number;
}

function prepare(r: Replay): Prepared {
  const ids = r.stations.map((s) => s.id as StationId);
  const n = r.cases.length;
  const offsets = new Int32Array(n + 1);
  let total = 0;
  for (let i = 0; i < n; i++) {
    offsets[i] = total;
    total += r.cases[i].length / 2;
  }
  offsets[n] = total;
  const stations = new Int8Array(total);
  const times = new Float64Array(total);
  const starts = new Float64Array(n);
  const finish: Record<string, number[]> = { activated: [], declined: [], cancelled: [] };
  for (let i = 0; i < n; i++) {
    const flat = r.cases[i];
    let t = 0;
    let prevVisual = -Infinity;
    for (let k = 0; k < flat.length / 2; k++) {
      t = k === 0 ? flat[1] : t + flat[2 * k + 1];
      const visual = k === 0 ? t : Math.max(t, prevVisual + MIN_LEG_MIN);
      stations[offsets[i] + k] = flat[2 * k];
      times[offsets[i] + k] = visual;
      prevVisual = visual;
    }
    starts[i] = times[offsets[i]];
    const last = ids[stations[offsets[i + 1] - 1]];
    if (last in finish) finish[last].push(times[offsets[i + 1] - 1]);
  }
  const tracks = new Map<string, Track>();
  for (const tr of r.transitions) {
    tracks.set(`${tr.from}>${tr.to}`, makeTrack(tr.from as StationId, tr.to as StationId));
  }
  const finishTimes: Record<string, Float64Array> = {};
  for (const [k, v] of Object.entries(finish)) finishTimes[k] = Float64Array.from(v.sort((a, b) => a - b));
  return {
    ids,
    t0: new Date(r.t0),
    total: r.minutes + MIN_LEG_MIN * 3,
    starts,
    offsets,
    stations,
    times,
    finishTimes,
    tracks,
    transitions: r.transitions.map((t) => ({ ...t, from: t.from as StationId, to: t.to as StationId })),
    n,
  };
}

function countBefore(sorted: Float64Array, t: number): number {
  let lo = 0;
  let hi = sorted.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (sorted[mid] <= t) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

function lineColor(kind: LineKind, p: Palette): string {
  switch (kind) {
    case "loop":
      return p.lineLoop;
    case "approved":
      return p.lineApproved;
    case "cancelled":
      return p.lineCancelled;
    case "declined":
      return p.lineDeclined;
    default:
      return p.lineNominal;
  }
}

const KIND_ORDER: LineKind[] = ["declined", "cancelled", "nominal", "approved", "loop"];
const KIND_LABEL: Record<LineKind, string> = {
  nominal: "Parcours nominal",
  loop: "Boucle de reprise",
  approved: "Vers le prêt activé",
  cancelled: "Vers l'annulation",
  declined: "Vers le refus",
};

interface Props {
  compactBreakpoint?: number;
  autoplay?: boolean;
}

export default function NetworkReplay({ compactBreakpoint = 640, autoplay = true }: Props) {
  const palette = usePalette();
  const reduced = useReducedMotion();
  const [data, setData] = useState<Prepared | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [t, setT] = useState(0);
  const [width, setWidth] = useState(1000);
  const [showTable, setShowTable] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const tRef = useRef(0);
  const pointers = useRef<Int32Array | null>(null);
  const visible = useRef(true);
  const started = useRef(false);

  useEffect(() => {
    let alive = true;
    loadReplay()
      .then((r) => {
        if (!alive) return;
        const p = prepare(r);
        pointers.current = new Int32Array(p.n);
        setData(p);
      })
      .catch((e: unknown) => alive && setError(String(e)));
    return () => {
      alive = false;
    };
  }, []);

  // Taille du conteneur.
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  // Démarrage : lecture automatique une seule fois (sauf mouvement réduit : état final).
  useEffect(() => {
    if (!data || started.current) return;
    started.current = true;
    if (reduced || !autoplay) {
      tRef.current = data.total;
      setT(data.total);
      return;
    }
    setPlaying(true);
  }, [data, reduced, autoplay]);

  // Pause hors écran.
  useEffect(() => {
    const el = wrapRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver((entries) => {
      visible.current = entries.some((e) => e.isIntersecting);
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const draw = useCallback(
    (time: number) => {
      const canvas = canvasRef.current;
      const d = data;
      if (!canvas || !d) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const s = (w / VIEW.w) * dpr;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.setTransform(s, 0, 0, s, -VIEW.x * s, -VIEW.y * s);
      const ptr = pointers.current as Int32Array;
      const r = w < compactBreakpoint ? 5.5 : 3.4;
      // Tous les dossiers ont la même couleur (encre) : c'est la ligne empruntée qui dit où ils vont.
      const colors: Record<LineKind, string> = {
        nominal: palette.ink,
        loop: palette.ink,
        approved: palette.ink,
        cancelled: palette.ink,
        declined: palette.ink,
      };
      const buckets: Record<LineKind, number[]> = {
        nominal: [],
        loop: [],
        approved: [],
        cancelled: [],
        declined: [],
      };
      for (let i = 0; i < d.n; i++) {
        if (time < d.starts[i]) continue;
        const a = d.offsets[i];
        const b = d.offsets[i + 1];
        if (b - a < 2) continue;
        if (time >= d.times[b - 1]) continue;
        let k = ptr[i];
        if (k < a || k >= b - 1 || d.times[k] > time) k = a;
        while (k < b - 2 && d.times[k + 1] <= time) k++;
        ptr[i] = k;
        const from = d.ids[d.stations[k]];
        const to = d.ids[d.stations[k + 1]];
        const track = d.tracks.get(`${from}>${to}`);
        if (!track) continue;
        const span = d.times[k + 1] - d.times[k] || 1;
        const p = (time - d.times[k]) / span;
        const pt = pointOnTrack(track, p);
        buckets[track.kind].push(pt[0], pt[1]);
      }
      for (const kind of KIND_ORDER) {
        const pts = buckets[kind];
        if (!pts.length) continue;
        // Points semi-opaques : là où les dossiers s'accumulent, la ligne s'assombrit (file d'attente).
        ctx.fillStyle = colors[kind];
        ctx.globalAlpha = 0.55;
        ctx.beginPath();
        for (let j = 0; j < pts.length; j += 2) {
          ctx.moveTo(pts[j] + r, pts[j + 1]);
          ctx.arc(pts[j], pts[j + 1], r, 0, Math.PI * 2);
        }
        ctx.fill();
        ctx.globalAlpha = 1;
      }
    },
    [data, palette, compactBreakpoint],
  );

  // Boucle d'animation.
  useEffect(() => {
    if (!data || !playing) return;
    let raf = 0;
    let last = performance.now();
    let lastUi = 0;
    const perMs = data.total / BASE_DURATION_MS;
    const tick = (now: number) => {
      const dt = Math.min(now - last, 64);
      last = now;
      if (visible.current) {
        tRef.current = Math.min(tRef.current + dt * perMs * speed, data.total);
        draw(tRef.current);
        if (now - lastUi > 120 || tRef.current >= data.total) {
          setT(tRef.current);
          lastUi = now;
        }
        if (tRef.current >= data.total) {
          setPlaying(false);
          return;
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [data, playing, speed, draw]);

  // Redessin hors lecture (thème, taille, curseur).
  useEffect(() => {
    if (!playing) draw(tRef.current);
  }, [draw, playing, width, t]);

  const compact = width < compactBreakpoint;
  const counts = useMemo(() => {
    if (!data) return null;
    const done = TERMINI.map((k) => countBefore(data.finishTimes[k], t));
    let startedN = 0;
    for (let i = 0; i < data.n; i++) if (data.starts[i] <= t) startedN++;
    const finished = done.reduce((a, b) => a + b, 0);
    return { activated: done[0], declined: done[1], cancelled: done[2], inProgress: startedN - finished };
  }, [data, t]);

  const clock = data ? new Date(data.t0.getTime() + Math.min(t, data.total - MIN_LEG_MIN * 3) * 60_000) : null;
  const atEnd = data ? t >= data.total : false;
  const total = data?.n ?? 0;

  const onPlay = () => {
    if (!data) return;
    if (atEnd) {
      tRef.current = 0;
      pointers.current?.fill(0);
      setT(0);
    }
    setPlaying((p) => !p);
  };

  const onScrub = (v: number) => {
    tRef.current = v;
    pointers.current?.fill(0);
    setT(v);
  };

  const tracks = data ? [...data.tracks.values()] : [];
  const casesByKey = new Map(data?.transitions.map((tr) => [`${tr.from}>${tr.to}`, tr.cases]) ?? []);
  const sorted = [...tracks].sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind));
  const labelSize = compact ? 30 : 15;

  return (
    <figure className="replay" aria-labelledby="replay-title">
      <figcaption className="replay-head">
        <div>
          <p id="replay-title" className="chart-title">
            Le journal réel rejoué : {num(total)} demandes, octobre 2011 → mars 2012
          </p>

        </div>
      </figcaption>

      <div ref={wrapRef} className="replay-stage">
        <svg
          viewBox={`${VIEW.x} ${VIEW.y} ${VIEW.w} ${VIEW.h}`}
          role="img"
          aria-label="Plan du processus de crédit : stations du dépôt au prêt activé, avec les branches vers le refus et l'annulation et les boucles de reprise."
        >
          {sorted.map((tr) => {
            const cases = casesByKey.get(`${tr.from}>${tr.to}`) ?? 0;
            if (cases < MIN_DRAWN_CASES) return null;
            const width = strokeFor(cases, total || 1);
            const color = lineColor(tr.kind, palette);
            return (
              <g key={`${tr.from}>${tr.to}`}>
                {tr.kind === "loop" && (
                  <path d={svgPath(tr.points)} fill="none" stroke={palette.casing} strokeWidth={width + 3} strokeLinejoin="round" strokeLinecap="round" />
                )}
                <path d={svgPath(tr.points)} fill="none" stroke={color} strokeWidth={width} strokeLinejoin="round" strokeLinecap="round" />
              </g>
            );
          })}
          {STATIONS.map((s, i) => {
            const rad = s.terminus ? 13 : 9;
            return (
              <g key={s.id}>
                <circle cx={s.x} cy={s.y} r={rad} fill={palette.stationFill} stroke={palette.stationStroke} strokeWidth={s.terminus ? 5 : 3.5} />
                {compact ? (
                  <text x={s.x} y={s.y + (s.y > 300 ? 52 : -24)} textAnchor="middle" fontSize={labelSize} fontWeight={750} fill={palette.ink} className="station-label">
                    {i + 1}
                  </text>
                ) : (
                  <text x={s.x + s.lx} y={s.y + s.ly} textAnchor={s.anchor} fontSize={labelSize} fontWeight={s.terminus ? 750 : 600} fill={palette.ink} className="station-label">
                    {s.label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
        <canvas ref={canvasRef} className="replay-canvas" aria-hidden="true" />
        {!data && !error && <p className="replay-loading">Chargement du journal…</p>}
        {error && <p className="replay-loading">Données indisponibles : {error}</p>}
      </div>

      {compact && (
        <ol className="replay-legend-compact">
          {STATIONS.map((s) => (
            <li key={s.id}>{s.label}</li>
          ))}
        </ol>
      )}

      <div className="replay-controls">
        <button type="button" className="btn primary" onClick={onPlay} disabled={!data} aria-label={playing ? "Mettre en pause le rejeu" : atEnd ? "Rejouer depuis le début" : "Lancer le rejeu"}>
          <PlayIcon playing={playing} />
          {playing ? "Pause" : atEnd ? "Rejouer" : "Lecture"}
        </button>
        <div className="seg" role="group" aria-label="Vitesse de lecture">
          {SPEEDS.map((v) => (
            <button key={v} type="button" aria-pressed={speed === v} onClick={() => setSpeed(v)}>
              {String(v).replace(".", ",")}×
            </button>
          ))}
        </div>
        <label className="replay-scrub">
          <span className="sr-only">Position dans le temps</span>
          <input
            type="range"
            min={0}
            max={data?.total ?? 1}
            step={60}
            value={Math.round(t)}
            onChange={(e) => onScrub(Number(e.target.value))}
            disabled={!data}
          />
        </label>
        <p className="replay-clock num" aria-live="off">
          {clock ? clock.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short", year: "numeric" }) : "—"}
        </p>
      </div>

      <dl className="replay-counters" aria-live="off">
        <div>
          <dt><span className="swatch" style={{ background: palette.ink }} />En cours</dt>
          <dd className="num">{counts ? num(counts.inProgress) : "—"}</dd>
        </div>
        <div>
          <dt><span className="swatch" style={{ background: palette.lineApproved }} />Prêt activé</dt>
          <dd className="num">{counts ? num(counts.activated) : "—"}</dd>
        </div>
        <div>
          <dt><span className="swatch" style={{ background: palette.lineDeclined }} />Refusée</dt>
          <dd className="num">{counts ? num(counts.declined) : "—"}</dd>
        </div>
        <div>
          <dt><span className="swatch" style={{ background: palette.lineCancelled }} />Annulée</dt>
          <dd className="num">{counts ? num(counts.cancelled) : "—"}</dd>
        </div>
      </dl>

      <div className="replay-foot">
        <ul className="replay-legend" aria-label="Légende des lignes">
          {(["nominal", "loop", "approved", "cancelled", "declined"] as LineKind[]).map((k) => (
            <li key={k}>
              <span className="swatch" style={{ background: lineColor(k, palette), outline: k === "loop" ? `1px solid ${palette.casing}` : undefined }} />
              {KIND_LABEL[k]}
            </li>
          ))}
        </ul>
        <button type="button" className="table-toggle" aria-expanded={showTable} onClick={() => setShowTable((v) => !v)}>
          {showTable ? "Masquer les données" : "Voir les données"}
        </button>
      </div>
      {showTable && data && (
        <div className="table-wrap">
          <table className="data">
            <caption className="sr-only">Nombre de dossiers par tronçon du plan</caption>
            <thead>
              <tr>
                <th>De</th>
                <th>Vers</th>
                <th className="r">Dossiers</th>
              </tr>
            </thead>
            <tbody>
              {data.transitions.map((tr) => (
                <tr key={`${tr.from}>${tr.to}`}>
                  <td>{BY_ID[tr.from].label}</td>
                  <td>{BY_ID[tr.to].label}</td>
                  <td className="r">{num(tr.cases)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="source">
        Chaque point est un dossier, qui avance d'étape en étape aux dates réelles du journal ; l'épaisseur d'une
        ligne est proportionnelle au nombre de dossiers qui l'empruntent. Source : BPI Challenge 2012 (van Dongen, 4TU.ResearchData). Durée d'affichage minimale de 6 h par tronçon
        pour rendre visibles les transitions quasi instantanées ; les compteurs suivent les dates réelles à quelques
        heures près.
      </p>
    </figure>
  );
}

function pointOnTrack(track: Track, p: number): [number, number] {
  const d = Math.min(Math.max(p, 0), 1) * track.length;
  const { cum, points } = track;
  let i = 1;
  while (i < cum.length - 1 && cum[i] < d) i++;
  const seg = cum[i] - cum[i - 1] || 1;
  const f = (d - cum[i - 1]) / seg;
  return [points[i - 1][0] + (points[i][0] - points[i - 1][0]) * f, points[i - 1][1] + (points[i][1] - points[i - 1][1]) * f];
}

function PlayIcon({ playing }: { playing: boolean }) {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" style={{ display: "inline-block" }}>
      {playing ? (
        <g fill="currentColor">
          <rect x="2" y="1" width="3.5" height="12" />
          <rect x="8.5" y="1" width="3.5" height="12" />
        </g>
      ) : (
        <path d="M3 1 L12 7 L3 13 Z" fill="currentColor" />
      )}
    </svg>
  );
}
