"""Contrats des exports JSON consommés par le site (exécutés sur les fichiers committés)."""

from __future__ import annotations

from conftest import load_export
from cpi.replay import STATIONS


def _share(x: float) -> bool:
    return 0.0 <= x <= 1.0


def test_meta_matches_source_counts() -> None:
    meta = load_export("meta")
    assert meta["counts"]["cases"] == 13_087
    assert meta["counts"]["events"] == 262_200
    assert meta["dataset"]["doi"].startswith("https://doi.org/10.4121/")


def test_outcomes_partition_the_cases() -> None:
    proc = load_export("process")
    outcomes = proc["outcomes"]
    assert sum(o["count"] for o in outcomes) == 13_087
    assert abs(sum(o["share"] for o in outcomes) - 1) < 1e-3


def test_process_maps_are_consistent() -> None:
    proc = load_export("process")
    for m in proc["maps"].values():
        ids = {n["id"] for n in m["nodes"]}
        for e in m["edges"]:
            assert e["source"] in ids and e["target"] in ids
            assert e["count"] > 0


def test_every_activity_has_a_french_label() -> None:
    labels = {a["code"] for a in load_export("labels")["activities"]}
    nodes = {n["id"] for n in load_export("process")["maps"]["complete"]["nodes"]}
    assert nodes - {"__start__", "__end__"} <= labels


def test_variants_coverage_is_monotonic() -> None:
    v = load_export("variants")
    for view in ("milestones", "complete"):
        cum = [x["cum_share"] for x in v[view]["variants"]]
        assert cum == sorted(cum) and _share(cum[-1])


def test_lead_time_histograms_cover_every_case() -> None:
    t = load_export("time")
    for oc in t["lead_times"]["by_outcome"].values():
        assert sum(oc["hist"]) == oc["quantiles"]["n"]


def test_model_export_is_well_formed() -> None:
    m = load_export("model")
    for name in ("rule", "logreg", "gbm"):
        metrics = m["models"][name]["metrics"]
        assert _share(metrics["roc_auc"]) and _share(metrics["pr_auc"])
    assert isinstance(m["acceptance"]["deployable"], bool)
    assert "test_scores" not in m  # pas de scores individuels publiés


def test_business_case_quantiles_are_ordered() -> None:
    bc = load_export("business_case")
    assert set(bc["opportunities"]) == {"completeness", "prioritization", "preanalysis"}
    for opp in bc["opportunities"].values():
        q = opp["monte_carlo"]["npv"]
        assert q["p10"] <= q["p50"] <= q["p90"]
        assert len(opp["central"]["cumulative"]) == bc["hypotheses"]["simulation"]["horizon_months"]
    assert len(bc["reference_scenarios"]) >= 3


def test_replay_encoding() -> None:
    r = load_export("replay")
    assert len(r["cases"]) == 13_087
    n_st = len(STATIONS)
    for flat in r["cases"][:500]:
        assert len(flat) % 2 == 0
        assert all(0 <= s < n_st for s in flat[0::2])
        assert all(d >= 0 for d in flat[1::2])
