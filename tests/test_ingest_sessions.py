"""Ordre canonique, appariement des sessions, nettoyage et temps d'attente."""

from __future__ import annotations

import pandas as pd
import pytest

from cpi.sessions import STATUS_MISSING_START, STATUS_OUTLIER, threshold_sensitivity


def test_simultaneous_milestones_follow_canonical_order(mini_log: pd.DataFrame) -> None:
    c1 = mini_log[mini_log["case_id"] == "C1"].sort_values("order")
    last4 = c1["activity"].tolist()[-4:]
    assert last4 == ["O_ACCEPTED", "A_APPROVED", "A_REGISTERED", "A_ACTIVATED"]


def test_sort_timestamp_is_monotonic_and_close_to_real(mini_log: pd.DataFrame) -> None:
    for _, g in mini_log.groupby("case_id"):
        g = g.sort_values("order")
        assert g["ts_order"].is_monotonic_increasing
        assert ((g["ts_order"] - g["timestamp"]).abs() <= pd.Timedelta(seconds=5)).all()


def test_work_events_keep_their_position(mini_log: pd.DataFrame) -> None:
    w = mini_log[mini_log["category"] == "W"].sort_values(["case_id", "order"])
    for _, g in w.groupby("case_id"):
        assert g["timestamp"].is_monotonic_increasing


def test_sessions_are_paired_fifo(mini: dict) -> None:
    s = mini["sessions"]
    c1 = s[s["case_id"] == "C1"].set_index("activity")
    assert c1.loc["W_Completeren aanvraag", "dur_s"] == pytest.approx(600)
    assert c1.loc["W_Nabellen offertes", "dur_s"] == pytest.approx(300)
    assert c1.loc["W_Valideren aanvraag", "dur_s"] == pytest.approx(1200)


def test_unclosed_start_is_ignored(mini: dict) -> None:
    assert mini["unclosed"] == 1  # C5, en cours
    assert (mini["sessions"]["case_id"] == "C5").sum() == 0


def test_outlier_and_missing_start_are_imputed_with_activity_median(mini: dict) -> None:
    s = mini["sessions"]
    c6 = s[(s["case_id"] == "C6") & (s["activity"] == "W_Completeren aanvraag")]
    assert set(c6["status"]) == {STATUS_OUTLIER, STATUS_MISSING_START}
    # Médiane des sessions valides de complétion : C1 (10 min) et C3 (4 min) → 7 min.
    assert c6["dur_s"].tolist() == pytest.approx([420, 420])
    assert c6.loc[c6["status"] == STATUS_OUTLIER, "dur_raw_s"].iloc[0] == pytest.approx(18_000)


def test_gap_between_attempts(mini: dict) -> None:
    s = mini["sessions"]
    c3 = s[(s["case_id"] == "C3") & (s["activity"] == "W_Nabellen offertes")]
    gap_h = c3["gap_since_prev_s"].dropna().iloc[0] / 3600
    assert gap_h == pytest.approx(7 * 24 - 2 / 60)


def test_queue_wait_from_schedule_to_first_start(mini: dict) -> None:
    w = mini["waits"]
    c1 = w[(w["case_id"] == "C1")].set_index("activity")
    assert c1.loc["W_Completeren aanvraag", "wait_s"] == pytest.approx((60 - 1.02) * 60)
    assert c1.loc["W_Valideren aanvraag", "wait_s"] == pytest.approx((24 * 60 - 1) * 60)


def test_threshold_sensitivity_is_monotonic(mini: dict) -> None:
    rows = threshold_sensitivity(mini["sessions"], (1, 2, 8))
    hours = [r["hours"] for r in rows]
    assert hours == sorted(hours)
