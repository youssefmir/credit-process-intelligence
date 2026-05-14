"""Acquisition reproductible des journaux d'événements.

* **BPI Challenge 2012** (obligatoire) : le processus de demande de crédit étudié ;
* **BPI Challenge 2017 – Offer log** (facultatif) : offres de la même institution en 2016,
  utilisées uniquement pour étalonner une hypothèse du business case (intérêts implicites).

Ordre de tentative pour chaque journal :

1. copie locale explicitement fournie (``CPI_LOCAL_SOURCE`` / ``CPI_LOCAL_SOURCE_2017``) ;
2. téléchargement officiel depuis 4TU.ResearchData (API publique du dépôt) ;
3. repli sur la copie publique du dépôt GitHub ``pm4py/pm4py-core`` (clone superficiel et
   partiel : seul le fichier utile est récupéré).

Chaque fichier est vérifié (empreinte, puis nombre de dossiers et d'événements) et sa
provenance est consignée dans ``data/raw/PROVENANCE-<jeu>.json``.
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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cpi.config import RAW_DIR

PM4PY_REPO = "https://github.com/pm4py/pm4py-core.git"
FOURTU_API = "https://data.4tu.nl/v2/articles/{uuid}/files"
TIMEOUT_S = 30


class DataError(RuntimeError):
    """Erreur d'acquisition ou de vérification des données."""


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    file: str
    doi: str
    citation: str
    fourtu_uuid: str
    official_name: str
    official_md5: str | None
    pm4py_path: str
    pm4py_sha256: str
    expected_cases: int
    expected_events: int
    env_var: str
    required: bool

    @property
    def path(self) -> Path:
        return RAW_DIR / self.file

    @property
    def provenance(self) -> Path:
        return RAW_DIR / f"PROVENANCE-{self.key}.json"


BPIC2012 = Source(
    key="bpic2012",
    title="BPI Challenge 2012",
    file="bpic2012.xes.gz",
    doi="https://doi.org/10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f",
    citation="van Dongen, B. (2012). BPI Challenge 2012. 4TU.ResearchData.",
    fourtu_uuid="533f66a4-8911-4ac7-8612-1235d65d1f37",
    official_name="BPI_Challenge_2012.xes.gz",
    official_md5="74c7ba9aba85bfcb181a22c9d565e5b5",
    pm4py_path="tests/input_data/bpic2012.xes.gz",
    pm4py_sha256="fdc916898cd56f0fb65f0c6c2f69140e6345fe9fc8be2ef1dde0647107db050b",
    expected_cases=13_087,
    expected_events=262_200,
    env_var="CPI_LOCAL_SOURCE",
    required=True,
)

BPIC2017_OFFERS = Source(
    key="bpic2017-offers",
    title="BPI Challenge 2017 - Offer log",
    file="bpic2017-offers.xes.gz",
    doi="https://doi.org/10.4121/uuid:7e326e7e-8b93-4701-8860-71213edf0fbe",
    citation="van Dongen, B. (2017). BPI Challenge 2017 - Offer log. 4TU.ResearchData.",
    fourtu_uuid="cc497753-1175-41f6-a107-425787c54266",
    official_name=".xes.gz",
    official_md5="48f8f345d64620037bcfafe63c1d5f78",
    pm4py_path="tests/compressed_input_data/05_bpic2017.xes.gz",
    pm4py_sha256="",
    expected_cases=42_995,
    expected_events=193_849,
    env_var="CPI_LOCAL_SOURCE_2017",
    required=False,
)

SOURCES = (BPIC2012, BPIC2017_OFFERS)


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


def verify_counts(path: Path, source: Source) -> LogCounts:
    counts = count_xes(path)
    if (counts.cases, counts.events) != (source.expected_cases, source.expected_events):
        raise DataError(
            f"Comptes inattendus pour {path.name} : {counts.cases} dossiers / "
            f"{counts.events} événements (attendu {source.expected_cases} / "
            f"{source.expected_events})."
        )
    return counts


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "credit-process-intelligence"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out)


def fetch_official(source: Source, dest: Path) -> dict[str, Any]:
    """Téléchargement depuis 4TU.ResearchData, contrôlé par l'empreinte MD5 publiée."""
    api = FOURTU_API.format(uuid=source.fourtu_uuid)
    req = urllib.request.Request(api, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        files = json.load(resp)
    match = next((f for f in files if str(f.get("name", "")).endswith(source.official_name)), None)
    if match is None or not match.get("download_url"):
        raise DataError(f"Fichier {source.official_name} introuvable dans l'API 4TU.")
    url = str(match["download_url"])
    _download(url, dest)
    md5 = file_hash(dest, "md5")
    if source.official_md5 and md5 != source.official_md5:
        raise DataError(f"Empreinte MD5 inattendue ({md5}) pour le fichier 4TU.")
    return {"source": "4TU.ResearchData", "url": url, "md5": md5}


def fetch_pm4py(source: Source, dest: Path) -> dict[str, Any]:
    """Repli : clone superficiel et partiel du dépôt public pm4py-core."""
    if shutil.which("git") is None:
        raise DataError("git est requis pour le repli pm4py-core.")
    with tempfile.TemporaryDirectory(prefix="cpi-pm4py-") as tmp:
        repo = Path(tmp) / "pm4py-core"

        def git(*args: str) -> str:
            done = subprocess.run(
                ["git", *args], check=True, capture_output=True, text=True, timeout=600
            )
            return done.stdout.strip()

        git("clone", "--depth", "1", "--filter=blob:none", "--sparse", PM4PY_REPO, str(repo))
        git("-C", str(repo), "sparse-checkout", "set", "--no-cone", source.pm4py_path)
        commit = git("-C", str(repo), "rev-parse", "HEAD")
        src = repo / source.pm4py_path
        if not src.exists():
            raise DataError(f"{source.pm4py_path} absent du dépôt pm4py-core.")
        shutil.copyfile(src, dest)
    info: dict[str, Any] = {
        "source": "pm4py-core (copie publique du fichier 4TU)",
        "url": f"{PM4PY_REPO.removesuffix('.git')}/blob/{commit}/{source.pm4py_path}",
        "commit": commit,
    }
    if source.pm4py_sha256:
        sha = file_hash(dest)
        info["sha256_expected"] = source.pm4py_sha256
        info["sha256_match"] = sha == source.pm4py_sha256
    return info


def fetch_local(src: Path, dest: Path) -> dict[str, Any]:
    shutil.copyfile(src, dest)
    return {"source": "copie locale", "path": src.name}


def acquire_source(
    source: Source, force: bool = False, log: Callable[[str], None] = print
) -> dict[str, Any]:
    """Obtient un journal, le vérifie et écrit sa provenance."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if source.path.exists() and source.provenance.exists() and not force:
        counts = verify_counts(source.path, source)
        log(
            f"{source.title} : déjà présent et vérifié ({counts.cases} dossiers, "
            f"{counts.events} événements)."
        )
        return dict(json.loads(source.provenance.read_text(encoding="utf-8")))

    tmp = source.path.with_suffix(".part")
    attempts: list[str] = []
    info: dict[str, Any] | None = None
    strategies: list[tuple[str, Callable[[], dict[str, Any]]]] = []
    local = os.environ.get(source.env_var)
    if local:
        strategies.append(("copie locale", lambda: fetch_local(Path(local), tmp)))
    strategies += [
        ("4TU.ResearchData", lambda: fetch_official(source, tmp)),
        ("pm4py-core", lambda: fetch_pm4py(source, tmp)),
    ]
    for name, strategy in strategies:
        try:
            log(f"{source.title} — tentative : {name}…")
            info = strategy()
            verify_counts(tmp, source)
            break
        except Exception as exc:
            attempts.append(f"{name} : {type(exc).__name__} : {exc}")
            log(f"  échec ({type(exc).__name__}) : {exc}")
            info = None
            tmp.unlink(missing_ok=True)
    if info is None:
        raise DataError(f"Aucune source disponible pour {source.title} :\n" + "\n".join(attempts))

    counts = verify_counts(tmp, source)
    tmp.replace(source.path)
    info.update(
        {
            "dataset": source.title,
            "doi": source.doi,
            "terms": "4TU General Terms of Use",
            "citation": source.citation,
            "file": source.file,
            "sha256": file_hash(source.path),
            "cases": counts.cases,
            "events": counts.events,
            "failed_attempts": attempts,
        }
    )
    source.provenance.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"  OK : {counts.cases} dossiers, {counts.events} événements ({info['source']}).")
    return info


def acquire(force: bool = False, log: Callable[[str], None] = print) -> dict[str, Any]:
    """Journal 2012 (obligatoire) puis journal des offres 2017 (facultatif)."""
    main = acquire_source(BPIC2012, force=force, log=log)
    try:
        acquire_source(BPIC2017_OFFERS, force=force, log=log)
    except DataError as exc:
        log(f"Journal 2017 indisponible (facultatif, étalonnage ignoré) : {exc}")
    return main


def provenance(source: Source = BPIC2012) -> dict[str, Any] | None:
    if not source.provenance.exists():
        return None
    return dict(json.loads(source.provenance.read_text(encoding="utf-8")))
