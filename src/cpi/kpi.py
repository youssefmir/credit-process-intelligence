"""Indicateurs de délai, de temps d'attente / de travail, de goulots et de charge."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from cpi import labels
from cpi.cases import PHASE_LABELS, PHASES, W_ACTIVITIES, phase_of_sessions
from cpi.config import TIMEZONE

QUANTILES = (0.1, 0.25, 0.5, 0.75, 0.9)


def _q(s: pd.Series, digits: int = 2) -> dict[str, float | None]:
    s = s.dropna()
    if s.empty:
        return {f"p{int(q * 100)}": None for q in QUANTILES} | {"mean": None, "n": 0}
    out: dict[str, float | None] = {
        f"p{int(q * 100)}": round(float(s.quantile(q)), digits) for q in QUANTILES
    }
    out["mean"] = round(float(s.mean()), digits)
    out["n"] = len(s)
    return out


def observation_window(events: pd.DataFrame) -> dict[str, Any]:
    """Fenêtre d'observation et facteur d'annualisation (dépôts / jour × 365)."""
    sub = events.loc[events["activity"] == "A_SUBMITTED", "timestamp"]
    days = (sub.max() - sub.min()).total_seconds() / 86400
    n = int(events["case_id"].nunique())
    return {
        "first_submission": sub.min().tz_convert(TIMEZONE).date().isoformat(),
        "last_submission": sub.max().tz_convert(TIMEZONE).date().isoformat(),
        "last_event": events["timestamp"].max().tz_convert(TIMEZONE).date().isoformat(),
        "submission_days": round(days, 2),
        "applications_per_day": round(n / days, 2),
        "annual_factor": round(365 / days, 4),
        "annualized_applications": round(n * 365 / days),
    }


def outcome_summary(cases: pd.DataFrame) -> list[dict[str, Any]]:
    n = len(cases)
    counts = cases["outcome"].value_counts()
    return [
        {
            "outcome": k,
            "label": labels.OUTCOME_LABELS[k],
            "count": int(counts.get(k, 0)),
            "share": round(float(counts.get(k, 0)) / n, 4),
        }
        for k in labels.OUTCOME_ORDER
    ]


def lead_times(cases: pd.DataFrame, max_days: int = 60) -> dict[str, Any]:
    """Délais jusqu'à l'issue : quantiles et histogrammes journaliers par issue."""
    closed = cases[cases["outcome"] != "open"]
    bins = np.arange(0, max_days + 1, 1)
    out: dict[str, Any] = {"bins_days": bins[:-1].tolist(), "by_outcome": {}}
    for oc in ("approved", "declined", "cancelled"):
        lt = closed.loc[closed["outcome"] == oc, "lead_time_d"]
        hist, _ = np.histogram(lt.clip(upper=max_days - 1e-9), bins=bins)
        out["by_outcome"][oc] = {
            "quantiles": _q(lt),
            "hist": hist.astype(int).tolist(),
            "within_1h_share": round(float((lt < 1 / 24).mean()), 4),
            "within_1d_share": round(float((lt < 1).mean()), 4),
        }
    out["all_closed"] = _q(closed["lead_time_d"])
    return out


def phase_decomposition(cases: pd.DataFrame, sessions: pd.DataFrame) -> dict[str, Any]:
    """Temps écoulé et temps de travail par phase (dossiers approuvés, et tous)."""
    ph = phase_of_sessions(sessions, cases)
    work = (
        sessions.assign(phase=ph.to_numpy())
        .groupby(["case_id", "phase"])["dur_s"]
        .sum()
        .unstack(fill_value=0.0)
        .reindex(columns=list(PHASES), fill_value=0.0)
    )
    result: dict[str, Any] = {}
    for scope, sub in (
        ("approved", cases[cases["outcome"] == "approved"]),
        ("closed", cases[cases["outcome"] != "open"]),
    ):
        rows = []
        w = work.reindex(sub.index).fillna(0.0)
        for phase in PHASES:
            elapsed = sub[f"phase_{phase}_d"]
            reached = elapsed.notna()
            rows.append(
                {
                    "phase": phase,
                    "label": PHASE_LABELS[phase],
                    "cases": int(reached.sum()),
                    "mean_elapsed_d": round(float(elapsed[reached].mean()), 3),
                    "median_elapsed_d": round(float(elapsed[reached].median()), 3),
                    "mean_work_h": round(float(w.loc[reached, phase].mean()) / 3600, 3),
                    "total_work_h": round(float(w.loc[reached, phase].sum()) / 3600, 1),
                }
            )
        result[scope] = rows
    appr = cases[cases["outcome"] == "approved"]
    result["approved_summary"] = {
        "cases": len(appr),
        "mean_lead_time_d": round(float(appr["lead_time_d"].mean()), 2),
        "median_lead_time_d": round(float(appr["lead_time_d"].median()), 2),
        "mean_work_h": round(float(appr["work_s"].mean()) / 3600, 3),
        "median_work_h": round(float(appr["work_s"].median()) / 3600, 3),
        "flow_efficiency_aggregate": round(
            float(appr["work_s"].sum() / (appr["lead_time_d"].sum() * 86400)), 5
        ),
        "flow_efficiency_median": round(float(appr["flow_efficiency"].median()), 5),
    }
    return result


def activity_times(sessions: pd.DataFrame, waits: pd.DataFrame) -> list[dict[str, Any]]:
    """Par tâche humaine : volume, travail, attente en file, délai entre tentatives."""
    rows = []
    for act in W_ACTIVITIES:
        s = sessions[sessions["activity"] == act]
        w = waits[waits["activity"] == act]
        gaps = s["gap_since_prev_s"].dropna()
        rows.append(
            {
                "activity": act,
                "label": labels.label(act),
                "sessions": len(s),
                "cases": int(s["case_id"].nunique()),
                "sessions_per_case": round(len(s) / max(s["case_id"].nunique(), 1), 2),
                "work_h": round(float(s["dur_s"].sum()) / 3600, 1),
                "median_session_min": round(float(s["dur_s"].median()) / 60, 2),
                "mean_session_min": round(float(s["dur_s"].mean()) / 60, 2),
                "median_wait_h": round(float(w["wait_s"].median()) / 3600, 2),
                "p90_wait_h": round(float(w["wait_s"].quantile(0.9)) / 3600, 2),
                "median_gap_h": round(float(gaps.median()) / 3600, 2) if len(gaps) else None,
            }
        )
    total = sum(r["work_h"] for r in rows)
    for r in rows:
        r["work_share"] = round(r["work_h"] / total, 4) if total else 0.0
    return rows


def flow_efficiency(cases: pd.DataFrame) -> dict[str, Any]:
    closed = cases[cases["outcome"] != "open"]
    out: dict[str, Any] = {}
    for oc in ("approved", "declined", "cancelled"):
        sub = closed[(closed["outcome"] == oc) & (closed["lead_time_d"] > 1 / 24)]
        out[oc] = {
            "median": round(float(sub["flow_efficiency"].median()), 5),
            "aggregate": round(float(sub["work_s"].sum() / (sub["lead_time_d"].sum() * 86400)), 5),
            "n": len(sub),
        }
    return out


def bottlenecks(dfg_edges: list[dict[str, Any]], top: int = 10) -> list[dict[str, Any]]:
    """Transitions où s'accumule le temps (fréquence × durée moyenne)."""
    rows = [e for e in dfg_edges if "total_h" in e]
    rows.sort(key=lambda e: -e["total_h"])
    total = sum(e["total_h"] for e in rows)
    return [
        {
            "source": e["source"],
            "target": e["target"],
            "source_label": labels.label(e["source"]),
            "target_label": labels.label(e["target"]),
            "count": e["count"],
            "median_h": e["median_h"],
            "mean_h": e["mean_h"],
            "total_h": e["total_h"],
            "share_of_time": round(e["total_h"] / total, 4) if total else 0.0,
        }
        for e in rows[:top]
    ]


def weekly_workload(sessions: pd.DataFrame) -> dict[str, Any]:
    """Heures de travail par semaine et par tâche (heure locale)."""
    local = sessions["end"].dt.tz_convert(TIMEZONE)
    week = local.dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time
    df = sessions.assign(week=week)
    pivot = (
        df.groupby(["week", "activity"])["dur_s"].sum().unstack(fill_value=0.0) / 3600
    ).reindex(columns=list(W_ACTIVITIES), fill_value=0.0)
    return {
        "weeks": [d.date().isoformat() for d in pivot.index],
        "series": {act: [round(float(x), 1) for x in pivot[act]] for act in W_ACTIVITIES},
    }


def work_heatmap(sessions: pd.DataFrame) -> dict[str, Any]:
    """Répartition des sessions de travail par jour de semaine et heure (locale)."""
    local = sessions["start"].fillna(sessions["end"]).dt.tz_convert(TIMEZONE)
    grid = pd.crosstab(local.dt.dayofweek, local.dt.hour).reindex(
        index=range(7), columns=range(24), fill_value=0
    )
    return {
        "days": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
        "hours": list(range(24)),
        "values": grid.to_numpy().astype(int).tolist(),
    }


def resource_workload(sessions: pd.DataFrame, annual_factor: float) -> dict[str, Any]:
    """Charge par ressource (identifiants pseudonymisés, présentés en agrégé)."""
    s = sessions.dropna(subset=["resource"])
    per = s.groupby("resource").agg(
        hours=("dur_s", "sum"), sessions=("dur_s", "size"), cases=("case_id", "nunique")
    )
    per["hours"] = per["hours"] / 3600
    per = per.sort_values("hours", ascending=False)
    hours = per["hours"].to_numpy()
    cum = np.cumsum(hours) / hours.sum()
    n = len(hours)
    # Indice de Gini de la répartition des heures.
    sorted_h = np.sort(hours)
    gini = float((2 * np.arange(1, n + 1) - n - 1).dot(sorted_h) / (n * sorted_h.sum()))
    main_act = (
        s.groupby(["resource", "activity"])["dur_s"]
        .sum()
        .groupby(level=0)
        .apply(lambda x: x.droplevel(0).idxmax())
    )
    main_share = (
        s.groupby(["resource", "activity"])["dur_s"]
        .sum()
        .groupby(level=0)
        .apply(lambda x: x.max() / x.sum())
    )
    return {
        "resources_with_work": n,
        "share_hours_known_resource": round(float(s["dur_s"].sum() / sessions["dur_s"].sum()), 4),
        "top10_share": round(float(cum[min(9, n - 1)]), 4),
        "top20pct_share": round(float(cum[max(int(np.ceil(0.2 * n)) - 1, 0)]), 4),
        "gini": round(gini, 3),
        "median_hours": round(float(np.median(hours)), 1),
        "lorenz": [round(float(x), 4) for x in np.r_[0, cum]],
        "hours_sorted": [round(float(x), 1) for x in hours],
        "specialists_share": round(float((main_share >= 0.8).mean()), 3),
        "main_activity_counts": {
            str(k): int(v) for k, v in main_act.map(labels.label).value_counts().items()
        },
        "observed_hours": round(float(sessions["dur_s"].sum()) / 3600, 1),
        "annualized_hours": round(float(sessions["dur_s"].sum()) / 3600 * annual_factor, 0),
    }
