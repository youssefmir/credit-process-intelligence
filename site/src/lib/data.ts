/** Chargement des exports JSON du pipeline (site/public/data) et types associés. */

import { useEffect, useState } from "react";

export type Outcome = "approved" | "declined" | "cancelled" | "open";

export interface ActivityLabel {
  code: string;
  label: string;
  short: string;
  category: "A" | "O" | "W";
  description: string;
  rank: number;
  category_label: string;
}

export interface MapNode {
  id: string;
  label: string;
  short?: string;
  category: string;
  count: number;
  cases: number;
  repeats?: number;
  median_work_min?: number;
  median_wait_h?: number;
}

export interface MapEdge {
  source: string;
  target: string;
  count: number;
  cases: number;
  median_h?: number;
  mean_h?: number;
  total_h?: number;
}

export interface ProcessMap {
  view: string;
  cases: number;
  events: number;
  nodes: MapNode[];
  edges: MapEdge[];
}

export interface Variant {
  rank: number;
  activities: string[];
  count: number;
  share: number;
  cum_share: number;
  outcomes: Record<Outcome, number>;
  median_lead_time_d: number | null;
  median_work_min: number;
}

export interface Quantiles {
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  mean: number;
  n: number;
}

export interface QualityCheck {
  id: string;
  label: string;
  status: "ok" | "attention" | "info";
  value: string;
  detail: string;
  treatment: string;
}

export interface Hypothesis {
  label: string;
  unit: string;
  min: number;
  mode: number;
  max: number;
  justification: string;
}

export type OppKey = "completeness" | "prioritization" | "preanalysis";

export interface Baseline {
  annual_factor: number;
  loop_cases: number;
  loop_hours: number;
  revalidation_hours: number;
  completion_hours: number;
  validation_hours: number;
  loop_cancel_gap: number;
  approval_given_returned: number;
  mean_amount_approved: number;
  abandons_after_offer: number;
  offered_cases: number;
  recall_at_target: number;
  median_offer_call_min: number;
  median_lead_time_approved_d: number;
}

export interface McQuantiles {
  p10: number;
  p50: number;
  p90: number;
  mean: number;
}

export interface Opportunity {
  title: string;
  short: string;
  build_months: number;
  central: {
    hours: number;
    loans: number;
    extra_hours: number;
    capacity_eur: number;
    conversion_eur: number;
    extra_cost_eur: number;
    benefit_eur: number;
    fte: number;
    npv: number;
    payback_month: number | null;
    cumulative: number[];
  };
  monte_carlo: {
    iterations: number;
    npv: McQuantiles;
    prob_npv_positive: number;
    annual_benefit: McQuantiles;
    annual_hours: McQuantiles;
    annual_loans: McQuantiles;
    payback_within_horizon_share: number;
    payback_p50_month: number | null;
    npv_hist: { edges: number[]; counts: number[] };
    median_lead_time_approved_after_d?: McQuantiles;
  };
  tornado: {
    reference_npv: number;
    hypothesis: string;
    label: string;
    low_value: number;
    high_value: number;
    npv_low: number;
    npv_high: number;
    swing: number;
  }[];
  random_targeting_npv?: number;
  break_even_recovery_rate?: number | null;
  break_even_recall?: number | null;
}

export interface Hypotheses {
  simulation: { iterations: number; horizon_months: number; ramp_up_months: number; hours_per_fte: number };
  common: Record<string, Hypothesis>;
  opportunities: Record<OppKey, Record<string, Hypothesis | string | number> & { title: string; short: string; build_months: number }>;
}

export interface ReferenceScenario {
  opportunity: OppKey;
  inputs: Record<string, number>;
  outputs: { benefit_eur: number; hours: number; loans: number; npv: number; payback_month: number | null };
}

export interface BusinessCase {
  baseline: Baseline;
  opportunities: Record<OppKey, Opportunity>;
  portfolio: { preanalysis_npv_after_completeness: number; total_npv_central: number; validation_hours_remaining_after_completeness: number };
  reference_scenarios: ReferenceScenario[];
  hypotheses: Hypotheses;
  calibration: {
    available: boolean;
    offers?: number;
    selected_offers?: number;
    apr?: Record<string, number>;
    terms_months?: Record<string, number>;
    amount_eur?: Record<string, number>;
    gross_interest_ratio?: Record<string, number>;
  };
}

export interface Replay {
  t0: string;
  minutes: number;
  stations: { id: string; label: string }[];
  transitions: { from: string; to: string; cases: number }[];
  cases: number[][];
}

// Les fichiers volumineux ou peu structurés restent typés de façon souple.
/* eslint-disable @typescript-eslint/no-explicit-any */
export interface AllData {
  meta: any;
  summary: any;
  labels: { activities: ActivityLabel[]; outcomes: Record<Outcome, string> };
  quality: { checks: QualityCheck[]; session_cleaning: any; threshold_sensitivity: any[] };
  process: { outcomes: any[]; maps: Record<"complete" | "milestones", ProcessMap>; conformance: any; inductive: any };
  variants: Record<"milestones" | "complete", { n_variants: number; n_cases: number; singletons: number; coverage_top: Record<string, number>; variants: Variant[] }>;
  time: any;
  rework: any;
  abandon: any;
  model: any;
  business_case: BusinessCase;
  preanalysis_example: any;
}
/* eslint-enable @typescript-eslint/no-explicit-any */

const FILES = [
  "meta",
  "summary",
  "labels",
  "quality",
  "process",
  "variants",
  "time",
  "rework",
  "abandon",
  "model",
  "business_case",
  "preanalysis_example",
] as const;

export function dataUrl(name: string): string {
  return `${import.meta.env.BASE_URL}data/${name}.json`;
}

async function fetchJson<T>(name: string): Promise<T> {
  const res = await fetch(dataUrl(name));
  if (!res.ok) throw new Error(`${name}.json : ${res.status}`);
  return (await res.json()) as T;
}

export async function loadAll(): Promise<AllData> {
  const entries = await Promise.all(FILES.map(async (f) => [f, await fetchJson(f)] as const));
  return Object.fromEntries(entries) as unknown as AllData;
}

export function useAllData(): { data: AllData | null; error: string | null } {
  const [data, setData] = useState<AllData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    loadAll()
      .then((d) => alive && setData(d))
      .catch((e: unknown) => alive && setError(String(e)));
    return () => {
      alive = false;
    };
  }, []);
  return { data, error };
}

export async function loadReplay(): Promise<Replay> {
  return fetchJson<Replay>("replay");
}
