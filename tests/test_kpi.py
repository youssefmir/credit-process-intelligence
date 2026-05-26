"""KPI calculés sur le mini-journal, vérifiés à la main."""

from __future__ import annotations

import pandas as pd
import pytest

from cpi import abandon, kpi, rework


def test_outcomes(mini: dict) -> None:
    c = mini["cases"]
    assert c.loc["C1", "outcome"] == "approved"
    assert c.loc["C2", "outcome"] == "declined"
    assert c.loc["C3", "outcome"] == "cancelled"
    assert c.loc["C5", "outcome"] == "open"
    summary = {o["outcome"]: o["count"] for o in kpi.outcome_summary(c)}
    assert summary == {"approved": 3, "declined": 1, "cancelled": 1, "open": 1}


def test_lead_time_and_stage(mini: dict) -> None:
    c = mini["cases"]
    assert c.loc["C1", "lead_time_d"] == pytest.approx(10.0)
    assert c.loc["C2", "lead_time_d"] == pytest.approx(1 / 1440)  # dépôt à 30 min, refus à 31 min
    assert pd.isna(c.loc["C5", "lead_time_d"])
    assert c.loc["C2", "stage"] == "precheck"
    assert c.loc["C3", "stage"] == "customer"
    assert c.loc["C5", "stage"] == "completion"
    assert c.loc["C1", "stage"] == "validation"


def test_flow_efficiency_is_work_over_lead_time(mini: dict) -> None:
    c = mini["cases"]
    assert c.loc["C1", "work_s"] == pytest.approx(35 * 60)
    assert c.loc["C1", "flow_efficiency"] == pytest.approx(35 * 60 / (10 * 86400))
    assert pd.isna(c.loc["C5", "flow_efficiency"])


def test_phases_partition_the_lead_time(mini: dict) -> None:
    c = mini["cases"].loc["C1"]
    total = sum(c[f"phase_{p}_d"] for p in ("precheck", "completion", "customer", "validation"))
    assert total == pytest.approx(c["lead_time_d"])
    assert c["phase_customer_d"] == pytest.approx(5 - 73.01 / 1440)


def test_phase_decomposition_work_sums_to_case_work(mini: dict) -> None:
    res = kpi.phase_decomposition(mini["cases"], mini["sessions"])
    approved = mini["cases"][mini["cases"]["outcome"] == "approved"]
    total_h = sum(r["total_work_h"] for r in res["approved"])
    assert total_h == pytest.approx(approved["work_s"].sum() / 3600, abs=0.2)


def test_observation_window_and_annual_factor(mini: dict) -> None:
    w = kpi.observation_window(mini["events"])
    assert w["annual_factor"] == pytest.approx(365 / w["submission_days"], rel=0.02)


def test_incomplete_loop_measures(mini: dict) -> None:
    loops = rework.incomplete_loops(mini["events"], mini["sessions"], mini["cases"])
    assert list(loops.index) == ["C4"]
    row = loops.loc["C4"]
    assert row["calls"] == 2
    assert row["call_work_s"] == pytest.approx(6 * 60)
    assert row["reval_work_s"] == pytest.approx(10 * 60)  # la 1re validation n'est pas comptée
    assert row["loop_delay_d"] == pytest.approx(2 - 16 / 1440)


def test_rework_summary_counts(mini: dict) -> None:
    r = rework.rework_summary(mini["events"], mini["sessions"], mini["cases"], annual_factor=2.0)
    assert r["incomplete"]["cases"] == 1
    assert r["offer_follow_ups"]["calls"] == 3
    assert r["total_rework_hours_annual"] == pytest.approx(2 * r["total_rework_hours"], abs=1)


def test_abandon_summary(mini: dict) -> None:
    a = abandon.abandon_summary(mini["cases"])
    assert a["cancelled"] == 1
    stages = {s["stage"]: s["cancelled"] for s in a["by_stage"]}
    assert stages["customer"] == 1
    assert a["after_offer"]["expiry_window_cases"] == 1  # annulé 31 jours après l'offre
