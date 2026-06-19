"""Interface en ligne de commande : ``python -m cpi <commande>``."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable


def _cmd_data(args: argparse.Namespace) -> None:
    from cpi.data import acquire

    acquire(force=args.force)


def _cmd_ingest(args: argparse.Namespace) -> None:
    from cpi.ingest import ingest

    df = ingest()
    print(f"Événements ingérés : {len(df):,} ({df['case_id'].nunique():,} dossiers)")


def _cmd_pipeline(args: argparse.Namespace) -> None:
    from cpi.ingest import ingest
    from cpi.pipeline import run

    if args.reingest:
        ingest()
    summary = run(with_docs=not args.no_docs)
    keys = (
        "cases",
        "approved_share",
        "median_lead_time_approved_d",
        "flow_efficiency_approved",
        "model_roc_auc",
        "model_recall_at_20",
    )
    print(json.dumps({k: summary[k] for k in keys}, ensure_ascii=False, indent=2))


def _cmd_docs(args: argparse.Namespace) -> None:
    from cpi.report import render_all

    for path in render_all():
        print(f"Document généré : {path.name}")


def _cmd_bpmn(args: argparse.Namespace) -> None:
    from cpi.bpmn import write_models
    from cpi.report import load_exports

    for path in write_models(load_exports()["summary"]):
        print(f"Modèle BPMN : {path}")


def _cmd_typo(args: argparse.Namespace) -> None:
    from pathlib import Path

    from cpi.config import DOCS_DIR, ROOT
    from cpi.typo import check_files

    paths = [Path(f) for f in args.files] or [ROOT / "README.md", *sorted(DOCS_DIR.glob("*.md"))]
    bad = check_files(paths, write=not args.check)
    for p in bad:
        print(f"{'À corriger' if args.check else 'Corrigé'} : {p.name}")
    if args.check and bad:
        raise SystemExit(1)
    print(f"Typographie : {len(paths)} fichier(s) vérifié(s).")


def _cmd_assistant(args: argparse.Namespace) -> None:
    from cpi.assistant import main

    main(args.case, use_llm=args.llm)


COMMANDS: dict[str, tuple[Callable[[argparse.Namespace], None], str]] = {
    "data": (_cmd_data, "télécharge et vérifie les journaux (BPIC 2012, BPIC 2017 facultatif)"),
    "ingest": (_cmd_ingest, "convertit le XES en table Parquet normalisée"),
    "pipeline": (_cmd_pipeline, "analyse complète et export JSON vers le site"),
    "docs": (_cmd_docs, "régénère les documents chiffrés depuis les exports"),
    "bpmn": (_cmd_bpmn, "régénère les modèles BPMN AS-IS et TO-BE"),
    "typo": (_cmd_typo, "typographie française des documents Markdown"),
    "assistant": (_cmd_assistant, "fiche de pré-analyse d'un dossier (LLM facultatif)"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cpi", description="Credit Process Intelligence")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_, help_text) in COMMANDS.items():
        p = sub.add_parser(name, help=help_text)
        if name == "data":
            p.add_argument("--force", action="store_true", help="retélécharger")
        if name == "pipeline":
            p.add_argument("--reingest", action="store_true", help="relire le XES")
            p.add_argument("--no-docs", action="store_true", help="sans BPMN ni documents")
        if name == "typo":
            p.add_argument("files", nargs="*", help="fichiers (défaut : README et docs)")
            p.add_argument("--check", action="store_true", help="vérifier sans corriger")
        if name == "assistant":
            p.add_argument("case", help="identifiant du dossier (ex. 173688)")
            p.add_argument(
                "--llm",
                action="store_true",
                help="rédaction par un LLM (clé fournie par l'utilisateur)",
            )
    args = parser.parse_args(argv)
    start = time.perf_counter()
    COMMANDS[args.command][0](args)
    print(f"[{args.command}] terminé en {time.perf_counter() - start:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
