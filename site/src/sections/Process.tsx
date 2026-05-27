import { lazy, Suspense } from "react";

import Figure from "../components/Figure";
import Reveal from "../components/Reveal";
import Section from "../components/Section";
import SegmentedBar from "../components/SegmentedBar";
import VariantExplorer from "../components/VariantExplorer";
import type { AllData } from "../lib/data";
import { num, pct } from "../lib/format";
import { usePalette } from "../lib/theme";

const ProcessMap = lazy(() => import("../components/ProcessMap"));

export default function Process({ data }: { data: AllData }) {
  const palette = usePalette();
  const outcomes = data.process.outcomes as { outcome: string; label: string; count: number; share: number }[];
  const conf = data.process.conformance;
  const ind = data.process.inductive;
  const variants = data.variants;
  const colors: Record<string, string> = {
    approved: palette.lineApproved,
    declined: palette.lineDeclined,
    cancelled: palette.lineCancelled,
    open: palette.ctx,
  };
  const labelOf = Object.fromEntries(data.labels.activities.map((a) => [a.code, a.label]));
  const topEdges = [...data.process.maps.milestones.edges]
    .filter((e) => !e.source.startsWith("__") && !e.target.startsWith("__"))
    .slice(0, 15);
  return (
    <Section
      id="parcours"
      num="03"
      kicker="Le parcours réel"
      title={<>5 parcours types couvrent {pct(variants.milestones.coverage_top["5"])} des demandes, mais seuls {pct(conf.first_time_right_share)} des prêts approuvés vont droit au but.</>}
      lede={
        <>
          Le process mining reconstitue le processus réel à partir du journal d'événements du système : chaque
          demande laisse une trace datée de ses étapes. On en déduit la carte des flux, les variantes (séquences
          distinctes d'étapes) et les écarts au chemin nominal.
        </>
      }
    >
      <div className="grid">
        <Reveal className="span-12">
          <Figure
            title="Issue des 13 087 demandes"
            subtitle="Une demande sur six seulement se conclut par un prêt."
            table={{
              columns: ["Issue", "Demandes", "Part"],
              rows: outcomes.map((o) => [o.label, num(o.count), pct(o.share, 1)]),
              numeric: [1, 2],
            }}
          >
            <SegmentedBar
              ariaLabel={outcomes.map((o) => `${o.label} ${pct(o.share)}`).join(", ")}
              segments={outcomes.map((o) => ({
                key: o.outcome,
                label: o.label,
                value: o.count,
                color: colors[o.outcome],
                textColor: o.outcome === "open" ? palette.ink : "#ffffff",
              }))}
            />
          </Figure>
        </Reveal>

        <Reveal className="span-12">
          <Figure
            title="Carte du processus observé"
            subtitle="Stations : activités ; liaisons : passages d'une activité à la suivante dans un même dossier."
            table={{
              columns: ["De", "Vers", "Passages", "Durée médiane"],
              rows: topEdges.map((e) => [
                labelOf[e.source] ?? e.source,
                labelOf[e.target] ?? e.target,
                num(e.count),
                e.median_h === undefined ? "—" : e.median_h < 48 ? `${num(e.median_h, 1)} h` : `${num(e.median_h / 24, 1)} j`,
              ]),
              numeric: [2, 3],
            }}
          >
            <Suspense fallback={<div className="pm-canvas placeholder">Chargement de la carte…</div>}>
              <ProcessMap maps={data.process.maps} />
            </Suspense>
          </Figure>
        </Reveal>

        <Reveal className="span-8">
          <Figure title="Explorateur de variantes" subtitle="Cliquez sur une variante pour dérouler ses étapes.">
            <VariantExplorer variants={variants} labels={data.labels.activities} />
          </Figure>
        </Reveal>

        <Reveal className="span-4 aside-col">
          <div className="callout">
            <p className="kicker">Conformité au chemin nominal</p>
            <p className="figure-number sm">{pct(conf.first_time_right_share)}</p>
            <p>
              des {num(conf.approved_cases)} prêts approuvés suivent le chemin nominal (une seule offre, aucune
              boucle « dossier incomplet »). Délai médian : {num(conf.median_lead_time_nominal_d, 1)} j contre{" "}
              {num(conf.median_lead_time_deviating_d, 1)} j pour les autres.
            </p>
            <p className="small muted">
              Écarts les plus fréquents (alignements pm4py) : {conf.extra_moves.slice(0, 2).map((m: { label: string; count: number }) => `${m.label.toLowerCase()} en trop (${num(m.count)})`).join(", ")}.
            </p>
          </div>
          <div className="callout">
            <p className="kicker">Modèle découvert automatiquement</p>
            <p>
              L'inductive miner reproduit {pct(ind.fitness)} du comportement observé (fitness) mais n'atteint qu'une
              précision de {num(ind.precision, 2)} : le modèle autorise bien plus de parcours qu'il n'en existe. La
              réalité est trop variable pour un modèle unique ; d'où l'analyse par variantes et un BPMN métier
              simplifié (section 08).
            </p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
