"""Découverte de processus : carte (DFG), variantes, conformité, modèle découvert.

Vues utilisées :

* ``complete`` : tous les événements terminés (COMPLETE) — jalons A_/O_ et tâches W_ ;
* ``milestones`` : jalons de la demande et de l'offre uniquement (A_/O_).

Le graphe des successions directes (DFG) est calculé avec pandas sur l'ordre canonique
(voir :mod:`cpi.ingest`), les durées sur les horodatages réels. Un test vérifie qu'il est
identique à celui de pm4py.
"""

from __future__ import annotations

import os
import warnings
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cpi import labels

os.environ.setdefault("PM4PY_SHOW_PROGRESS_BAR", "False")

PM4PY_KEYS = {"activity_key": "activity", "case_id_key": "case_id", "timestamp_key": "ts_order"}

#: Chemin nominal (« happy path ») d'une demande approuvée, en jalons.
NOMINAL_PATH: tuple[str, ...] = (
    "A_SUBMITTED",
    "A_PARTLYSUBMITTED",
    "A_PREACCEPTED",
    "A_ACCEPTED",
    "O_SELECTED",
    "A_FINALIZED",
    "O_CREATED",
    "O_SENT",
    "O_SENT_BACK",
    "O_ACCEPTED",
    "A_APPROVED",
    "A_REGISTERED",
    "A_ACTIVATED",
)

START, END = "__start__", "__end__"


def view(events: pd.DataFrame, name: str) -> pd.DataFrame:
    """Sous-ensemble ordonné d'événements correspondant à une vue."""
    mask = events["lifecycle"] == "COMPLETE"
    if name == "milestones":
        mask &= events["category"].isin(["A", "O"])
    elif name != "complete":
        raise ValueError(f"vue inconnue : {name}")
    return events.loc[mask].sort_values(["case_id", "order"], kind="mergesort")


def directly_follows(events: pd.DataFrame, view_name: str = "complete") -> pd.DataFrame:
    """Successions directes (source, cible) avec fréquence et durées (secondes)."""
    v = view(events, view_name)
    nxt = v.groupby("case_id", sort=False)
    v = v.assign(
        target=nxt["activity"].shift(-1),
        target_ts=nxt["timestamp"].shift(-1),
    ).dropna(subset=["target"])
    v = v.assign(dur_s=(v["target_ts"] - v["timestamp"]).dt.total_seconds())
    return (
        v.groupby(["activity", "target"])
        .agg(
            count=("dur_s", "size"),
            cases=("case_id", "nunique"),
            median_s=("dur_s", "median"),
            mean_s=("dur_s", "mean"),
            total_s=("dur_s", "sum"),
        )
        .reset_index()
        .rename(columns={"activity": "source"})
    )


def process_map(
    events: pd.DataFrame,
    sessions: pd.DataFrame,
    waits: pd.DataFrame,
    view_name: str = "complete",
) -> dict[str, Any]:
    """Carte de processus exportable : nœuds, arcs (dont début/fin), boucles."""
    v = view(events, view_name)
    dfg = directly_follows(events, view_name)
    loops = dfg[dfg["source"] == dfg["target"]].set_index("source")
    edges_df = dfg[dfg["source"] != dfg["target"]]

    firsts = v.groupby("case_id", sort=False)["activity"].first().value_counts()
    lasts = v.groupby("case_id", sort=False)["activity"].last().value_counts()
    work = sessions.groupby("activity")["dur_s"].median()
    wait = waits.groupby("activity")["wait_s"].median()

    nodes: list[dict[str, Any]] = []
    for act, grp in v.groupby("activity"):
        act = str(act)
        node: dict[str, Any] = {
            "id": act,
            "label": labels.label(act),
            "short": labels.short_label(act),
            "category": labels.category(act),
            "count": len(grp),
            "cases": int(grp["case_id"].nunique()),
            "repeats": int(loops.loc[act, "count"]) if act in loops.index else 0,
        }
        if act in work.index:
            node["median_work_min"] = round(float(work[act]) / 60, 2)
        if act in wait.index and not np.isnan(wait[act]):
            node["median_wait_h"] = round(float(wait[act]) / 3600, 2)
        nodes.append(node)
    n_cases = int(v["case_id"].nunique())
    nodes.append(
        {"id": START, "label": "Début", "category": "S", "count": n_cases, "cases": n_cases}
    )
    nodes.append({"id": END, "label": "Fin", "category": "S", "count": n_cases, "cases": n_cases})

    edges: list[dict[str, Any]] = [
        {
            "source": str(r.source),
            "target": str(r.target),
            "count": int(r.count),
            "cases": int(r.cases),
            "median_h": round(float(r.median_s) / 3600, 3),
            "mean_h": round(float(r.mean_s) / 3600, 3),
            "total_h": round(float(r.total_s) / 3600, 1),
        }
        for r in edges_df.itertuples(index=False)
    ]
    edges += [
        {"source": START, "target": str(a), "count": int(n), "cases": int(n)}
        for a, n in firsts.items()
    ]
    edges += [
        {"source": str(a), "target": END, "count": int(n), "cases": int(n)}
        for a, n in lasts.items()
    ]
    edges.sort(key=lambda e: -e["count"])
    return {
        "view": view_name,
        "cases": n_cases,
        "events": len(v),
        "nodes": nodes,
        "edges": edges,
    }


def _collapse(seq: tuple[str, ...]) -> tuple[str, ...]:
    out: list[str] = []
    for a in seq:
        if not out or out[-1] != a:
            out.append(a)
    return tuple(out)


def variants(
    events: pd.DataFrame, cases: pd.DataFrame, view_name: str = "milestones", top: int = 40
) -> dict[str, Any]:
    """Variantes (séquences distinctes) avec volume, issues et délai médian.

    Dans la vue complète, les répétitions consécutives d'une même tâche (appels
    successifs) sont regroupées pour que la variante décrive le parcours.
    """
    v = view(events, view_name)
    seqs = v.groupby("case_id", sort=False)["activity"].agg(tuple)
    if view_name == "complete":
        seqs = seqs.map(_collapse)
    df = pd.DataFrame({"seq": seqs}).join(cases[["outcome", "lead_time_d", "work_s"]])
    counts = Counter(df["seq"])
    total = len(df)
    out: list[dict[str, Any]] = []
    cum = 0
    for rank, (seq, n) in enumerate(counts.most_common(top), start=1):
        sub = df[df["seq"] == seq]
        cum += n
        oc = sub["outcome"].value_counts()
        lt = sub["lead_time_d"].dropna()
        out.append(
            {
                "rank": rank,
                "activities": list(seq),
                "count": int(n),
                "share": round(n / total, 5),
                "cum_share": round(cum / total, 5),
                "outcomes": {k: int(oc.get(k, 0)) for k in labels.OUTCOME_ORDER},
                "median_lead_time_d": round(float(lt.median()), 2) if len(lt) else None,
                "median_work_min": round(float(sub["work_s"].median()) / 60, 1),
            }
        )
    sizes = sorted(counts.values(), reverse=True)
    coverage = {
        str(k): round(sum(sizes[:k]) / total, 4) for k in (1, 5, 10, 20, 50) if k <= len(sizes)
    }
    return {
        "view": view_name,
        "n_variants": len(counts),
        "n_cases": total,
        "singletons": int(sum(1 for s in sizes if s == 1)),
        "coverage_top": coverage,
        "variants": out,
    }


def nominal_conformance(events: pd.DataFrame, cases: pd.DataFrame) -> dict[str, Any]:
    """Écarts des dossiers approuvés au chemin nominal (alignements pm4py)."""
    import pm4py

    tree = pm4py.parse_process_tree("->(" + ", ".join(f"'{a}'" for a in NOMINAL_PATH) + ")")
    net, im, fm = pm4py.convert_to_petri_net(tree)
    approved = cases.index[cases["outcome"] == "approved"]
    m = view(events, "milestones")
    m = m[m["case_id"].isin(approved)]
    case_order = m["case_id"].drop_duplicates().tolist()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        aligned = pm4py.conformance_diagnostics_alignments(m, net, im, fm, **PM4PY_KEYS)
    fitness = pd.Series([a["fitness"] for a in aligned], index=case_order)
    log_moves: Counter[str] = Counter()
    model_moves: Counter[str] = Counter()
    for a in aligned:
        for log_label, model_label in a["alignment"]:
            if model_label == ">>":
                log_moves[str(log_label)] += 1
            elif log_label == ">>" and model_label is not None:
                model_moves[str(model_label)] += 1
    perfect = fitness == 1.0
    c = cases.loc[approved]
    no_incomplete = ~c["has_incomplete_calls"].reindex(fitness.index)
    first_time_right = perfect & no_incomplete
    lead = c["lead_time_d"].reindex(fitness.index)
    return {
        "nominal_path": list(NOMINAL_PATH),
        "approved_cases": len(fitness),
        "perfect_share": round(float(perfect.mean()), 4),
        "mean_fitness": round(float(fitness.mean()), 4),
        "first_time_right_share": round(float(first_time_right.mean()), 4),
        "median_lead_time_nominal_d": round(float(lead[first_time_right].median()), 2),
        "median_lead_time_deviating_d": round(float(lead[~first_time_right].median()), 2),
        "extra_moves": [
            {"activity": k, "count": int(n), "label": labels.label(k)}
            for k, n in log_moves.most_common()
        ],
        "missing_moves": [
            {"activity": k, "count": int(n), "label": labels.label(k)}
            for k, n in model_moves.most_common()
        ],
    }


def inductive_model(events: pd.DataFrame, bpmn_out: Path | None = None) -> dict[str, Any]:
    """Modèle découvert (inductive miner, filtre de bruit 20 %) et sa qualité."""
    import pm4py

    v = view(events, "complete")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree = pm4py.discover_process_tree_inductive(v, noise_threshold=0.2, **PM4PY_KEYS)
        net, im, fm = pm4py.convert_to_petri_net(tree)
        fit = pm4py.fitness_token_based_replay(v, net, im, fm, **PM4PY_KEYS)
        precision = pm4py.precision_token_based_replay(v, net, im, fm, **PM4PY_KEYS)
        if bpmn_out is not None:
            bpmn_out.parent.mkdir(parents=True, exist_ok=True)
            pm4py.write_bpmn(pm4py.convert_to_bpmn(tree), str(bpmn_out), auto_layout=False)
    return {
        "algorithm": "Inductive Miner infrequent (pm4py), filtre de bruit 0,2",
        "process_tree": str(tree),
        "transitions": len([t for t in net.transitions if t.label]),
        "silent_transitions": len([t for t in net.transitions if not t.label]),
        "places": len(net.places),
        "fitness": round(float(fit["log_fitness"]), 4),
        "fitting_traces_share": round(float(fit["perc_fit_traces"]) / 100, 4),
        "precision": round(float(precision), 4),
    }
