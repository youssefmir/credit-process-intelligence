"""Acquisition reproductible du journal BPI Challenge 2012.

Ordre de tentative :

1. copie locale explicitement fournie (variable ``CPI_LOCAL_SOURCE``), utile hors ligne ;
2. téléchargement officiel depuis 4TU.ResearchData (API publique du dépôt) ;
3. repli sur la copie publique incluse dans le dépôt GitHub ``pm4py/pm4py-core``
   (clone superficiel et partiel : seul le fichier utile est récupéré).

Le fichier obtenu est vérifié (empreinte, puis nombre de dossiers et d'événements)
et sa provenance est consignée dans ``data/raw/PROVENANCE.json``.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cpi.config import DATASET, PROVENANCE_FILE, RAW_DIR, RAW_LOG

OFFICIAL_API = "https://data.4tu.nl/v2/articles/533f66a4-8911-4ac7-8612-1235d65d1f37/files"
OFFICIAL_FILE_NAME = "BPI_Challenge_2012.xes.gz"
#: Empreinte MD5 publiée par 4TU pour BPI_Challenge_2012.xes.gz.
OFFICIAL_MD5 = "74c7ba9aba85bfcb181a22c9d565e5b5"

PM4PY_REPO = "https://github.com/pm4py/pm4py-core.git"
PM4PY_PATH = "tests/input_data/bpic2012.xes.gz"
#: Empreinte SHA-256 de la copie pm4py-core (recompression gzip du même XES).
PM4PY_SHA256 = "fdc916898cd56f0fb65f0c6c2f69140e6345fe9fc8be2ef1dde0647107db050b"

TIMEOUT_S = 30


class DataError(RuntimeError):
    """Erreur d'acquisition ou de vérification des données."""


@dataclass(frozen=True)
class LogCounts:
    cases: int
    events: int


def file_hash(path: Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_xes(path: Path) -> LogCounts:
    """Compte dossiers (``<trace>``) et événements (``<event>``) par lecture en flux.

    Lecture ligne à ligne sans charger le XML en mémoire : rapide et indépendante
    du parseur utilisé ensuite pour l'ingestion.
    """
    trace_re = re.compile(rb"<trace[\s>]")
    event_re = re.compile(rb"<event[\s>]")
    cases = events = 0
    with path.open("rb") as probe:
        is_gzip = probe.read(2) == b"\x1f\x8b"
    opener = gzip.open if is_gzip else open
    with opener(path, "rb") as fh:
        for line in fh:
            cases += len(trace_re.findall(line))
            events += len(event_re.findall(line))
    return LogCounts(cases=cases, events=events)


def verify_counts(path: Path) -> LogCounts:
    counts = count_xes(path)
    if (counts.cases, counts.events) != (DATASET.expected_cases, DATASET.expected_events):
        raise DataError(
            f"Comptes inattendus pour {path.name} : {counts.cases} dossiers / "
            f"{counts.events} événements (attendu {DATASET.expected_cases} / "
            f"{DATASET.expected_events})."
        )
    return counts


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "credit-process-intelligence"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out)


def fetch_official(dest: Path) -> dict[str, Any]:
    """Téléchargement depuis 4TU.ResearchData, contrôlé par l'empreinte MD5 publiée."""
    req = urllib.request.Request(OFFICIAL_API, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        files = json.load(resp)
    match = next((f for f in files if f.get("name") == OFFICIAL_FILE_NAME), None)
    if match is None or not match.get("download_url"):
        raise DataError("Fichier BPI_Challenge_2012.xes.gz introuvable dans l'API 4TU.")
    url = str(match["download_url"])
    _download(url, dest)
    md5 = file_hash(dest, "md5")
    if md5 != OFFICIAL_MD5:
        raise DataError(f"Empreinte MD5 inattendue ({md5}) pour le fichier 4TU.")
    return {"source": "4TU.ResearchData", "url": url, "md5": md5}


def fetch_pm4py(dest: Path) -> dict[str, Any]:
    """Repli : clone superficiel et partiel du dépôt public pm4py-core."""
    if shutil.which("git") is None:
        raise DataError("git est requis pour le repli pm4py-core.")
    with tempfile.TemporaryDirectory(prefix="cpi-pm4py-") as tmp:
        repo = Path(tmp) / "pm4py-core"
        run = {"check": True, "capture_output": True, "text": True, "timeout": 600}
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                PM4PY_REPO,
                str(repo),
            ],
            **run,  # type: ignore[call-overload]
        )
        subprocess.run(
            ["git", "-C", str(repo), "sparse-checkout", "set", "--no-cone", PM4PY_PATH],
            **run,  # type: ignore[call-overload]
        )
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            **run,  # type: ignore[call-overload]
        ).stdout.strip()
        src = repo / PM4PY_PATH
        if not src.exists():
            raise DataError(f"{PM4PY_PATH} absent du dépôt pm4py-core.")
        shutil.copyfile(src, dest)
    sha = file_hash(dest)
    return {
        "source": "pm4py-core (copie publique du fichier 4TU)",
        "url": f"{PM4PY_REPO.removesuffix('.git')}/blob/{commit}/{PM4PY_PATH}",
        "commit": commit,
        "sha256": sha,
        "sha256_expected": PM4PY_SHA256,
        "sha256_match": sha == PM4PY_SHA256,
    }


def fetch_local(src: Path, dest: Path) -> dict[str, Any]:
    shutil.copyfile(src, dest)
    return {"source": "copie locale (CPI_LOCAL_SOURCE)", "path": str(src)}


def acquire(force: bool = False, log: Any = print) -> dict[str, Any]:
    """Obtient ``data/raw/bpic2012.xes.gz``, le vérifie et écrit sa provenance."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_LOG.exists() and PROVENANCE_FILE.exists() and not force:
        counts = verify_counts(RAW_LOG)
        log(
            f"Données déjà présentes et vérifiées : {counts.cases} dossiers, "
            f"{counts.events} événements."
        )
        return dict(json.loads(PROVENANCE_FILE.read_text(encoding="utf-8")))

    tmp = RAW_LOG.with_suffix(".part")
    attempts: list[str] = []
    info: dict[str, Any] | None = None
    local = os.environ.get("CPI_LOCAL_SOURCE")
    strategies: list[tuple[str, Any]] = []
    if local:
        strategies.append(("copie locale", lambda: fetch_local(Path(local), tmp)))
    strategies += [
        ("4TU.ResearchData", lambda: fetch_official(tmp)),
        ("pm4py-core", lambda: fetch_pm4py(tmp)),
    ]
    for name, strategy in strategies:
        try:
            log(f"Tentative : {name}…")
            info = strategy()
            break
        except Exception as exc:
            attempts.append(f"{name} : {type(exc).__name__} : {exc}")
            log(f"  échec ({type(exc).__name__}) : {exc}")
            tmp.unlink(missing_ok=True)
    if info is None:
        raise DataError("Aucune source disponible :\n" + "\n".join(attempts))

    counts = verify_counts(tmp)
    tmp.replace(RAW_LOG)
    info.update(
        {
            "dataset": DATASET.name,
            "doi": DATASET.doi_url,
            "terms": DATASET.terms,
            "citation": DATASET.citation,
            "file": RAW_LOG.name,
            "sha256": file_hash(RAW_LOG),
            "cases": counts.cases,
            "events": counts.events,
            "failed_attempts": attempts,
        }
    )
    PROVENANCE_FILE.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"OK : {counts.cases} dossiers, {counts.events} événements ({info['source']}).")
    return info
