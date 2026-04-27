"""Ingestion : XES → table d'événements normalisée (Parquet).

Colonnes produites :

``case_id, activity, lifecycle, timestamp (UTC), resource, amount_req, category,
event_idx (ordre d'origine), order (ordre canonique dans le dossier), ts_order``.

``ts_order`` est un horodatage de tri : identique à ``timestamp`` sauf pour les jalons
A_/O_ enregistrés au même instant (écart ≤ 1 s), réordonnés selon l'ordre canonique
de :mod:`cpi.labels` (l'ordre d'écriture de ces jalons simultanés est arbitraire
dans le journal). Toutes les durées sont calculées sur ``timestamp`` (réel).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from cpi import labels
from cpi.config import EVENTS_FILE, RAW_LOG, TIE_WINDOW_SECONDS

COLUMNS = {
    "case:concept:name": "case_id",
    "concept:name": "activity",
    "lifecycle:transition": "lifecycle",
    "time:timestamp": "timestamp",
    "org:resource": "resource",
    "case:AMOUNT_REQ": "amount_req",
}


def read_xes(path: Path = RAW_LOG) -> pd.DataFrame:
    """Lit le XES avec pm4py et renomme les colonnes."""
    import warnings

    import pm4py

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avertissement d'option d'accélération facultative
        raw = pm4py.read_xes(str(path), show_progress_bar=False)
    return normalize(raw)


def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=COLUMNS)[list(COLUMNS.values())].copy()
    df["case_id"] = df["case_id"].astype(str)
    df["activity"] = df["activity"].astype(str)
    df["lifecycle"] = df["lifecycle"].astype(str).str.upper()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["resource"] = df["resource"].astype("string")
    df["amount_req"] = pd.to_numeric(df["amount_req"], errors="coerce").astype(float)
    df["category"] = df["activity"].map(labels.category)
    df["event_idx"] = np.arange(len(df), dtype=np.int64)
    return canonical_order(df)


def canonical_order(df: pd.DataFrame, window_s: float = TIE_WINDOW_SECONDS) -> pd.DataFrame:
    """Réordonne les jalons A_/O_ simultanés selon l'ordre canonique.

    Les événements W_ conservent exactement leur position ; seuls les créneaux occupés
    par des jalons A_/O_ d'un même groupe simultané sont réattribués.
    """
    df = df.sort_values(["case_id", "timestamp", "event_idx"], kind="mergesort")
    df = df.reset_index(drop=True)
    ts = df["timestamp"].to_numpy()
    case = df["case_id"].to_numpy()
    new_case = np.r_[True, case[1:] != case[:-1]]
    gap = np.r_[np.inf, np.diff(ts).astype("timedelta64[us]").astype(np.float64) / 1e6]
    group = np.cumsum(new_case | (gap > window_s))

    milestone = df["category"].isin(["A", "O"]).to_numpy()
    rank = df["activity"].map(labels.rank).to_numpy()
    order = np.arange(len(df))
    # Pour chaque groupe simultané comportant au moins 2 jalons, on trie les jalons.
    grp_ms = pd.Series(group[milestone])
    multi = grp_ms.value_counts()
    multi_groups = set(multi[multi > 1].index)
    if multi_groups:
        idx_ms = np.flatnonzero(milestone)
        sel = np.isin(group[idx_ms], list(multi_groups))
        idx = idx_ms[sel]
        sub = pd.DataFrame({"pos": idx, "grp": group[idx], "rank": rank[idx], "orig": idx})
        sorted_sub = sub.sort_values(["grp", "rank", "orig"], kind="mergesort")
        slots = sub.sort_values(["grp", "pos"], kind="mergesort")["pos"].to_numpy()
        order_vals = order.copy()
        order_vals[slots] = sorted_sub["orig"].to_numpy()
        df = df.iloc[order_vals].reset_index(drop=True)
        group = group[order_vals]

    df["order"] = df.groupby("case_id", sort=False).cumcount().astype(np.int64)
    # Horodatage de tri : début du groupe simultané + rang (µs) dans le groupe.
    groups = pd.Series(group)
    size = groups.map(groups.value_counts()).to_numpy()
    first_ts = df.groupby(group, sort=False)["timestamp"].transform("min")
    pos_in_group = groups.groupby(group, sort=False).cumcount().to_numpy()
    in_tie = size > 1
    ts_order = df["timestamp"].where(~in_tie, first_ts)
    df["ts_order"] = ts_order + pd.to_timedelta(np.where(in_tie, pos_in_group, 0), unit="us")
    return df


def ingest(path: Path = RAW_LOG, out: Path = EVENTS_FILE) -> pd.DataFrame:
    df = read_xes(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return df


def load_events(path: Path = EVENTS_FILE) -> pd.DataFrame:
    """Charge la table d'événements (lance l'ingestion si nécessaire)."""
    if not path.exists():
        return ingest(out=path)
    return pd.read_parquet(path)
