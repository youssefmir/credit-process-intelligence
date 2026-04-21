"""Interface en ligne de commande : ``python -m cpi <commande>``."""

from __future__ import annotations

import argparse
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


COMMANDS: dict[str, tuple[Callable[[argparse.Namespace], None], str]] = {
    "data": (_cmd_data, "télécharge et vérifie le journal BPI Challenge 2012"),
    "ingest": (_cmd_ingest, "convertit le XES en table Parquet normalisée"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cpi", description="Credit Process Intelligence")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_, help_text) in COMMANDS.items():
        p = sub.add_parser(name, help=help_text)
        if name == "data":
            p.add_argument("--force", action="store_true", help="retélécharger")
    args = parser.parse_args(argv)
    start = time.perf_counter()
    COMMANDS[args.command][0](args)
    print(f"[{args.command}] terminé en {time.perf_counter() - start:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
