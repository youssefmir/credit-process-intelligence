"""Jeu de données de préfixes au point de décision (envoi de la 1re offre).

Chaque dossier ayant reçu une offre donne une ligne. Les variables n'utilisent que les
événements **antérieurs ou égaux** au point de décision (préfixe du dossier) : aucune
information postérieure n'est accessible au modèle. Aucun identifiant de collaborateur
n'est utilisé comme variable (pas d'évaluation individuelle des salariés).

Étiquette : 1 si le dossier finit annulé (abandon), 0 s'il finit approuvé ou refusé ;
les dossiers sans issue à la fin du journal sont exclus (issue inconnue).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from cpi.config import (
    DECISION_ACTIVITY,
    INNER_VALIDATION_SHARE,
    OBSERVATION_DAYS,
    TEST_START,
    TIMEZONE,
    TRAIN_END,
    TRAIN_START,
)

SYSTEM_RESOURCE = "112"

#: Variables du modèle, avec leur libellé métier.
FEATURES: dict[str, str] = {
    "amount_req": "Montant demandé (€)",
    "hours_to_offer": "Délai dépôt → 1re offre (h)",
    "hours_precheck": "Durée du pré-contrôle (h)",
    "hours_completion": "Durée de la complétion (h)",
    "n_events": "Nombre d'événements avant l'offre",
    "completion_calls": "Appels de complétion",
    "completion_work_min": "Travail de complétion (min)",
    "completion_wait_h": "Attente avant 1er appel de complétion (h)",
    "max_gap_completion_h": "Plus long intervalle entre deux appels (h)",
    "lead_calls": "Appels de traitement de lead",
    "fraud_check": "Contrôle fraude avant l'offre",
    "n_resources": "Collaborateurs intervenus",
    "submit_hour": "Heure de dépôt",
    "submit_weekend": "Dépôt le week-end",
    "offer_hour": "Heure d'envoi de l'offre",
    "offer_weekday": "Jour d'envoi de l'offre (0 = lundi)",
    "offer_same_day": "Offre envoyée le jour du dépôt",
}


@dataclass(frozen=True)
class Split:
    train: pd.DataFrame
    inner_train: pd.DataFrame
    inner_valid: pd.DataFrame
    test: pd.DataFrame
    excluded: dict[str, int]


def decision_events(events: pd.DataFrame) -> pd.DataFrame:
    """Premier événement « offre envoyée » de chaque dossier (timestamp et ordre)."""
    dec = events[events["activity"] == DECISION_ACTIVITY].sort_values(["case_id", "order"])
    first = dec.groupby("case_id").first()
    return first[["timestamp", "order"]].rename(columns={"timestamp": "t_dec", "order": "o_dec"})


def build_dataset(
    events: pd.DataFrame, sessions: pd.DataFrame, waits: pd.DataFrame, cases: pd.DataFrame
) -> pd.DataFrame:
    dec = decision_events(events)
    ev = events.join(dec, on="case_id", how="inner")
    prefix = ev[ev["order"] <= ev["o_dec"]]
    g = prefix.groupby("case_id")

    df = pd.DataFrame(index=dec.index)
    df["t_dec"] = dec["t_dec"]
    c = cases.reindex(df.index)
    df["amount_req"] = c["amount_req"]
    start = c["start"]
    df["hours_to_offer"] = (df["t_dec"] - start).dt.total_seconds() / 3600
    pre = c["t_preaccepted"]
    df["hours_precheck"] = ((pre - start).dt.total_seconds() / 3600).fillna(0.0)
    df["hours_completion"] = ((df["t_dec"] - pre).dt.total_seconds() / 3600).fillna(
        df["hours_to_offer"]
    )
    df["n_events"] = g.size()
    res = prefix["resource"].astype(object)
    human = prefix[(res.notna()) & (res != SYSTEM_RESOURCE)]
    df["n_resources"] = human.groupby("case_id")["resource"].nunique().reindex(df.index)

    s = sessions.join(dec, on="case_id", how="inner")
    s = s[s["end"] <= s["t_dec"]]
    comp = s[s["activity"] == "W_Completeren aanvraag"]
    df["completion_calls"] = comp.groupby("case_id").size().reindex(df.index)
    df["completion_work_min"] = comp.groupby("case_id")["dur_s"].sum().reindex(df.index) / 60
    df["max_gap_completion_h"] = (
        comp.groupby("case_id")["gap_since_prev_s"].max().reindex(df.index) / 3600
    )
    leads = s[s["activity"] == "W_Afhandelen leads"]
    df["lead_calls"] = leads.groupby("case_id").size().reindex(df.index)
    fraud = s[s["activity"] == "W_Beoordelen fraude"]
    df["fraud_check"] = df.index.isin(fraud["case_id"]).astype(int)

    w = waits.join(dec, on="case_id", how="inner")
    w = w[(w["activity"] == "W_Completeren aanvraag") & (w["scheduled"] <= w["t_dec"])]
    started = w["first_start"] <= w["t_dec"]
    wait_h = ((w["first_start"] - w["scheduled"]).dt.total_seconds() / 3600).where(started)
    df["completion_wait_h"] = wait_h.groupby(w["case_id"]).min().reindex(df.index)

    sub_local = start.dt.tz_convert(TIMEZONE)
    off_local = df["t_dec"].dt.tz_convert(TIMEZONE)
    df["submit_hour"] = sub_local.dt.hour
    df["submit_weekend"] = (sub_local.dt.dayofweek >= 5).astype(int)
    df["offer_hour"] = off_local.dt.hour
    df["offer_weekday"] = off_local.dt.dayofweek
    df["offer_same_day"] = (sub_local.dt.date == off_local.dt.date).astype(int)

    for col in ("completion_calls", "completion_work_min", "lead_calls", "n_resources"):
        df[col] = df[col].fillna(0)
    df["max_gap_completion_h"] = df["max_gap_completion_h"].fillna(0.0)
    df["completion_wait_h"] = df["completion_wait_h"].fillna(0.0)

    df["outcome"] = c["outcome"]
    df["outcome_ts"] = c["outcome_ts"]
    df["label"] = (df["outcome"] == "cancelled").astype(int)
    return df


def temporal_split(df: pd.DataFrame, log_end: pd.Timestamp) -> Split:
    """Découpage temporel strict, sans fuite.

    * apprentissage : offres envoyées entre ``TRAIN_START`` et ``TRAIN_END`` dont l'issue
      était connue au déploiement simulé (``TEST_START``) ;
    * zone tampon : offres de ``TRAIN_END`` à ``TEST_START`` (non utilisées) ;
    * test : offres envoyées à partir de ``TEST_START`` et au moins
      ``OBSERVATION_DAYS`` jours avant la fin du journal (issue observable).
    """
    t = df["t_dec"]
    closed = df["outcome"] != "open"
    test_end = log_end - pd.Timedelta(days=OBSERVATION_DAYS)
    in_train_window = (t >= TRAIN_START) & (t < TRAIN_END)
    known_at_deploy = closed & (df["outcome_ts"] < TEST_START)
    train = df[in_train_window & known_at_deploy].sort_values("t_dec")
    test_window = (t >= TEST_START) & (t <= test_end)
    test = df[test_window & closed].sort_values("t_dec")
    n_inner = int(np.floor(len(train) * (1 - INNER_VALIDATION_SHARE)))
    excluded = {
        "train_window_purged_unknown_at_deploy": int((in_train_window & ~known_at_deploy).sum()),
        "buffer_window": int(((t >= TRAIN_END) & (t < TEST_START)).sum()),
        "test_window_open": int((test_window & ~closed).sum()),
        "after_test_window": int((t > test_end).sum()),
    }
    return Split(
        train=train,
        inner_train=train.iloc[:n_inner],
        inner_valid=train.iloc[n_inner:],
        test=test,
        excluded=excluded,
    )


#: Variables supplémentaires disponibles quand on observe le dossier après l'offre.
FOLLOW_UP_FEATURES: dict[str, str] = {
    "offer_calls": "Appels de relance de l'offre",
    "offer_call_min": "Durée cumulée des relances (min)",
    "offer_call_max_min": "Plus long appel de relance (min)",
    "since_last_call_h": "Temps depuis le dernier appel (h)",
    "offers_sent": "Offres envoyées",
    "offers_cancelled": "Offres remplacées",
}


def observe_after_offer(
    base: pd.DataFrame,
    events: pd.DataFrame,
    sessions: pd.DataFrame,
    cases: pd.DataFrame,
    days: float,
) -> pd.DataFrame:
    """Jeu de données observé ``days`` jours après la 1re offre (dossiers encore en attente).

    Ne conserve que les dossiers sans issue ni retour d'offre à cet instant, et ajoute les
    informations de relance accumulées depuis l'offre (toujours antérieures à l'instant
    d'observation).
    """
    df = base.copy()
    df["t_obs"] = df["t_dec"] + pd.Timedelta(days=days)
    c = cases.reindex(df.index)
    waiting = (c["outcome_ts"].isna() | (c["outcome_ts"] > df["t_obs"])) & (
        c["t_sent_back"].isna() | (c["t_sent_back"] > df["t_obs"])
    )
    df = df[waiting].copy()
    calls = sessions[sessions["activity"] == "W_Nabellen offertes"].join(
        df[["t_obs"]], on="case_id", how="inner"
    )
    calls = calls[calls["end"] <= calls["t_obs"]]
    g = calls.groupby("case_id")
    df["offer_calls"] = g.size().reindex(df.index).fillna(0)
    df["offer_call_min"] = (g["dur_s"].sum() / 60).reindex(df.index).fillna(0.0)
    df["offer_call_max_min"] = (g["dur_s"].max() / 60).reindex(df.index).fillna(0.0)
    last = g["end"].max().reindex(df.index)
    df["since_last_call_h"] = ((df["t_obs"] - last).dt.total_seconds() / 3600).fillna(days * 24)
    for act, col in (("O_SENT", "offers_sent"), ("O_CANCELLED", "offers_cancelled")):
        ev = events[events["activity"] == act][["case_id", "timestamp"]].join(
            df[["t_obs"]], on="case_id", how="inner"
        )
        ev = ev[ev["timestamp"] <= ev["t_obs"]]
        df[col] = ev.groupby("case_id").size().reindex(df.index).fillna(0)
    df["t_dec"] = df["t_obs"]  # le découpage temporel porte sur l'instant d'observation
    return df
