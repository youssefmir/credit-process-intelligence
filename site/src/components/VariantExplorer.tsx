import { useMemo, useState } from "react";

import type { ActivityLabel, Outcome, Variant } from "../lib/data";
import { num, pct } from "../lib/format";
import { usePalette } from "../lib/theme";

interface Props {
  variants: Record<"milestones" | "complete", { n_variants: number; n_cases: number; variants: Variant[]; coverage_top: Record<string, number> }>;
  labels: ActivityLabel[];
}

type Filter = "all" | Exclude<Outcome, "open">;

const OUTCOME_LABEL: Record<Outcome, string> = {
  approved: "Approuvée",
  declined: "Refusée",
  cancelled: "Annulée",
  open: "En cours",
};

function dominant(v: Variant): Outcome {
  const entries = Object.entries(v.outcomes) as [Outcome, number][];
  return entries.sort((a, b) => b[1] - a[1])[0][0];
}

export default function VariantExplorer({ variants, labels }: Props) {
  const palette = usePalette();
  const [view, setView] = useState<"milestones" | "complete">("milestones");
  const [filter, setFilter] = useState<Filter>("all");
  const [limit, setLimit] = useState(10);
  const [open, setOpen] = useState<number | null>(1);
  const label = useMemo(() => Object.fromEntries(labels.map((l) => [l.code, l])), [labels]);
  const data = variants[view];
  const list = data.variants.filter((v) => filter === "all" || dominant(v) === filter);
  const maxShare = Math.max(...data.variants.map((v) => v.share));
  const longest = Math.max(...list.slice(0, limit).map((v) => v.activities.length), 2);
  const stepW = Math.max(4, Math.min(16, Math.floor(260 / (longest - 1))));
  const color: Record<Outcome, string> = {
    approved: palette.lineApproved,
    declined: palette.lineDeclined,
    cancelled: palette.lineCancelled,
    open: palette.context,
  };

  return (
    <div className="variants">
      <div className="controls">
        <div className="seg" role="group" aria-label="Vue des variantes">
          <button type="button" aria-pressed={view === "milestones"} onClick={() => { setView("milestones"); setOpen(1); }}>
            Jalons ({num(variants.milestones.n_variants)})
          </button>
          <button type="button" aria-pressed={view === "complete"} onClick={() => { setView("complete"); setOpen(1); }}>
            Avec les tâches ({num(variants.complete.n_variants)})
          </button>
        </div>
        <div className="seg" role="group" aria-label="Filtrer par issue">
          {(["all", "approved", "declined", "cancelled"] as Filter[]).map((f) => (
            <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)}>
              {f === "all" ? "Toutes" : OUTCOME_LABEL[f]}
            </button>
          ))}
        </div>
      </div>
      <p className="small muted">
        Les 5 premières variantes couvrent {pct(data.coverage_top["5"])} des dossiers, les 10 premières{" "}
        {pct(data.coverage_top["10"])}. Une variante est une séquence distincte d'étapes ; les répétitions immédiates
        d'une même tâche sont regroupées.
      </p>
      <ol className="variant-list">
        {list.slice(0, limit).map((v) => {
          const dom = dominant(v);
          const isOpen = open === v.rank;
          return (
            <li key={v.rank} className={isOpen ? "open" : ""}>
              <button type="button" className="variant-row" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : v.rank)}>
                <span className="variant-rank num">{v.rank}</span>
                <span className="variant-line" aria-hidden="true">
                  <svg width={stepW * Math.max(v.activities.length - 1, 1) + 12} height="14" viewBox={`0 0 ${stepW * Math.max(v.activities.length - 1, 1) + 12} 14`}>
                    <line x1="6" y1="7" x2={stepW * Math.max(v.activities.length - 1, 1) + 6} y2="7" stroke={color[dom]} strokeWidth="4" />
                    {v.activities.map((_, i) => (
                      <circle key={i} cx={6 + i * stepW} cy="7" r="4" fill={palette.stationFill} stroke={palette.stationStroke} strokeWidth="1.6" />
                    ))}
                  </svg>
                </span>
                <span className="variant-meta">
                  <span className="variant-outcome">
                    <span className="swatch" style={{ background: color[dom] }} />
                    {OUTCOME_LABEL[dom]} · {v.activities.length} étapes
                  </span>
                  <span className="variant-bar" aria-hidden="true">
                    <span style={{ width: `${(v.share / maxShare) * 100}%`, background: palette.ink }} />
                  </span>
                </span>
                <span className="variant-count num">
                  {num(v.count)} <span className="muted">({pct(v.share, 1)})</span>
                </span>
                <span className="variant-lead num muted">
                  {v.median_lead_time_d === null ? "—" : `${num(v.median_lead_time_d, 1)}\u00a0j`}
                </span>
              </button>
              {isOpen && (
                <ol className="variant-steps">
                  {v.activities.map((a, i) => (
                    <li key={`${a}-${i}`} className={`cat-${label[a]?.category ?? "x"}`}>
                      {label[a]?.label ?? a}
                    </li>
                  ))}
                </ol>
              )}
            </li>
          );
        })}
      </ol>
      {list.length > limit && (
        <button type="button" className="btn" onClick={() => setLimit((l) => l + 10)}>
          Afficher 10 variantes de plus
        </button>
      )}
      <p className="source">Colonnes : rang, parcours, issue majoritaire, dossiers (part), délai médian jusqu'à l'issue.</p>
    </div>
  );
}
