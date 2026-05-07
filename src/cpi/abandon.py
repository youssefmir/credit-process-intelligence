"""Abandons (dossiers annulés) : à quelle étape, après combien de temps, pour quel montant."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from cpi.cases import STAGE_LABELS

AMOUNT_BINS = [0, 5_000, 10_000, 15_000, 25_000, 50_000, np.inf]
AMOUNT_LABELS = ["< 5 k€", "5–10 k€", "10–15 k€", "15–25 k€", "25–50 k€", "≥ 50 k€"]
DELAY_BINS = [0, 1, 3, 7, 14, np.inf]
DELAY_LABELS = ["< 1 j", "1–3 j", "3–7 j", "7–14 j", "≥ 14 j"]


def _rate_table(df: pd.DataFrame, col: str, order: list[str]) -> list[dict[str, Any]]:
    rows = []
    for band in order:
        sub = df[df[col] == band]
        rows.append(
            {
                "band": band,
                "cases": len(sub),
                "cancelled": int((sub["outcome"] == "cancelled").sum()),
                "cancel_rate": round(float((sub["outcome"] == "cancelled").mean()), 4)
                if len(sub)
                else None,
                "approval_rate": round(float((sub["outcome"] == "approved").mean()), 4)
                if len(sub)
                else None,
            }
        )
    return rows


def abandon_summary(cases: pd.DataFrame) -> dict[str, Any]:
    closed = cases[cases["outcome"] != "open"].copy()
    cancelled = closed[closed["outcome"] == "cancelled"]
    offered = closed[closed["t_first_offer"].notna()].copy()

    stage_counts = cancelled["stage"].value_counts()
    by_stage = [
        {
            "stage": k,
            "label": v,
            "cancelled": int(stage_counts.get(k, 0)),
            "share": round(float(stage_counts.get(k, 0)) / len(cancelled), 4),
            "median_days_from_submission": round(
                float(cancelled.loc[cancelled["stage"] == k, "lead_time_d"].median()), 2
            )
            if stage_counts.get(k, 0)
            else None,
        }
        for k, v in STAGE_LABELS.items()
    ]

    after_offer = cancelled[cancelled["t_last_offer"].notna()]
    since_last = (
        after_offer["outcome_ts"] - after_offer["t_last_offer"]
    ).dt.total_seconds() / 86400
    expiry = since_last.between(29, 32)
    hist, _ = np.histogram(since_last.clip(upper=59.999), bins=np.arange(0, 61, 1))

    closed["amount_band"] = pd.cut(
        closed["amount_req"], AMOUNT_BINS, labels=AMOUNT_LABELS, right=False
    ).astype(str)
    offered["amount_band"] = pd.cut(
        offered["amount_req"], AMOUNT_BINS, labels=AMOUNT_LABELS, right=False
    ).astype(str)
    offered["delay_band"] = pd.cut(
        (offered["t_first_offer"] - offered["start"]).dt.total_seconds() / 86400,
        DELAY_BINS,
        labels=DELAY_LABELS,
        right=False,
    ).astype(str)

    amount_by_outcome = {
        oc: round(float(closed.loc[closed["outcome"] == oc, "amount_req"].median()), 0)
        for oc in ("approved", "declined", "cancelled")
    }
    return {
        "cancelled": len(cancelled),
        "share_of_closed": round(len(cancelled) / len(closed), 4),
        "offered_closed": len(offered),
        "cancel_rate_after_offer": round(float((offered["outcome"] == "cancelled").mean()), 4),
        "approval_rate_after_offer": round(float((offered["outcome"] == "approved").mean()), 4),
        "by_stage": by_stage,
        "after_offer": {
            "cases": len(after_offer),
            "median_days_since_last_offer": round(float(since_last.median()), 2),
            "expiry_window_cases": int(expiry.sum()),
            "expiry_window_share": round(float(expiry.mean()), 4),
            "hist_days_since_last_offer": hist.astype(int).tolist(),
        },
        "median_amount_by_outcome": amount_by_outcome,
        "by_amount_all": _rate_table(closed, "amount_band", AMOUNT_LABELS),
        "by_amount_offered": _rate_table(offered, "amount_band", AMOUNT_LABELS),
        "by_delay_to_offer": _rate_table(offered, "delay_band", DELAY_LABELS),
    }
