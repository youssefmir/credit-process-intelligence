import { useCallback, useMemo, useState } from "react";

import EChart, { axisCommon, type OptionBuilder } from "../components/EChart";
import Figure from "../components/Figure";
import Reveal from "../components/Reveal";
import Section from "../components/Section";
import type { AllData } from "../lib/data";
import { num, pct } from "../lib/format";

type Curve = [number, number][];

function recallAt(curve: Curve, share: number): number {
  for (let i = 1; i < curve.length; i++) {
    if (curve[i][0] >= share) {
      const [x0, y0] = curve[i - 1];
      const [x1, y1] = curve[i];
      const f = (share - x0) / (x1 - x0 || 1);
      return y0 + (y1 - y0) * f;
    }
  }
  return 1;
}

const MODEL_LABEL: Record<string, string> = {
  rule: "Règle simple (délai avant offre)",
  logreg: "Régression logistique",
  gbm: "Gradient boosting (LightGBM)",
};

export default function Prediction({ data }: { data: AllData }) {
  const m = data.model;
  const proto = m.protocol;
  const gbm = m.models.gbm;
  const [share, setShare] = useState(0.2);
  const curve = gbm.gains.curve as Curve;
  const recall = useMemo(() => recallAt(curve, share), [curve, share]);

  const gainsBuild = useCallback<OptionBuilder>(
    (p) => ({
      grid: { left: 8, right: 24, top: 16, bottom: 30, containLabel: true },
      xAxis: { ...axisCommon(p), type: "value", min: 0, max: 1, name: "part des dossiers appelés en priorité", nameLocation: "middle", nameGap: 26, axisLabel: { ...axisCommon(p).axisLabel, formatter: (v: number) => pct(v) } },
      yAxis: { ...axisCommon(p), type: "value", min: 0, max: 1, axisLabel: { ...axisCommon(p).axisLabel, formatter: (v: number) => pct(v) } },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "line", lineStyle: { color: p.ink, width: 1 } },
        formatter: (items: { seriesName: string; value: [number, number] }[]) =>
          `${pct(items[0].value[0])} des dossiers appelés<br/>` + items.map((it) => `<strong>${pct(it.value[1])}</strong> des abandons · ${it.seriesName}`).join("<br/>"),
      },
      series: [
        {
          name: "hasard",
          type: "line",
          data: [[0, 0], [1, 1]],
          showSymbol: false,
          lineStyle: { color: p.context, width: 1.5 },
          itemStyle: { color: p.context },
          markPoint: {
            symbol: "rect",
            symbolSize: 1,
            itemStyle: { color: "transparent" },
            label: { show: true, formatter: "hasard", color: p.muted, position: "right" },
            data: [{ coord: [0.86, 0.82] }],
          },
        },
        {
          name: "règle simple",
          type: "line",
          data: m.models.rule.gains.curve,
          showSymbol: false,
          lineStyle: { color: p.grey, width: 1.5 },
          itemStyle: { color: p.grey },
        },
        {
          name: "LightGBM",
          type: "line",
          data: curve,
          showSymbol: false,
          lineStyle: { color: p.blue, width: 2.5 },
          itemStyle: { color: p.blue },
          markLine: {
            symbol: "none",
            silent: true,
            lineStyle: { color: p.ink, width: 1, type: "solid" },
            label: { show: false },
            data: [{ xAxis: share }],
          },
          markPoint: {
            symbol: "circle",
            symbolSize: 11,
            itemStyle: { color: p.blue, borderColor: p.bg, borderWidth: 2 },
            label: { show: true, position: "bottom", distance: 10, color: p.ink, fontWeight: 650, formatter: () => `${pct(recall)} des abandons` },
            data: [{ coord: [share, recall] }],
          },
        },
      ],
    }),
    [curve, share, recall, m.models.rule.gains.curve],
  );

  const calBuild = useCallback<OptionBuilder>(
    (p) => {
      const cal = gbm.calibration as { mean_predicted: number; observed_rate: number; n: number }[];
      return {
        grid: { left: 8, right: 16, top: 12, bottom: 30, containLabel: true },
        xAxis: { ...axisCommon(p), type: "value", min: 0.2, max: 0.5, name: "probabilité prédite", nameLocation: "middle", nameGap: 26, axisLabel: { ...axisCommon(p).axisLabel, formatter: (v: number) => pct(v) } },
        yAxis: { ...axisCommon(p), type: "value", min: 0.2, max: 0.5, axisLabel: { ...axisCommon(p).axisLabel, formatter: (v: number) => pct(v) } },
        tooltip: { formatter: (it: { value: [number, number] }) => `prédit <strong>${pct(it.value[0], 1)}</strong><br/>observé <strong>${pct(it.value[1], 1)}</strong>` },
        series: [
          { type: "line", data: [[0.2, 0.2], [0.5, 0.5]], showSymbol: false, lineStyle: { color: p.context, width: 1.5 }, silent: true },
          {
            type: "scatter",
            data: cal.map((c) => [c.mean_predicted, c.observed_rate]),
            symbolSize: 10,
            itemStyle: { color: p.blue, borderColor: p.bg, borderWidth: 2 },
          },
        ],
      };
    },
    [gbm.calibration],
  );

  const horizonBuild = useCallback<OptionBuilder>(
    (p) => {
      const rows = m.horizons as { days_after_offer: number; gbm_roc_auc: number; logreg_roc_auc: number }[];
      return {
        grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
        xAxis: { ...axisCommon(p), type: "category", data: rows.map((r) => `J+${r.days_after_offer}`), boundaryGap: false, splitLine: { show: false } },
        yAxis: { ...axisCommon(p), type: "value", min: 0.45, max: 0.7, splitNumber: 5, axisLabel: { ...axisCommon(p).axisLabel, formatter: (v: number) => num(v, 2) } },
        tooltip: { trigger: "axis", formatter: (items: { axisValue: string; seriesName: string; value: number }[]) => `${items[0].axisValue}<br/>` + items.map((it) => `<strong>${num(it.value, 3)}</strong> ${it.seriesName}`).join("<br/>") },
        series: [
          {
            name: "LightGBM",
            type: "line",
            data: rows.map((r) => r.gbm_roc_auc),
            symbolSize: 8,
            lineStyle: { color: p.blue, width: 2 },
            itemStyle: { color: p.blue, borderColor: p.bg, borderWidth: 2 },
            markLine: {
              symbol: "none",
              silent: true,
              lineStyle: { color: p.red, width: 1.5, type: "solid" },
              label: { formatter: "seuil 0,65", color: p.ink, position: "insideEndTop" },
              data: [{ yAxis: 0.65 }],
            },
          },
          {
            name: "Régression logistique",
            type: "line",
            data: rows.map((r) => r.logreg_roc_auc),
            symbolSize: 8,
            lineStyle: { color: p.grey, width: 2 },
            itemStyle: { color: p.grey, borderColor: p.bg, borderWidth: 2 },
          },
        ],
      };
    },
    [m.horizons],
  );

  const shapBuild = useCallback<OptionBuilder>(
    (p) => {
      const imp = (m.shap.importance as { label: string; mean_abs_shap: number }[]).slice(0, 8).reverse();
      return {
        grid: { left: 8, right: 56, top: 8, bottom: 8, containLabel: true },
        xAxis: { ...axisCommon(p), type: "value", axisLabel: { show: false }, splitLine: { show: false }, axisLine: { show: false } },
        yAxis: { ...axisCommon(p), type: "category", data: imp.map((r) => r.label), axisLine: { lineStyle: { color: p.ink } }, axisLabel: { ...axisCommon(p).axisLabel, color: p.ink2, width: 160, overflow: "break", lineHeight: 13 } },
        tooltip: { formatter: (it: { name: string; value: number }) => `<strong>${num(it.value, 3)}</strong> (|SHAP| moyen, log-odds)<br/>${it.name}` },
        series: [
          {
            type: "bar",
            barWidth: 14,
            data: imp.map((r) => r.mean_abs_shap),
            itemStyle: { color: p.blue },
            label: { show: true, position: "right", color: p.ink, formatter: (it: { value: number }) => num(it.value, 3) },
          },
        ],
      };
    },
    [m.shap],
  );

  const ci = m.bootstrap_ci as Record<string, [number, number]>;
  const at20 = (k: string) => (m.models[k].gains.at_k as { share: number; recall: number; lift: number }[]).find((a) => a.share === 0.2);
  const acc = m.acceptance as { checks: { criterion: string; threshold: string; value: number; passed: boolean }[]; deployable: boolean };

  return (
    <Section
      id="prediction"
      num="07"
      kicker="Prédire les abandons"
      title={
        <>
          Les traces du processus ne prédisent pas l'abandon : ROC-AUC de {num(gbm.metrics.roc_auc, 2)}, le modèle n'est pas mis en production.
        </>
      }
      lede={
        <>
          Objectif : dès l'envoi de la première offre, classer les dossiers par risque d'abandon pour prioriser les
          relances. Ce score n'intervient jamais dans la décision de crédit. Protocole strict : découpage temporel,
          aucune information postérieure au point de décision, seuils d'acceptation fixés avant l'évaluation.
        </>
      }
    >
      <div className="grid">
        <Reveal className="span-12">
          <div className="protocol" role="img" aria-label={`Apprentissage sur les offres d'octobre et novembre 2011 (${num(proto.train_cases)} dossiers), zone tampon en décembre, test en janvier 2012 (${num(proto.test_cases)} dossiers)`}>
            <div className="protocol-band train">
              <strong>Apprentissage</strong>
              <span>offres d'oct. à nov. 2011 · {num(proto.train_cases)} dossiers dont l'issue était connue au 1er janvier</span>
            </div>
            <div className="protocol-band buffer">
              <strong>Zone tampon</strong>
              <span>décembre · {num(proto.excluded.buffer_window)} dossiers non utilisés (issues pas encore connues)</span>
            </div>
            <div className="protocol-band test">
              <strong>Test</strong>
              <span>janvier 2012 · {num(proto.test_cases)} dossiers, issue observée au moins {proto.observation_days} j plus tard</span>
            </div>
          </div>
          <p className="source">
            Déploiement simulé au {new Date(proto.deployment_date).toLocaleDateString("fr-FR")} ; hyperparamètres choisis par validation croisée temporelle à 3 plis dans la période d'apprentissage ; aucun identifiant de collaborateur parmi les {proto.features.length} variables.
          </p>
        </Reveal>

        <Reveal className="span-12">
          <div className="table-wrap">
            <table className="data">
              <caption className="sr-only">Performances sur la période de test</caption>
              <thead>
                <tr>
                  <th scope="col">Modèle</th>
                  <th scope="col" className="r">ROC-AUC [IC 95 %]</th>
                  <th scope="col" className="r">PR-AUC</th>
                  <th scope="col" className="r">Abandons couverts à 20 %</th>
                  <th scope="col" className="r">Lift à 20 %</th>
                </tr>
              </thead>
              <tbody>
                {(["rule", "logreg", "gbm"] as const).map((k) => (
                  <tr key={k}>
                    <td>{MODEL_LABEL[k]}</td>
                    <td className="r">
                      {num(m.models[k].metrics.roc_auc, 3)} <span className="muted">[{num(ci[`${k}_roc_auc`][0], 2)} ; {num(ci[`${k}_roc_auc`][1], 2)}]</span>
                    </td>
                    <td className="r">{num(m.models[k].metrics.pr_auc, 3)}</td>
                    <td className="r">{pct(at20(k)?.recall, 1)}</td>
                    <td className="r">{num(at20(k)?.lift, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="source">
            Taux d'abandon de base sur le test : {pct(gbm.metrics.base_rate, 1)}. Écart LightGBM − règle simple : IC 95 % de{" "}
            {num(ci.gbm_minus_rule_auc[0], 3)} à {num(ci.gbm_minus_rule_auc[1], 3)} (non significatif). Contrôle sans zone tampon : ROC-AUC {num(m.alternative_split.roc_auc, 3)}.
          </p>
        </Reveal>

        <Reveal className="span-7">
          <Figure
            title="Courbe de gain : qui appeler en premier ?"
            subtitle="Part des abandons couverts selon la part des dossiers appelés en priorité (période de test)."
            table={{
              columns: ["Dossiers appelés", "Abandons couverts", "Précision", "Lift"],
              rows: (gbm.gains.at_k as { share: number; recall: number; precision: number; lift: number }[]).map((a) => [pct(a.share), pct(a.recall, 1), pct(a.precision, 1), num(a.lift, 2)]),
              numeric: [1, 2, 3],
            }}
          >
            <div className="range gains-range">
              <label htmlFor="gains-k">
                Dossiers appelés en priorité <output>{pct(share)}</output>
              </label>
              <input id="gains-k" type="range" min={0.05} max={0.95} step={0.05} value={share} onChange={(e) => setShare(Number(e.target.value))} />
            </div>
            <p className="gains-read" aria-live="polite">
              En appelant d'abord les <strong>{pct(share)}</strong> de dossiers jugés les plus à risque, on couvre{" "}
              <strong>{pct(recall)}</strong> des abandons, contre {pct(share)} au hasard.
            </p>
            <EChart build={gainsBuild} height={300} label="Courbe de gain du modèle LightGBM comparée au hasard" deps={[share]} />
          </Figure>
        </Reveal>
        <Reveal className="span-5" delay={0.06}>
          <div className="acceptance">
            <p className="kicker">Seuils d'acceptation fixés à l'avance</p>
            <ul>
              {acc.checks.map((c) => (
                <li key={c.criterion} className={c.passed ? "ok" : "ko"}>
                  <span className="acc-icon" aria-hidden="true">{c.passed ? "✓" : "✕"}</span>
                  <span>
                    {c.criterion} <span className="muted">({c.threshold.replace(".", ",")})</span>
                    <br />
                    <strong>{num(c.value, c.value < 1 ? 3 : 2)}</strong> · {c.passed ? "atteint" : "non atteint"}
                  </span>
                </li>
              ))}
            </ul>
            <p className="acc-verdict">
              <span className={`tag ${acc.deployable ? "ok" : "ko"}`}>{acc.deployable ? "Déployable" : "Non déployable"}</span>
            </p>
            <p className="small muted">
              Bien calibré et stable, mais pas assez discriminant : le signal n'est pas dans les traces. Ajouter
              l'identifiant du conseiller n'améliore rien et poserait un problème d'évaluation individuelle.
            </p>
          </div>
        </Reveal>

        <Reveal className="span-4">
          <Figure title="Attendre ne suffit pas" subtitle="ROC-AUC si l'on observe le dossier J jours après l'offre (avec l'historique des relances).">
            <ul className="mini-legend" aria-hidden="true">
              <li><span className="swatch" style={{ background: "var(--c-blue)" }} />LightGBM</li>
              <li><span className="swatch" style={{ background: "var(--c-grey)" }} />Régression logistique</li>
              <li><span className="swatch" style={{ background: "var(--c-red)" }} />Seuil d'acceptation</li>
            </ul>
            <EChart build={horizonBuild} height={210} label="ROC-AUC selon le moment d'observation" />
          </Figure>
        </Reveal>
        <Reveal className="span-4" delay={0.06}>
          <Figure title="Calibration (LightGBM)" subtitle="Déciles de probabilité : prédit contre observé.">
            <EChart build={calBuild} height={230} label="Diagramme de calibration" />
          </Figure>
        </Reveal>
        <Reveal className="span-4" delay={0.12}>
          <Figure
            title="Ce qui pèse dans le score"
            subtitle="Importance SHAP moyenne (TreeSHAP natif de LightGBM)."
            table={{
              columns: ["Variable", "|SHAP| moyen", "Importance par permutation"],
              rows: (m.shap.importance as { feature: string; label: string; mean_abs_shap: number }[]).map((r) => {
                const perm = (m.permutation_importance as { feature: string; mean: number }[]).find((x) => x.feature === r.feature);
                return [r.label, num(r.mean_abs_shap, 3), num(perm?.mean ?? 0, 4)];
              }),
              numeric: [1, 2],
            }}
          >
            <EChart build={shapBuild} height={260} label="Importance des variables" />
          </Figure>
        </Reveal>

        <Reveal className="span-12">
          <div className="frontier">
            <p className="kicker">Frontière réglementaire</p>
            <p>
              Un score de solvabilité ou d'octroi serait un système d'IA à haut risque (AI Act, annexe III, point 5 b).
              Ce score-ci ne sert qu'à ordonner une file de relance : aucune décision de crédit, aucun effet sur le client
              au-delà d'un appel plus ou moins tôt, un conseiller toujours décideur. Garde-fous prévus : supervision
              humaine, suivi des dérives (PSI du score : {num(m.drift.score_psi_train_vs_test, 3)}), information des
              clients (profilage, RGPD) et limite assumée : sans attribut sensible dans les données, l'équité entre
              groupes ne peut pas être mesurée ; seule la stabilité par tranche de montant l'est.
            </p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
