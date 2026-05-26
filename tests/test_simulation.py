"""Invariants du business case et concordance des scénarios de référence."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from cpi import simulation as sim

BASE = sim.Baseline(
    annual_factor=2.4,
    loop_cases=1600,
    loop_hours=1500.0,
    revalidation_hours=500.0,
    completion_hours=2100.0,
    validation_hours=2100.0,
    loop_cancel_gap=0.07,
    approval_given_returned=0.7,
    mean_amount_approved=15_000.0,
    abandons_after_offer=1600,
    offered_cases=5000,
    recall_at_target=0.25,
    median_offer_call_min=1.7,
    median_lead_time_approved_d=14.4,
)


@pytest.fixture(scope="module")
def hyp() -> dict:
    return sim.load_hypotheses()


def test_effects_increase_with_avoided_loops(hyp: dict) -> None:
    h = sim.modes(hyp, "completeness")
    lo = sim.annual_effects("completeness", BASE, {**h, "loops_avoided": 0.2})
    hi = sim.annual_effects("completeness", BASE, {**h, "loops_avoided": 0.5})
    assert hi["hours"] > lo["hours"] and hi["benefit_eur"] > lo["benefit_eur"]


def test_no_lever_means_no_benefit_and_negative_npv(hyp: dict) -> None:
    h = {**sim.modes(hyp, "completeness"), "loops_avoided": 0.0, "completion_calls_avoided": 0.0}
    r = sim.evaluate_scenario("completeness", BASE, h, hyp)
    assert r["benefit_eur"] == 0
    assert r["npv"] < 0
    assert r["payback_month"] is None


def test_full_effort_shift_cancels_hours(hyp: dict) -> None:
    h = {**sim.modes(hyp, "completeness"), "effort_shift": 1.0}
    assert sim.annual_effects("completeness", BASE, h)["hours"] == pytest.approx(0)


def test_prioritization_without_targeting_only_costs(hyp: dict) -> None:
    h = sim.modes(hyp, "prioritization")
    r = sim.annual_effects("prioritization", replace(BASE, recall_at_target=0.0), h)
    assert r["loans"] == 0 and r["benefit_eur"] < 0


def test_npv_decreases_with_build_cost(hyp: dict) -> None:
    h = sim.modes(hyp, "preanalysis")
    a = sim.evaluate_scenario("preanalysis", BASE, {**h, "build_cost": 50_000}, hyp)
    b = sim.evaluate_scenario("preanalysis", BASE, {**h, "build_cost": 150_000}, hyp)
    assert a["npv"] > b["npv"]


def test_cash_flows_spread_build_cost() -> None:
    cf = sim.cash_flows(120_000, 60_000, 12_000, build_months=4, ramp_months=6, horizon_months=36)
    assert cf[:4].sum() == pytest.approx(-60_000)
    assert cf[-1] == pytest.approx(120_000 / 12 - 12_000 / 12)
    assert len(cf) == 36


def test_payback_month() -> None:
    assert sim.payback_month(np.array([-10.0, 5.0, 5.0, 5.0])) == 3
    assert sim.payback_month(np.array([-10.0, 1.0])) is None


def _loops() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 200
    return pd.DataFrame(
        {
            "call_work_s": rng.uniform(100, 3000, n),
            "reval_work_s": rng.uniform(0, 1500, n),
            "loop_delay_d": rng.uniform(0.5, 6, n),
        },
        index=[f"L{i}" for i in range(n)],
    )


def test_monte_carlo_is_reproducible_and_ordered(hyp: dict) -> None:
    loops = _loops()
    base = replace(
        BASE,
        loop_cases=len(loops),
        loop_hours=float((loops["call_work_s"] + loops["reval_work_s"]).sum() / 3600),
    )
    lead = pd.Series(np.full(50, 14.0), index=[f"L{i}" for i in range(50)])
    a = sim.monte_carlo("completeness", base, hyp, loops, lead, n=300)
    b = sim.monte_carlo("completeness", base, hyp, loops, lead, n=300)
    assert a == b
    q = a["npv"]
    assert q["p10"] <= q["p50"] <= q["p90"]
    assert 0 <= a["prob_npv_positive"] <= 1
    # Le rejeu retire des boucles : le délai médian ne peut que baisser.
    assert a["median_lead_time_approved_after_d"]["p90"] <= 14.0


def test_reference_scenarios_are_consistent(hyp: dict) -> None:
    for sc in sim.reference_scenarios(BASE, hyp, k=2):
        r = sim.evaluate_scenario(sc["opportunity"], BASE, sc["inputs"], hyp)
        assert r["npv"] == pytest.approx(sc["outputs"]["npv"])
        assert r["payback_month"] == sc["outputs"]["payback_month"]


def test_break_even_recovery_rate(hyp: dict) -> None:
    be = sim.break_even("prioritization", BASE, hyp, "recovery_rate")
    assert be is not None and 0 < be < 1
    h = {**sim.modes(hyp, "prioritization"), "recovery_rate": be}
    assert sim.evaluate_scenario("prioritization", BASE, h, hyp)["npv"] == pytest.approx(0, abs=50)
