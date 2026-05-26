"""Absence de fuite, découpage temporel, reproductibilité et métriques du modèle."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cpi import features, model
from cpi.config import OBSERVATION_DAYS, TEST_START, TRAIN_END, TRAIN_START


def test_features_only_use_the_prefix(mini: dict) -> None:
    ev, s, w, c = mini["events"], mini["sessions"], mini["waits"], mini["cases"]
    full = features.build_dataset(ev, s, w, c)
    dec = features.decision_events(ev)
    truncated = ev.join(dec, on="case_id", how="left")
    truncated = truncated[truncated["o_dec"].isna() | (truncated["order"] <= truncated["o_dec"])]
    truncated = truncated.drop(columns=["t_dec", "o_dec"])
    from cpi.sessions import build_sessions, build_waits

    s2, _ = build_sessions(truncated)
    w2 = build_waits(truncated)
    cut = features.build_dataset(truncated, s2, w2, c)  # même issue, futur supprimé
    cols = list(features.FEATURES)
    pd.testing.assert_frame_equal(full[cols], cut[cols], check_dtype=False)


def test_prefix_features_values(mini: dict) -> None:
    ds = features.build_dataset(mini["events"], mini["sessions"], mini["waits"], mini["cases"])
    assert ds.loc["C1", "hours_to_offer"] == pytest.approx(73.01 / 60)
    assert ds.loc["C1", "completion_calls"] == 1
    assert ds.loc["C3", "label"] == 1
    assert ds.loc["C1", "label"] == 0
    assert "C2" not in ds.index  # jamais d'offre : hors population


def _synthetic(n: int = 900, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = pd.date_range("2011-10-01", "2012-01-31", periods=n, tz="Europe/Amsterdam")
    df = pd.DataFrame(
        {f: rng.gamma(2.0, 2.0, n) for f in features.FEATURES}, index=[f"S{i}" for i in range(n)]
    )
    logit = 0.6 * np.log1p(df["hours_to_offer"]) - 1.0
    df["label"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    df["t_dec"] = t
    df["outcome"] = np.where(df["label"] == 1, "cancelled", "approved")
    df["outcome_ts"] = df["t_dec"] + pd.to_timedelta(rng.integers(1, 40, n), unit="D")
    return df


def test_temporal_split_has_no_overlap_and_known_labels() -> None:
    df = _synthetic()
    log_end = pd.Timestamp("2012-03-14", tz="Europe/Amsterdam")
    sp = features.temporal_split(df, log_end)
    assert sp.train["t_dec"].max() < TRAIN_END
    assert sp.train["t_dec"].min() >= TRAIN_START
    assert (sp.train["outcome_ts"] < TEST_START).all()  # issue connue au déploiement
    assert sp.test["t_dec"].min() >= TEST_START
    assert sp.test["t_dec"].max() <= log_end - pd.Timedelta(days=OBSERVATION_DAYS)
    assert not set(sp.train.index) & set(sp.test.index)
    assert sp.inner_train["t_dec"].max() <= sp.inner_valid["t_dec"].min()


def test_model_training_is_reproducible() -> None:
    df = _synthetic()
    sp = features.temporal_split(df, pd.Timestamp("2012-03-14", tz="Europe/Amsterdam"))
    a = model.fit_models(sp)
    b = model.fit_models(sp)
    x = sp.test[model.FEATURE_NAMES]
    np.testing.assert_array_equal(a.gbm.predict_proba(x), b.gbm.predict_proba(x))
    np.testing.assert_array_equal(a.logreg.predict_proba(x), b.logreg.predict_proba(x))
    assert a.gbm_params == b.gbm_params


def test_gains_on_a_perfect_ranking() -> None:
    y = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    p = np.linspace(1, 0, 10)
    g = model.gains(y, p, shares=(0.2, 0.5))
    assert g["at_k"][0]["recall"] == 1.0
    assert g["at_k"][0]["lift"] == pytest.approx(5.0)


def test_psi_is_zero_for_identical_distributions() -> None:
    x = np.random.default_rng(1).normal(size=2000)
    assert model.psi(x, x) == pytest.approx(0.0, abs=1e-9)
    assert model.psi(x, x + 2) > 0.2


def test_acceptance_flags_weak_model() -> None:
    gbm = {
        "metrics": {"roc_auc": 0.55, "ece": 0.02},
        "gains": {"at_k": [{"share": 0.2, "lift": 1.1}]},
    }
    res = model.acceptance(gbm, score_psi=0.05)
    assert res["deployable"] is False
