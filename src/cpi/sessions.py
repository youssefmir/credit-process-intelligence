"""Sessions de travail et temps d'attente des tâches humaines (W_).

Le cycle de vie des tâches W_ permet de séparer :

* le **temps d'attente en file** : de la planification (SCHEDULE) au premier démarrage
  (START) de la tâche ;
* le **temps de travail** : la somme des sessions START → COMPLETE ;
* le **temps entre deux tentatives** : d'une fin de session (COMPLETE) au démarrage
  suivant de la même tâche (client injoignable, rappel programmé…).

Règles de nettoyage (voir ``docs/02-analyse-as-is.md``) :

* appariement START → COMPLETE dans l'ordre d'arrivée (FIFO) par dossier et activité ;
* COMPLETE sans START : session conservée, durée imputée (médiane de l'activité) ;
* START sans COMPLETE (dossier en cours à la fin du journal) : session ignorée ;
* session de plus de ``SESSION_MAX_SECONDS`` : considérée comme restée ouverte
  (oubli de clôture), durée imputée (médiane de l'activité).
"""

from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

from cpi.config import SESSION_MAX_SECONDS

STATUS_OK = "ok"
STATUS_MISSING_START = "start_manquant"
STATUS_OUTLIER = "session_non_cloturee"


def _work_events(events: pd.DataFrame) -> pd.DataFrame:
    w = events[events["category"] == "W"]
    return w.sort_values(["case_id", "activity", "order"], kind="mergesort")


def build_sessions(
    events: pd.DataFrame, max_seconds: float = SESSION_MAX_SECONDS
) -> tuple[pd.DataFrame, int]:
    """Construit les sessions de travail. Retourne (sessions, nb de START non clôturés)."""
    w = _work_events(events)
    w = w[w["lifecycle"].isin(["START", "COMPLETE"])]
    cases = w["case_id"].to_numpy()
    acts = w["activity"].to_numpy()
    lcs = w["lifecycle"].to_numpy()
    tss = w["timestamp"].to_numpy()
    res = w["resource"].astype(object).to_numpy()

    rows: list[tuple[object, ...]] = []
    unclosed = 0
    opened: deque[tuple[np.datetime64, object]] = deque()
    prev_key: tuple[object, object] | None = None
    for case, act, lc, ts, r in zip(cases, acts, lcs, tss, res, strict=True):
        key = (case, act)
        if key != prev_key:
            unclosed += len(opened)
            opened = deque()
            prev_key = key
        if lc == "START":
            opened.append((ts, r))
        elif opened:
            t0, r0 = opened.popleft()
            rows.append((case, act, t0, ts, r if r is not None else r0))
        else:
            rows.append((case, act, np.datetime64("NaT"), ts, r))
    unclosed += len(opened)

    s = pd.DataFrame(rows, columns=["case_id", "activity", "start", "end", "resource"])
    s["start"] = pd.to_datetime(s["start"], utc=True)
    s["end"] = pd.to_datetime(s["end"], utc=True)
    s["resource"] = s["resource"].astype("string")
    s["dur_raw_s"] = (s["end"] - s["start"]).dt.total_seconds()
    s["status"] = STATUS_OK
    s.loc[s["start"].isna(), "status"] = STATUS_MISSING_START
    s.loc[s["dur_raw_s"] > max_seconds, "status"] = STATUS_OUTLIER
    valid = s["status"] == STATUS_OK
    medians = s[valid].groupby("activity")["dur_raw_s"].median()
    s["dur_s"] = s["dur_raw_s"].where(valid, s["activity"].map(medians))
    # Temps écoulé depuis la fin de la session précédente (même dossier, même tâche).
    prev_end = s.groupby(["case_id", "activity"], sort=False)["end"].shift(1)
    ref = s["start"].fillna(s["end"])
    s["gap_since_prev_s"] = (ref - prev_end).dt.total_seconds()
    return s.reset_index(drop=True), unclosed


def build_waits(events: pd.DataFrame) -> pd.DataFrame:
    """Attente en file : chaque SCHEDULE est rapproché du premier START qui le suit."""
    w = _work_events(events)
    w = w[w["lifecycle"].isin(["SCHEDULE", "START"])]
    rows: list[tuple[object, ...]] = []
    for (case, act), g in w.groupby(["case_id", "activity"], sort=False):
        lcs = g["lifecycle"].to_numpy()
        tss = g["timestamp"].to_numpy()
        starts = tss[lcs == "START"]
        for ts in tss[lcs == "SCHEDULE"]:
            later = starts[starts >= ts]
            rows.append((case, act, ts, later[0] if len(later) else np.datetime64("NaT")))
    waits = pd.DataFrame(rows, columns=["case_id", "activity", "scheduled", "first_start"])
    waits["scheduled"] = pd.to_datetime(waits["scheduled"], utc=True)
    waits["first_start"] = pd.to_datetime(waits["first_start"], utc=True)
    waits["wait_s"] = (waits["first_start"] - waits["scheduled"]).dt.total_seconds()
    return waits


def session_cleaning_summary(sessions: pd.DataFrame) -> dict[str, float]:
    """Effet chiffré des règles de nettoyage (pour le rapport qualité)."""
    raw_known = sessions["dur_raw_s"].fillna(0)
    return {
        "sessions": len(sessions),
        "missing_start": int((sessions["status"] == STATUS_MISSING_START).sum()),
        "outliers": int((sessions["status"] == STATUS_OUTLIER).sum()),
        "outlier_share": float((sessions["status"] == STATUS_OUTLIER).mean()),
        "hours_raw": float(raw_known.sum() / 3600),
        "hours_in_outliers_raw": float(
            sessions.loc[sessions["status"] == STATUS_OUTLIER, "dur_raw_s"].sum() / 3600
        ),
        "hours_clean": float(sessions["dur_s"].sum() / 3600),
    }


def threshold_sensitivity(
    sessions: pd.DataFrame, thresholds_h: tuple[float, ...] = (0.5, 1, 2, 4, 8)
) -> list[dict[str, float]]:
    """Heures de travail totales selon le seuil de session non clôturée."""
    out = []
    known = sessions["dur_raw_s"].notna()
    for th in thresholds_h:
        lim = th * 3600
        valid = known & (sessions["dur_raw_s"] <= lim)
        med = sessions[valid].groupby("activity")["dur_raw_s"].median()
        dur = sessions["dur_raw_s"].where(valid, sessions["activity"].map(med))
        out.append(
            {
                "threshold_h": th,
                "hours": float(dur.sum() / 3600),
                "share_imputed": float((~valid).mean()),
            }
        )
    return out
