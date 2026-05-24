"""Orchestration : ingestion → qualité → découverte → KPI → modèle → simulation → export.

Une seule commande (``python -m cpi pipeline``) régénère tous les fichiers JSON consommés
par le site (``site/public/data``) ainsi que les modèles BPMN et les documents générés.
Les sorties sont déterministes (graine fixe, pas d'horodatage d'exécution).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cpi import (
    abandon,
    assistant,
    calibration,
    data,
    discovery,
    features,
    kpi,
    labels,
    model,
    quality,
    replay,
    rework,
    simulation,
)
from cpi.cases import build_cases
from cpi.config import DATASET, DOCS_DIR, MODELS_DIR, SEED, SITE_DATA_DIR
from cpi.ingest import load_events
from cpi.sessions import build_sessions, build_waits

SCHEMA_VERSION = 1


def _clean(obj: Any) -> Any:
    """Convertit récursivement en types JSON (NaN → null, numpy → Python)."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [_clean(v) for v in obj.tolist()]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if np.isnan(f) or np.isinf(f) else f
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def write_json(name: str, payload: Any, out_dir: Path = SITE_DATA_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    body = {"schema_version": SCHEMA_VERSION, **payload} if isinstance(payload, dict) else payload
    path.write_text(
        json.dumps(_clean(body), ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return path


class Steps:
    """Petit chronométrage lisible des étapes."""

    def __init__(self, log: Callable[[str], None]) -> None:
        self.log = log
        self.t = time.perf_counter()

    def __call__(self, label: str) -> None:
        now = time.perf_counter()
        self.log(f"  {label} ({now - self.t:.1f} s)")
        self.t = now


def run(log: Callable[[str], None] = print, with_docs: bool = True) -> dict[str, Any]:
    step = Steps(log)
    events = load_events()
    sessions, unclosed = build_sessions(events)
    waits = build_waits(events)
    cases = build_cases(events, sessions)
    window = kpi.observation_window(events)
    annual = float(window["annual_factor"])
    step("ingestion, sessions et dossiers")

    checks, quality_extra = quality.run_checks(events, sessions, unclosed, cases)
    step("qualité des données")

    maps = {
        v: discovery.process_map(events, sessions, waits, v) for v in ("complete", "milestones")
    }
    variants = {v: discovery.variants(events, cases, v, top=40) for v in ("milestones", "complete")}
    conformance = discovery.nominal_conformance(events, cases)
    inductive = discovery.inductive_model(events, DOCS_DIR / "bpmn" / "discovered-inductive.bpmn")
    step("découverte de processus")

    lead = kpi.lead_times(cases)
    phases = kpi.phase_decomposition(cases, sessions)
    activities = kpi.activity_times(sessions, waits)
    flow = kpi.flow_efficiency(cases)
    bottlenecks = kpi.bottlenecks(maps["milestones"]["edges"])
    weekly = kpi.weekly_workload(sessions)
    heatmap = kpi.work_heatmap(sessions)
    resources = kpi.resource_workload(sessions, annual)
    rw = rework.rework_summary(events, sessions, cases, annual)
    ab = abandon.abandon_summary(cases)
    step("KPI, allers-retours et abandons")

    dataset = features.build_dataset(events, sessions, waits, cases)
    split = features.temporal_split(dataset, events["timestamp"].max())
    model_results, trained = model.run(dataset, split, events, sessions, cases)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    trained.gbm.booster_.save_model(str(MODELS_DIR / "abandon_gbm.txt"))
    step("modèle de risque d'abandon")

    target_share = 0.2
    recall = next(
        a["recall"]
        for a in model_results["models"]["gbm"]["gains"]["at_k"]
        if a["share"] == target_share
    )
    loops = rework.incomplete_loops(events, sessions, cases)
    median_call_min = float(
        sessions.loc[sessions["activity"] == "W_Nabellen offertes", "dur_s"].median() / 60
    )
    business = simulation.run(cases, loops, annual, recall, median_call_min)
    calib = calibration.run()
    step("business case (rejeu + Monte Carlo)")

    prov = data.provenance(data.BPIC2012) or {}
    prov17 = data.provenance(data.BPIC2017_OFFERS)
    outcomes = kpi.outcome_summary(cases)
    meta = {
        "dataset": {
            "name": DATASET.name,
            "author": DATASET.author,
            "publisher": DATASET.publisher,
            "doi": DATASET.doi_url,
            "landing_page": DATASET.landing_page,
            "terms": DATASET.terms,
            "citation": DATASET.citation,
            "source_used": prov.get("source"),
            "sha256": prov.get("sha256"),
        },
        "secondary_dataset": None
        if prov17 is None
        else {
            "name": data.BPIC2017_OFFERS.title,
            "doi": data.BPIC2017_OFFERS.doi,
            "citation": data.BPIC2017_OFFERS.citation,
            "terms": "4TU General Terms of Use",
            "use": "Étalonnage de l'hypothèse de marge (intérêts implicites des offres 2016).",
        },
        "counts": {
            "cases": int(cases.shape[0]),
            "events": len(events),
            "activities": int(events["activity"].nunique()),
            "resources": int(events["resource"].nunique()),
        },
        "window": window,
        "seed": SEED,
        "commands": {"all": "make all", "pipeline": "make pipeline", "data": "make data"},
    }
    write_json("meta", meta)
    write_json(
        "labels",
        {
            "activities": labels.as_records(),
            "outcomes": labels.OUTCOME_LABELS,
            "lifecycle": labels.LIFECYCLE_LABELS,
        },
    )
    write_json("quality", {"checks": quality.as_records(checks), **quality_extra})
    write_json(
        "process",
        {
            "outcomes": outcomes,
            "maps": maps,
            "conformance": conformance,
            "inductive": inductive,
        },
    )
    write_json("variants", variants)
    write_json(
        "time",
        {
            "lead_times": lead,
            "phases": phases,
            "activities": activities,
            "flow_efficiency": flow,
            "bottlenecks": bottlenecks,
            "weekly": weekly,
            "heatmap": heatmap,
            "resources": resources,
        },
    )
    write_json("rework", rw)
    write_json("abandon", ab)
    model_export = {k: v for k, v in model_results.items() if k != "test_scores"}
    write_json("model", model_export)
    write_json("business_case", {**business, "calibration": calib})
    write_json("replay", replay.export(events, cases))
    example = cases[
        (cases["outcome"] == "approved") & cases["has_incomplete_calls"] & (cases["n_offers"] >= 2)
    ].index.sort_values()[0]
    write_json("preanalysis_example", assistant.build_brief(example, events, sessions, cases))
    step("export JSON")

    summary = headline(
        cases,
        window,
        phases,
        flow,
        rw,
        ab,
        conformance,
        variants,
        model_results,
        business,
        outcomes,
    )
    write_json("summary", summary)

    if with_docs:
        from cpi import bpmn, report

        bpmn.write_models(summary)
        report.render_all()
        step("BPMN et documents générés")
    return summary


def headline(
    cases: pd.DataFrame,
    window: dict[str, Any],
    phases: dict[str, Any],
    flow: dict[str, Any],
    rw: dict[str, Any],
    ab: dict[str, Any],
    conformance: dict[str, Any],
    variants: dict[str, Any],
    model_results: dict[str, Any],
    business: dict[str, Any],
    outcomes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Chiffres clés repris par la synthèse, le README et les documents."""
    appr = phases["approved_summary"]
    gbm = model_results["models"]["gbm"]
    at20 = next(a for a in gbm["gains"]["at_k"] if a["share"] == 0.2)
    opp = business["opportunities"]
    by = {o["outcome"]: o for o in outcomes}
    return {
        "cases": int(cases.shape[0]),
        "annualized_applications": window["annualized_applications"],
        "approved_share": by["approved"]["share"],
        "declined_share": by["declined"]["share"],
        "cancelled_share": by["cancelled"]["share"],
        "median_lead_time_approved_d": appr["median_lead_time_d"],
        "mean_work_approved_h": appr["mean_work_h"],
        "flow_efficiency_approved": appr["flow_efficiency_aggregate"],
        "waiting_share_approved": round(1 - appr["flow_efficiency_aggregate"], 4),
        "first_time_right_share": conformance["first_time_right_share"],
        "milestone_variants": variants["milestones"]["n_variants"],
        "top5_variant_coverage": variants["milestones"]["coverage_top"]["5"],
        "incomplete_share_of_validated": rw["incomplete"]["share_of_validated"],
        "incomplete_loop_hours_annual": rw["incomplete"]["loop_hours_annual"],
        "rework_hours_annual": rw["total_rework_hours_annual"],
        "cancel_rate_after_offer": ab["cancel_rate_after_offer"],
        "expiry_window_share": ab["after_offer"]["expiry_window_share"],
        "model_roc_auc": gbm["metrics"]["roc_auc"],
        "model_recall_at_20": at20["recall"],
        "model_lift_at_20": at20["lift"],
        "model_deployable": model_results["acceptance"]["deployable"],
        "business": {
            k: {
                "title": v["title"],
                "npv_p50": v["monte_carlo"]["npv"]["p50"],
                "npv_p10": v["monte_carlo"]["npv"]["p10"],
                "npv_p90": v["monte_carlo"]["npv"]["p90"],
                "prob_npv_positive": v["monte_carlo"]["prob_npv_positive"],
                "annual_benefit_p50": v["monte_carlo"]["annual_benefit"]["p50"],
                "annual_hours_p50": v["monte_carlo"]["annual_hours"]["p50"],
                "payback_month_central": v["central"]["payback_month"],
            }
            for k, v in opp.items()
        },
    }
