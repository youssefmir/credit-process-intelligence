"""Le README et les documents publiés : chiffres justes, typographie et liens.

Le README est rédigé à la main. Ce test vérifie que chaque chiffre clé qu'il cite est la valeur
calculée par le pipeline, avec le même arrondi que le site et les documents : si les données ou
le calcul changent, le test échoue tant que le texte n'est pas mis à jour.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from cpi.report import fr_num, fr_pct
from cpi.typo import check_files

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "public" / "data"
README = ROOT / "README.md"


def plain(text: str) -> str:
    """Espaces insécables ramenées à des espaces ordinaires pour la comparaison."""
    return text.replace(" ", " ").replace(" ", " ")


def signed_k(x: float) -> str:
    """VAN en milliers d'euros avec son signe : +48, −4."""
    s = plain(fr_num(x / 1000))
    return s if s.startswith("−") else f"+{s}"


@pytest.fixture(scope="module")
def readme() -> str:
    return plain(README.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def exports() -> dict[str, Any]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in DATA.glob("*.json")}


def expected_phrases(e: dict[str, Any]) -> list[str]:
    s = e["summary"]
    appr = e["time"]["phases"]["approved_summary"]
    phase = {p["phase"]: p for p in e["time"]["phases"]["approved"]}
    edges = {(x["source"], x["target"]): x for x in e["process"]["maps"]["milestones"]["edges"]}
    work_min = round(appr["mean_work_h"] * 60)
    work = f"{work_min // 60} h {work_min % 60:02d}"
    sent_back_d = edges[("O_SENT", "O_SENT_BACK")]["median_h"] / 24
    sent_cancel_d = edges[("O_SENT", "O_CANCELLED")]["median_h"] / 24
    mc = e["business_case"]["opportunities"]["completeness"]["monte_carlo"]
    phrases = [
        f"{fr_pct(s['waiting_share_approved'], 1)} de son délai à attendre",
        f"rejeu animé des {fr_num(s['cases'])} demandes réelles",
        f"appliqué à {fr_num(s['cases'])} demandes réelles",
        f"{fr_pct(s['incomplete_share_of_validated'])} des dossiers validés repartent chercher",
        f"(VAN médiane {signed_k(s['business']['completeness']['npv_p50'])} k€ sur 3 ans)",
        f"vers son retour signé ({fr_num(sent_back_d, 1)} jours)",
        f"vers son annulation ({fr_num(sent_cancel_d, 1)} jours)",
        f"soit {fr_num(appr['mean_lead_time_d'] * 24)} carrés",
        f"n'en remplit que {fr_num(appr['mean_work_h'], 1)} ({work})",
        f"le client tient {fr_num(phase['customer']['mean_elapsed_d'], 1)} jours",
        f"la file de validation {fr_num(phase['validation']['mean_elapsed_d'], 1)}.",
        f"ne couvre que {fr_pct(s['model_recall_at_20'])} des abandons",
        f"5 variantes couvrent {fr_pct(s['top5_variant_coverage'])} des demandes",
        f"{fr_pct(s['first_time_right_share'])} des prêts approuvés suivent le chemin nominal",
        f"{fr_num(appr['mean_lead_time_d'], 1)} jours de délai moyen pour {work} de travail",
        f"efficacité de flux de {fr_pct(appr['flow_efficiency_aggregate'], 2)}",
        f"{fr_num(s['rework_hours_annual'])} heures de relances et de reprises par an",
        f"{fr_pct(s['cancel_rate_after_offer'])} des offres envoyées finissent annulées",
        f"dont {fr_pct(s['expiry_window_share'])} à l'expiration des 30 jours",
        f"ROC-AUC de {fr_num(s['model_roc_auc'], 2)} sur la période de test",
        f"puis {fr_num(mc['iterations'])} tirages de Monte Carlo",
        f"extrapolés (× {fr_num(e['business_case']['baseline']['annual_factor'], 2)})",
        f"{fr_num(e['meta']['counts']['cases'])} demandes et "
        f"{fr_num(e['meta']['counts']['events'])} événements",
    ]
    for key in ("completeness", "prioritization", "preanalysis"):
        b = s["business"][key]
        prob = b["prob_npv_positive"]
        share = "moins de 1 %" if prob < 0.005 else fr_pct(prob)
        phrases.append(
            f"| {signed_k(b['npv_p50'])} k€ ({signed_k(b['npv_p10'])} à "
            f"{signed_k(b['npv_p90'])} k€) | {share} des tirages |"
        )
    return [plain(p) for p in phrases]


def test_readme_key_figures_match_exports(readme: str, exports: dict[str, Any]) -> None:
    missing = [p for p in expected_phrases(exports) if p not in readme]
    assert not missing, "Chiffres du README à mettre à jour :\n" + "\n".join(missing)


def test_published_markdown_follows_french_typography() -> None:
    files = [README, *sorted((ROOT / "docs").glob("*.md"))]
    assert check_files(files, write=False) == []


def test_relative_links_are_not_broken() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_links.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
