"""Typographie française des documents Markdown.

Espace insécable avant « : ; ? ! », à l'intérieur des guillemets « », avant « % » et les
unités, espace fine insécable comme séparateur des milliers (13 087). Le code (blocs et
`en ligne`), les URL et les balises HTML sont laissés intacts. Dans les titres, GitHub retire
les espaces insécables des ancres comme la ponctuation : les liens vers les titres sans
ponctuation ne changent pas.
"""

from __future__ import annotations

import re
from pathlib import Path

NBSP = "\u00a0"
NNBSP = "\u202f"
PROTECT = re.compile(r"(`[^`]*`|\]\([^)]*\)|<[^>]+>|https?://\S+)")
UNITS = r"(%|€|k€|h|j|min|mois|ans)(?![\w])"


def _fix_text(s: str) -> str:
    s = re.sub(r" ([:;?!»])", NBSP + r"\1", s)
    s = s.replace("« ", "«" + NBSP)
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"(?<![\d,.])(\d{1,3}) (\d{3})(?!\d)", r"\1" + NNBSP + r"\2", s)
        s = re.sub(r"(\d) (\d{3})(?=" + NNBSP + r"\d{3})", r"\1" + NNBSP + r"\2", s)
    s = re.sub(r"(\d) " + UNITS, r"\1" + NBSP + r"\2", s)
    s = re.sub(r"(\d" + NBSP + r"h) (\d{2})\b", r"\1" + NBSP + r"\2", s)
    return s


def fix_markdown(text: str) -> str:
    out = []
    in_fence = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence or stripped.startswith("|---"):
            out.append(line)
            continue
        parts = PROTECT.split(line)
        out.append("".join(p if PROTECT.fullmatch(p) else _fix_text(p) for p in parts))
    return "\n".join(out)


def check_files(paths: list[Path], write: bool) -> list[Path]:
    """Retourne les fichiers non conformes (et les corrige si ``write``)."""
    bad = []
    for p in paths:
        text = p.read_text(encoding="utf-8")
        fixed = fix_markdown(text)
        if fixed != text:
            bad.append(p)
            if write:
                p.write_text(fixed, encoding="utf-8")
    return bad
