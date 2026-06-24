"""Vérifie les liens relatifs (fichiers et ancres) des documents Markdown du dépôt.

    uv run python scripts/check_links.py          # README.md et docs/
    uv run python scripts/check_links.py FICHIER  # fichiers précis

Sortie non nulle si un lien relatif est cassé. Les liens externes (http, https, mailto)
ne sont pas vérifiés : ils demanderaient un accès réseau.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[(?:[^\]\\]|\\.)*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_SRC = re.compile(r"""(?:src|href)=["']([^"']+)["']""")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^(```|~~~)")


def slug(heading: str) -> str:
    """Ancre GitHub : minuscules, ponctuation retirée, espaces en tirets."""
    text = re.sub(r"`|\*|_{2,}|\[|\]\([^)]*\)", "", heading).strip().lower()
    text = unicodedata.normalize("NFC", text)
    out = []
    for ch in text:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch == " ":
            out.append("-")
    return "".join(out)


def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if m:
            base = slug(m.group(2))
            n = counts.get(base, 0)
            found.add(base if n == 0 else f"{base}-{n}")
            counts[base] = n + 1
    found |= set(re.findall(r'<a\s+(?:id|name)="([^"]+)"', path.read_text(encoding="utf-8")))
    return found


def links(path: Path) -> list[str]:
    targets: list[str] = []
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        targets += LINK.findall(line) + HTML_SRC.findall(line)
    return targets


def check(path: Path) -> list[str]:
    errors = []
    for target in links(path):
        if re.match(r"^[a-z]+:", target) or target.startswith("//"):
            continue
        file_part, _, anchor = target.partition("#")
        dest = path if not file_part else (path.parent / file_part).resolve()
        if not dest.exists():
            errors.append(f"{path.relative_to(ROOT)} : fichier introuvable « {target} »")
            continue
        if anchor and dest.suffix == ".md" and anchor not in anchors(dest):
            errors.append(f"{path.relative_to(ROOT)} : ancre introuvable « {target} »")
    return errors


def main(argv: list[str]) -> int:
    files = [Path(a).resolve() for a in argv] or [
        ROOT / "README.md",
        *sorted((ROOT / "docs").glob("*.md")),
    ]
    errors = [e for f in files for e in check(f)]
    for e in errors:
        print(e)
    print(f"{len(files)} fichiers vérifiés, {len(errors)} lien(s) cassé(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
