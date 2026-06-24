"""Documents générés : les chiffres des documents d'analyse viennent des exports du pipeline.

Les gabarits Jinja2 de ``src/cpi/templates/*.md.j2`` sont rendus dans ``docs/`` à partir des
fichiers JSON de ``site/public/data``. Aucun chiffre n'est saisi à la main : relancer le
pipeline met à jour les documents.
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from cpi import labels
from cpi.config import DOCS_DIR, SITE_DATA_DIR
from cpi.typo import fix_markdown

TEMPLATES = Path(__file__).parent / "templates"
NBSP = "\u202f"  # espace fine insécable (séparateur des milliers)


def fr_num(x: float | int | None, digits: int = 0) -> str:
    """Nombre au format français : 13 087 ; 14,4."""
    if x is None:
        return "n.d."
    # Arrondi décimal « au plus proche, loin de zéro » sur la représentation la plus courte,
    # comme Intl.NumberFormat dans le site : mêmes chiffres partout.
    d = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    s = f"{d:,.{digits}f}"
    s = s.replace(",", NBSP).replace(".", ",")
    return "\u2212" + s[1:] if s.startswith("-") else s


def fr_pct(x: float | None, digits: int = 0) -> str:
    if x is None:
        return "n.d."
    return f"{fr_num(100 * float(x), digits)} %"


def fr_share(x: float | None, compact: bool = False) -> str:
    """Part de tirages : un événement rare mais observé ne s'affiche pas « 0 % » (ni « 100 % »)."""
    if x is None:
        return "n.d."
    if 0 < x < 0.005:
        return ("<\u00a0" if compact else "moins de ") + fr_pct(0.01)
    if 0.995 <= x < 1:
        return (">\u00a0" if compact else "plus de ") + fr_pct(0.99)
    return fr_pct(x)


def fr_eur(x: float | None, digits: int = 0, unit: str = "") -> str:
    """Montant en euros ; ``unit='k'`` pour les milliers d'euros."""
    if x is None:
        return "n.d."
    if unit == "k":
        return f"{fr_num(float(x) / 1000, digits)} k€"
    return f"{fr_num(x, digits)} €"


def fr_days(x: float | None, digits: int = 1) -> str:
    return "n.d." if x is None else f"{fr_num(x, digits)} j"


MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


def fr_date(iso: str) -> str:
    """« 2011-10-01 » → « 1er octobre 2011 »."""
    y, m, d = (int(v) for v in iso[:10].split("-"))
    day = "1er" if d == 1 else str(d)
    return f"{day} {MONTHS[m - 1]} {y}"


def fr_hyp(value: float, unit: str) -> str:
    """Valeur d'hypothèse formatée selon son unité."""
    if unit.startswith("part"):
        return fr_pct(value, 1 if abs(value * 100 - round(value * 100)) > 1e-9 else 0)
    if unit in ("€", "€/an"):
        return fr_eur(value, 0, "k") + ("/an" if unit == "€/an" else "")
    if unit == "€/h":
        return f"{fr_num(value)}\u00a0€/h"
    if unit == "facteur":
        return fr_num(value, 2)
    return fr_num(value)


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
        {
            "num": fr_num,
            "pct": fr_pct,
            "share": fr_share,
            "eur": fr_eur,
            "days": fr_days,
            "frdate": fr_date,
            "hyp": fr_hyp,
            "label": labels.label,
        }
    )
    return env


def render_all(out_dir: Path = DOCS_DIR) -> list[Path]:
    data = load_exports()
    env = environment()
    written = []
    for tpl in sorted(TEMPLATES.glob("*.md.j2")):
        text = fix_markdown(env.get_template(tpl.name).render(**data))
        path = out_dir / tpl.name.removesuffix(".j2")
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written
