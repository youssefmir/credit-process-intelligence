import { motion, useReducedMotion } from "motion/react";
import { useCallback, useState } from "react";

import BpmnViewer from "../components/BpmnViewer";
import EChart, { axisCommon, type OptionBuilder } from "../components/EChart";
import Figure from "../components/Figure";
import Reveal from "../components/Reveal";
import Section from "../components/Section";
import Simulator from "../components/Simulator";
import type { AllData, OppKey, Opportunity } from "../lib/data";
import { keur, num, pct } from "../lib/format";

const ORDER: OppKey[] = ["completeness", "prioritization", "preanalysis"];

const LEVER: Record<OppKey, string> = {
  completeness: "Pièces vérifiées au dépôt : moins de boucles « dossier incomplet » et d'appels de complétion.",
  prioritization: "Relance renforcée des 20 % d'offres jugées les plus à risque, à capacité de relance constante.",
  preanalysis: "Fiche de synthèse et contrôles de cohérence préparés pour l'analyste, qui reste décideur.",
};

function Tornado({ opp }: { opp: Opportunity }) {
  const reduced = useReducedMotion();
  const rows = opp.tornado.slice(0, 7);
  const ref = rows[0]?.reference_npv ?? 0;
  const lo = Math.min(...rows.map((r) => Math.min(r.npv_low, r.npv_high)), ref);
  const hi = Math.max(...rows.map((r) => Math.max(r.npv_low, r.npv_high)), ref, 0);
  const span = hi - lo || 1;
  const x = (v: number) => ((v - lo) / span) * 100;
  return (
    <div className="tornado" role="img" aria-label="Sensibilité de la VAN aux hypothèses">
      <div className="tornado-axis">
        <span style={{ left: `${x(0)}%` }} className="tornado-zero">
          VAN = 0
        </span>
        <span style={{ left: `${x(ref)}%` }} className="tornado-ref">
          centrale {keur(ref, 0, true)}
        </span>
      </div>
      {rows.map((r, i) => {
        const a = Math.min(r.npv_low, r.npv_high);
        const b = Math.max(r.npv_low, r.npv_high);
        return (
          <div className="tornado-row" key={r.hypothesis}>
            <span className="tornado-label">{r.label}</span>
            <span className="tornado-track">
              <span className="tornado-zero-line" style={{ left: `${x(0)}%` }} />
              <motion.span
                className="tornado-bar"
                style={{ left: `${x(a)}%`, width: `${Math.max(x(b) - x(a), 0.6)}%`, transformOrigin: `${((x(ref) - x(a)) / Math.max(x(b) - x(a), 0.6)) * 100}% 50%` }}
                initial={reduced ? false : { scaleX: 0 }}
                whileInView={{ scaleX: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay: reduced ? 0 : i * 0.05 }}
              />
              <span className="tornado-ref-line" style={{ left: `${x(ref)}%` }} />
            </span>
            <span className="tornado-values num">
              {keur(a, 0, true)} / {keur(b, 0, true)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function Opportunities({ data }: { data: AllData }) {
  const bc = data.business_case;
  const [tornadoOpp, setTornadoOpp] = useState<OppKey>("completeness");
  const comp = bc.opportunities.completeness;
  const prio = bc.opportunities.prioritization;
  const cal = bc.calibration;
  const ex = data.preanalysis_example;

  const histBuild = useCallback<OptionBuilder>(
    (p, { width }) => {
      const narrow = width < 640;
      const grids = ORDER.map((_, i) =>
        narrow ? { left: 40, right: 12, top: 30 + i * 150, height: 96 } : { left: `${3 + i * 33}%`, width: "28%", top: 40, height: 150 },
      );
      return {
        grid: grids,
        xAxis: ORDER.map((k, i) => {
          const edges = bc.opportunities[k].monte_carlo.npv_hist.edges;
          return {
            ...axisCommon(p),
            gridIndex: i,
            type: "value",
            min: edges[0],
            max: edges[edges.length - 1],
            splitNumber: 3,
            splitLine: { show: false },
            axisLabel: { ...axisCommon(p).axisLabel, formatter: (v: number) => keur(v), showMinLabel: false, showMaxLabel: false },
          };
        }),
        yAxis: ORDER.map((_, i) => ({ ...axisCommon(p), gridIndex: i, type: "value", min: 0, show: false })),
        graphic: ORDER.map((k, i) => ({
          type: "text",
          left: narrow ? 40 : `${3 + i * 33}%`,
          top: narrow ? 8 + i * 150 : 6,
          style: {
            text: `${bc.opportunities[k].short} — P(VAN > 0) = ${pct(bc.opportunities[k].monte_carlo.prob_npv_positive)}`,
            fill: p.ink,
            font: '600 13px "Archivo Variable", sans-serif',
          },
        })),
        tooltip: {
          formatter: (it: { value: [number, number, number] }) => `<strong>${num(it.value[2])} tirages</strong><br/>VAN entre ${keur(it.value[0])} et ${keur(it.value[1])}`,
        },
        series: ORDER.map((k, i) => {
          const h = bc.opportunities[k].monte_carlo.npv_hist;
          return {
            type: "custom",
            xAxisIndex: i,
            yAxisIndex: i,
            encode: { x: [0, 1], y: 2 },
            data: h.counts.map((c, j) => [h.edges[j], h.edges[j + 1], c]),
            renderItem: (_: unknown, api: { value: (d: number) => number; coord: (v: [number, number]) => [number, number] }) => {
              const x0 = api.value(0);
              const x1 = api.value(1);
              const c = api.value(2);
              const [px0, py] = api.coord([x0, c]);
              const [px1, py0] = api.coord([x1, 0]);
              const positive = (x0 + x1) / 2 >= 0;
              return {
                type: "rect",
                shape: { x: px0 + 1, y: py, width: Math.max(px1 - px0 - 2, 1), height: py0 - py },
                style: { fill: positive ? p.blue : p.ctx },
              };
            },
            markLine: {
              symbol: "none",
              silent: true,
              lineStyle: { color: p.ink, width: 1.5, type: "solid" },
              label: { show: false },
              data: [{ xAxis: 0 }],
            },
          };
        }),
      };
    },
    [bc],
  );

  return (
    <Section
      id="business-case"
      num="08"
      kicker="Opportunités IA et business case"
      title={
        <>
          Une opportunité sur trois est rentable : le contrôle de complétude, positif dans {pct(comp.monte_carlo.prob_npv_positive)} des scénarios.
        </>
      }
      lede={
        <>
          Chaque opportunité part d'un constat mesuré. Les dossiers réels sont rejoués avec et sans l'apport de l'IA
          (rejeu contrefactuel), puis {num(comp.monte_carlo.iterations)} tirages de Monte Carlo font varier les
          hypothèses dans leur fourchette. Les hypothèses sont explicites, sourcées quand c'est possible, et
          modifiables ci-dessous.
        </>
      }
    >
      <Reveal>
        <div className="opp-table" role="table" aria-label="Synthèse des trois opportunités">
          <div className="opp-row opp-head" role="row">
            <span role="columnheader">Opportunité et levier</span>
            <span role="columnheader">Gain annuel (médiane)</span>
            <span role="columnheader">VAN 3 ans (P10 · P50 · P90)</span>
            <span role="columnheader">Retour</span>
          </div>
          {ORDER.map((k) => {
            const o = bc.opportunities[k];
            const mc = o.monte_carlo;
            return (
              <div className="opp-row" role="row" key={k}>
                <span role="cell">
                  <strong>{o.title}</strong>
                  <span className="muted small">{LEVER[k]}</span>
                </span>
                <span role="cell" className="num">
                  {keur(mc.annual_benefit.p50)}
                  <span className="muted small">
                    {k === "prioritization" ? `${num(mc.annual_loans.p50)} prêts de plus par an` : `${num(mc.annual_hours.p50)} h libérées par an`}
                  </span>
                </span>
                <span role="cell" className="num">
                  <span className="opp-npv">
                    <span className="muted">{keur(mc.npv.p10, 0, true)}</span> <strong>{keur(mc.npv.p50, 0, true)}</strong>{" "}
                    <span className="muted">{keur(mc.npv.p90, 0, true)}</span>
                  </span>
                  <span className="muted small">VAN positive dans {pct(mc.prob_npv_positive)} des tirages</span>
                </span>
                <span role="cell" className="num">
                  {o.central.payback_month === null ? "au-delà de 36 mois" : `${o.central.payback_month} mois`}
                  <span className="muted small">scénario central</span>
                </span>
              </div>
            );
          })}
        </div>
      </Reveal>

      <div className="grid">
        <Reveal className="span-12">
          <Figure
            title="Distribution de la VAN sur 36 mois"
            subtitle="Tirages de Monte Carlo sur les hypothèses ; en bleu, les scénarios rentables."
            table={{
              columns: ["Opportunité", "P10", "P50", "P90", "P(VAN > 0)"],
              rows: ORDER.map((k) => {
                const q = bc.opportunities[k].monte_carlo.npv;
                return [bc.opportunities[k].short, keur(q.p10, 0, true), keur(q.p50, 0, true), keur(q.p90, 0, true), pct(bc.opportunities[k].monte_carlo.prob_npv_positive)];
              }),
              numeric: [1, 2, 3, 4],
            }}
          >
            <EChart build={histBuild} height={230} label="Distributions de la valeur actuelle nette des trois opportunités" />
          </Figure>
        </Reveal>

        <Reveal className="span-7">
          <Figure title="Quelles hypothèses font basculer la VAN ?" subtitle="Chaque hypothèse à son minimum puis à son maximum, les autres au centre.">
            <div className="seg tornado-tabs" role="tablist" aria-label="Opportunité">
              {ORDER.map((k) => (
                <button key={k} type="button" role="tab" aria-selected={tornadoOpp === k} onClick={() => setTornadoOpp(k)}>
                  {bc.opportunities[k].short}
                </button>
              ))}
            </div>
            <Tornado key={tornadoOpp} opp={bc.opportunities[tornadoOpp]} />
          </Figure>
        </Reveal>
        <Reveal className="span-5 aside-col" delay={0.06}>
          <div className="callout">
            <p className="kicker">Ce que dit le rejeu</p>
            <p>
              Avec le contrôle de complétude, le délai médian des prêts approuvés passerait de{" "}
              {num(bc.baseline.median_lead_time_approved_d, 1)} j à{" "}
              {num(comp.monte_carlo.median_lead_time_approved_after_d?.p50, 1)} j : les boucles évitées sont rejouées dossier
              par dossier, avec leur durée réelle.
            </p>
          </div>
          <div className="callout">
            <p className="kicker">Pourquoi la priorisation reste incertaine</p>
            <p>
              Le ciblage par score couvre {pct(bc.baseline.recall_at_target, 1)} des abandons quand on appelle 20 % des
              dossiers, à peine mieux que le hasard. La VAN passe à zéro dès que le taux de récupération tombe sous{" "}
              {pct(prio.break_even_recovery_rate ?? 0, 1)}, ou que le ciblage descend sous{" "}
              {pct(prio.break_even_recall ?? 0, 1)} de couverture. Un ciblage au hasard donnerait{" "}
              {keur(prio.random_targeting_npv ?? 0, 0, true)}. D'où un pilote A/B sur une règle simple avant tout développement.
            </p>
          </div>
          {cal.available && (
            <div className="callout">
              <p className="kicker">Hypothèse de marge étalonnée</p>
              <p>
                Les {num(cal.selected_offers)} offres retenues du BPI Challenge 2017 (même établissement, 2016) impliquent
                un taux annuel médian de {pct(cal.apr?.p50, 1)} sur {num(cal.terms_months?.p50)} mois, soit des intérêts
                bruts de {pct(cal.gross_interest_ratio?.p50)} du montant. La marge nette retenue (
                {pct(bc.hypotheses.common.net_margin.mode)}, fourchette {pct(bc.hypotheses.common.net_margin.min)} à{" "}
                {pct(bc.hypotheses.common.net_margin.max)}) en représente environ le quart.
              </p>
            </div>
          )}
        </Reveal>

        <Reveal className="span-12">
          <Figure title="Simulateur : modifiez les hypothèses" subtitle="Les effets se recalculent instantanément ; les volumes de référence restent ceux mesurés dans le journal.">
            <Simulator bc={bc} />
          </Figure>
        </Reveal>

        <Reveal className="span-12">
          <Figure title="Du processus observé au processus cible" subtitle="BPMN 2.0 : trois apports de l'IA, aucune décision de crédit automatisée.">
            <BpmnViewer />
          </Figure>
        </Reveal>

        <Reveal className="span-6">
          <div className="brief">
            <p className="kicker">Prototype : fiche de pré-analyse d'un dossier réel</p>
            <h3 className="h3">Dossier {ex.case_id}</h3>
            <dl className="brief-grid">
              <dt>Montant demandé</dt>
              <dd className="num">{num(ex.amount_requested_eur)} €</dd>
              <dt>Dépôt</dt>
              <dd className="num">{ex.submitted}</dd>
              <dt>Première offre</dt>
              <dd className="num">{ex.first_offer ?? "—"}</dd>
              <dt>Offre retournée</dt>
              <dd className="num">{ex.offer_returned ?? "—"}</dd>
              <dt>Offres · appels</dt>
              <dd className="num">
                {ex.offers} offres · {ex.completion_calls} appel{ex.completion_calls > 1 ? "s" : ""} de complétion · {ex.incomplete_calls} relance{ex.incomplete_calls > 1 ? "s" : ""} pour pièces
              </dd>
            </dl>
            <p className="kicker">Points d'attention</p>
            <ul>
              {(ex.alerts as string[]).map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
            <p className="small muted">{ex.disclaimer} Rédaction par un modèle de langage possible en option (clé fournie par l'utilisateur), jamais affichée ici.</p>
          </div>
        </Reveal>
        <Reveal className="span-6" delay={0.06}>
          <div className="roadmap" aria-label="Feuille de route sur 18 mois">
            <p className="kicker">Feuille de route recommandée (mois)</p>
            <div className="roadmap-scale" aria-hidden="true">
              {[0, 3, 6, 9, 12, 15, 18].map((m) => (
                <span key={m} style={{ left: `${(m / 18) * 100}%` }}>
                  M{m}
                </span>
              ))}
            </div>
            {[
              { label: "Cadrage, AIPD, données", start: 0, end: 2, kind: "base" },
              { label: "Complétude : construction", start: 2, end: 7, kind: "go" },
              { label: "Complétude : montée en charge", start: 7, end: 13, kind: "go-light" },
              { label: "Relances : pilote A/B (règle simple)", start: 3, end: 7, kind: "pilot" },
              { label: "Décision sur le score d'abandon", start: 7, end: 7.4, kind: "gate" },
              { label: "Pré-analyse : réévaluation", start: 12, end: 13, kind: "gate" },
            ].map((r) => (
              <div className="roadmap-row" key={r.label}>
                <span className="roadmap-label">{r.label}</span>
                <span className="roadmap-track">
                  <span className={`roadmap-bar ${r.kind}`} style={{ left: `${(r.start / 18) * 100}%`, width: `${((r.end - r.start) / 18) * 100}%` }} />
                </span>
              </div>
            ))}
            <p className="small muted">
              La pré-analyse sera réexaminée après la mise en service du socle documentaire de la complétude (mutualisation
              des coûts) et à l'approche des obligations haut risque de l'AI Act (2 décembre 2027).
            </p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
