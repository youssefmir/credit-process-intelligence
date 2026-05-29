import { useCallback, useMemo, useState } from "react";

import { evaluate, modes, type Inputs } from "../lib/businessCase";
import type { BusinessCase, Hypothesis, OppKey } from "../lib/data";
import { keur, num, pct } from "../lib/format";
import EChart, { axisCommon, type OptionBuilder } from "./EChart";

interface SliderDef {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  hyp?: Hypothesis;
}

const SHARE = (v: number) => pct(v);
const EUR_K = (v: number) => keur(v);

function slidersFor(opp: OppKey, bc: BusinessCase): SliderDef[] {
  const h = bc.hypotheses;
  const o = h.opportunities[opp] as unknown as Record<string, Hypothesis>;
  const c = h.common;
  const share = (key: string, hyp: Hypothesis): SliderDef => ({ key, label: hyp.label, min: 0, max: Math.min(1, hyp.max * 1.6), step: 0.01, format: SHARE, hyp });
  const costs: SliderDef[] = [
    { key: "build_cost", label: o.build_cost.label, min: 0, max: o.build_cost.max * 1.5, step: 5000, format: EUR_K, hyp: o.build_cost },
    { key: "run_cost", label: o.run_cost.label, min: 0, max: o.run_cost.max * 1.5, step: 1000, format: EUR_K, hyp: o.run_cost },
  ];
  const hourly: SliderDef = { key: "hourly_cost", label: c.hourly_cost.label, min: 25, max: 80, step: 1, format: (v) => `${num(v)}\u00a0€/h`, hyp: c.hourly_cost };
  const margin: SliderDef = { key: "net_margin", label: c.net_margin.label, min: 0, max: 0.12, step: 0.005, format: (v) => pct(v, 1), hyp: c.net_margin };
  if (opp === "completeness") {
    return [share("loops_avoided", o.loops_avoided), share("completion_calls_avoided", o.completion_calls_avoided), share("effort_shift", o.effort_shift), share("causal_share", o.causal_share), hourly, margin, ...costs];
  }
  if (opp === "prioritization") {
    return [
      share("recovery_rate", o.recovery_rate),
      {
        key: "recall_at_target",
        label: "Abandons couverts par les 20 % de dossiers ciblés (qualité du ciblage)",
        min: 0.2,
        max: 0.7,
        step: 0.01,
        format: SHARE,
      },
      { key: "extra_calls", label: o.extra_calls.label, min: 0, max: 5, step: 0.5, format: (v) => num(v, 1), hyp: o.extra_calls },
      margin,
      ...costs,
    ];
  }
  return [share("validation_time_saved", o.validation_time_saved), hourly, ...costs];
}

interface Props {
  bc: BusinessCase;
}

export default function Simulator({ bc }: Props) {
  const [opp, setOpp] = useState<OppKey>("completeness");
  const initial = useCallback(
    (k: OppKey): Inputs => ({ ...modes(bc.hypotheses, k), ...(k === "prioritization" ? { recall_at_target: bc.baseline.recall_at_target } : {}) }),
    [bc],
  );
  const [inputs, setInputs] = useState<Record<OppKey, Inputs>>(() => ({
    completeness: initial("completeness"),
    prioritization: initial("prioritization"),
    preanalysis: initial("preanalysis"),
  }));
  const h = inputs[opp];
  const result = useMemo(() => evaluate(opp, bc.baseline, h, bc.hypotheses), [opp, bc, h]);
  const sliders = useMemo(() => slidersFor(opp, bc), [opp, bc]);
  const central = bc.opportunities[opp].central;

  const set = (key: string, v: number) => setInputs((s) => ({ ...s, [opp]: { ...s[opp], [key]: v } }));
  const reset = () => setInputs((s) => ({ ...s, [opp]: initial(opp) }));

  const parts = [
    { key: "capacity", label: "Capacité libérée", value: result.capacityEur, sign: 1 },
    { key: "conversion", label: "Prêts supplémentaires (marge)", value: result.conversionEur, sign: 1 },
    { key: "extra", label: "Coût des appels supplémentaires", value: -result.extraCostEur, sign: -1 },
    { key: "run", label: "Coût de fonctionnement", value: -h.run_cost, sign: -1 },
  ];
  const scale = Math.max(150_000, ...parts.map((p) => Math.abs(p.value)));

  const cumBuild = useCallback<OptionBuilder>(
    (p) => ({
      grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
      xAxis: { ...axisCommon(p), type: "category", data: result.cumulative.map((_, i) => i + 1), boundaryGap: false, axisLabel: { ...axisCommon(p).axisLabel, interval: 5, formatter: (v: string) => `M${v}` }, splitLine: { show: false } },
      yAxis: { ...axisCommon(p), type: "value", splitNumber: 4, axisLabel: { ...axisCommon(p).axisLabel, formatter: (v: number) => keur(v) } },
      tooltip: { trigger: "axis", axisPointer: { type: "line", lineStyle: { color: p.ink, width: 1 } }, formatter: (it: { axisValue: string; value: number }[]) => `Mois ${it[0].axisValue}<br/><strong>${keur(it[0].value)}</strong> cumulés` },
      series: [
        {
          type: "line",
          data: result.cumulative.map((v) => Math.round(v)),
          showSymbol: false,
          lineStyle: { color: p.blue, width: 2.5 },
          itemStyle: { color: p.blue },
          areaStyle: { color: p.blue, opacity: 0.08 },
          markLine: { symbol: "none", silent: true, lineStyle: { color: p.ink, width: 1, type: "solid" }, label: { show: false }, data: [{ yAxis: 0 }] },
        },
      ],
    }),
    [result.cumulative],
  );

  return (
    <div className="sim">
      <div className="seg sim-tabs" role="tablist" aria-label="Opportunité simulée">
        {(["completeness", "prioritization", "preanalysis"] as OppKey[]).map((k) => (
          <button key={k} type="button" role="tab" aria-selected={opp === k} onClick={() => setOpp(k)}>
            {bc.opportunities[k].short}
          </button>
        ))}
      </div>
      <div className="grid sim-grid">
        <div className="span-5 sim-inputs">
          {sliders.map((s) => {
            const v = h[s.key];
            return (
              <div className="range" key={s.key}>
                <label htmlFor={`sim-${opp}-${s.key}`}>
                  <span>{s.label}</span>
                  <output>{s.format(v)}</output>
                </label>
                <input id={`sim-${opp}-${s.key}`} type="range" min={s.min} max={s.max} step={s.step} value={v} onChange={(e) => set(s.key, Number(e.target.value))} />
                {s.hyp && (
                  <span className="range-hint">
                    hypothèse : {s.format(s.hyp.min)} à {s.format(s.hyp.max)}, centrale {s.format(s.hyp.mode)}
                  </span>
                )}
                {s.key === "recall_at_target" && <span className="range-hint">mesuré sur le test : {pct(bc.baseline.recall_at_target, 1)} (hasard : 20 %)</span>}
              </div>
            );
          })}
          <button type="button" className="btn" onClick={reset}>
            Revenir aux hypothèses centrales
          </button>
        </div>
        <div className="span-7 sim-outputs" aria-live="polite">
          <div className="sim-kpis">
            <div className="stat">
              <p className="figure-number sm num">{keur(result.npv, 0, true)}</p>
              <p className="label">VAN sur 36 mois (centrale : {keur(central.npv, 0, true)})</p>
            </div>
            <div className="stat">
              <p className="figure-number sm num">{result.paybackMonth === null ? "> 36" : `${result.paybackMonth}`}</p>
              <p className="label">mois avant retour sur investissement</p>
            </div>
            <div className="stat">
              <p className="figure-number sm num">{opp === "prioritization" ? num(result.loans) : num(result.hours)}</p>
              <p className="label">{opp === "prioritization" ? "prêts supplémentaires par an" : `heures par an libérées (${num(result.fte, 1)} ETP)`}</p>
            </div>
          </div>
          <p className="kicker sim-bars-title">Effets annuels en régime de croisière</p>
          <ul className="sim-bars">
            {parts.map((p) => (
              <li key={p.key}>
                <span className="sim-bar-label">{p.label}</span>
                <span className="sim-bar-track">
                  <span
                    className={`sim-bar ${p.sign < 0 ? "neg" : "pos"}`}
                    style={{ transform: `scaleX(${Math.min(Math.abs(p.value) / scale, 1)})` }}
                  />
                </span>
                <span className="sim-bar-value num">{keur(p.value, 0, true)}</span>
              </li>
            ))}
          </ul>
          <p className="kicker sim-bars-title">Trésorerie cumulée (mois 1 à 36)</p>
          <EChart build={cumBuild} height={200} label="Trésorerie cumulée du scénario simulé" deps={[result.cumulative]} />
          <p className="source">
            Calcul identique au pipeline Python (test croisé). Hypothèses détaillées dans le business case du dépôt.
          </p>
        </div>
      </div>
    </div>
  );
}

