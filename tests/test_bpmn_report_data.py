"""Modèles BPMN, documents générés, acquisition des données et fiche de pré-analyse."""

from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cpi import assistant, bpmn, data, report

NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
}
SUMMARY = {
    "declined_share": 0.58,
    "cancel_rate_after_offer": 0.35,
    "expiry_window_share": 0.36,
    "incomplete_share_of_validated": 0.51,
    "first_time_right_share": 0.35,
    "model_roc_auc": 0.56,
}


@pytest.mark.parametrize("builder", [bpmn.as_is, bpmn.to_be])
def test_bpmn_is_valid_and_fully_drawn(builder) -> None:
    root = ET.fromstring(bpmn.to_xml(builder(SUMMARY)))
    proc = root.find("bpmn:process", NS)
    assert proc is not None
    ids = {el.get("id") for el in proc.iter() if el.get("id")}
    flows = proc.findall("bpmn:sequenceFlow", NS)
    for f in flows:
        assert f.get("sourceRef") in ids and f.get("targetRef") in ids
    drawn = {s.get("bpmnElement") for s in root.iter(f"{{{NS['bpmndi']}}}BPMNShape")}
    drawn |= {s.get("bpmnElement") for s in root.iter(f"{{{NS['bpmndi']}}}BPMNEdge")}
    nodes = [
        el for el in proc if el.tag.split("}")[1] not in ("laneSet", "sequenceFlow", "association")
    ]
    assert all(n.get("id") in drawn for n in nodes)
    assert all(f.get("id") in drawn for f in flows)


def test_to_be_adds_three_ai_tasks() -> None:
    tobe = {n.id for n in bpmn.to_be(SUMMARY).nodes}
    asis = {n.id for n in bpmn.as_is(SUMMARY).nodes}
    assert tobe - asis == {"T_ai_check", "T_ai_score", "T_ai_brief"}


def test_french_number_formatting() -> None:
    assert report.fr_num(13087) == "13 087"
    assert report.fr_num(14.436, 1) == "14,4"
    assert report.fr_pct(0.1716) == "17 %"
    assert report.fr_eur(47918, unit="k") == "48 k€"


def test_templates_render_without_missing_values() -> None:
    root = Path(__file__).resolve().parents[1] / "site" / "public" / "data"
    if not (root / "summary.json").exists():
        pytest.skip("exports absents")
    env = report.environment()
    data_ = report.load_exports(root)
    for tpl in report.TEMPLATES.glob("*.md.j2"):
        text = env.get_template(tpl.name).render(**data_)
        assert "n.d." not in text


def _tiny_xes(path: Path, traces: int, events: int) -> None:
    body = "".join(
        "<trace>"
        + "".join('<event><string key="concept:name" value="A"/></event>' for _ in range(events))
        + "</trace>\n"
        for _ in range(traces)
    )
    content = f'<?xml version="1.0"?>\n<log>\n{body}</log>\n'.encode()
    path.write_bytes(gzip.compress(content))


def test_count_xes_and_contract(tmp_path: Path) -> None:
    p = tmp_path / "mini.xes.gz"
    _tiny_xes(p, traces=3, events=2)
    assert data.count_xes(p) == data.LogCounts(cases=3, events=6)
    with pytest.raises(data.DataError):
        data.verify_counts(p, data.BPIC2012)


def test_preanalysis_brief_is_factual(mini: dict) -> None:
    brief = assistant.build_brief("C4", mini["events"], mini["sessions"], mini["cases"])
    assert brief["incomplete_calls"] == 2
    assert any("Pièces manquantes" in a for a in brief["alerts"])
    md = assistant.to_markdown(brief)
    assert "aucune appréciation de solvabilité" in md


def test_llm_is_optional_and_mockable(mini: dict) -> None:
    assert assistant.client_from_env({}) is None

    class Fake:
        def complete(self, system: str, user: str) -> str:
            assert "solvabilité" in system
            return "note"

    brief = assistant.build_brief("C1", mini["events"], mini["sessions"], mini["cases"])
    assert assistant.draft_note(brief, Fake()) == "note"
