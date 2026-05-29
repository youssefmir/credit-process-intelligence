import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { annualEffects, cashFlows, evaluate, modes, npv, paybackMonth } from "../src/lib/businessCase";
import type { BusinessCase } from "../src/lib/data";

const bc = JSON.parse(
  readFileSync(resolve(__dirname, "../public/data/business_case.json"), "utf-8"),
) as BusinessCase;

describe("concordance avec le pipeline Python", () => {
  it.each(bc.reference_scenarios.map((s, i) => [i, s] as const))("scénario %i", (_, sc) => {
    const r = evaluate(sc.opportunity, bc.baseline, sc.inputs, bc.hypotheses);
    expect(r.benefitEur).toBeCloseTo(sc.outputs.benefit_eur, 6);
    expect(r.hours).toBeCloseTo(sc.outputs.hours, 6);
    expect(r.loans).toBeCloseTo(sc.outputs.loans, 6);
    expect(r.npv).toBeCloseTo(sc.outputs.npv, 4);
    expect(r.paybackMonth).toBe(sc.outputs.payback_month);
  });

  it("scénario central identique à l'export", () => {
    for (const opp of ["completeness", "prioritization", "preanalysis"] as const) {
      const r = evaluate(opp, bc.baseline, modes(bc.hypotheses, opp), bc.hypotheses);
      expect(r.npv).toBeCloseTo(bc.opportunities[opp].central.npv, 0);
    }
  });
});

describe("invariants", () => {
  it("la construction est étalée sur sa durée", () => {
    const cf = cashFlows(120_000, 60_000, 12_000, 4, 6, 36);
    expect(cf.slice(0, 4).reduce((a, b) => a + b, 0)).toBeCloseTo(-60_000, 6);
    expect(cf).toHaveLength(36);
  });

  it("pas de retour sur investissement sans bénéfice", () => {
    expect(paybackMonth([-10, 1, 1])).toBeNull();
    expect(npv([-10, 0, 0], 0.1)).toBeLessThan(0);
  });

  it("plus de boucles évitées, plus de gain", () => {
    const h = modes(bc.hypotheses, "completeness");
    const lo = annualEffects("completeness", bc.baseline, { ...h, loops_avoided: 0.2 });
    const hi = annualEffects("completeness", bc.baseline, { ...h, loops_avoided: 0.5 });
    expect(hi.benefitEur).toBeGreaterThan(lo.benefitEur);
  });
});
