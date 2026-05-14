"""Données du rejeu animé : chaque dossier réel devient un parcours de « stations ».

Le plan de réseau du site représente les étapes métier comme des stations ; un dossier
circule d'une station à l'autre aux instants réels où le journal enregistre l'entrée dans
l'étape. Les temps sont exprimés en minutes depuis le premier dépôt et encodés en écarts
successifs (fichier compact).

Stations : dépôt, pré-contrôle, complétion, offre envoyée (avec la boucle « nouvelle
offre »), offre retournée, validation (avec la boucle « pièces manquantes ») et trois
terminus : prêt activé, refusée, annulée.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

STATIONS = (
    ("depot", "Dépôt"),
    ("precheck", "Pré-contrôle"),
    ("completion", "Complétion"),
    ("offer", "Offre envoyée"),
    ("reoffer", "Nouvelle offre"),
    ("returned", "Offre retournée"),
    ("validation", "Validation"),
    ("missing", "Pièces manquantes"),
    ("activated", "Prêt activé"),
    ("declined", "Refusée"),
    ("cancelled", "Annulée"),
)
INDEX = {key: i for i, (key, _) in enumerate(STATIONS)}
TERMINAL = {"A_ACTIVATED": "activated", "A_DECLINED": "declined", "A_CANCELLED": "cancelled"}


def station_paths(events: pd.DataFrame) -> dict[str, list[tuple[str, pd.Timestamp]]]:
    """Séquence (station, instant d'entrée) de chaque dossier."""
    ev = events.sort_values(["case_id", "order"], kind="mergesort")
    keep = ev["activity"].isin(
        [
            "A_SUBMITTED",
            "A_PARTLYSUBMITTED",
            "A_PREACCEPTED",
            "O_SENT",
            "O_SENT_BACK",
            "A_ACTIVATED",
            "A_DECLINED",
            "A_CANCELLED",
            "W_Valideren aanvraag",
            "W_Nabellen incomplete dossiers",
            "O_SELECTED",
        ]
    )
    ev = ev[keep]
    paths: dict[str, list[tuple[str, pd.Timestamp]]] = {}
    for case_id, g in ev.groupby("case_id", sort=False):
        path: list[tuple[str, pd.Timestamp]] = []
        returned = False
        n_sent = 0
        in_loop = False
        done = False
        for act, lc, ts in zip(g["activity"], g["lifecycle"], g["timestamp"], strict=True):
            if done:
                break
            last = path[-1][0] if path else None
            if act == "A_SUBMITTED":
                path.append(("depot", ts))
            elif act == "A_PARTLYSUBMITTED" and last == "depot":
                path.append(("precheck", ts))
            elif act == "A_PREACCEPTED" and last == "precheck":
                path.append(("completion", ts))
            elif act == "O_SELECTED" and n_sent >= 1 and not returned and last == "offer":
                path.append(("reoffer", ts))
            elif act == "O_SENT" and not returned:
                n_sent += 1
                if last != "offer":
                    path.append(("offer", ts))
            elif act == "O_SENT_BACK" and not returned:
                returned = True
                path.append(("returned", ts))
            elif act == "W_Valideren aanvraag" and lc == "START" and returned:
                if last in ("returned", "missing"):
                    path.append(("validation", ts))
                    in_loop = False
            elif (
                act == "W_Nabellen incomplete dossiers"
                and lc == "SCHEDULE"
                and returned
                and not in_loop
                and last == "validation"
            ):
                path.append(("missing", ts))
                in_loop = True
            elif act in TERMINAL:
                path.append((TERMINAL[act], ts))
                done = True
        paths[str(case_id)] = path
    return paths


def export(events: pd.DataFrame, cases: pd.DataFrame) -> dict[str, Any]:
    paths = station_paths(events)
    t0 = events["timestamp"].min()
    encoded: list[list[int]] = []
    transitions: Counter[tuple[str, str]] = Counter()
    for case_id in cases.index:
        path = paths.get(str(case_id), [])
        flat: list[int] = []
        prev_min = 0
        for k, (station, ts) in enumerate(path):
            minute = int((ts - t0).total_seconds() // 60)
            flat += [INDEX[station], minute - prev_min if k else minute]
            prev_min = minute
            if k:
                transitions[(path[k - 1][0], station)] += 1
        encoded.append(flat)
    t_end = events["timestamp"].max()
    return {
        "t0": t0.isoformat(),
        "minutes": int((t_end - t0).total_seconds() // 60),
        "stations": [{"id": k, "label": v} for k, v in STATIONS],
        "transitions": [
            {"from": a, "to": b, "cases": n} for (a, b), n in transitions.most_common()
        ],
        "encoding": "Par dossier : [station, minutes depuis t0, station, écart en minutes, …]",
        "cases": encoded,
    }
