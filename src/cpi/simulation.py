"""Business case : rejeu contrefactuel des dossiers réels et Monte Carlo sur les hypothèses.

Trois opportunités sont évaluées séparément, puis en portefeuille :

* ``completeness`` — contrôle automatique de complétude à la soumission ;
* ``prioritization`` — priorisation des relances d'offres par score d'abandon ;
* ``preanalysis`` — pré-analyse assistée des dossiers à valider.

Les **valeurs de référence** (volumes, heures, taux) sont mesurées dans le journal ; les
**hypothèses** viennent de ``config/hypotheses.yaml``. La fonction déterministe
:func:`annual_effects` (valeurs espérées) est reproduite à l'identique dans le simulateur
du site ; des scénarios de référence exportés garantissent la concordance (test croisé).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from cpi.config import HYPOTHESES_FILE, SEED

OPPORTUNITIES = ("completeness", "prioritization", "preanalysis")
COMMON = ("hourly_cost", "discount_rate", "volume_factor", "adoption", "net_margin")
SPECIFIC = {
    "completeness": ("loops_avoided", "completion_calls_avoided", "effort_shift", "causal_share"),
    "prioritization": ("targeted_share", "recovery_rate", "extra_calls"),
    "preanalysis": ("validation_time_saved",),
}
COSTS = ("build_cost", "run_cost")


def load_hypotheses(path: Path = HYPOTHESES_FILE) -> dict[str, Any]:
    return dict(yaml.safe_load(path.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class Baseline:
    """Valeurs mesurées sur la fenêtre d'observation (non annualisées)."""

    annual_factor: float
    loop_cases: int
    loop_hours: float
    revalidation_hours: float
    completion_hours: float
    validation_hours: float
    loop_cancel_gap: float
    approval_given_returned: float
    mean_amount_approved: float
    abandons_after_offer: int
    offered_cases: int
    recall_at_target: float
    median_offer_call_min: float
    median_lead_time_approved_d: float


def measure_baseline(
    cases: pd.DataFrame,
    loops: pd.DataFrame,
    annual_factor: float,
    recall_at_target: float,
    median_offer_call_min: float,
) -> Baseline:
    closed = cases[cases["outcome"] != "open"]
    returned = closed[closed["t_sent_back"].notna()]
    has_loop = returned.index.isin(loops.index)
    cancel = returned["outcome"] == "cancelled"
    gap = float(cancel[has_loop].mean() - cancel[~has_loop].mean())
    after_offer = closed[(closed["outcome"] == "cancelled") & closed["t_first_offer"].notna()]
    approved = cases[cases["outcome"] == "approved"]
    return Baseline(
        annual_factor=annual_factor,
        loop_cases=len(loops),
        loop_hours=float((loops["call_work_s"] + loops["reval_work_s"]).sum() / 3600),
        revalidation_hours=float(loops["reval_work_s"].sum() / 3600),
        completion_hours=float(cases["work_completion_s"].sum() / 3600),
        validation_hours=float(cases["work_validation_s"].sum() / 3600),
        loop_cancel_gap=max(gap, 0.0),
        approval_given_returned=float((returned["outcome"] == "approved").mean()),
        mean_amount_approved=float(approved["amount_req"].mean()),
        abandons_after_offer=len(after_offer),
        offered_cases=int(cases["t_first_offer"].notna().sum()),
        recall_at_target=recall_at_target,
        median_offer_call_min=median_offer_call_min,
        median_lead_time_approved_d=float(approved["lead_time_d"].median()),
    )


def modes(hyp: dict[str, Any], opp: str) -> dict[str, float]:
    """Valeurs centrales (mode) des hypothèses utiles à une opportunité."""
    out = {k: float(hyp["common"][k]["mode"]) for k in COMMON}
    spec = hyp["opportunities"][opp]
    out |= {k: float(spec[k]["mode"]) for k in SPECIFIC[opp] + COSTS}
    return out


def bounds(hyp: dict[str, Any], opp: str) -> dict[str, tuple[float, float, float]]:
    out = {k: hyp["common"][k] for k in COMMON}
    spec = hyp["opportunities"][opp]
    out |= {k: spec[k] for k in SPECIFIC[opp] + COSTS}
    return {k: (float(v["min"]), float(v["mode"]), float(v["max"])) for k, v in out.items()}


def annual_effects(
    opp: str,
    base: Baseline,
    h: dict[str, float],
    validation_hours_override: float | None = None,
    replay: dict[str, float] | None = None,
) -> dict[str, float]:
    """Effets annuels en régime de croisière.

    Sans ``replay`` : valeurs espérées (formules reproduites à l'identique dans
    ``site/src/lib/businessCase.ts``). Avec ``replay`` : heures et dossiers réellement
    évités lors d'un rejeu dossier par dossier (Monte Carlo).
    """
    scale = base.annual_factor * h["volume_factor"] * h["adoption"]
    hours = 0.0
    loans = 0.0
    extra_hours = 0.0
    if opp == "completeness":
        loop_hours = h["loops_avoided"] * base.loop_hours
        loop_cases = h["loops_avoided"] * base.loop_cases
        if replay is not None:
            loop_hours, loop_cases = replay["loop_hours"], replay["loop_cases"]
        hours = (loop_hours + h["completion_calls_avoided"] * base.completion_hours) * (
            1 - h["effort_shift"]
        )
        loans = loop_cases * base.loop_cancel_gap * h["causal_share"] * base.approval_given_returned
    elif opp == "prioritization":
        recovered = base.abandons_after_offer * base.recall_at_target * h["recovery_rate"]
        loans = recovered * base.approval_given_returned
        extra_hours = (
            h["targeted_share"]
            * base.offered_cases
            * h["extra_calls"]
            * base.median_offer_call_min
            / 60
        )
    elif opp == "preanalysis":
        val = (
            base.validation_hours
            if validation_hours_override is None
            else validation_hours_override
        )
        hours = h["validation_time_saved"] * val
    else:  # pragma: no cover - garde-fou
        raise ValueError(opp)
    hours, loans, extra_hours = hours * scale, loans * scale, extra_hours * scale
    capacity_eur = hours * h["hourly_cost"]
    conversion_eur = loans * base.mean_amount_approved * h["net_margin"]
    extra_cost_eur = extra_hours * h["hourly_cost"]
    return {
        "hours": hours,
        "loans": loans,
        "extra_hours": extra_hours,
        "capacity_eur": capacity_eur,
        "conversion_eur": conversion_eur,
        "extra_cost_eur": extra_cost_eur,
        "benefit_eur": capacity_eur + conversion_eur - extra_cost_eur,
    }


def cash_flows(
    benefit_eur: float,
    build_cost: float,
    run_cost: float,
    build_months: int,
    ramp_months: int,
    horizon_months: int,
) -> np.ndarray:
    """Flux mensuels : construction étalée, puis bénéfices en montée en charge linéaire."""
    m = np.arange(1, horizon_months + 1)
    live = m > build_months
    ramp = np.clip((m - build_months) / ramp_months, 0, 1)
    cf = np.where(live, benefit_eur / 12 * ramp - run_cost / 12, -build_cost / build_months)
    return np.asarray(cf, dtype=float)


def npv(cf: np.ndarray, rate: float) -> float:
    m = np.arange(1, len(cf) + 1)
    return float(np.sum(cf / (1 + rate) ** (m / 12)))


def payback_month(cf: np.ndarray) -> int | None:
    cum = np.cumsum(cf)
    hit = np.flatnonzero(cum >= 0)
    return int(hit[0] + 1) if len(hit) else None


def evaluate_scenario(
    opp: str,
    base: Baseline,
    h: dict[str, float],
    hyp: dict[str, Any],
    validation_hours_override: float | None = None,
    replay: dict[str, float] | None = None,
) -> dict[str, Any]:
    eff = annual_effects(opp, base, h, validation_hours_override, replay)
    sim = hyp["simulation"]
    cf = cash_flows(
        eff["benefit_eur"],
        h["build_cost"],
        h["run_cost"],
        int(hyp["opportunities"][opp]["build_months"]),
        int(sim["ramp_up_months"]),
        int(sim["horizon_months"]),
    )
    return {
        **eff,
        "fte": eff["hours"] / float(sim["hours_per_fte"]),
        "npv": npv(cf, h["discount_rate"]),
        "payback_month": payback_month(cf),
        "cumulative": np.cumsum(cf),
    }


def _triangular(rng: np.random.Generator, lo: float, mode: float, hi: float, n: int) -> np.ndarray:
    if hi <= lo:
        return np.full(n, mode)
    return rng.triangular(lo, mode, hi, n)


def _quantiles(x: np.ndarray) -> dict[str, float]:
    return {
        "p10": round(float(np.percentile(x, 10)), 1),
        "p50": round(float(np.percentile(x, 50)), 1),
        "p90": round(float(np.percentile(x, 90)), 1),
        "mean": round(float(np.mean(x)), 1),
    }


def monte_carlo(
    opp: str,
    base: Baseline,
    hyp: dict[str, Any],
    loops: pd.DataFrame,
    approved_lead: pd.Series,
    n: int | None = None,
    seed: int = SEED,
) -> dict[str, Any]:
    """Monte Carlo sur les hypothèses ; rejeu dossier par dossier pour la complétude.

    Pour ``completeness``, chaque boucle réelle est évitée ou non (tirage de Bernoulli) :
    les heures économisées sont celles des boucles effectivement évitées, et le délai de
    chaque dossier approuvé est recalculé sans sa boucle.
    """
    n = int(n or hyp["simulation"]["iterations"])
    rng = np.random.default_rng(seed)
    b = bounds(hyp, opp)
    draws = {k: _triangular(rng, *v, n) for k, v in b.items()}
    npvs = np.empty(n)
    benefits = np.empty(n)
    hours = np.empty(n)
    loans = np.empty(n)
    paybacks: list[int | None] = []
    medians_after = np.empty(n) if opp == "completeness" else None

    loop_work_h = ((loops["call_work_s"] + loops["reval_work_s"]) / 3600).to_numpy()
    loop_delay_all = loops["loop_delay_d"].to_numpy()
    pos = loops.index.get_indexer(approved_lead.index)  # -1 : dossier approuvé sans boucle
    lead = approved_lead.to_numpy()
    for i in range(n):
        h = {k: float(v[i]) for k, v in draws.items()}
        if opp == "completeness":
            # Rejeu : chaque boucle réelle est évitée ou non ; on retire ses heures réelles
            # et, pour un dossier approuvé, son délai réel.
            avoided = rng.random(len(loop_work_h)) < h["loops_avoided"]
            replay = {
                "loop_hours": float(loop_work_h[avoided].sum()),
                "loop_cases": float(avoided.sum()),
            }
            res = evaluate_scenario(opp, base, h, hyp, replay=replay)
            appr_avoided = np.where(pos >= 0, avoided[np.clip(pos, 0, None)], False)
            saved = np.where(appr_avoided, loop_delay_all[np.clip(pos, 0, None)], 0.0)
            assert medians_after is not None
            medians_after[i] = np.median(lead - saved)
        else:
            res = evaluate_scenario(opp, base, h, hyp)
        npvs[i] = res["npv"]
        benefits[i] = res["benefit_eur"]
        hours[i] = res["hours"]
        loans[i] = res["loans"]
        paybacks.append(res["payback_month"])

    pb = np.array([p if p is not None else np.inf for p in paybacks], dtype=float)
    hist_counts, hist_edges = np.histogram(npvs, bins=30)
    out: dict[str, Any] = {
        "iterations": n,
        "npv": _quantiles(npvs),
        "prob_npv_positive": round(float((npvs > 0).mean()), 4),
        "annual_benefit": _quantiles(benefits),
        "annual_hours": _quantiles(hours),
        "annual_loans": _quantiles(loans),
        "payback_within_horizon_share": round(float(np.isfinite(pb).mean()), 4),
        "payback_p50_month": float(np.median(pb)) if np.isfinite(np.median(pb)) else None,
        "npv_hist": {
            "edges": [round(float(e), 0) for e in hist_edges],
            "counts": hist_counts.astype(int).tolist(),
        },
    }
    if medians_after is not None:
        out["median_lead_time_approved_after_d"] = _quantiles(medians_after)
    return out


def tornado(opp: str, base: Baseline, hyp: dict[str, Any]) -> list[dict[str, Any]]:
    """Sensibilité : VAN quand une hypothèse passe à son min / max (les autres au mode)."""
    center = modes(hyp, opp)
    ref = evaluate_scenario(opp, base, center, hyp)["npv"]
    rows = []
    for k, (lo, _, hi) in bounds(hyp, opp).items():
        if lo == hi:
            continue
        v_lo = evaluate_scenario(opp, base, {**center, k: lo}, hyp)["npv"]
        v_hi = evaluate_scenario(opp, base, {**center, k: hi}, hyp)["npv"]
        label = (hyp["common"].get(k) or hyp["opportunities"][opp].get(k))["label"]
        rows.append(
            {
                "hypothesis": k,
                "label": label,
                "low_value": lo,
                "high_value": hi,
                "npv_low": round(v_lo, 0),
                "npv_high": round(v_hi, 0),
                "swing": round(abs(v_hi - v_lo), 0),
            }
        )
    rows.sort(key=lambda r: -r["swing"])
    return [{"reference_npv": round(ref, 0), **r} for r in rows]


def break_even(opp: str, base: Baseline, hyp: dict[str, Any], key: str) -> float | None:
    """Valeur de l'hypothèse ``key`` qui annule la VAN (autres hypothèses au mode)."""
    center = modes(hyp, opp)

    def f(x: float) -> float:
        if key == "recall_at_target":
            b2 = Baseline(**{**asdict(base), "recall_at_target": x})
            return float(evaluate_scenario(opp, b2, center, hyp)["npv"])
        return float(evaluate_scenario(opp, base, {**center, key: x}, hyp)["npv"])

    lo, hi = 0.0, 1.0
    if f(hi) < 0:
        return None
    if f(lo) > 0:
        return 0.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2, 4)


def run(
    cases: pd.DataFrame,
    loops: pd.DataFrame,
    annual_factor: float,
    recall_at_target: float,
    median_offer_call_min: float,
    hyp: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hyp = hyp or load_hypotheses()
    base = measure_baseline(cases, loops, annual_factor, recall_at_target, median_offer_call_min)
    approved_lead = cases.loc[cases["outcome"] == "approved", "lead_time_d"]
    results: dict[str, Any] = {"baseline": asdict(base), "opportunities": {}}
    for opp in OPPORTUNITIES:
        center = modes(hyp, opp)
        central = evaluate_scenario(opp, base, center, hyp)
        entry: dict[str, Any] = {
            "title": hyp["opportunities"][opp]["title"],
            "short": hyp["opportunities"][opp]["short"],
            "build_months": hyp["opportunities"][opp]["build_months"],
            "central": {
                k: (round(float(v), 2) if not isinstance(v, np.ndarray) else None)
                for k, v in central.items()
                if k not in ("cumulative", "payback_month")
            }
            | {
                "payback_month": central["payback_month"],
                "cumulative": [round(float(x), 0) for x in central["cumulative"]],
            },
            "monte_carlo": monte_carlo(opp, base, hyp, loops, approved_lead),
            "tornado": tornado(opp, base, hyp),
        }
        results["opportunities"][opp] = entry
    prio = results["opportunities"]["prioritization"]
    random_base = Baseline(
        **{**asdict(base), "recall_at_target": modes(hyp, "prioritization")["targeted_share"]}
    )
    prio["random_targeting_npv"] = round(
        evaluate_scenario("prioritization", random_base, modes(hyp, "prioritization"), hyp)["npv"],
        0,
    )
    prio["break_even_recovery_rate"] = break_even("prioritization", base, hyp, "recovery_rate")
    prio["break_even_recall"] = break_even("prioritization", base, hyp, "recall_at_target")

    # Portefeuille : la pré-analyse s'applique aux heures de validation restantes après
    # la suppression des re-validations évitées par le contrôle de complétude.
    c_mode = modes(hyp, "completeness")
    remaining_val = base.validation_hours - c_mode["loops_avoided"] * base.revalidation_hours
    pre_net = evaluate_scenario(
        "preanalysis", base, modes(hyp, "preanalysis"), hyp, validation_hours_override=remaining_val
    )
    total_npv = (
        results["opportunities"]["completeness"]["central"]["npv"]
        + results["opportunities"]["prioritization"]["central"]["npv"]
        + pre_net["npv"]
    )
    results["portfolio"] = {
        "preanalysis_npv_after_completeness": round(pre_net["npv"], 0),
        "total_npv_central": round(total_npv, 0),
        "validation_hours_remaining_after_completeness": round(remaining_val, 1),
    }
    results["reference_scenarios"] = reference_scenarios(base, hyp)
    results["hypotheses"] = hyp
    return results


def reference_scenarios(base: Baseline, hyp: dict[str, Any], k: int = 4) -> list[dict]:
    """Scénarios (entrées → sorties) servant au test de concordance du simulateur web."""
    rng = np.random.default_rng(SEED + 1)
    out = []
    for opp in OPPORTUNITIES:
        b = bounds(hyp, opp)
        scenarios = [modes(hyp, opp)] + [
            {
                key: float(rng.uniform(lo, hi)) if hi > lo else mode
                for key, (lo, mode, hi) in b.items()
            }
            for _ in range(k)
        ]
        for h in scenarios:
            r = evaluate_scenario(opp, base, h, hyp)
            out.append(
                {
                    "opportunity": opp,
                    "inputs": h,
                    "outputs": {
                        "benefit_eur": r["benefit_eur"],
                        "hours": r["hours"],
                        "loans": r["loans"],
                        "npv": r["npv"],
                        "payback_month": r["payback_month"],
                    },
                }
            )
    return out
