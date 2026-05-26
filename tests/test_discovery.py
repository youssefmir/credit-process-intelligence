"""Carte de processus, variantes et conformité ; concordance avec pm4py."""

from __future__ import annotations

import warnings

import pandas as pd

from cpi import discovery


def test_dfg_counts_on_mini_log(mini_log: pd.DataFrame) -> None:
    dfg = discovery.directly_follows(mini_log, "milestones").set_index(["source", "target"])
    assert dfg.loc[("A_SUBMITTED", "A_PARTLYSUBMITTED"), "count"] == 6
    assert dfg.loc[("A_PARTLYSUBMITTED", "A_PREACCEPTED"), "count"] == 5
    assert dfg.loc[("A_PARTLYSUBMITTED", "A_DECLINED"), "count"] == 1
    assert dfg.loc[("O_SENT", "O_SENT_BACK"), "count"] == 3


def test_dfg_matches_pm4py(mini_log: pd.DataFrame) -> None:
    import pm4py

    view = discovery.view(mini_log, "complete")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ref, _, _ = pm4py.discover_dfg(view, **discovery.PM4PY_KEYS)
    ours = discovery.directly_follows(mini_log, "complete")
    assert {(r.source, r.target): r.count for r in ours.itertuples()} == dict(ref)


def test_process_map_has_start_and_end(mini: dict) -> None:
    m = discovery.process_map(mini["events"], mini["sessions"], mini["waits"], "milestones")
    ids = {n["id"] for n in m["nodes"]}
    assert {discovery.START, discovery.END} <= ids
    starts = [e for e in m["edges"] if e["source"] == discovery.START]
    assert sum(e["count"] for e in starts) == 6


def test_variants_and_coverage(mini: dict) -> None:
    v = discovery.variants(mini["events"], mini["cases"], "milestones")
    top = v["variants"][0]
    assert top["count"] == 3  # C1, C4, C6 : chemin nominal des jalons
    assert top["activities"] == list(discovery.NOMINAL_PATH)
    assert v["variants"][-1]["cum_share"] == 1.0


def test_nominal_conformance(mini: dict) -> None:
    c = discovery.nominal_conformance(mini["events"], mini["cases"])
    assert c["approved_cases"] == 3
    assert c["perfect_share"] == 1.0
    assert abs(c["first_time_right_share"] - 2 / 3) < 1e-3  # C4 a une boucle
