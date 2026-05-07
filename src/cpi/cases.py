"""Table des dossiers : une ligne par demande, avec issue, jalons, phases et travail.

Définitions (reprises dans la documentation) :

* **issue** : ``approved`` (A_APPROVED), ``declined`` (A_DECLINED), ``cancelled``
  (A_CANCELLED) ; ``open`` si aucune issue n'est enregistrée à la fin du journal ;
* **délai de traitement** : du dépôt (A_SUBMITTED) à l'issue ;
* **phases** : pré-contrôle (dépôt → pré-acceptation), complétion (→ 1re offre envoyée),
  retour client (→ 1re offre retournée signée), validation (→ issue) ;
* **étape d'arrêt** : dernière phase atteinte par le dossier ;
* **efficacité de flux** : temps de travail effectif / délai de traitement.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

OUTCOME_ACTIVITIES = {
    "A_APPROVED": "approved",
    "A_DECLINED": "declined",
    "A_CANCELLED": "cancelled",
}

PHASES = ("precheck", "completion", "customer", "validation")
PHASE_LABELS = {
    "precheck": "Pré-contrôle",
    "completion": "Complétion",
    "customer": "Retour client",
    "validation": "Validation",
}
#: Étape d'arrêt (la dernière phase atteinte).
STAGE_LABELS = {
    "precheck": "Au pré-contrôle",
    "completion": "En complétion (avant offre)",
    "customer": "Offre envoyée, non retournée",
    "validation": "Offre retournée, en validation",
}

W_ACTIVITIES = (
    "W_Afhandelen leads",
    "W_Completeren aanvraag",
    "W_Nabellen offertes",
    "W_Valideren aanvraag",
    "W_Nabellen incomplete dossiers",
    "W_Beoordelen fraude",
)
W_SHORT = {
    "W_Afhandelen leads": "leads",
    "W_Completeren aanvraag": "completion",
    "W_Nabellen offertes": "offer_calls",
    "W_Valideren aanvraag": "validation",
    "W_Nabellen incomplete dossiers": "incomplete_calls",
    "W_Beoordelen fraude": "fraud",
}


def _first(events: pd.DataFrame, activity: str) -> pd.Series:
    return events.loc[events["activity"] == activity].groupby("case_id")["timestamp"].min()


def _last(events: pd.DataFrame, activity: str) -> pd.Series:
    return events.loc[events["activity"] == activity].groupby("case_id")["timestamp"].max()


def _count(events: pd.DataFrame, activity: str) -> pd.Series:
    return events.loc[events["activity"] == activity].groupby("case_id").size()


def build_cases(events: pd.DataFrame, sessions: pd.DataFrame) -> pd.DataFrame:
    g = events.groupby("case_id", sort=True)
    cases = pd.DataFrame(
        {
            "amount_req": g["amount_req"].first(),
            "start": g["timestamp"].min(),
            "last_event": g["timestamp"].max(),
            "n_events": g.size(),
        }
    )
    idx = cases.index

    # Issue : première activité terminale rencontrée.
    term = events[events["activity"].isin(OUTCOME_ACTIVITIES)].sort_values("order")
    first_term = term.groupby("case_id").first()
    cases["outcome"] = first_term["activity"].map(OUTCOME_ACTIVITIES).reindex(idx).fillna("open")
    cases["outcome_ts"] = first_term["timestamp"].reindex(idx)

    cases["t_preaccepted"] = _first(events, "A_PREACCEPTED").reindex(idx)
    cases["t_first_offer"] = _first(events, "O_SENT").reindex(idx)
    cases["t_last_offer"] = _last(events, "O_SENT").reindex(idx)
    cases["t_sent_back"] = _first(events, "O_SENT_BACK").reindex(idx)
    cases["n_offers"] = _count(events, "O_CREATED").reindex(idx).fillna(0).astype(int)

    cases["lead_time_d"] = (cases["outcome_ts"] - cases["start"]).dt.total_seconds() / 86400

    # Étape d'arrêt = dernière phase atteinte.
    stage = np.select(
        [
            cases["t_sent_back"].notna(),
            cases["t_first_offer"].notna(),
            cases["t_preaccepted"].notna(),
        ],
        ["validation", "customer", "completion"],
        default="precheck",
    )
    cases["stage"] = stage

    # Présence de tâches et volumes de sessions par tâche.
    w_events = events[events["category"] == "W"]
    presence = pd.crosstab(w_events["case_id"], w_events["activity"]) > 0
    for act, short in W_SHORT.items():
        has = presence[act] if act in presence.columns else pd.Series(dtype=bool)
        cases[f"has_{short}"] = has.reindex(idx, fill_value=False).astype(bool)
    sess = sessions.groupby(["case_id", "activity"]).agg(n=("dur_s", "size"), s=("dur_s", "sum"))
    for act, short in W_SHORT.items():
        sub = sess.xs(act, level="activity") if act in sess.index.get_level_values(1) else None
        n = sub["n"] if sub is not None else pd.Series(dtype=float)
        s = sub["s"] if sub is not None else pd.Series(dtype=float)
        cases[f"n_{short}"] = n.reindex(idx).fillna(0).astype(int)
        cases[f"work_{short}_s"] = s.reindex(idx).fillna(0.0)
    cases["work_s"] = sessions.groupby("case_id")["dur_s"].sum().reindex(idx).fillna(0.0)
    closed = cases["outcome"] != "open"
    lead_s = cases["lead_time_d"] * 86400
    cases["flow_efficiency"] = (cases["work_s"] / lead_s).where(closed & (lead_s > 0))

    cases = add_phases(cases)
    cases.index.name = "case_id"
    return cases


def add_phases(cases: pd.DataFrame) -> pd.DataFrame:
    """Durée (jours) de chaque phase pour les dossiers qui l'ont traversée."""
    end = cases["outcome_ts"]
    bounds = {
        "precheck": (cases["start"], cases["t_preaccepted"].fillna(end)),
        "completion": (cases["t_preaccepted"], cases["t_first_offer"].fillna(end)),
        "customer": (cases["t_first_offer"], cases["t_sent_back"].fillna(end)),
        "validation": (cases["t_sent_back"], end),
    }
    for phase, (a, b) in bounds.items():
        cases[f"phase_{phase}_d"] = (b - a).dt.total_seconds() / 86400
    return cases


def phase_of_sessions(sessions: pd.DataFrame, cases: pd.DataFrame) -> pd.Series:
    """Phase à laquelle appartient chaque session (selon son horodatage de fin)."""
    c = cases.reindex(sessions["case_id"])
    t = sessions["end"].to_numpy()
    pre = c["t_preaccepted"].to_numpy()
    first_offer = c["t_first_offer"].to_numpy()
    sent_back = c["t_sent_back"].to_numpy()

    def before(x: np.ndarray) -> np.ndarray:
        return np.where(pd.isna(x), True, t < x)

    phase = np.select(
        [before(pre), before(first_offer), before(sent_back)],
        ["precheck", "completion", "customer"],
        default="validation",
    )
    return pd.Series(phase, index=sessions.index)
