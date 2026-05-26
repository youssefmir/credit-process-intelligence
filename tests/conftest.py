"""Mini-journal synthétique : cas maîtrisés pour tester les KPI à la main.

Dossiers :

* ``C1`` approuvé, chemin nominal ; les quatre jalons finaux sont enregistrés au même
  instant dans un ordre désordonné (test de l'ordre canonique) ;
* ``C2`` refusé au pré-contrôle ;
* ``C3`` offre envoyée puis annulé 30 jours plus tard (2 relances d'offre) ;
* ``C4`` approuvé après une boucle « dossier incomplet » (2 appels puis re-validation) ;
* ``C5`` en cours à la fin du journal ;
* ``C6`` approuvé, avec une session restée ouverte (> 2 h) et une fin sans démarrage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cpi.ingest import canonical_order
from cpi.labels import category

T0 = pd.Timestamp("2011-10-03 08:00", tz="UTC")
ROOT = Path(__file__).resolve().parents[1]
SITE_DATA = ROOT / "site" / "public" / "data"


def ev(
    case: str,
    act: str,
    minutes: float,
    lc: str = "COMPLETE",
    res: str | None = "100",
    amount: float = 10_000.0,
) -> dict[str, object]:
    return {
        "case_id": case,
        "activity": act,
        "lifecycle": lc,
        "timestamp": T0 + pd.Timedelta(minutes=minutes),
        "resource": res,
        "amount_req": amount,
    }


def _session(case: str, act: str, start: float, minutes: float) -> list[dict[str, object]]:
    return [ev(case, act, start, "START"), ev(case, act, start + minutes, "COMPLETE")]


def build_mini_log() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    day = 24 * 60
    # C1 : nominal, approuvé à J+10.
    rows += [
        ev("C1", "A_SUBMITTED", 0, res="112"),
        ev("C1", "A_PARTLYSUBMITTED", 0.01, res="112"),
        ev("C1", "A_PREACCEPTED", 1, res="112"),
        ev("C1", "W_Completeren aanvraag", 1.02, "SCHEDULE", res="112"),
    ]
    rows += _session("C1", "W_Completeren aanvraag", 60, 10)
    rows += [
        ev("C1", "A_ACCEPTED", 71),
        ev("C1", "O_SELECTED", 72),
        ev("C1", "A_FINALIZED", 72),
        ev("C1", "O_CREATED", 73),
        ev("C1", "O_SENT", 73.01),
        ev("C1", "W_Nabellen offertes", 73.02, "SCHEDULE"),
    ]
    rows += _session("C1", "W_Nabellen offertes", 2 * day, 5)
    rows += [
        ev("C1", "O_SENT_BACK", 5 * day),
        ev("C1", "W_Valideren aanvraag", 5 * day + 1, "SCHEDULE"),
    ]
    rows += _session("C1", "W_Valideren aanvraag", 6 * day, 20)
    final = 10 * day
    # Ordre d'écriture désordonné, au même instant.
    rows += [
        ev("C1", "A_ACTIVATED", final),
        ev("C1", "A_REGISTERED", final),
        ev("C1", "O_ACCEPTED", final),
        ev("C1", "A_APPROVED", final),
    ]

    # C2 : refusé au pré-contrôle.
    rows += [
        ev("C2", "A_SUBMITTED", 30, res="112", amount=2_000),
        ev("C2", "A_PARTLYSUBMITTED", 30.01, res="112", amount=2_000),
        ev("C2", "A_DECLINED", 31, res="112", amount=2_000),
    ]

    # C3 : offre envoyée puis annulée à J+31.
    rows += [
        ev("C3", "A_SUBMITTED", 60, res="112"),
        ev("C3", "A_PARTLYSUBMITTED", 60.01, res="112"),
        ev("C3", "A_PREACCEPTED", 61, res="112"),
        ev("C3", "W_Completeren aanvraag", 61.02, "SCHEDULE", res="112"),
    ]
    rows += _session("C3", "W_Completeren aanvraag", 120, 4)
    rows += [
        ev("C3", "A_ACCEPTED", 125),
        ev("C3", "O_SELECTED", 126),
        ev("C3", "A_FINALIZED", 126),
        ev("C3", "O_CREATED", 127),
        ev("C3", "O_SENT", 127.01),
        ev("C3", "W_Nabellen offertes", 127.02, "SCHEDULE"),
    ]
    rows += _session("C3", "W_Nabellen offertes", 3 * day, 2)
    rows += _session("C3", "W_Nabellen offertes", 10 * day, 3)
    rows += [ev("C3", "O_CANCELLED", 31 * day), ev("C3", "A_CANCELLED", 31 * day)]

    # C4 : boucle « dossier incomplet ».
    rows += [
        ev("C4", "A_SUBMITTED", 90, res="112", amount=20_000),
        ev("C4", "A_PARTLYSUBMITTED", 90.01, res="112", amount=20_000),
        ev("C4", "A_PREACCEPTED", 91, res="112", amount=20_000),
    ]
    rows += [
        ev("C4", "A_ACCEPTED", 150, amount=20_000),
        ev("C4", "O_SELECTED", 151, amount=20_000),
        ev("C4", "A_FINALIZED", 151, amount=20_000),
        ev("C4", "O_CREATED", 152, amount=20_000),
        ev("C4", "O_SENT", 152.01, amount=20_000),
        ev("C4", "O_SENT_BACK", 4 * day, amount=20_000),
        ev("C4", "W_Valideren aanvraag", 4 * day + 1, "SCHEDULE", amount=20_000),
    ]
    for r in _session("C4", "W_Valideren aanvraag", 5 * day, 15):
        r["amount_req"] = 20_000
        rows.append(r)
    loop_start = 5 * day + 16
    rows.append(ev("C4", "W_Nabellen incomplete dossiers", loop_start, "SCHEDULE", amount=20_000))
    for start in (loop_start + 60, loop_start + day):
        for r in _session("C4", "W_Nabellen incomplete dossiers", start, 3):
            r["amount_req"] = 20_000
            rows.append(r)
    reval = 7 * day
    for r in _session("C4", "W_Valideren aanvraag", reval, 10):
        r["amount_req"] = 20_000
        rows.append(r)
    rows += [
        ev("C4", "O_ACCEPTED", reval + 11, amount=20_000),
        ev("C4", "A_APPROVED", reval + 11, amount=20_000),
        ev("C4", "A_REGISTERED", reval + 11, amount=20_000),
        ev("C4", "A_ACTIVATED", reval + 11, amount=20_000),
    ]

    # C5 : en cours.
    rows += [
        ev("C5", "A_SUBMITTED", 200, res="112"),
        ev("C5", "A_PARTLYSUBMITTED", 200.01, res="112"),
        ev("C5", "A_PREACCEPTED", 201, res="112"),
        ev("C5", "W_Completeren aanvraag", 201.02, "SCHEDULE", res="112"),
        ev("C5", "W_Completeren aanvraag", 300, "START"),
    ]

    # C6 : session non clôturée (5 h) et fin sans démarrage.
    rows += [
        ev("C6", "A_SUBMITTED", 400, res="112"),
        ev("C6", "A_PARTLYSUBMITTED", 400.01, res="112"),
        ev("C6", "A_PREACCEPTED", 401, res="112"),
        ev("C6", "W_Completeren aanvraag", 401.02, "SCHEDULE", res="112"),
    ]
    rows += _session("C6", "W_Completeren aanvraag", 500, 300)
    rows.append(ev("C6", "W_Completeren aanvraag", 900, "COMPLETE"))
    rows += [
        ev("C6", "A_ACCEPTED", 901),
        ev("C6", "O_SELECTED", 902),
        ev("C6", "A_FINALIZED", 902),
        ev("C6", "O_CREATED", 903),
        ev("C6", "O_SENT", 903.01),
        ev("C6", "O_SENT_BACK", 3 * day),
    ]
    for r in _session("C6", "W_Valideren aanvraag", 4 * day, 30):
        rows.append(r)
    rows += [
        ev("C6", "O_ACCEPTED", 6 * day),
        ev("C6", "A_APPROVED", 6 * day),
        ev("C6", "A_REGISTERED", 6 * day),
        ev("C6", "A_ACTIVATED", 6 * day),
    ]

    df = pd.DataFrame(rows)
    df["resource"] = df["resource"].astype("string")
    df["category"] = df["activity"].map(category)
    df = df.sort_values(["case_id", "timestamp"], kind="mergesort").reset_index(drop=True)
    df["event_idx"] = range(len(df))
    return canonical_order(df)


@pytest.fixture(scope="session")
def mini_log() -> pd.DataFrame:
    return build_mini_log()


@pytest.fixture(scope="session")
def mini(mini_log: pd.DataFrame) -> dict[str, object]:
    from cpi.cases import build_cases
    from cpi.sessions import build_sessions, build_waits

    sessions, unclosed = build_sessions(mini_log)
    waits = build_waits(mini_log)
    cases = build_cases(mini_log, sessions)
    return {
        "events": mini_log,
        "sessions": sessions,
        "unclosed": unclosed,
        "waits": waits,
        "cases": cases,
    }


def load_export(name: str) -> dict[str, object]:
    path = SITE_DATA / f"{name}.json"
    if not path.exists():
        pytest.skip(f"export {name}.json absent (lancer `make pipeline`)")
    return dict(json.loads(path.read_text(encoding="utf-8")))
