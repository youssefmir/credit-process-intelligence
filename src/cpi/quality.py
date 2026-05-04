"""Contrôles de qualité des données, chacun avec son statut, son impact et son traitement."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from cpi.config import DATASET, SESSION_MAX_SECONDS, TIMEZONE
from cpi.sessions import (
    STATUS_MISSING_START,
    STATUS_OUTLIER,
    session_cleaning_summary,
    threshold_sensitivity,
)


@dataclass
class Check:
    id: str
    label: str
    status: str  # "ok" | "attention" | "info"
    value: str
    detail: str
    treatment: str


def _fmt(n: float, digits: int = 0) -> str:
    s = f"{n:,.{digits}f}".replace(",", " ").replace(".", ",")
    return s.replace(" ", " ")


def _plural(n: int, word: str) -> str:
    return f"{_fmt(n)} {word}{'s' if n > 1 else ''}"


def _pct(x: float, digits: int = 1) -> str:
    return f"{_fmt(100 * x, digits)} %"


def run_checks(
    events: pd.DataFrame, sessions: pd.DataFrame, unclosed: int, cases: pd.DataFrame
) -> tuple[list[Check], dict[str, object]]:
    checks: list[Check] = []
    n_cases = events["case_id"].nunique()
    n_events = len(events)
    ok_counts = (n_cases, n_events) == (DATASET.expected_cases, DATASET.expected_events)
    checks.append(
        Check(
            "contract_counts",
            "Volumétrie conforme à la source",
            "ok" if ok_counts else "attention",
            f"{_fmt(n_cases)} dossiers · {_fmt(n_events)} événements",
            "Comptes attendus d'après la publication 4TU.ResearchData.",
            "Arrêt du pipeline en cas d'écart.",
        )
    )

    required = ["case_id", "activity", "lifecycle", "timestamp"]
    nulls = int(events[required].isna().sum().sum())
    checks.append(
        Check(
            "required_fields",
            "Champs obligatoires renseignés",
            "ok" if nulls == 0 else "attention",
            f"{_plural(nulls, 'valeur manquante')}" if nulls else "aucune valeur manquante",
            "Dossier, activité, cycle de vie, horodatage.",
            "Aucun.",
        )
    )

    local = events["timestamp"].dt.tz_convert(TIMEZONE)
    sub = local[events["activity"] == "A_SUBMITTED"]
    checks.append(
        Check(
            "period",
            "Période couverte",
            "info",
            f"{local.min():%d/%m/%Y} → {local.max():%d/%m/%Y}",
            f"Dépôts du {sub.min():%d/%m/%Y} au {sub.max():%d/%m/%Y} ; "
            f"événements jusqu'au {local.max():%d/%m/%Y}.",
            "Annualisation explicite des volumes (voir le business case).",
        )
    )

    dup = int(events.duplicated(["case_id", "activity", "lifecycle", "timestamp"]).sum())
    checks.append(
        Check(
            "duplicates",
            "Doublons exacts",
            "ok" if dup == 0 else "attention",
            _plural(dup, "doublon") if dup else "aucun doublon",
            "Même dossier, activité, cycle de vie et horodatage.",
            "Aucun." if dup == 0 else "Conservés et signalés.",
        )
    )

    missing_res = events["resource"].isna()
    checks.append(
        Check(
            "resource_missing",
            "Ressource non renseignée",
            "attention",
            f"{_fmt(missing_res.sum())} événements ({_pct(missing_res.mean())})",
            "Surtout des START/COMPLETE de tâches W_ ; l'événement reste daté.",
            "Analyses de charge sur les sessions dont la ressource est connue.",
        )
    )

    raw_seq = (
        events[events["category"].isin(["A", "O"])]
        .sort_values(["case_id", "event_idx"])
        .groupby("case_id")["activity"]
        .agg(tuple)
    )
    canon_seq = (
        events[events["category"].isin(["A", "O"])]
        .sort_values(["case_id", "order"])
        .groupby("case_id")["activity"]
        .agg(tuple)
    )
    moved = int((raw_seq != canon_seq.reindex(raw_seq.index)).sum())
    checks.append(
        Check(
            "simultaneous_milestones",
            "Jalons enregistrés au même instant",
            "attention",
            f"{_fmt(moved)} dossiers concernés",
            f"Ordre d'écriture arbitraire : {_fmt(raw_seq.nunique())} variantes de jalons brutes "
            f"contre {_fmt(canon_seq.nunique())} après remise en ordre canonique.",
            "Réordonnancement canonique des jalons A_/O_ distants de moins d'1 s ; "
            "durées calculées sur les horodatages réels.",
        )
    )

    n_missing_start = int((sessions["status"] == STATUS_MISSING_START).sum())
    checks.append(
        Check(
            "complete_without_start",
            "Fin de tâche sans démarrage",
            "attention",
            f"{_fmt(n_missing_start)} sessions",
            "COMPLETE sans START correspondant pour la même tâche du dossier.",
            "Session conservée, durée imputée à la médiane de l'activité.",
        )
    )
    checks.append(
        Check(
            "start_without_complete",
            "Démarrage sans fin de tâche",
            "info",
            f"{_fmt(unclosed)} sessions",
            "Dossiers en cours à la fin de l'extraction.",
            "Sessions ignorées dans le temps de travail.",
        )
    )

    clean = session_cleaning_summary(sessions)
    checks.append(
        Check(
            "unclosed_sessions",
            f"Sessions de plus de {SESSION_MAX_SECONDS // 3600} h",
            "attention",
            f"{_fmt(clean['outliers'])} sessions ({_pct(clean['outlier_share'], 2)})",
            f"Elles pèsent {_fmt(clean['hours_in_outliers_raw'])} h sur "
            f"{_fmt(clean['hours_raw'])} h brutes : sessions restées ouvertes, pas du travail.",
            f"Durée imputée à la médiane de l'activité : {_fmt(clean['hours_clean'])} h de "
            "travail retenues (estimation prudente).",
        )
    )

    never = events[(events["activity"] == "W_Wijzigen contractgegevens")]
    checks.append(
        Check(
            "never_executed",
            "Tâche planifiée jamais exécutée",
            "info",
            f"{_fmt(len(never))} planifications",
            "« Modification du contrat » : aucun START/COMPLETE.",
            "Exclue des analyses de travail.",
        )
    )

    amount = cases["amount_req"]
    checks.append(
        Check(
            "amount",
            "Montant demandé",
            "info",
            f"médiane {_fmt(amount.median())} € · max {_fmt(amount.max())} €",
            f"{_plural(int((amount == 0).sum()), 'demande')} à 0 € ; "
            f"plafond de saisie probable à {_fmt(amount.max())} €.",
            "Conservé tel quel ; analyses par tranches de montant.",
        )
    )

    n_open = int((cases["outcome"] == "open").sum())
    checks.append(
        Check(
            "open_cases",
            "Dossiers sans issue à la fin du journal",
            "info",
            f"{_fmt(n_open)} dossiers ({_pct(n_open / n_cases)})",
            "Dossiers récents encore en cours au 14 mars 2012.",
            "Exclus des délais et du modèle (issue inconnue).",
        )
    )

    multi = events[events["activity"].isin(["A_APPROVED", "A_DECLINED", "A_CANCELLED"])]
    n_multi = int(
        multi.drop_duplicates(["case_id", "activity"]).groupby("case_id").size().gt(1).sum()
    )
    checks.append(
        Check(
            "single_outcome",
            "Une seule issue par dossier",
            "ok" if n_multi == 0 else "attention",
            _plural(n_multi, "dossier") + " en conflit" if n_multi else "aucun conflit",
            "Approuvée, refusée ou annulée.",
            "Aucun." if n_multi == 0 else "Première issue retenue.",
        )
    )

    first_act = events.sort_values(["case_id", "order"]).groupby("case_id")["activity"].first()
    n_bad_start = int((first_act != "A_SUBMITTED").sum())
    checks.append(
        Check(
            "case_start",
            "Chaque dossier commence par le dépôt",
            "ok" if n_bad_start == 0 else "attention",
            _plural(n_bad_start, "exception") if n_bad_start else "aucune exception",
            "Premier événement = A_SUBMITTED.",
            "Aucun.",
        )
    )

    extra: dict[str, object] = {
        "session_cleaning": clean,
        "threshold_sensitivity": threshold_sensitivity(sessions),
        "missing_resource_by_lifecycle": {
            k: int(v) for k, v in events[missing_res].groupby("lifecycle").size().items()
        },
        "outliers_by_activity": {
            k: int(v)
            for k, v in sessions[sessions["status"] == STATUS_OUTLIER]
            .groupby("activity")
            .size()
            .items()
        },
    }
    return checks, extra


def as_records(checks: list[Check]) -> list[dict[str, str]]:
    return [asdict(c) for c in checks]
