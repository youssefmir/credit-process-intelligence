"""Coût des allers-retours : dossiers incomplets, offres multiples, relances d'offres."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

INCOMPLETE = "W_Nabellen incomplete dossiers"
VALIDATION = "W_Valideren aanvraag"
OFFER_CALLS = "W_Nabellen offertes"


def _h(seconds: float) -> float:
    return round(float(seconds) / 3600, 1)


def incomplete_loops(
    events: pd.DataFrame, sessions: pd.DataFrame, cases: pd.DataFrame
) -> pd.DataFrame:
    """Une ligne par dossier ayant connu la boucle « dossier incomplet ».

    * début de boucle : 1re planification d'une relance pour pièces manquantes ;
    * fin de boucle : 1er démarrage d'une validation après la dernière relance terminée
      (à défaut : l'issue du dossier) ;
    * travail de boucle : appels de relance + sessions de validation postérieures au début
      de boucle (re-validation).
    """
    sched = events[(events["activity"] == INCOMPLETE) & (events["lifecycle"] == "SCHEDULE")]
    loop_start = sched.groupby("case_id")["timestamp"].min()
    inc = sessions[sessions["activity"] == INCOMPLETE]
    last_call = inc.groupby("case_id")["end"].max()
    df = pd.DataFrame({"loop_start": loop_start}).join(last_call.rename("last_call"))
    val = sessions[sessions["activity"] == VALIDATION][["case_id", "start", "end", "dur_s"]]
    val = val.join(df, on="case_id", how="inner")
    # Re-validation : sessions de validation démarrées après le début de la boucle.
    reval = val[val["start"].fillna(val["end"]) > val["loop_start"]]
    after_last = val[val["start"].fillna(val["end"]) > val["last_call"]]
    df["loop_end"] = after_last.groupby("case_id")["start"].min()
    df["loop_end"] = df["loop_end"].fillna(cases["outcome_ts"].reindex(df.index))
    df["loop_end"] = df["loop_end"].fillna(df["last_call"])
    df["loop_delay_d"] = (df["loop_end"] - df["loop_start"]).dt.total_seconds() / 86400
    df["calls"] = inc.groupby("case_id").size().reindex(df.index).fillna(0).astype(int)
    df["call_work_s"] = inc.groupby("case_id")["dur_s"].sum().reindex(df.index).fillna(0.0)
    df["reval_work_s"] = reval.groupby("case_id")["dur_s"].sum().reindex(df.index).fillna(0.0)
    df["reval_sessions"] = reval.groupby("case_id").size().reindex(df.index).fillna(0)
    df["outcome"] = cases["outcome"].reindex(df.index)
    return df


def rework_summary(
    events: pd.DataFrame, sessions: pd.DataFrame, cases: pd.DataFrame, annual_factor: float
) -> dict[str, Any]:
    loops = incomplete_loops(events, sessions, cases)
    reached_validation = cases["t_sent_back"].notna()
    appr = cases[cases["outcome"] == "approved"]
    appr_loop = appr.index.isin(loops.index)

    loop_work = loops["call_work_s"] + loops["reval_work_s"]
    incomplete: dict[str, Any] = {
        "cases": len(loops),
        "share_of_validated": round(len(loops) / int(reached_validation.sum()), 4),
        "share_of_approved": round(float(appr_loop.mean()), 4),
        "calls": int(loops["calls"].sum()),
        "median_calls_per_case": float(loops["calls"].median()),
        "call_hours": _h(loops["call_work_s"].sum()),
        "revalidation_hours": _h(loops["reval_work_s"].sum()),
        "loop_hours": _h(loop_work.sum()),
        "loop_hours_annual": round(float(loop_work.sum()) / 3600 * annual_factor),
        "median_loop_delay_d": round(float(loops["loop_delay_d"].median()), 2),
        "mean_loop_delay_d": round(float(loops["loop_delay_d"].mean()), 2),
        "median_lead_time_approved_with_d": round(
            float(appr.loc[appr_loop, "lead_time_d"].median()), 2
        ),
        "median_lead_time_approved_without_d": round(
            float(appr.loc[~appr_loop, "lead_time_d"].median()), 2
        ),
        "outcomes": {str(k): int(v) for k, v in loops["outcome"].value_counts().items()},
    }

    # Offres multiples : appels de relance postérieurs à l'envoi de la 2e offre.
    sent = events[events["activity"] == "O_SENT"].sort_values(["case_id", "order"])
    second = sent.groupby("case_id")["timestamp"].nth(1)
    second = pd.Series(second.to_numpy(), index=sent.loc[second.index, "case_id"])
    offer_calls = sessions[sessions["activity"] == OFFER_CALLS]
    oc = offer_calls.join(second.rename("second_sent"), on="case_id", how="inner")
    after_second = oc[oc["end"] > oc["second_sent"]]
    reached_offer = cases["t_first_offer"].notna()
    multi = cases[cases["n_offers"] >= 2]
    span = (multi["t_last_offer"] - multi["t_first_offer"]).dt.total_seconds() / 86400
    by_n = (
        cases[reached_offer & (cases["outcome"] != "open")]
        .assign(n=lambda d: d["n_offers"].clip(upper=4))
        .groupby("n")["outcome"]
        .value_counts(normalize=True)
        .unstack(fill_value=0)
    )
    multiple = {
        "cases": len(multi),
        "share_of_offered": round(len(multi) / int(reached_offer.sum()), 4),
        "extra_offers": int((multi["n_offers"] - 1).sum()),
        "median_span_d": round(float(span.median()), 2),
        "calls_after_second_offer": len(after_second),
        "hours_after_second_offer": _h(after_second["dur_s"].sum()),
        "hours_after_second_offer_annual": round(
            float(after_second["dur_s"].sum()) / 3600 * annual_factor
        ),
        "outcome_by_offers": {
            str(n): {str(k): round(float(v), 4) for k, v in row.items()}
            for n, row in by_n.iterrows()
        },
    }

    # Relances d'offres.
    per_case = offer_calls.groupby("case_id").agg(n=("dur_s", "size"), s=("dur_s", "sum"))
    per_case = per_case.join(cases["outcome"])
    returned = cases[cases["t_sent_back"].notna()]
    ret_d = (returned["t_sent_back"] - returned["t_first_offer"]).dt.total_seconds() / 86400
    hours_by_outcome = per_case.groupby("outcome")["s"].sum() / 3600
    follow_ups: dict[str, Any] = {
        "cases": len(per_case),
        "calls": int(per_case["n"].sum()),
        "hours": _h(per_case["s"].sum()),
        "hours_annual": round(float(per_case["s"].sum()) / 3600 * annual_factor),
        "median_calls_per_case": float(per_case["n"].median()),
        "mean_calls_by_outcome": {
            str(k): round(float(v), 2) for k, v in per_case.groupby("outcome")["n"].mean().items()
        },
        "hours_by_outcome": {str(k): round(float(v), 1) for k, v in hours_by_outcome.items()},
        "share_hours_on_cancelled": round(
            float(hours_by_outcome.get("cancelled", 0.0) / hours_by_outcome.sum()), 4
        ),
        "median_return_d": round(float(ret_d.median()), 2),
        "p90_return_d": round(float(ret_d.quantile(0.9)), 2),
    }

    # Les appels postérieurs à une 2e offre sont inclus dans les relances d'offres.
    total_h = float(incomplete["loop_hours"]) + float(follow_ups["hours"])
    return {
        "incomplete": incomplete,
        "multiple_offers": multiple,
        "offer_follow_ups": follow_ups,
        "total_rework_hours": round(total_h, 1),
        "total_rework_hours_annual": round(total_h * annual_factor),
        "loop_delay_hist": np.histogram(
            loops["loop_delay_d"].clip(upper=29.999), bins=np.arange(0, 31, 1)
        )[0]
        .astype(int)
        .tolist(),
    }
