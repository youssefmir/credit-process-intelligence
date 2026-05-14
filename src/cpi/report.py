"""Documents générés : les chiffres des documents d'analyse viennent des exports du pipeline.

Les gabarits Jinja2 de ``src/cpi/templates/*.md.j2`` sont rendus dans ``docs/`` à partir des
fichiers JSON de ``site/public/data``. Aucun chiffre n'est saisi à la main : relancer le
pipeline met à jour les documents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from cpi import labels
from cpi.config import DOCS_DIR, SITE_DATA_DIR

TEMPLATES = Path(__file__).parent / "templates"
NBSP = " "  # espace fine insécable (séparateur des milliers)


def fr_num(x: float | int | None, digits: int = 0) -> str:
    """Nombre au format français : 13 087 ; 14,4."""
    if x is None:
        return "n.d."
    s = f"{float(x):,.{digits}f}"
    return s.replace(",", NBSP).replace(".", ",")


def fr_pct(x: float | None, digits: int = 0) -> str:
    if x is None:
        return "n.d."
    return f"{fr_num(100 * float(x), digits)} %"


def fr_eur(x: float | None, digits: int = 0, unit: str = "") -> str:
    """Montant en euros ; ``unit='k'`` pour les milliers d'euros."""
    if x is None:
        return "n.d."
    if unit == "k":
        return f"{fr_num(float(x) / 1000, digits)} k€"
    return f"{fr_num(x, digits)} €"


def fr_days(x: float | None, digits: int = 1) -> str:
    return "n.d." if x is None else f"{fr_num(x, digits)} j"


def load_exports(folder: Path = SITE_DATA_DIR) -> dict[str, Any]:
    return {
        p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))
    }


def environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(
        {"num": fr_num, "pct": fr_pct, "eur": fr_eur, "days": fr_days, "label": labels.label}
    )
    return env


def render_all(out_dir: Path = DOCS_DIR) -> list[Path]:
    data = load_exports()
    env = environment()
    written = []
    for tpl in sorted(TEMPLATES.glob("*.md.j2")):
        text = env.get_template(tpl.name).render(**data)
        path = out_dir / tpl.name.removesuffix(".j2")
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written
