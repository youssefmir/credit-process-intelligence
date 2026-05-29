/**
 * Business case déterministe (valeurs espérées) : réplique exacte de
 * `src/cpi/simulation.py` (annual_effects, cash_flows, npv, payback_month).
 * Un test croisé compare ces résultats aux scénarios de référence exportés par Python.
 */

import type { Baseline, Hypotheses, OppKey } from "./data";

export type Inputs = Record<string, number>;

export interface Effects {
  hours: number;
  loans: number;
  extraHours: number;
  capacityEur: number;
  conversionEur: number;
  extraCostEur: number;
  benefitEur: number;
}

export interface ScenarioResult extends Effects {
  fte: number;
  npv: number;
  paybackMonth: number | null;
  cumulative: number[];
}

export function annualEffects(opp: OppKey, base: Baseline, h: Inputs): Effects {
  const scale = base.annual_factor * h.volume_factor * h.adoption;
  let hours = 0;
  let loans = 0;
  let extraHours = 0;
  if (opp === "completeness") {
    const loopHours = h.loops_avoided * base.loop_hours;
    const loopCases = h.loops_avoided * base.loop_cases;
    hours = (loopHours + h.completion_calls_avoided * base.completion_hours) * (1 - h.effort_shift);
    loans = loopCases * base.loop_cancel_gap * h.causal_share * base.approval_given_returned;
  } else if (opp === "prioritization") {
    const recall = h.recall_at_target ?? base.recall_at_target;
    const recovered = base.abandons_after_offer * recall * h.recovery_rate;
    loans = recovered * base.approval_given_returned;
    extraHours = (h.targeted_share * base.offered_cases * h.extra_calls * base.median_offer_call_min) / 60;
  } else {
    hours = h.validation_time_saved * base.validation_hours;
  }
  hours *= scale;
  loans *= scale;
  extraHours *= scale;
  const capacityEur = hours * h.hourly_cost;
  const conversionEur = loans * base.mean_amount_approved * h.net_margin;
  const extraCostEur = extraHours * h.hourly_cost;
  return {
    hours,
    loans,
    extraHours,
    capacityEur,
    conversionEur,
    extraCostEur,
    benefitEur: capacityEur + conversionEur - extraCostEur,
  };
}

export function cashFlows(
  benefitEur: number,
  buildCost: number,
  runCost: number,
  buildMonths: number,
  rampMonths: number,
  horizonMonths: number,
): number[] {
  const cf: number[] = [];
  for (let m = 1; m <= horizonMonths; m++) {
    if (m > buildMonths) {
      const ramp = Math.min(Math.max((m - buildMonths) / rampMonths, 0), 1);
      cf.push((benefitEur / 12) * ramp - runCost / 12);
    } else {
      cf.push(-buildCost / buildMonths);
    }
  }
  return cf;
}

export function npv(cf: number[], rate: number): number {
  return cf.reduce((acc, v, i) => acc + v / (1 + rate) ** ((i + 1) / 12), 0);
}

export function paybackMonth(cf: number[]): number | null {
  let cum = 0;
  for (let i = 0; i < cf.length; i++) {
    cum += cf[i];
    if (cum >= 0) return i + 1;
  }
  return null;
}

export function evaluate(opp: OppKey, base: Baseline, h: Inputs, hyp: Hypotheses): ScenarioResult {
  const eff = annualEffects(opp, base, h);
  const buildMonths = Number(hyp.opportunities[opp].build_months);
  const cf = cashFlows(
    eff.benefitEur,
    h.build_cost,
    h.run_cost,
    buildMonths,
    hyp.simulation.ramp_up_months,
    hyp.simulation.horizon_months,
  );
  let cum = 0;
  const cumulative = cf.map((v) => (cum += v));
  return {
    ...eff,
    fte: eff.hours / hyp.simulation.hours_per_fte,
    npv: npv(cf, h.discount_rate),
    paybackMonth: paybackMonth(cf),
    cumulative,
  };
}

export const COMMON_KEYS = ["hourly_cost", "discount_rate", "volume_factor", "adoption", "net_margin"] as const;
export const SPECIFIC_KEYS: Record<OppKey, string[]> = {
  completeness: ["loops_avoided", "completion_calls_avoided", "effort_shift", "causal_share"],
  prioritization: ["targeted_share", "recovery_rate", "extra_calls"],
  preanalysis: ["validation_time_saved"],
};
export const COST_KEYS = ["build_cost", "run_cost"] as const;

/** Valeurs centrales (mode) des hypothèses d'une opportunité. */
export function modes(hyp: Hypotheses, opp: OppKey): Inputs {
  const out: Inputs = {};
  for (const k of COMMON_KEYS) out[k] = hyp.common[k].mode;
  const spec = hyp.opportunities[opp] as unknown as Record<string, { mode: number }>;
  for (const k of [...SPECIFIC_KEYS[opp], ...COST_KEYS]) out[k] = spec[k].mode;
  return out;
}
