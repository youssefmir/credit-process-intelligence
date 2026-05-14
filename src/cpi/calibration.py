"""Étalonnage facultatif à partir du BPI Challenge 2017 – Offer log (même institution, 2016).

Le journal 2012 ne contient pas les conditions financières des offres. Le journal des offres
2017 donne, pour 42 995 offres, le montant proposé, la mensualité et le nombre d'échéances :
on en déduit le taux annuel implicite (formule de l'annuité) et le total des intérêts bruts
rapporté au montant. Ces ordres de grandeur servent uniquement à justifier l'hypothèse de
marge nette du business case ; ils ne sont pas mélangés aux analyses du processus 2012.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cpi.config import RAW_LOG_2017


def implied_monthly_rate(amount: np.ndarray, payment: np.ndarray, terms: np.ndarray) -> np.ndarray:
    """Taux mensuel r tel que payment = amount · r / (1 - (1 + r)^-terms) (dichotomie)."""
    lo = np.full(amount.shape, 1e-9)
    hi = np.full(amount.shape, 0.1)
    for _ in range(100):
        mid = (lo + hi) / 2
        pay = amount * mid / (1 - (1 + mid) ** (-terms))
        too_high = pay > payment
        hi = np.where(too_high, mid, hi)
        lo = np.where(too_high, lo, mid)
    return (lo + hi) / 2


def load_offers(path: Path = RAW_LOG_2017) -> pd.DataFrame:
    import pm4py

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = pm4py.read_xes(str(path), show_progress_bar=False)
    return raw.groupby("case:concept:name").agg(
        amount=("case:OfferedAmount", "first"),
        payment=("case:MonthlyCost", "first"),
        terms=("case:NumberOfTerms", "first"),
        selected=("case:Selected", "first"),
        accepted=("case:Accepted", "first"),
    )


def summarize(offers: pd.DataFrame) -> dict[str, Any]:
    o = offers.astype({"amount": float, "payment": float, "terms": float})
    valid = (o["amount"] > 0) & (o["terms"] > 0) & (o["payment"] * o["terms"] > o["amount"])
    o = o[valid].copy()
    r = implied_monthly_rate(o["amount"].to_numpy(), o["payment"].to_numpy(), o["terms"].to_numpy())
    o["apr"] = (1 + r) ** 12 - 1
    o["interest_ratio"] = (o["payment"] * o["terms"] - o["amount"]) / o["amount"]
    sel = o[o["selected"].astype(str).str.lower() == "true"]

    def q(s: pd.Series) -> dict[str, float]:
        return {
            "p25": round(float(s.quantile(0.25)), 4),
            "p50": round(float(s.median()), 4),
            "p75": round(float(s.quantile(0.75)), 4),
        }

    return {
        "available": True,
        "offers": len(o),
        "selected_offers": len(sel),
        "apr": q(sel["apr"]),
        "terms_months": q(sel["terms"]),
        "amount_eur": q(sel["amount"]),
        "gross_interest_ratio": q(sel["interest_ratio"]),
        "period": "2016",
    }


def run(path: Path = RAW_LOG_2017) -> dict[str, Any]:
    if not path.exists():
        return {"available": False, "reason": "journal 2017 non téléchargé (facultatif)"}
    return summarize(load_offers(path))
